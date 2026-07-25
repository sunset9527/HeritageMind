"""
FastAPI后端服务 - 非遗知识问答系统API
"""

import logging
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Header, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session

from config import settings
from src.workflow.graph import HeritageWorkflowGraph, get_workflow
from src.workflow.state import QueryRequest, QueryResponse, state_to_response
from src.graph.heritage_graph import HeritageKnowledgeGraph
from src.graph.builder import KnowledgeGraphBuilder
from src.retrieval.document_loader import HeritageDocumentLoader
from src.retrieval.retriever import MultiSourceRetriever
from src.knowledge.gap_detector import KnowledgeGapDetector
from src.graph.visualizer import HeritageGraphVisualizer
from src.database import init_db
from src.deps import get_db, get_current_user, get_optional_user
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
)
from src.services.auth import create_user, authenticate_user, create_access_token
from src.services.chat import save_chat_history, get_user_history, get_user_history_count, get_chat_detail
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global workflow, knowledge_graph, document_loader, retriever, visualizer

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
    
    # 初始化可视化器
    visualizer = HeritageGraphVisualizer(knowledge_graph)
    
    # 初始化文档加载器
    document_loader = HeritageDocumentLoader()
    
    # 初始化检索器
    retriever = MultiSourceRetriever(document_loader=document_loader)
    
    logger.info("应用初始化完成")
    
    yield
    
    logger.info("应用关闭")


# 创建FastAPI应用
app = FastAPI(
    title="非遗知识问答系统API",
    description="基于多智能体的非遗知识保存与传承平台",
    version="1.0.0",
    lifespan=lifespan
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
    try:
        if x_api_key or x_model:
            set_request_override(api_key=x_api_key, base_url=x_api_base, model=x_model)

        logger.info(f"处理问题: {request.question[:50]}...")

        response = workflow.query(
            question=request.question,
            user_profile=request.user_profile,
            include_narrative=request.include_narrative
        )

        # 如果用户已登录，自动保存聊天历史
        if current_user is not None:
            try:
                save_chat_history(
                    db=db,
                    user_id=current_user.id,
                    question=request.question,
                    answer=response.answer,
                    user_profile=request.user_profile,
                    agents_used=[a.get("id", "") for a in response.source_agents],
                    has_gaps=response.has_gaps,
                )
            except Exception as e:
                logger.warning(f"保存聊天历史失败（不影响问答）: {e}")

        return response

    except Exception as e:
        logger.error(f"问答处理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
async def get_graph_stats():
    """获取知识图谱统计信息"""
    try:
        stats = knowledge_graph.get_statistics()
        return GraphStatsResponse(**stats)
    except Exception as e:
        logger.error(f"获取图谱统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph/visualize")
async def visualize_graph(
    filter_type: Optional[str] = None,
    layout: str = "force"
):
    """
    获取交互式图谱HTML
    
    - **filter_type**: 节点类型过滤（可选）
    - **layout**: 布局类型 ("force", "random", "circular")
    """
    try:
        if visualizer is None:
            raise HTTPException(status_code=503, detail="可视化器未初始化")
        
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
