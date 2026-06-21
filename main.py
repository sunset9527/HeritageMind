"""
Streamlit前端 - 非遗知识问答系统用户界面 (V2)
60/40 双栏布局，包含辩论时间线、Agent气泡、知识图谱可视化
"""

import streamlit as st
import requests
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import time

from config import settings

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# 页面配置
# ============================================================================

st.set_page_config(
    page_title="非遗知识问答系统 V2",
    page_icon="🏺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS - 非遗文化感配色
st.markdown("""
<style>
    /* 变量定义 */
    :root {
        --primary-color: #8B4513;
        --secondary-color: #D2691E;
        --background-color: #FFF8F0;
        --text-color: #333333;
        --border-color: #D2691E;
    }
    
    /* 全局背景 */
    .stApp {
        background-color: #FFF8F0;
    }
    
    /* 主标题 */
    .main-title {
        font-size: 2.2rem;
        font-weight: bold;
        color: #8B4513;
        text-align: center;
        padding: 0.5rem 0;
        border-bottom: 3px solid #D2691E;
        margin-bottom: 1rem;
        font-family: 'Georgia', serif;
    }
    
    /* Agent气泡样式 */
    .agent-bubble {
        border-radius: 15px;
        padding: 15px 20px;
        margin: 10px 0;
        position: relative;
        font-family: 'Microsoft YaHei', sans-serif;
    }
    
    /* 技艺专家 - 绿色 */
    .agent-craft-expert {
        background: linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%);
        border: 2px solid #4CAF50;
        border-left: 5px solid #2E7D32;
    }
    
    /* 历史专家 - 蓝色 */
    .agent-history-expert {
        background: linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 100%);
        border: 2px solid #2196F3;
        border-left: 5px solid #1565C0;
    }
    
    /* 传承专家 - 橙色 */
    .agent-heritage-expert {
        background: linear-gradient(135deg, #FFF3E0 0%, #FFE0B2 100%);
        border: 2px solid #FF9800;
        border-left: 5px solid #EF6C00;
    }
    
    /* 综合回答 - 紫色 */
    .agent-synthesis {
        background: linear-gradient(135deg, #F3E5F5 0%, #E1BEE7 100%);
        border: 2px solid #9C27B0;
        border-left: 5px solid #7B1FA2;
    }
    
    /* Agent标签 */
    .agent-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: bold;
        margin-bottom: 8px;
    }
    
    .badge-craft {
        background-color: #2E7D32;
        color: white;
    }
    
    .badge-history {
        background-color: #1565C0;
        color: white;
    }
    
    .badge-heritage {
        background-color: #EF6C00;
        color: white;
    }
    
    .badge-synthesis {
        background-color: #7B1FA2;
        color: white;
    }
    
    /* 辩论时间线 */
    .timeline {
        position: relative;
        padding-left: 30px;
    }
    
    .timeline::before {
        content: '';
        position: absolute;
        left: 10px;
        top: 0;
        bottom: 0;
        width: 3px;
        background: linear-gradient(to bottom, #8B4513, #D2691E);
        border-radius: 2px;
    }
    
    .timeline-item {
        position: relative;
        margin-bottom: 20px;
        padding: 12px 15px;
        background: white;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border-left: 3px solid #D2691E;
    }
    
    .timeline-item::before {
        content: '';
        position: absolute;
        left: -24px;
        top: 15px;
        width: 14px;
        height: 14px;
        background: #8B4513;
        border: 3px solid #FFF8F0;
        border-radius: 50%;
    }
    
    .timeline-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 8px;
    }
    
    .timeline-title {
        font-weight: bold;
        color: #8B4513;
    }
    
    .timeline-time {
        font-size: 0.75rem;
        color: #888;
    }
    
    /* 引用溯源卡片 */
    .citation-card {
        background: white;
        border-radius: 8px;
        padding: 12px 15px;
        margin: 8px 0;
        border-left: 4px solid #D2691E;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    }
    
    .citation-title {
        font-weight: bold;
        color: #333;
        margin-bottom: 5px;
    }
    
    .citation-source {
        font-size: 0.8rem;
        color: #666;
    }
    
    /* 缺口警告 */
    .gap-warning {
        background: linear-gradient(135deg, #FFF8E1 0%, #FFECB3 100%);
        border-left: 4px solid #FFC107;
        padding: 12px 15px;
        border-radius: 0 8px 8px 0;
        margin: 10px 0;
    }
    
    /* 快捷问题按钮 */
    .quick-btn {
        background: white;
        border: 2px solid #D2691E;
        color: #8B4513;
        padding: 8px 15px;
        border-radius: 25px;
        cursor: pointer;
        transition: all 0.3s;
        font-size: 0.9rem;
    }
    
    .quick-btn:hover {
        background: #D2691E;
        color: white;
    }
    
    /* 右侧面板 */
    .right-panel {
        background: white;
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
    }
    
    /* Tab样式 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #FFF8F0;
        border-radius: 10px;
        padding: 5px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        font-weight: bold;
    }
    
    /* 隐藏默认streamlit元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 用户消息右对齐 */
    .user-message {
        text-align: right;
    }
    
    /* 滚动条样式 */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #FFF8F0;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #D2691E;
        border-radius: 4px;
    }
    
    /* 关键洞见 */
    .insight-item {
        background: linear-gradient(90deg, #FFF8F0, white);
        padding: 10px 15px;
        border-radius: 8px;
        margin: 8px 0;
        border-left: 4px solid #8B4513;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# API配置
# ============================================================================

API_BASE_URL = getattr(settings, 'api_url', 'http://localhost:8000')


# ============================================================================
# 会话状态初始化
# ============================================================================

def init_session_state():
    """初始化会话状态"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "user_profile" not in st.session_state:
        st.session_state.user_profile = "curious"
    
    if "include_narrative" not in st.session_state:
        st.session_state.include_narrative = False
    
    if "current_craft" not in st.session_state:
        st.session_state.current_craft = None
    
    if "debate_session" not in st.session_state:
        st.session_state.debate_session = None
    
    if "selected_insight" not in st.session_state:
        st.session_state.selected_insight = None


# ============================================================================
# API交互函数
# ============================================================================

def call_api(endpoint: str, data: Dict = None, method: str = "GET") -> Dict:
    """调用API"""
    try:
        if method == "GET":
            response = requests.get(f"{API_BASE_URL}{endpoint}", params=data, timeout=300)
        else:
            response = requests.post(f"{API_BASE_URL}{endpoint}", json=data, timeout=300)
        
        return response.json()
    except requests.exceptions.ConnectionError:
        return {"error": "API服务未启动，请先运行 python api.py"}
    except Exception as e:
        return {"error": str(e)}


def query_question(question: str) -> Dict:
    """发送问答请求"""
    data = {
        "question": question,
        "user_profile": st.session_state.user_profile,
        "include_narrative": st.session_state.include_narrative
    }
    return call_api("/query", data, "POST")


def get_graph_html(filter_type: str = None, layout: str = "force") -> str:
    """获取图谱HTML"""
    params = {"layout": layout}
    if filter_type:
        params["filter_type"] = filter_type
    result = call_api("/graph/visualize", params)
    return result.get("html", "")


def get_graph_stats() -> Dict:
    """获取图谱统计"""
    return call_api("/graph/stats")


def get_crafts() -> List[Dict]:
    """获取技艺列表"""
    result = call_api("/crafts")
    return result.get("crafts", [])


def get_profiles() -> List[Dict]:
    """获取用户画像列表"""
    result = call_api("/profiles")
    return result.get("profiles", [])


# ============================================================================
# Agent气泡渲染
# ============================================================================

def render_agent_bubble(agent_type: str, content: str, timestamp: str = None):
    """
    渲染Agent气泡
    
    Args:
        agent_type: Agent类型 (craft_expert, history_expert, heritage_expert, synthesis)
        content: 内容
        timestamp: 时间戳
    """
    # 映射关系
    badge_map = {
        "craft_expert": ("🎨 技艺专家", "badge-craft", "agent-craft-expert"),
        "history_expert": ("📜 历史专家", "badge-history", "agent-history-expert"),
        "heritage_expert": ("🏛️ 传承专家", "badge-heritage", "agent-heritage-expert"),
        "synthesis": ("✨ 综合分析", "badge-synthesis", "agent-synthesis"),
    }
    
    badge_text, badge_class, bubble_class = badge_map.get(
        agent_type, 
        ("❓ 未知", "badge-heritage", "agent-heritage-expert")
    )
    
    # 时间显示
    time_str = timestamp if timestamp else datetime.now().strftime("%H:%M")
    
    html = f"""
    <div class="agent-bubble {bubble_class}">
        <div class="agent-badge {badge_class}">{badge_text}</div>
        <div class="agent-content">{content}</div>
        <div class="timeline-time" style="margin-top:8px; text-align:right;">{time_str}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_debate_timeline(debate_data: Dict):
    """
    渲染辩论时间线
    
    Args:
        debate_data: 辩论数据
    """
    st.markdown('<div class="timeline">', unsafe_allow_html=True)
    
    rounds = debate_data.get("rounds", [])
    
    for i, round_data in enumerate(rounds):
        round_num = round_data.get("round", i + 1)
        agent = round_data.get("agent", "unknown")
        content = round_data.get("content", "")
        timestamp = round_data.get("timestamp", "")
        
        # Agent图标
        agent_icons = {
            "craft_expert": "🎨",
            "history_expert": "📜",
            "heritage_expert": "🏛️",
        }
        icon = agent_icons.get(agent, "💬")
        
        # Agent名称
        agent_names = {
            "craft_expert": "技艺专家",
            "history_expert": "历史专家",
            "heritage_expert": "传承专家",
        }
        name = agent_names.get(agent, "专家")
        
        st.markdown(f"""
        <div class="timeline-item">
            <div class="timeline-header">
                <span style="font-size:1.2rem;">{icon}</span>
                <span class="timeline-title">第{round_num}轮 - {name}</span>
                <span class="timeline-time">{timestamp}</span>
            </div>
            <div class="timeline-content">
                {content[:200]}{'...' if len(content) > 200 else ''}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)


def render_citations(citations: List[Dict]):
    """
    渲染引用溯源
    
    Args:
        citations: 引用列表
    """
    if not citations:
        st.info("暂无引用来源")
        return
    
    for i, citation in enumerate(citations):
        title = citation.get("title", "未命名来源")
        source = citation.get("source", "未知")
        url = citation.get("url", "")
        
        with st.expander(f"📄 {title}", expanded=i == 0):
            st.markdown(f"**来源**: {source}")
            if url:
                st.markdown(f"**链接**: [{url}]({url})")
            snippet = citation.get("snippet", "")
            if snippet:
                st.markdown(f"**摘录**: _{snippet}_")


def render_insights(insights: List[str]):
    """
    渲染关键洞见列表
    
    Args:
        insights: 洞见列表
    """
    if not insights:
        st.info("暂无关键洞见")
        return
    
    for insight in insights:
        st.markdown(f"""
        <div class="insight-item">
            💡 {insight}
        </div>
        """, unsafe_allow_html=True)


# ============================================================================
# 侧边栏
# ============================================================================

def render_sidebar():
    """渲染侧边栏配置"""
    with st.sidebar:
        st.markdown("### 🏺 非遗知识问答")
        st.markdown("---")
        
        # 用户画像选择
        st.markdown("#### 👤 用户画像")
        profiles = get_profiles()
        
        # 兜底：API未启动时使用默认画像列表
        if not profiles or not isinstance(profiles, list) or len(profiles) == 0:
            profiles = [
                {"id": "curious", "name": "好奇者", "depth": "浅层"},
                {"id": "learner", "name": "学习者", "depth": "中层"},
                {"id": "researcher", "name": "研究者", "depth": "深层"}
            ]
        
        profile_names = {p["id"]: f"{p['name']} ({p['depth']})" for p in profiles}
        
        profile_keys = list(profile_names.keys())
        current_idx = profile_keys.index(st.session_state.user_profile) if st.session_state.user_profile in profile_keys else 0
        
        if not profile_keys:
            st.warning("⚠️ 后端API未启动，请先运行: python -m uvicorn api:app --host 0.0.0.0 --port 8000")
            selected_profile = st.session_state.user_profile
        else:
            selected_profile = st.selectbox(
                "选择学习阶段",
                options=profile_keys,
                format_func=lambda x: profile_names.get(x, x),
                index=current_idx,
                label_visibility="collapsed"
            )
        
        if selected_profile and selected_profile != st.session_state.user_profile:
            st.session_state.user_profile = selected_profile
            st.rerun()
        
        display_name = profile_names.get(selected_profile, selected_profile or "未选择")
        st.markdown(f"**当前**: {display_name}")
        
        # 叙事模式
        st.markdown("---")
        st.markdown("#### 🎭 叙事模式")
        include_narrative = st.checkbox(
            "使用传承人口吻",
            value=st.session_state.include_narrative,
            help="以老匠人口吻讲述技艺知识"
        )
        
        if include_narrative != st.session_state.include_narrative:
            st.session_state.include_narrative = include_narrative
        
        # 技艺筛选
        st.markdown("---")
        st.markdown("#### 🎨 技艺选择")
        crafts = get_crafts()
        
        # 兜底：API未启动时使用默认技艺列表
        if not crafts or not isinstance(crafts, list) or len(crafts) == 0:
            crafts = [
                {"id": "jingtailan", "name": "景泰蓝"},
                {"id": "suxiu", "name": "苏绣"},
                {"id": "longquan_ci", "name": "龙泉青瓷"},
                {"id": "yixing_zisha", "name": "宜兴紫砂"},
                {"id": "wuhu_tiehua", "name": "芜湖铁画"},
                {"id": "shujin", "name": "蜀锦"}
            ]
        
        craft_options = ["全部技艺"] + [c["name"] for c in crafts]
        
        current_craft_idx = 0
        if st.session_state.current_craft:
            if st.session_state.current_craft in craft_options:
                current_craft_idx = craft_options.index(st.session_state.current_craft)
        
        selected_craft = st.selectbox(
            "选择关注的技艺",
            options=craft_options,
            index=current_craft_idx,
            label_visibility="collapsed"
        )
        
        st.session_state.current_craft = selected_craft if selected_craft != "全部技艺" else None
        
        # 知识图谱统计
        st.markdown("---")
        st.markdown("#### 📊 知识图谱")
        stats = get_graph_stats()
        
        if isinstance(stats, dict) and "error" not in stats and "total_nodes" in stats:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("节点", stats.get("total_nodes", 0))
            with col2:
                st.metric("边", stats.get("total_edges", 0))
            
            with st.expander("节点类型", expanded=False):
                for node_type, count in stats.get("node_types", {}).items():
                    type_names = {
                        "craft": "技艺",
                        "material": "材料",
                        "tool": "工具",
                        "inheritor": "传承人",
                        "region": "地域",
                        "dynasty": "朝代"
                    }
                    name = type_names.get(node_type, node_type)
                    st.write(f"- {name}: {count}")
        else:
            st.info("图谱加载中...")
        
        # 帮助
        st.markdown("---")
        with st.expander("❓ 使用帮助"):
            st.markdown("""
            **功能说明**：
            1. 输入问题，系统多专家协作回答
            2. 右侧面板展示辩论过程
            3. 知识图谱可视化展示关联
            
            **快捷问题**：
            - 点击底部示例问题快速体验
            """)


# ============================================================================
# 知识图谱Tab
# ============================================================================

def render_graph_tab():
    """渲染知识图谱Tab"""
    st.markdown("#### 🔍 知识图谱探索")
    
    # 布局选项
    layout_option = st.selectbox(
        "选择布局",
        ["force", "circular"],
        format_func=lambda x: {"force": "力导向布局", "circular": "圆形布局"}[x]
    )
    
    # 类型筛选
    filter_options = [None, "craft", "material", "tool", "inheritor", "region", "dynasty"]
    filter_labels = ["全部", "技艺", "材料", "工具", "传承人", "地域", "朝代"]
    
    filter_idx = st.selectbox(
        "筛选节点类型",
        range(len(filter_options)),
        format_func=lambda x: filter_labels[x]
    )
    filter_type = filter_options[filter_idx]
    
    # 获取并显示图谱
    with st.spinner("加载知识图谱..."):
        html_content = get_graph_html(filter_type=filter_type, layout=layout_option)
    
    if html_content and html_content.startswith("<!DOCTYPE"):
        st.components.v1.html(html_content, height=550, scrolling=True)
    elif "pyvis未安装" in html_content:
        st.warning("请安装pyvis: `pip install pyvis>=2.1.0`")
        st.code("pip install pyvis>=2.1.0")
    elif "知识图谱未加载" in html_content:
        st.info("正在初始化知识图谱，请稍后刷新...")
    else:
        st.info("图谱加载中...")


# ============================================================================
# 辩论时间线Tab
# ============================================================================

def render_debate_tab():
    """渲染辩论时间线Tab"""
    st.markdown("#### ⚔️ 辩论时间线")
    
    # 检查是否有辩论数据
    if st.session_state.debate_session is None:
        st.info("💡 提问后，系统会展示多专家的协作辩论过程")
        
        # 显示模拟示例
        st.markdown("**📋 示例辩论流程**")
        
        st.markdown("""
        <div class="timeline">
            <div class="timeline-item">
                <div class="timeline-header">
                    <span style="font-size:1.2rem;">🔍</span>
                    <span class="timeline-title">问题解析</span>
                </div>
                <div class="timeline-content">
                    分析用户问题，识别关键实体和所需专家类型
                </div>
            </div>
            <div class="timeline-item">
                <div class="timeline-header">
                    <span style="font-size:1.2rem;">🎨</span>
                    <span class="timeline-title">技艺专家发言</span>
                </div>
                <div class="timeline-content">
                    从技艺制作角度分析问题，提供工艺流程和材料信息
                </div>
            </div>
            <div class="timeline-item">
                <div class="timeline-header">
                    <span style="font-size:1.2rem;">📜</span>
                    <span class="timeline-title">历史专家发言</span>
                </div>
                <div class="timeline-content">
                    从历史文化角度补充，提供历史渊源和发展脉络
                </div>
            </div>
            <div class="timeline-item">
                <div class="timeline-header">
                    <span style="font-size:1.2rem;">🏛️</span>
                    <span class="timeline-title">传承专家发言</span>
                </div>
                <div class="timeline-content">
                    从传承现状角度分析，提供传承人和保护现状信息
                </div>
            </div>
            <div class="timeline-item">
                <div class="timeline-header">
                    <span style="font-size:1.2rem;">✨</span>
                    <span class="timeline-title">综合整合</span>
                </div>
                <div class="timeline-content">
                    融合各专家观点，生成最终回答
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # 渲染真实辩论数据
        render_debate_timeline(st.session_state.debate_session)


# ============================================================================
# 引用溯源Tab
# ============================================================================

def render_citation_tab():
    """渲染引用溯源Tab"""
    st.markdown("#### 📚 引用溯源")
    
    # 从消息历史中提取引用
    citations = []
    for msg in st.session_state.messages:
        if msg.get("role") == "assistant" and msg.get("metadata"):
            msg_citations = msg["metadata"].get("citations", [])
            citations.extend(msg_citations)
    
    if citations:
        render_citations(citations)
    else:
        st.info("💡 提问后，系统会展示回答的引用来源")


# ============================================================================
# 主界面
# ============================================================================

def main():
    """主函数"""
    init_session_state()
    render_sidebar()
    
    # 标题
    st.markdown('<h1 class="main-title">🏺 非遗知识问答系统 V2</h1>', unsafe_allow_html=True)
    
    # 60/40 双栏布局
    left_col, right_col = st.columns([3, 2])
    
    # ========== 左侧：对话区 (60%) ==========
    with left_col:
        st.markdown("### 💬 对话区")
        
        # 示例问题
        st.markdown("#### 💡 快捷问题")
        example_questions = [
            "景泰蓝的制作流程是什么？",
            "苏绣的四大名绣特点是什么？",
            "龙泉青瓷的釉色有什么特点？",
            "如何学习宜兴紫砂壶制作？",
            "芜湖铁画的传承现状如何？",
            "蜀锦的历史和文化意义是什么？"
        ]
        
        quick_cols = st.columns(3)
        for i, q in enumerate(example_questions):
            with quick_cols[i % 3]:
                if st.button(f"🔹 {q[:10]}...", key=f"quick_{i}", use_container_width=True):
                    st.session_state.messages.append({
                        "role": "user",
                        "content": q,
                        "timestamp": datetime.now().strftime("%H:%M")
                    })
                    st.rerun()
        
        st.markdown("---")
        
        # 聊天历史
        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                timestamp = msg.get("timestamp", "")
                metadata = msg.get("metadata", {})
                
                if role == "user":
                    # 用户消息
                    with st.chat_message("user"):
                        st.markdown(content)
                        if timestamp:
                            st.caption(f"🕐 {timestamp}")
                else:
                    # Agent回答
                    source_agents = metadata.get("source_agents", [])
                    debate_session = metadata.get("debate_session")
                    
                    # 显示各个Agent的气泡
                    if source_agents:
                        for agent_info in source_agents:
                            agent_type = agent_info.get("type", "synthesis")
                            agent_content = agent_info.get("content", "")
                            
                            if agent_content:
                                render_agent_bubble(
                                    agent_type,
                                    agent_content[:500] + ("..." if len(agent_content) > 500 else ""),
                                    timestamp
                                )
                    else:
                        # 综合回答（降级模式）
                        render_agent_bubble("synthesis", content[:500], timestamp)
                    
                    # 保存辩论数据到session_state供右侧面板使用
                    if debate_session:
                        st.session_state.debate_session = debate_session
                    
                    # 缺口警告
                    if metadata.get("has_gaps"):
                        st.markdown(f"""
                        <div class="gap-warning">
                            ⚠️ <b>知识缺口提示</b><br>
                            {metadata.get("gap_report", "部分信息暂缺")}
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # 引用
                    citations = metadata.get("citations", [])
                    if citations:
                        with st.expander("📚 查看引用来源"):
                            for cit in citations[:3]:
                                st.markdown(f"- *{cit.get('title', '来源')}*")
        
        # 聊天输入
        if prompt := st.chat_input("请输入您的问题..."):
            # 添加用户消息
            st.session_state.messages.append({
                "role": "user",
                "content": prompt,
                "timestamp": datetime.now().strftime("%H:%M")
            })
            
            # 显示用户消息
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # 调用API获取回答
            with st.chat_message("assistant"):
                with st.spinner("🤔 多专家协作思考中..."):
                    start_time = time.time()
                    response = query_question(prompt)
                    elapsed_time = time.time() - start_time
                    
                    if "error" in response:
                        st.error(response["error"])
                    else:
                        # 提取回答
                        answer = response.get("answer", "")
                        
                        # 提取Agent来源
                        source_agents = response.get("source_agents", [])
                        
                        # 提取辩论数据（如果有）
                        debate_session = response.get("debate_session")
                        
                        # 缺口信息
                        has_gaps = response.get("has_gaps", False)
                        gap_report = response.get("gap_report", "")
                        
                        # 显示回答
                        if source_agents:
                            for agent_info in source_agents:
                                agent_type = agent_info.get("type", "synthesis")
                                agent_content = agent_info.get("content", "")
                                
                                if agent_content:
                                    render_agent_bubble(
                                        agent_type,
                                        agent_content[:500] + ("..." if len(agent_content) > 500 else ""),
                                        datetime.now().strftime("%H:%M")
                                    )
                        else:
                            # 降级模式：直接显示回答
                            render_agent_bubble("synthesis", answer[:500], datetime.now().strftime("%H:%M"))
                        
                        # 保存辩论数据
                        if debate_session:
                            st.session_state.debate_session = debate_session
                        
                        # 缺口警告
                        if has_gaps:
                            st.markdown(f"""
                            <div class="gap-warning">
                                ⚠️ <b>知识缺口提示</b><br>
                                {gap_report}
                            </div>
                            """, unsafe_allow_html=True)
                        
                        # 元数据
                        st.caption(f"⏱️ 处理时间: {elapsed_time:.2f}秒")
                        
                        # 添加到历史
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": answer,
                            "timestamp": datetime.now().strftime("%H:%M"),
                            "metadata": {
                                "source_agents": source_agents,
                                "debate_session": debate_session,
                                "has_gaps": has_gaps,
                                "gap_report": gap_report,
                                "citations": response.get("citations", [])
                            }
                        })
    
    # ========== 右侧：知识增强面板 (40%) ==========
    with right_col:
        st.markdown("### 📊 知识增强面板")
        
        # Tabs
        tab1, tab2, tab3 = st.tabs([
            "⚔️ 辩论时间线",
            "🕸️ 知识图谱",
            "📚 引用溯源"
        ])
        
        with tab1:
            render_debate_tab()
        
        with tab2:
            render_graph_tab()
        
        with tab3:
            render_citation_tab()
        
        # 关键洞见
        st.markdown("---")
        st.markdown("#### 💎 关键洞见")
        
        # 从历史中提取洞见
        insights = []
        for msg in st.session_state.messages:
            if msg.get("role") == "assistant" and msg.get("metadata"):
                msg_insights = msg["metadata"].get("insights", [])
                insights.extend(msg_insights)
        
        if insights:
            render_insights(insights[:5])  # 最多显示5个
        else:
            st.info("💡 提问后可在此处查看关键洞见")
        
        # 清理按钮
        if st.button("🗑️ 清理对话历史", use_container_width=True):
            st.session_state.messages = []
            st.session_state.debate_session = None
            st.rerun()
    
    # 页脚
    st.markdown("---")
    st.markdown("""
    <div style="text-align:center; padding:15px; color:#888; font-size:0.85rem;">
        <p>🏺 非遗知识问答系统 V2 | 基于多智能体架构</p>
        <p>技术栈：LangGraph + LangChain + DeepSeek</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
