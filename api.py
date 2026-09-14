"""
FastAPI后端服务 - 非遗知识问答系统API
"""

import asyncio
import logging
from uuid import uuid4
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Header, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import settings
from src.workflow.graph import HeritageWorkflowGraph, get_workflow
from src.workflow.state import QueryRequest, QueryResponse, state_to_response, create_initial_state
from src.workflow.events import WorkflowEventEmitter, build_base_workflow_graph, create_runtime_event
from src.graph.heritage_graph import HeritageKnowledgeGraph
from src.graph.builder import KnowledgeGraphBuilder
from src.retrieval.document_loader import HeritageDocumentLoader
from src.retrieval.retriever import MultiSourceRetriever
from src.knowledge.gap_detector import KnowledgeGapDetector
from src.graph.visualizer import HeritageGraphVisualizer
from src.database import init_db
from src.deps import get_db, get_current_user, get_optional_user, require_admin
from src.models.user import User
from src.schemas.user import (
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    TokenResponse,
)
from src.schemas.chat import (
    ChatHistoryItem,
    ChatHistoryListResponse,
    ChatDetailResponse,
    ChatSessionResponse,
    ChatSessionListResponse,
    ChatSessionMessagesResponse,
)
from src.services.auth import create_user, authenticate_user, create_access_token
from src.services.chat import save_chat_history, get_user_history, get_user_history_count, get_chat_detail
from src.services.evaluation import persist_evaluation
from src.services.feedback import set_feedback
from src.services.agent_configuration import serialize_registered_agents, update_configuration, load_configured_registry
from src.agents.registry import get_default_agent_registry
from src.schemas.feedback import FeedbackRequest, FeedbackResponse
from src.schemas.admin import AgentConfigurationUpdate
from src.services.session_memory import (
    create_session, extract_known_crafts, get_conversation_context,
    get_session_for_user, get_session_turns, list_user_sessions, touch_session,
    update_user_preferences,
)
from src.models.user_preference import UserPreference
from src.services.prompt import create_prompt, get_prompt, list_prompts, update_prompt, delete_prompt
from src.schemas.prompt import PromptCreate, PromptUpdate, PromptResponse, PromptListResponse
from src.services.media import upload_media, list_media, get_media, delete_media, get_media_url, STORAGE_ROOT
from src.schemas.media import MediaResponse, MediaListResponse, MediaUpdateStatus
from src.models.media import MediaDocument, MediaType
from src.models.audio_transcript import AudioTranscript, AudioTranscriptStatus
from src.retrieval.audio_store import get_audio_store
from src.schemas.audio import (
    AudioSearchHit,
    AudioSearchResponse,
    AudioTranscribeEnqueueResponse,
    TranscriptStatusResponse,
)
from src.services.audio_transcript import ensure_audio_job, get_transcript
from src.services.audio_worker import run_worker
from src.services.cache import get_qa_cache
from src.services.queue import close_redis
from src.services.document_parser import parse_document
from src.models.favorite import Favorite
from src.models.platform import AuditLog, CraftEntry, GraphChangeCandidate, InheritorProfile, SourceEvidence
from src.services.graph_curation import merge_approved_candidate
from src.services.platform_content import approve_graph_candidate, make_slug, reject_graph_candidate
from src.services.ai_search import AiSearchService
from src.services.mcp_tools import search_web
from src.retrieval.multimodal_search import search_images_by_text, search_similar_images, index_all_images
from src.utils.llm import set_request_override, clear_request_override

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 全局实例
workflow: Optional[HeritageWorkflowGraph] = None
knowledge_graph: Optional[HeritageKnowledgeGraph] = None
document_loader: Optional[HeritageDocumentLoader] = None
retriever: Optional[MultiSourceRetriever] = None
visualizer: Optional[HeritageGraphVisualizer] = None

# v1.4 音频转写 worker 生命周期句柄（lifespan 启动/停止）
_worker_stop: Optional[asyncio.Event] = None
_worker_task: Optional[asyncio.Task] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global workflow, knowledge_graph, document_loader, retriever, visualizer
    global _worker_stop, _worker_task

    logger.info("初始化应用...")

    # 检查 API Key 配置
    if not settings.deepseek_api_key or "your-" in settings.deepseek_api_key.lower() or settings.deepseek_api_key.startswith("sk-your"):
        logger.warning("=" * 60)
        logger.warning("⚠️  未配置有效的 DeepSeek API Key！")
        logger.warning("   请编辑 .env 文件，将 DEEPSEEK_API_KEY 设为真实值")
        logger.warning("   或在设置页面填写你自己的 API Key")
        logger.warning("   当前 Key: " + (settings.deepseek_api_key[:12] + "..." if settings.deepseek_api_key else "(空)"))
        logger.warning("=" * 60)

    # 初始化数据库表
    init_db()

    # 初始化工作流
    workflow = get_workflow()
    
    # 初始化知识图谱
    knowledge_graph = HeritageKnowledgeGraph()
    if not knowledge_graph.load_from_json():
        # 如果文件不存在，构建初始图谱
        builder = KnowledgeGraphBuilder()
        knowledge_graph = builder.build_initial_graph()
        knowledge_graph.save_to_json()

    from src.services.graph_projection import sync_curated_source_nodes
    sync_curated_source_nodes(knowledge_graph)
    
    # 初始化可视化器
    visualizer = HeritageGraphVisualizer(knowledge_graph)
    
    # 初始化文档加载器
    document_loader = HeritageDocumentLoader()
    
    # 初始化检索器
    retriever = MultiSourceRetriever(document_loader=document_loader)

    # v1.4：初始化热门问答缓存后端（auto：探测 Redis，不可达进程内 LRU）
    await get_qa_cache().init_cache()

    # v1.4：启动音频转写 worker（单 asyncio 任务；Redis 不可达时 run_worker 自检后静默退出）
    if settings.audio_worker_enabled:
        _worker_stop = asyncio.Event()
        _worker_task = asyncio.create_task(run_worker(_worker_stop))
        logger.info("音频转写 worker 任务已创建")

    logger.info("应用初始化完成")

    yield

    logger.info("应用关闭")
    # 停 worker + 关 Redis/缓存后端
    if _worker_task is not None:
        _worker_stop.set()
        try:
            await asyncio.wait_for(_worker_task, timeout=5)
        except Exception:
            logger.warning("转写 worker 未在 5s 内退出，强制取消")
            _worker_task.cancel()
        _worker_task = None
        _worker_stop = None
    get_qa_cache().reset()
    await close_redis()
    logger.info("资源已释放")


# 创建FastAPI应用
app = FastAPI(
    title="HeritageMind — 非遗知识平台 API",
    description="""
## 概述
基于多智能体协作的非遗知识问答与保存平台。

### 功能模块
- **问答**: 三专家 Agent 协作 + 辩论引擎 + 知识缺口检测
- **知识库**: 23 种非遗技艺，55,000 字知识文档
- **知识图谱**: 65 节点交互式可视化
- **多媒体**: 图片/音频上传与存储
- **认证**: JWT 登录注册

### 使用方式
1. 无需认证的端点可直接调用（如 /query、/graph/visualize）
2. 需要认证的端点（🔒）需携带 `Authorization: Bearer <token>`
3. 可通过 `X-API-Key` / `X-Model` header 自定义 LLM 配置
    """,
    version="2.2.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "问答", "description": "非遗知识问答核心接口"},
        {"name": "知识图谱", "description": "知识图谱查询与可视化"},
        {"name": "知识库", "description": "文档管理、分类、上传"},
        {"name": "多媒体", "description": "图片/音频上传与管理"},
        {"name": "认证", "description": "用户注册、登录、Token 管理"},
        {"name": "聊天历史", "description": "问答记录查询（需登录）"},
        {"name": "收藏", "description": "用户收藏管理（需登录）"},
        {"name": "Prompt", "description": "Prompt 模板管理"},
        {"name": "系统", "description": "健康检查、配置等"},
    ],
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# 请求/响应模型
# ============================================================================

class QueryRequest(BaseModel):
    """查询请求"""
    question: str = Field(..., description="用户问题", min_length=1)
    user_profile: str = Field(default="curious", description="用户画像")
    include_narrative: bool = Field(default=False, description="是否使用传承人口吻")
    craft_filter: Optional[str] = Field(default=None, description="技艺过滤")
    session_id: Optional[str] = Field(default=None, description="v1.5 会话ID；登录用户不传时自动创建")


class QueryResponse(BaseModel):
    """查询响应"""
    question: str
    answer: str
    user_profile: str
    source_agents: List[Dict[str, str]]
    has_gaps: bool
    gap_report: str
    reading_time: int
    metadata: Dict[str, Any]


class GraphQueryRequest(BaseModel):
    """知识图谱查询请求"""
    query: str = Field(..., description="查询内容")
    craft_name: Optional[str] = Field(default=None, description="技艺名称")
    relation_type: Optional[str] = Field(default=None, description="关系类型")


class GapReportResponse(BaseModel):
    """缺口报告响应"""
    coverage_level: str
    relevant_documents: int
    coverage_score: float
    gaps: List[Dict[str, Any]]
    can_answer: bool
    suggestions: List[str]


class UserProfileRequest(BaseModel):
    """用户画像切换请求"""
    profile: str = Field(..., description="用户画像类型")


class DocumentUploadResponse(BaseModel):
    """文档上传响应"""
    success: bool
    document_id: str
    message: str


class GraphStatsResponse(BaseModel):
    """图谱统计响应"""
    total_nodes: int
    total_edges: int
    node_types: Dict[str, int]
    edge_types: Dict[str, int]


# ============================================================================
# API端点
# ============================================================================

@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "非遗知识问答系统API",
        "version": "1.0.0",
        "description": "基于多智能体的非遗知识保存与传承平台"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


# ============================================================================
# 问答接口
# ============================================================================

@app.post("/query", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    x_api_base: Optional[str] = Header(None, alias="X-API-Base"),
    x_model: Optional[str] = Header(None, alias="X-Model"),
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """
    非遗知识问答接口

    - **question**: 用户问题
    - **user_profile**: 用户画像 (curious/learner/researcher)

    通过自定义 Header 支持用户自己的 API Key 和模型。
    """
    # Fast-fail: 检查 API Key 是否有效
    effective_key = x_api_key or settings.deepseek_api_key
    if not effective_key or "your-" in effective_key.lower() or "api-key" in effective_key.lower() or effective_key.startswith("sk-your"):
        raise HTTPException(
            status_code=503,
            detail="未配置有效的 API Key。请在设置页填写你的 DeepSeek API Key，或在 .env 中配置 DEEPSEEK_API_KEY。"
        )
    # P1优化：热门问答缓存——命中直接返回，避免重复调用LLM（自定义Header时跳过，因不同Key/模型答案不同）
    # v1.4：后端由 api.py 内联 LRU 迁到 src/services/cache.py 的 QaCache（auto：Redis 可达优先，不可达进程内 LRU）
    # 有会话上下文时相同问题的答案不再等价，禁止跨会话命中热门问答缓存。
    use_cache = settings.cache_enabled and current_user is None and not (x_api_key or x_model or x_api_base)
    if use_cache:
        cached = await get_qa_cache().get_response(request.question)
        if cached is not None:
            logger.info(f"热门问答缓存命中: {request.question[:30]}...")
            return cached
    override_set = bool(x_api_key or x_model)
    try:
        if override_set:
            set_request_override(api_key=x_api_key, base_url=x_api_base, model=x_model)

        logger.info(f"处理问题: {request.question[:50]}...")

        chat_session = None
        conversation_context = ""
        memory_preferences = {}
        if current_user is not None:
            if request.session_id:
                chat_session = get_session_for_user(db, request.session_id, current_user.id)
                if chat_session is None:
                    raise HTTPException(status_code=404, detail="聊天会话不存在")
            else:
                chat_session = create_session(db, current_user.id, request.question)
            try:
                conversation_context = get_conversation_context(db, chat_session.id, current_user.id)
                preference = db.get(UserPreference, current_user.id)
                if preference is not None:
                    memory_preferences = {
                        "preferred_crafts": preference.preferred_crafts or [],
                        "preferred_profile": preference.preferred_profile,
                    }
            except Exception as e:
                logger.warning(f"加载会话记忆失败，降级为空上下文: {e}")

        agent_registry = load_configured_registry(db, get_default_agent_registry())

        response = workflow.query(
            question=request.question,
            user_profile=request.user_profile,
            include_narrative=request.include_narrative,
            thread_id=chat_session.id if chat_session else None,
            conversation_context=conversation_context,
            memory_preferences=memory_preferences,
            agent_registry=agent_registry,
        )

        if chat_session is not None:
            response.metadata = dict(response.metadata or {})
            response.metadata["session_id"] = chat_session.id

        # P1优化：写入热门问答缓存（LRU + TTL）
        if use_cache:
            await get_qa_cache().set_response(request.question, response)

        # 如果用户已登录，自动保存聊天历史
        if current_user is not None:
            try:
                chat = save_chat_history(
                    db=db,
                    user_id=current_user.id,
                    question=request.question,
                    answer=response.answer,
                    user_profile=request.user_profile,
                    agents_used=[a.get("id", "") for a in response.source_agents],
                    has_gaps=response.has_gaps,
                    session_id=chat_session.id,
                )
                evaluation = persist_evaluation(
                    db,
                    chat_id=chat.id,
                    answer=response.answer,
                    citations=response.citations,
                    source_agents=response.source_agents,
                    has_gaps=response.has_gaps,
                    gap_report=response.gap_report,
                    workflow_trace=response.metadata.get("workflow_trace", []),
                )
                touch_session(db, chat_session)
                db.commit()
                response.metadata["chat_id"] = chat.id
                response.metadata["evaluation"] = {
                    "total_score": evaluation.total_score,
                    "rule_version": evaluation.rule_version,
                    "details": evaluation.score_details,
                }
                preference = update_user_preferences(
                    db,
                    current_user.id,
                    extract_known_crafts(request.question, response.answer, request.craft_filter or ""),
                    request.user_profile,
                )
                response.metadata["memory_preferences"] = {
                    "preferred_crafts": preference.preferred_crafts or [],
                    "preferred_profile": preference.preferred_profile,
                }
            except Exception as e:
                logger.warning(f"保存聊天历史失败（不影响问答）: {e}")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"问答处理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # v1.4 顺带修复：请求级 API 覆盖是进程内共享状态，成功/失败都必须清除，防止泄漏到后续请求
        if override_set:
            clear_request_override()


@app.post("/query/stream")
async def query_stream(
    request: QueryRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    x_api_base: Optional[str] = Header(None, alias="X-API-Base"),
    x_model: Optional[str] = Header(None, alias="X-Model"),
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """SSE 流式问答 — 每个步骤实时推送进度"""
    import json as _json

    chat_session = None
    conversation_context = ""
    memory_preferences = {}
    if current_user is not None:
        if request.session_id:
            chat_session = get_session_for_user(db, request.session_id, current_user.id)
            if chat_session is None:
                raise HTTPException(status_code=404, detail="聊天会话不存在")
        else:
            chat_session = create_session(db, current_user.id, request.question)
        try:
            conversation_context = get_conversation_context(db, chat_session.id, current_user.id)
            preference = db.get(UserPreference, current_user.id)
            if preference is not None:
                memory_preferences = {
                    "preferred_crafts": preference.preferred_crafts or [],
                    "preferred_profile": preference.preferred_profile,
                }
        except Exception as e:
            logger.warning(f"加载流式会话记忆失败，降级为空上下文: {e}")

    agent_registry = load_configured_registry(db, get_default_agent_registry())

    async def event_stream():
        override_set = bool(x_api_key and x_api_key.strip())
        try:
            logger.info(f"流式请求 header: X-API-Key={'***' if x_api_key else '(空)'}, X-Model={x_model or '(空)'}")
            if override_set:
                set_request_override(api_key=x_api_key.strip(), base_url=x_api_base, model=x_model)
            elif not settings.deepseek_api_key or 'your-' in settings.deepseek_api_key:
                yield f"data: {_json.dumps({'step': 'error', 'msg': '未配置API Key，请在设置页填写'}, ensure_ascii=False)}\n\n"
                return

            yield f"data: {_json.dumps({'step': 'start', 'msg': '开始分析问题...'}, ensure_ascii=False)}\n\n"

            # v1.8：节点内事件从工作线程安全转入 asyncio 队列，协作消息无需等待整张图结束。
            event_queue: asyncio.Queue = asyncio.Queue()
            loop = asyncio.get_running_loop()
            run_id = uuid4().hex

            def enqueue_runtime_event(event: Dict[str, Any]) -> None:
                loop.call_soon_threadsafe(event_queue.put_nowait, event)

            emitter = WorkflowEventEmitter(run_id, enqueue_runtime_event)
            initial_state = create_initial_state(
                question=request.question,
                user_profile=request.user_profile,
                include_narrative=request.include_narrative,
                thread_id=chat_session.id if chat_session else None,
                conversation_context=conversation_context,
                memory_preferences=memory_preferences,
                runtime_emitter=emitter,
                agent_registry=agent_registry,
            )
            graph_config = {"configurable": {"thread_id": chat_session.id}} if chat_session else None

            step_names = {
                "analyze_question": "分析问题意图...",
                "plan_question": "规划复杂问题子方面...",
                "dispatch_to_experts": "调度专家Agent...",
                "collect_responses": "专家正在检索资料...",
                "fuse_knowledge": "融合多专家观点...",
                "detect_gaps": "检测知识覆盖度...",
                "generate_response": "生成最终回答...",
            }

            emitter.emit(
                "workflow_started",
                step="start",
                msg="开始分析问题",
                payload={"nodes": build_base_workflow_graph()["nodes"], "edges": build_base_workflow_graph()["edges"]},
            )

            def run_workflow() -> Optional[Dict[str, Any]]:
                final_state = None
                for chunk in workflow.graph.stream(initial_state, config=graph_config):
                    for node_name, state_val in chunk.items():
                        final_state = state_val
                        emitter.emit(
                            "node_completed",
                            step=node_name,
                            msg=step_names.get(node_name, node_name),
                        )
                return final_state

            worker = asyncio.create_task(asyncio.to_thread(run_workflow))
            while not worker.done() or not event_queue.empty():
                try:
                    event = await asyncio.wait_for(event_queue.get(), timeout=0.1)
                    yield f"data: {_json.dumps(event, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    continue
            final = await worker

            if final:
                resp = state_to_response(final)
                if current_user is not None and chat_session is not None:
                    try:
                        chat = save_chat_history(
                            db, current_user.id, request.question, resp.answer, request.user_profile,
                            [a.get("id", "") for a in resp.source_agents], resp.has_gaps, chat_session.id,
                        )
                        evaluation = persist_evaluation(
                            db,
                            chat_id=chat.id,
                            answer=resp.answer,
                            citations=resp.citations,
                            source_agents=resp.source_agents,
                            has_gaps=resp.has_gaps,
                            gap_report=resp.gap_report,
                            workflow_trace=resp.metadata.get("workflow_trace", []),
                        )
                        touch_session(db, chat_session)
                        db.commit()
                        update_user_preferences(
                            db, current_user.id,
                            extract_known_crafts(request.question, resp.answer, request.craft_filter or ""),
                            request.user_profile,
                        )
                    except Exception as e:
                        logger.warning(f"保存流式会话记忆失败（不影响响应）: {e}")
                done_event = create_runtime_event(
                    "done",
                    run_id=run_id,
                    step="done",
                    msg="回答生成完成",
                    payload={
                        "answer": resp.answer,
                        "source_agents": resp.source_agents,
                        "has_gaps": resp.has_gaps,
                        "gap_report": resp.gap_report,
                        "session_id": chat_session.id if chat_session else None,
                        "chat_id": chat.id if current_user is not None and chat_session is not None else None,
                        "evaluation": ({"total_score": evaluation.total_score, "rule_version": evaluation.rule_version,
                                        "details": evaluation.score_details}
                                       if current_user is not None and chat_session is not None else None),
                        "workflow_trace": resp.metadata.get("workflow_trace", []),
                        "citations": resp.citations,
                        "collaboration_messages": final.get("collaboration_messages", []) if final else [],
                    },
                )
                yield f"data: {_json.dumps(done_event, ensure_ascii=False)}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: {_json.dumps({'event': 'error', 'step': 'error', 'msg': str(e)}, ensure_ascii=False)}\n\n"

        finally:
            # v1.4 顺带修复：流式请求（含异常 / 客户端中断提前关闭生成器）结束后清除请求级 API 覆盖
            if override_set:
                clear_request_override()

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/query/simple")
async def simple_query(
    question: str = Form(...),
    user_profile: str = Form("curious"),
    include_narrative: bool = Form(False)
):
    """
    简化版问答接口（表单提交）
    """
    try:
        response = workflow.query(
            question=question,
            user_profile=user_profile,
            include_narrative=include_narrative
        )
        
        return response
        
    except Exception as e:
        logger.error(f"问答处理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 文档上传接口
# ============================================================================

@app.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    craft_id: str = Form(...),
    file: UploadFile = File(...)
):
    """
    上传非遗文档
    
    - **craft_id**: 技艺ID
    - **file**: 文档文件（支持txt, md, json）
    """
    try:
        # 检查文件类型
        allowed_types = ["text/plain", "text/markdown", "application/json"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {file.content_type}"
            )
        
        # 读取内容
        content = await file.read()
        text_content = content.decode("utf-8")
        
        # 保存文档
        success = document_loader.add_document(craft_id, text_content)
        
        if success:
            # 重新加载检索器
            global retriever
            retriever = MultiSourceRetriever(document_loader=document_loader)
            
            return DocumentUploadResponse(
                success=True,
                document_id=craft_id,
                message=f"文档 {craft_id} 上传成功"
            )
        else:
            return DocumentUploadResponse(
                success=False,
                document_id=craft_id,
                message="文档保存失败"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文档上传失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 知识图谱接口
# ============================================================================

@app.get("/graph/stats", response_model=GraphStatsResponse)
async def get_graph_stats(db: Session = Depends(get_db)):
    """获取知识图谱统计信息"""
    try:
        from src.services.graph_projection import sync_curated_source_nodes, sync_published_platform_nodes
        sync_published_platform_nodes(db, knowledge_graph)
        sync_curated_source_nodes(knowledge_graph)
        stats = knowledge_graph.get_statistics()
        return GraphStatsResponse(**stats)
    except Exception as e:
        logger.error(f"获取图谱统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph/visualize")
async def visualize_graph(
    filter_type: Optional[str] = None,
    layout: str = "force",
    db: Session = Depends(get_db),
):
    """
    获取交互式图谱HTML
    
    - **filter_type**: 节点类型过滤（可选）
    - **layout**: 布局类型 ("force", "random", "circular")
    """
    try:
        if visualizer is None:
            raise HTTPException(status_code=503, detail="可视化器未初始化")
        from src.services.graph_projection import sync_curated_source_nodes, sync_published_platform_nodes
        sync_published_platform_nodes(db, knowledge_graph)
        sync_curated_source_nodes(knowledge_graph)
        
        html = visualizer.render_interactive(
            filter_type=filter_type,
            layout=layout
        )
        
        return {"html": html}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"图谱可视化失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph/subgraph/{craft_name}")
async def get_subgraph(craft_name: str, depth: int = 1):
    """
    获取技艺的子图
    
    - **craft_name**: 技艺名称
    - **depth**: 扩展深度
    """
    try:
        subgraph = knowledge_graph.get_subgraph(craft_name, depth)
        return subgraph
    except Exception as e:
        logger.error(f"获取子图失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 缺口报告接口
# ============================================================================

@app.get("/gap-report")
async def get_gap_report(question: str):
    """获取问题对应的知识缺口报告"""
    try:
        gap_detector = KnowledgeGapDetector()
        docs = retriever.retrieve(question, top_k=5)
        result = gap_detector.detect(question, docs)
        
        return {
            "coverage_level": result.coverage_level,
            "relevant_documents": result.relevant_documents,
            "coverage_score": result.coverage_score,
            "gaps": [
                {
                    "aspect": g.aspect,
                    "description": g.description,
                    "suggestion": g.suggestion
                }
                for g in result.identified_gaps
            ],
            "can_answer": result.can_answer,
            "suggestions": gap_detector.get_supplementary_queries(question, result),
            "report": gap_detector.generate_gap_report(question, result)
        }
        
    except Exception as e:
        logger.error(f"获取缺口报告失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 用户画像接口
# ============================================================================

@app.post("/switch-profile")
async def switch_profile(request: UserProfileRequest):
    """切换用户画像"""
    valid_profiles = ["curious", "learner", "researcher"]
    
    if request.profile not in valid_profiles:
        raise HTTPException(
            status_code=400,
            detail=f"无效的用户画像，有效值: {valid_profiles}"
        )
    
    return {
        "success": True,
        "profile": request.profile,
        "message": f"已切换到{request.profile}画像"
    }


# ============================================================================
# 技艺列表接口
# ============================================================================

@app.get("/crafts")
async def list_crafts():
    """获取支持的技艺列表"""
    return {
        "crafts": [
            {"id": "jingtailan", "name": "景泰蓝"},
            {"id": "suxiu", "name": "苏绣"},
            {"id": "longquan_ci", "name": "龙泉青瓷"},
            {"id": "yixing_zisha", "name": "宜兴紫砂"},
            {"id": "wuhu_tiehua", "name": "芜湖铁画"},
            {"id": "shujin", "name": "蜀锦"},
            {"id": "jianzhi", "name": "剪纸"},
            {"id": "jingdezhen_ciqi", "name": "景德镇瓷器"},
            {"id": "nanjing_yunjin", "name": "南京云锦"},
            {"id": "dongyang_mudiao", "name": "东阳木雕"},
            {"id": "miaozu_laran", "name": "苗族蜡染"},
            {"id": "muban_nianhua", "name": "木版年画"},
            {"id": "kesi", "name": "缂丝"},
            {"id": "zhubian", "name": "竹编"},
            {"id": "yudiao", "name": "玉雕"},
            {"id": "qiqi", "name": "漆器"},
            {"id": "tangsancai", "name": "唐三彩"},
            {"id": "junci", "name": "钧瓷"},
            {"id": "ruci", "name": "汝瓷"},
            {"id": "nirenzhang", "name": "泥人张"},
            {"id": "piyingxi", "name": "皮影戏"},
            {"id": "zhuangjin", "name": "壮锦"},
            {"id": "jingju", "name": "京剧"},
        ]
    }


@app.get("/profiles")
async def list_profiles():
    """获取用户画像列表"""
    return {
        "profiles": [
            {
                "id": "curious",
                "name": "好奇者",
                "description": "对非遗技艺有初步兴趣，想要了解基本情况",
                "depth": "浅层"
            },
            {
                "id": "learner",
                "name": "学习者",
                "description": "想要深入学习非遗技艺，具备一定基础",
                "depth": "中层"
            },
            {
                "id": "researcher",
                "name": "研究者",
                "description": "需要深度资料用于学术研究或专业创作",
                "depth": "深层"
            }
        ]
    }


# ============================================================================
# 服务器配置接口
# ============================================================================

class ServerConfigResponse(BaseModel):
    """服务器默认LLM配置"""
    model: str
    base_url: str
    provider: str


@app.get("/config")
async def get_server_config():
    """
    获取服务器默认 LLM 配置。

    前端据此显示——用户不填 API Key 时，默认使用服务器配置。
    """
    model = settings.deepseek_model
    base = settings.deepseek_base_url

    # 根据 base_url 推断 provider
    provider = "DeepSeek"
    if "openai.com" in base:
        provider = "OpenAI"
    elif "dashscope" in base:
        provider = "Qwen (通义千问)"
    elif "anthropic" in base:
        provider = "Claude"

    return ServerConfigResponse(
        model=model,
        base_url=base,
        provider=provider,
    )


# ============================================================================
# 文档统计接口
# ============================================================================

@app.get("/documents/summary")
async def get_document_summary():
    """获取文档库摘要"""
    try:
        summary = document_loader.get_document_summary()
        return summary
    except Exception as e:
        logger.error(f"获取文档摘要失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Prompt 管理接口
# ============================================================================

@app.get("/prompts", response_model=PromptListResponse)
async def list_prompt_templates(limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    """获取 Prompt 模板列表"""
    items, total = list_prompts(db, limit, offset)
    return PromptListResponse(
        items=[PromptResponse.model_validate(p) for p in items],
        total=total,
    )


@app.post("/prompts", response_model=PromptResponse)
async def create_prompt_template(data: PromptCreate, db: Session = Depends(get_db)):
    """创建 Prompt 模板"""
    existing = await _get_prompt_by_name_safe(db, data.name)
    if existing:
        raise HTTPException(status_code=409, detail=f"Prompt '{data.name}' 已存在")
    return PromptResponse.model_validate(create_prompt(db, data))


@app.get("/prompts/{prompt_id}", response_model=PromptResponse)
async def get_prompt_template(prompt_id: int, db: Session = Depends(get_db)):
    """获取单个 Prompt 模板"""
    prompt = get_prompt(db, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt 不存在")
    return PromptResponse.model_validate(prompt)


@app.put("/prompts/{prompt_id}", response_model=PromptResponse)
async def update_prompt_template(prompt_id: int, data: PromptUpdate, db: Session = Depends(get_db)):
    """更新 Prompt 模板（自动递增版本号）"""
    prompt = update_prompt(db, prompt_id, data)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt 不存在")
    return PromptResponse.model_validate(prompt)


@app.delete("/prompts/{prompt_id}")
async def delete_prompt_template(prompt_id: int, db: Session = Depends(get_db)):
    """删除 Prompt 模板"""
    ok = delete_prompt(db, prompt_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Prompt 不存在")
    return {"success": True}


async def _get_prompt_by_name_safe(db: Session, name: str):
    """安全查询：避免同步调用在 async 上下文报错"""
    from src.services.prompt import get_prompt_by_name
    return get_prompt_by_name(db, name)


# ============================================================================
# 多媒体接口
# ============================================================================

@app.post("/media/upload", response_model=MediaResponse)
async def upload_media_file(
    file: UploadFile = File(...),
    craft_name: str = Form(...),
    media_type: str = Form("image"),
    title: str = Form(""),
    db: Session = Depends(get_db),
):
    """上传图片或音频文件"""
    if file.content_type is None:
        raise HTTPException(status_code=400, detail="无法识别文件类型")
    doc = upload_media(db=db, file=file.file, original_name=file.filename or "unknown",
                       mime_type=file.content_type, craft_name=craft_name,
                       media_type=media_type, title=title)
    resp = MediaResponse.model_validate(doc)
    resp.url = get_media_url(doc)
    # v1.4：audio 上传自动入队转写（不阻断上传；入队失败仅 warning，worker sweep 兜底）
    if media_type == MediaType.AUDIO.value and settings.audio_transcribe_enabled:
        try:
            tr = await ensure_audio_job(db, doc.id, craft_name)
            resp.transcript_status = tr.status
            resp.transcript_updated_at = tr.updated_at
        except Exception as e:
            logger.warning(f"音频自动转写入队失败（不影响上传）media_id={doc.id}: {e}")
    return resp


@app.get("/media/list", response_model=MediaListResponse)
async def list_media_files(craft_name: Optional[str] = None, media_type: Optional[str] = None,
                           limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    """列出媒体文件"""
    items, total = list_media(db, craft_name, media_type, limit, offset)
    result = []
    for item in items:
        r = MediaResponse.model_validate(item); r.url = get_media_url(item); result.append(r)
    return MediaListResponse(items=result, total=total)


@app.get("/media/{media_id}", response_model=MediaResponse)
async def get_media_file(media_id: int, db: Session = Depends(get_db)):
    doc = get_media(db, media_id)
    if not doc: raise HTTPException(status_code=404, detail="文件不存在")
    resp = MediaResponse.model_validate(doc); resp.url = get_media_url(doc); return resp


@app.delete("/media/{media_id}")
async def delete_media_item(media_id: int, db: Session = Depends(get_db)):
    ok = delete_media(db, media_id)
    if not ok:
        raise HTTPException(status_code=404, detail="文件不存在")
    return {"success": True}


@app.put("/media/{media_id}/status")
async def update_media_status(media_id: int, body: MediaUpdateStatus, db: Session = Depends(get_db)):
    doc = get_media(db, media_id)
    if not doc: raise HTTPException(status_code=404, detail="文件不存在")
    doc.status = body.status
    db.commit()
    return {"id": media_id, "status": body.status}

@app.post("/knowledge/rebuild-embeddings")
async def rebuild_embeddings(db: Session = Depends(get_db)):
    from src.retrieval.embeddings import EmbeddingManager, reset_embedding_model
    reset_embedding_model()
    global retriever
    r = MultiSourceRetriever(document_loader=document_loader)
    r.build_index()
    retriever = r
    return {"message": "向量索引已重建", "documents": len(r.documents)}
async def delete_media_file(media_id: int, db: Session = Depends(get_db)):
    ok = delete_media(db, media_id)
    if not ok: raise HTTPException(status_code=404, detail="文件不存在")
    return {"success": True}


@app.get("/media/file/{media_type}/{filename}")
async def serve_media_file(media_type: str, filename: str):
    file_path = STORAGE_ROOT / media_type / filename
    if not file_path.exists(): raise HTTPException(status_code=404, detail="文件不存在")
    from fastapi.responses import FileResponse
    return FileResponse(str(file_path))


# ============================================================================
# 多模态检索接口
# ============================================================================

@app.get("/search/image")
async def search_image_by_text(q: str, top_k: int = 6, db: Session = Depends(get_db)):
    """文搜图：用文字描述搜索已上传的图片"""
    results = search_images_by_text(db, q, top_k)
    return {"query": q, "results": results, "total": len(results)}


@app.post("/search/similar")
async def search_similar_image(file: UploadFile = File(...), top_k: int = 6,
                               db: Session = Depends(get_db)):
    """以图搜图：上传图片搜索相似图片"""
    content = await file.read()
    results = search_similar_images(db, content, top_k)
    return {"results": results, "total": len(results)}


@app.post("/search/index-images")
async def rebuild_image_index(db: Session = Depends(get_db)):
    """重建图片向量索引"""
    count = index_all_images(db)
    return {"indexed": count, "message": f"已索引 {count} 张图片"}


# ============================================================================
# 音频转写与检索接口（v1.4）
# ============================================================================

def _to_transcript_status(media_id: int, tr: Optional[AudioTranscript]) -> TranscriptStatusResponse:
    """sidecar 行 → 状态响应（无行时 status='none'，便于前端轮询）。"""
    if tr is None:
        return TranscriptStatusResponse(media_id=media_id, status="none")
    return TranscriptStatusResponse(
        media_id=media_id,
        status=tr.status,
        craft_name=tr.craft_name,
        attempts=tr.attempts,
        language=tr.language,
        duration_ms=tr.duration_ms,
        chunk_count=tr.chunk_count,
        error=tr.error,
        created_at=tr.created_at,
        updated_at=tr.updated_at,
    )


@app.get("/media/{media_id}/transcript", response_model=TranscriptStatusResponse)
async def get_media_transcript(media_id: int, db: Session = Depends(get_db)):
    """查询音频转写状态（上传后轮询 UPLOADED→TRANSCRIBING→INDEXED/FAILED）。无记录返回 status=none。"""
    return _to_transcript_status(media_id, get_transcript(db, media_id))


@app.post("/media/{media_id}/transcribe", response_model=AudioTranscribeEnqueueResponse)
async def enqueue_media_transcribe(media_id: int, db: Session = Depends(get_db)):
    """手动触发/重试转写：无记录→建 sidecar 入队；UPLOADED/FAILED→复位入队；转写中/已完成→409。"""
    from src.services.queue import push_audio_job

    doc = get_media(db, media_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文件不存在")

    tr = get_transcript(db, media_id)
    if tr is None:
        tr = await ensure_audio_job(db, media_id, doc.craft_name)
        return AudioTranscribeEnqueueResponse(
            media_id=media_id, status=tr.status, enqueued=True, detail="已新建转写任务并入队"
        )
    if tr.status == AudioTranscriptStatus.TRANSCRIBING.value:
        raise HTTPException(status_code=409, detail="正在转写中，请稍候")
    if tr.status == AudioTranscriptStatus.INDEXED.value:
        raise HTTPException(status_code=409, detail="已完成转写（如需重转写请先删除该媒体）")
    if tr.attempts >= settings.audio_max_attempts:
        raise HTTPException(status_code=409, detail=f"已达最大尝试次数({settings.audio_max_attempts})，需人工处理")

    # UPLOADED/FAILED → 复位 UPLOADED 并（重）入队
    tr.status = AudioTranscriptStatus.UPLOADED.value
    tr.error = None
    db.commit()
    ok = await push_audio_job(media_id)
    return AudioTranscribeEnqueueResponse(
        media_id=media_id, status=tr.status, enqueued=ok,
        detail="已复位并入队" if ok else "入队失败（保持 UPLOADED，worker 启动 sweep 兜底）",
    )


@app.get("/search/audio", response_model=AudioSearchResponse)
async def search_audio(
    q: str,
    top_k: int = 10,
    craft_name: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """文搜音频：按文字命中已转写音频（转写文本向量检索，逐 media 取最佳 chunk）。

    与 /search/image 风格一致：命中后回连 media_documents 带出 url/title/审核状态。
    """
    query = (q or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="搜索词 q 不能为空")
    hits = get_audio_store().search(query, top_k=top_k, craft_name=craft_name)
    if not hits:
        return AudioSearchResponse(query=q, top_k=top_k, total=0, results=[])

    # 按 media_id 聚合成一条（同 media 保留 score 最高的 chunk）
    best: Dict[int, dict] = {}
    for h in hits:
        cur = best.get(h["media_id"])
        if cur is None or h["score"] > cur["score"]:
            best[h["media_id"]] = h
    media_map = {
        d.id: d for d in db.scalars(select(MediaDocument).where(MediaDocument.id.in_(list(best)))).all()
    }
    results: List[AudioSearchHit] = []
    for h in best.values():
        d = media_map.get(h["media_id"])
        results.append(AudioSearchHit(
            media_id=h["media_id"],
            craft_name=h["craft_name"],
            title=d.title if d else h["title"],
            original_name=d.original_name if d else "",
            url=get_media_url(d) if d else "",
            snippet=h["snippet"],
            score=h["score"],
            media_status=d.status if d else "draft",
        ))
    results.sort(key=lambda r: r.score, reverse=True)
    return AudioSearchResponse(query=q, top_k=top_k, total=len(results), results=results)


@app.post("/search/audio/index")
async def rebuild_audio_index(db: Session = Depends(get_db)):
    """重建音频转写向量索引：遍历 status=INDEXED 的 sidecar，用其 full_text 全量重放。"""
    rows = db.scalars(
        select(AudioTranscript).where(AudioTranscript.status == AudioTranscriptStatus.INDEXED.value)
    ).all()
    store = get_audio_store()
    total_chunks = 0
    for tr in rows:
        doc = get_media(db, tr.media_id)
        title = doc.title if doc else ""
        chunks = store.index_transcript(tr.media_id, tr.craft_name, title, tr.full_text or "")
        total_chunks += chunks
    return {"indexed": len(rows), "chunks": total_chunks, "message": f"已重建 {len(rows)} 条音频转写索引"}


# ============================================================================
# 收藏接口
# ============================================================================

@app.post("/favorites")
async def add_favorite(craft_name: str = Form(...), chat_id: Optional[int] = Form(None),
                       note: str = Form(""), current_user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    fav = Favorite(user_id=current_user.id, craft_name=craft_name, chat_id=chat_id, note=note)
    db.add(fav); db.commit(); db.refresh(fav)
    return {"id": fav.id, "craft_name": fav.craft_name, "created_at": fav.created_at.isoformat()}


@app.get("/favorites")
async def list_favorites(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    favs = db.scalars(
        select(Favorite).where(Favorite.user_id == current_user.id).order_by(Favorite.created_at.desc())
    ).all()
    return {"items": [{"id": f.id, "craft_name": f.craft_name, "chat_id": f.chat_id,
                        "note": f.note, "created_at": f.created_at.isoformat()} for f in favs]}


@app.delete("/favorites/{fav_id}")
async def remove_favorite(fav_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    fav = db.get(Favorite, fav_id)
    if not fav or fav.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="收藏不存在")
    db.delete(fav); db.commit()
    return {"success": True}


# ============================================================================
# 文档解析上传接口
# ============================================================================

KNOWLEDGE_CATEGORIES = ["陶瓷", "织绣", "雕刻", "金属工艺", "纸艺版画", "戏曲", "印染", "编织", "漆艺", "彩塑"]


@app.get("/knowledge/categories")
async def list_categories():
    """知识库分类列表"""
    cats = []
    for cat in KNOWLEDGE_CATEGORIES:
        crafts_in_cat = [c["name"] for c in _get_craft_list() if _craft_category(c["name"]) == cat]
        cats.append({"name": cat, "crafts": crafts_in_cat, "count": len(crafts_in_cat)})
    return {"categories": cats}


def _craft_category(name: str) -> str:
    mapping = {
        "景泰蓝": "金属工艺", "芜湖铁画": "金属工艺",
        "苏绣": "织绣", "蜀锦": "织绣", "南京云锦": "织绣", "缂丝": "织绣", "壮锦": "织绣",
        "龙泉青瓷": "陶瓷", "景德镇瓷器": "陶瓷", "宜兴紫砂": "陶瓷", "唐三彩": "陶瓷", "钧瓷": "陶瓷", "汝瓷": "陶瓷",
        "东阳木雕": "雕刻", "玉雕": "雕刻",
        "剪纸": "纸艺版画", "木版年画": "纸艺版画",
        "京剧": "戏曲", "皮影戏": "戏曲",
        "苗族蜡染": "印染",
        "竹编": "编织",
        "漆器": "漆艺",
        "泥人张": "彩塑",
    }
    return mapping.get(name, "其他")


def _get_craft_list():
    return [
        {"id": "jingtailan", "name": "景泰蓝"}, {"id": "suxiu", "name": "苏绣"},
        {"id": "longquan_ci", "name": "龙泉青瓷"}, {"id": "yixing_zisha", "name": "宜兴紫砂"},
        {"id": "wuhu_tiehua", "name": "芜湖铁画"}, {"id": "shujin", "name": "蜀锦"},
        {"id": "jianzhi", "name": "剪纸"}, {"id": "jingdezhen_ciqi", "name": "景德镇瓷器"},
        {"id": "nanjing_yunjin", "name": "南京云锦"}, {"id": "dongyang_mudiao", "name": "东阳木雕"},
        {"id": "miaozu_laran", "name": "苗族蜡染"}, {"id": "muban_nianhua", "name": "木版年画"},
        {"id": "kesi", "name": "缂丝"}, {"id": "zhubian", "name": "竹编"},
        {"id": "yudiao", "name": "玉雕"}, {"id": "qiqi", "name": "漆器"},
        {"id": "tangsancai", "name": "唐三彩"}, {"id": "junci", "name": "钧瓷"},
        {"id": "ruci", "name": "汝瓷"}, {"id": "nirenzhang", "name": "泥人张"},
        {"id": "piyingxi", "name": "皮影戏"}, {"id": "zhuangjin", "name": "壮锦"},
        {"id": "jingju", "name": "京剧"},
    ]


@app.post("/documents/upload")
async def upload_document(file: UploadFile = File(...), craft_name: str = Form(...),
                          db: Session = Depends(get_db)):
    """上传文档（PDF/Word/Markdown/TXT），自动解析文本"""
    if not file.filename or not file.content_type:
        raise HTTPException(status_code=400, detail="无效文件")
    content = await file.read()
    text = parse_document(content, file.filename, file.content_type)
    if not text:
        raise HTTPException(status_code=400, detail="无法解析此文件格式")
    # 保存为 txt 到知识库
    import os
    docs_dir = Path(settings.crafts_doc_path)
    docs_dir.mkdir(parents=True, exist_ok=True)
    safe_name = craft_name + "_upload.txt"
    file_path = docs_dir / safe_name
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"{craft_name}\n\n{text}")
    logger.info(f"文档已解析保存: {safe_name} ({len(text)} 字)")
    return {"filename": safe_name, "craft_name": craft_name, "length": len(text),
            "message": "文档已解析并加入知识库，重启后端后生效"}


# ============================================================================
# 认证接口
# ============================================================================

@app.post("/auth/register", response_model=TokenResponse)
async def register(request: UserRegisterRequest, db: Session = Depends(get_db)):
    """
    用户注册

    - **username**: 用户名（2-50字符）
    - **email**: 邮箱
    - **password**: 密码（最少6位）
    """
    user, error = create_user(db, request.username, request.email, request.password)
    if error:
        raise HTTPException(status_code=400, detail=error)

    token = create_access_token(user.id, user.username)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            created_at=user.created_at,
        ),
    )


@app.post("/auth/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    用户登录（OAuth2密码流）

    使用表单格式提交 username 和 password，
    返回 JWT access_token。
    """
    user, error = authenticate_user(db, form_data.username, form_data.password)
    if error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error,
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(user.id, user.username)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            created_at=user.created_at,
        ),
    )


@app.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    获取当前登录用户信息（需认证）。

    在请求头中携带: Authorization: Bearer <token>
    """
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
        created_at=current_user.created_at,
    )


# ============================================================================
# 聊天历史接口
# ============================================================================

@app.get("/chat/history", response_model=ChatHistoryListResponse)
async def get_chat_history(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取当前用户的聊天历史（需认证）。

    - **limit**: 每页条数（默认20）
    - **offset**: 偏移量
    """
    records = get_user_history(db, current_user.id, limit=limit, offset=offset)
    total = get_user_history_count(db, current_user.id)

    items = []
    for r in records:
        # 截取前100字作为预览
        question_preview = r.question[:100] + "..." if len(r.question) > 100 else r.question
        answer_preview = r.answer[:100] + "..." if len(r.answer) > 100 else r.answer

        items.append(ChatHistoryItem(
            id=r.id,
            question=question_preview,
            answer_preview=answer_preview,
            user_profile=r.user_profile,
            agents_used=r.agents_used,
            has_gaps=r.has_gaps,
            created_at=r.created_at,
        ))

    return ChatHistoryListResponse(items=items, total=total)


@app.get("/chat/sessions", response_model=ChatSessionListResponse)
async def get_chat_sessions(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """按最近活跃时间列出当前用户可继续的对话。"""
    records = list_user_sessions(db, current_user.id, limit=limit)
    return ChatSessionListResponse(items=[ChatSessionResponse.model_validate(row) for row in records])


@app.post("/chat/sessions", response_model=ChatSessionResponse)
async def create_chat_session(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建空白会话；首轮问答仍会在 /query 自动创建会话。"""
    chat_session = create_session(db, current_user.id)
    return ChatSessionResponse.model_validate(chat_session)


@app.get("/chat/sessions/{session_id}/messages", response_model=ChatSessionMessagesResponse)
async def get_chat_session_messages(
    session_id: str,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """分页读取本人某一会话的完整问答轮次，越权会话按不存在处理。"""
    if get_session_for_user(db, session_id, current_user.id) is None:
        raise HTTPException(status_code=404, detail="聊天会话不存在")
    records = get_session_turns(db, session_id, current_user.id, limit=limit, offset=offset)
    return ChatSessionMessagesResponse(
        items=[ChatDetailResponse.model_validate(row) for row in records], total=len(records)
    )


@app.get("/chat/history/{chat_id}", response_model=ChatDetailResponse)
async def get_chat_detail_endpoint(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取单条聊天详情（需认证，仅限查看自己的记录）。
    """
    record = get_chat_detail(db, chat_id, current_user.id)
    if record is None:
        raise HTTPException(status_code=404, detail="聊天记录不存在")

    return ChatDetailResponse(
        id=record.id,
        question=record.question,
        answer=record.answer,
        user_profile=record.user_profile,
        agents_used=record.agents_used,
        has_gaps=record.has_gaps,
        created_at=record.created_at,
    )


# ============================================================================
# v1.8 回答反馈与 Agent 管理
# ============================================================================

@app.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create, replace or cancel the caller's one feedback record for an owned answer."""
    try:
        feedback = set_feedback(
            db,
            user_id=current_user.id,
            chat_id=request.chat_id,
            sentiment=request.sentiment,
            comment=request.comment,
        )
        db.commit()
    except ValueError as error:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(error))
    return FeedbackResponse(
        chat_id=request.chat_id,
        sentiment=feedback.sentiment if feedback else None,
        comment=feedback.comment if feedback else None,
    )


@app.get("/admin/agents")
async def list_admin_agents(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List the fixed built-in Agent set and its safe data overrides."""
    return {"items": serialize_registered_agents(db, get_default_agent_registry())}


@app.get("/admin/evaluations")
async def list_admin_evaluations(
    limit: int = 30,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Return recent explainable evaluation records for operational review."""
    from src.models.chat import ChatHistory
    from src.models.evaluation import AnswerEvaluation

    rows = db.query(AnswerEvaluation, ChatHistory).join(ChatHistory, AnswerEvaluation.chat_id == ChatHistory.id).order_by(
        AnswerEvaluation.created_at.desc()
    ).limit(min(max(limit, 1), 100)).all()
    return {"items": [{
        "chat_id": evaluation.chat_id, "score": evaluation.total_score, "rule_version": evaluation.rule_version,
        "details": evaluation.score_details, "question": chat.question, "answer": chat.answer,
        "has_gaps": chat.has_gaps, "created_at": evaluation.created_at,
    } for evaluation, chat in rows]}


@app.get("/admin/feedback")
async def list_admin_feedback(
    limit: int = 30,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Return recent feedback with its answer context, without credentials or prompts."""
    from src.models.chat import ChatHistory
    from src.models.feedback import UserFeedback

    rows = db.query(UserFeedback, ChatHistory).join(ChatHistory, UserFeedback.chat_id == ChatHistory.id).order_by(
        UserFeedback.updated_at.desc()
    ).limit(min(max(limit, 1), 100)).all()
    return {"items": [{
        "id": feedback.id, "chat_id": feedback.chat_id, "sentiment": feedback.sentiment,
        "comment": feedback.comment, "question": chat.question, "answer": chat.answer,
        "updated_at": feedback.updated_at,
    } for feedback, chat in rows]}


@app.patch("/admin/agents/{agent_id}")
async def update_admin_agent(
    agent_id: str,
    request: AgentConfigurationUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update safe metadata/configuration for a registered Agent only."""
    try:
        row = update_configuration(
            db,
            agent_id=agent_id,
            values=request.model_dump(),
            updated_by_user_id=current_user.id,
            default_registry=get_default_agent_registry(),
        )
        db.commit()
    except ValueError as error:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(error))
    return {
        "agent_id": row.agent_id,
        "enabled": row.enabled,
        "display_name": row.display_name,
        "capability": row.capability,
        "collaboration_priority": row.collaboration_priority,
        "parameters": row.parameters or {},
    }


@app.delete("/admin/agents/{agent_id}/override")
async def reset_admin_agent_override(
    agent_id: str,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete a persisted override so the built-in Agent definition is restored."""
    from src.models.agent_configuration import AgentConfiguration

    row = db.query(AgentConfiguration).filter(AgentConfiguration.agent_id == agent_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Agent 配置覆盖不存在")
    db.delete(row)
    db.commit()
    return {"agent_id": agent_id, "reset": True}


# ============================================================================
# v2.0 公开百科、传承人档案与图谱候选审核
# ============================================================================

def _serialize_inheritor(row: InheritorProfile, db: Session) -> Dict[str, Any]:
    sources = db.query(SourceEvidence).filter(
        SourceEvidence.subject_type == "inheritor", SourceEvidence.subject_id == row.id
    ).all()
    return {
        "id": row.id, "name": row.name, "slug": row.slug, "craft_name": row.craft_name,
        "region": row.region, "recognition": row.recognition, "biography": row.biography,
        "lineage": row.lineage, "representative_works": row.representative_works, "status": row.status,
        "sources": [{"name": item.source_name, "url": item.source_url, "evidence": item.evidence_text} for item in sources],
    }


@app.get("/encyclopedia")
async def list_encyclopedia(db: Session = Depends(get_db)):
    """List only published craft entries for the public encyclopedia."""
    rows = db.query(CraftEntry).filter(CraftEntry.status == "published").order_by(CraftEntry.name).all()
    return {"items": [{"name": row.name, "slug": row.slug, "summary": row.summary} for row in rows]}


@app.post("/search/ai")
async def ai_search(request: GraphQueryRequest, db: Session = Depends(get_db)):
    """Aggregate local evidence first; optional Web search is explicitly degradable."""
    if retriever is None or knowledge_graph is None:
        raise HTTPException(status_code=503, detail="检索服务尚未初始化")
    service = AiSearchService(
        retrieve=lambda query: retriever.retrieve(query),
        graph=lambda query: {"nodes": knowledge_graph.search_nodes(query), "edges": []},
        media=lambda query: search_images_by_text(db, query),
        optional_tools={"web": lambda query: search_web(query, endpoint="", api_key="")},
    )
    return await service.search(request.query)


@app.get("/encyclopedia/{slug}")
async def get_encyclopedia_entry(slug: str, db: Session = Depends(get_db)):
    row = db.query(CraftEntry).filter(CraftEntry.slug == slug, CraftEntry.status == "published").first()
    if row is None:
        raise HTTPException(status_code=404, detail="技艺百科条目不存在")
    return {"name": row.name, "slug": row.slug, "summary": row.summary, "content": row.content}


@app.get("/inheritors")
async def list_inheritors(db: Session = Depends(get_db)):
    rows = db.query(InheritorProfile).filter(InheritorProfile.status == "published").order_by(InheritorProfile.name).all()
    return {"items": [_serialize_inheritor(row, db) for row in rows]}


@app.get("/inheritors/{slug}")
async def get_inheritor(slug: str, db: Session = Depends(get_db)):
    row = db.query(InheritorProfile).filter(InheritorProfile.slug == slug, InheritorProfile.status == "published").first()
    if row is None:
        raise HTTPException(status_code=404, detail="传承人档案不存在")
    return _serialize_inheritor(row, db)


@app.get("/admin/graph-candidates")
async def list_graph_candidates(
    status_filter: Optional[str] = None,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(GraphChangeCandidate).order_by(GraphChangeCandidate.created_at.desc())
    if status_filter:
        query = query.filter(GraphChangeCandidate.status == status_filter)
    rows = query.limit(100).all()
    return {"items": [{
        "id": row.id, "source_entity": row.source_entity, "source_type": row.source_type,
        "relation": row.relation, "target_entity": row.target_entity, "target_type": row.target_type,
        "evidence_text": row.evidence_text, "source_url": row.source_url, "status": row.status,
    } for row in rows]}


def _serialize_craft(row: CraftEntry) -> Dict[str, Any]:
    return {
        "id": row.id, "name": row.name, "slug": row.slug, "summary": row.summary,
        "content": row.content, "status": row.status, "updated_at": row.updated_at,
    }


class AdminCraftCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    summary: str = ""
    content: str = ""


class AdminCraftUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    summary: Optional[str] = None
    content: Optional[str] = None


@app.get("/admin/crafts")
async def list_admin_crafts(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.query(CraftEntry).order_by(CraftEntry.updated_at.desc()).limit(200).all()
    return {"items": [_serialize_craft(row) for row in rows]}


@app.post("/admin/crafts")
async def create_admin_craft(request: AdminCraftCreate, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    name = request.name.strip()
    craft = CraftEntry(name=name, slug=make_slug(name), summary=request.summary.strip(), content=request.content.strip())
    db.add(craft)
    db.flush()
    from src.services.platform_content import _audit
    _audit(db, current_user.id, "craft.created", "craft", craft.id)
    db.commit()
    db.refresh(craft)
    return _serialize_craft(craft)


@app.patch("/admin/crafts/{craft_id}")
async def update_admin_craft(craft_id: int, request: AdminCraftUpdate, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    craft = db.get(CraftEntry, craft_id)
    if craft is None:
        raise HTTPException(status_code=404, detail="百科条目不存在")
    if request.name is not None:
        craft.name = request.name.strip()
        craft.slug = make_slug(craft.name)
    if request.summary is not None:
        craft.summary = request.summary.strip()
    if request.content is not None:
        craft.content = request.content.strip()
    from src.services.platform_content import _audit
    _audit(db, current_user.id, "craft.updated", "craft", craft.id)
    db.commit()
    db.refresh(craft)
    return _serialize_craft(craft)


@app.post("/admin/crafts/{craft_id}/publish")
async def publish_admin_craft(craft_id: int, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    from src.services.platform_content import publish_craft_entry
    try:
        craft = publish_craft_entry(db, craft_id=craft_id, actor_id=current_user.id)
        db.commit()
    except ValueError as error:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(error))
    return _serialize_craft(craft)


@app.delete("/admin/crafts/{craft_id}")
async def delete_admin_craft(craft_id: int, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    craft = db.get(CraftEntry, craft_id)
    if craft is None:
        raise HTTPException(status_code=404, detail="百科条目不存在")
    from src.services.platform_content import _audit
    _audit(db, current_user.id, "craft.deleted", "craft", craft.id)
    db.delete(craft)
    db.commit()
    return {"id": craft_id, "deleted": True}


class AdminInheritorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    craft_name: str = Field(min_length=1, max_length=100)
    region: str = ""
    biography: str = ""
    source_url: str = Field(min_length=8, max_length=500)
    source_name: str = Field(min_length=1, max_length=255)
    evidence_text: str = Field(min_length=1)


class AdminInheritorUpdate(BaseModel):
    craft_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    region: Optional[str] = None
    biography: Optional[str] = None
    recognition: Optional[str] = None
    lineage: Optional[str] = None
    representative_works: Optional[str] = None


@app.get("/admin/inheritors")
async def list_admin_inheritors(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.query(InheritorProfile).order_by(InheritorProfile.updated_at.desc()).limit(200).all()
    return {"items": [_serialize_inheritor(row, db) for row in rows]}


@app.post("/admin/inheritors")
async def create_admin_inheritor(request: AdminInheritorCreate, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Create a draft record and its required public-source evidence together."""
    from src.services.platform_content import add_source_evidence, create_inheritor_profile
    profile = create_inheritor_profile(db, actor_id=current_user.id, name=request.name, craft_name=request.craft_name,
        region=request.region, biography=request.biography)
    add_source_evidence(db, subject_type="inheritor", subject_id=profile.id, source_url=request.source_url,
        source_name=request.source_name, evidence_text=request.evidence_text, actor_id=current_user.id)
    db.commit()
    return {"id": profile.id, "slug": profile.slug, "status": profile.status}


@app.patch("/admin/inheritors/{profile_id}")
async def update_admin_inheritor(profile_id: int, request: AdminInheritorUpdate, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    profile = db.get(InheritorProfile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="传承人档案不存在")
    for field in ("craft_name", "region", "biography", "recognition", "lineage", "representative_works"):
        value = getattr(request, field)
        if value is not None:
            setattr(profile, field, value.strip())
    from src.services.platform_content import _audit
    _audit(db, current_user.id, "inheritor.updated", "inheritor", profile.id)
    db.commit()
    db.refresh(profile)
    return _serialize_inheritor(profile, db)


@app.delete("/admin/inheritors/{profile_id}")
async def delete_admin_inheritor(profile_id: int, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    profile = db.get(InheritorProfile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="传承人档案不存在")
    db.query(SourceEvidence).filter(SourceEvidence.subject_type == "inheritor", SourceEvidence.subject_id == profile.id).delete()
    from src.services.platform_content import _audit
    _audit(db, current_user.id, "inheritor.deleted", "inheritor", profile.id)
    db.delete(profile)
    db.commit()
    return {"id": profile_id, "deleted": True}


@app.post("/admin/inheritors/{profile_id}/publish")
async def publish_admin_inheritor(profile_id: int, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Publish only after the required source-evidence check succeeds."""
    from src.services.platform_content import publish_inheritor_profile
    try:
        profile = publish_inheritor_profile(db, profile_id=profile_id, actor_id=current_user.id)
        db.commit()
    except ValueError as error:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(error))
    return {"id": profile.id, "slug": profile.slug, "status": profile.status}


@app.post("/admin/graph-candidates/scan")
async def scan_graph_candidates(current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Manually scan published content; no server-side cron is installed."""
    from src.services.graph_scheduler import scan_published_crafts
    from src.services.platform_content import _audit
    result = scan_published_crafts(db)
    _audit(db, current_user.id, "graph_candidate.manual_scan", "craft", 0, str(result))
    db.commit()
    return result


@app.post("/admin/graph-candidates/{candidate_id}/approve")
async def approve_and_merge_graph_candidate(
    candidate_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Approve first, then persist the source-backed graph mutation."""
    candidate = approve_graph_candidate(db, candidate_id=candidate_id, actor_id=current_user.id)
    if knowledge_graph is None:
        raise HTTPException(status_code=503, detail="知识图谱尚未初始化")
    merge_approved_candidate(db, candidate_id=candidate.id, graph=knowledge_graph)
    if not knowledge_graph.save_to_json():
        db.rollback()
        raise HTTPException(status_code=500, detail="知识图谱保存失败")
    db.commit()
    return {"id": candidate.id, "status": candidate.status, "merged": True}


class GraphCandidateRejectRequest(BaseModel):
    reason: str = Field(default="", max_length=2000)


@app.post("/admin/graph-candidates/{candidate_id}/reject")
async def reject_admin_graph_candidate(candidate_id: int, request: GraphCandidateRejectRequest, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    try:
        candidate = reject_graph_candidate(db, candidate_id=candidate_id, actor_id=current_user.id, reason=request.reason)
        db.commit()
    except ValueError as error:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(error))
    return {"id": candidate.id, "status": candidate.status}


@app.get("/admin/audit-logs")
async def list_admin_audit_logs(limit: int = 100, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(max(1, min(limit, 200))).all()
    return {"items": [{
        "id": row.id, "actor_user_id": row.actor_user_id, "action": row.action,
        "subject_type": row.subject_type, "subject_id": row.subject_id,
        "detail": row.detail, "created_at": row.created_at,
    } for row in rows]}


# ============================================================================
# 启动命令
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
