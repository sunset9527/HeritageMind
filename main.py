"""
HeritageMind · 首页 Dashboard
"""
import streamlit as st
from ui_components import inject_css, init_session, get_graph_stats

st.set_page_config(page_title="HeritageMind", page_icon="🏺", layout="wide", initial_sidebar_state="collapsed")
inject_css()
init_session()

# ===== Hero =====
st.markdown("""
<div class="hero">
    <h1>探索<span>非物质文化遗产</span></h1>
    <p>多智能体协作 · 知识图谱驱动 · 传承人视角叙事 · 多模态知识库</p>
</div>
""", unsafe_allow_html=True)

# ===== 图片轮播（CSS 动画替代静态数字） =====
st.markdown("""
<style>
    .carousel {
        position: relative; width: 100%; height: 200px; overflow: hidden;
        border-radius: 20px; margin: 0 0 32px;
    }
    .carousel-track {
        display: flex; width: 600%; height: 100%;
        animation: carouselSlide 18s ease-in-out infinite;
    }
    .carousel-slide {
        width: 16.666%; height: 100%; display: flex; align-items: center; justify-content: center;
        padding: 32px 48px; box-sizing: border-box;
    }
    .carousel-slide:nth-child(1) { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: #fff; }
    .carousel-slide:nth-child(2) { background: linear-gradient(135deg, #0f0f23 0%, #1a1a3e 100%); color: #fff; }
    .carousel-slide:nth-child(3) { background: linear-gradient(135deg, #1a1a2e 0%, #0d1b2a 100%); color: #fff; }
    .carousel-slide:nth-child(4) { background: linear-gradient(135deg, #16213e 0%, #1a1a2e 100%); color: #fff; }
    .carousel-slide:nth-child(5) { background: linear-gradient(135deg, #0d1b2a 0%, #1a1a2e 100%); color: #fff; }
    .carousel-slide:nth-child(6) { background: linear-gradient(135deg, #1a1a3e 0%, #0f0f23 100%); color: #fff; }
    .carousel-icon { font-size: 4rem; margin-right: 36px; flex-shrink: 0; }
    .carousel-text h2 { font-size: 1.6rem; font-weight: 700; margin: 0 0 6px; letter-spacing: -0.02em; }
    .carousel-text p { font-size: 0.95rem; margin: 0; opacity: 0.75; line-height: 1.6; max-width: 500px; }

    @keyframes carouselSlide {
        0%, 13%   { transform: translateX(0); }
        16%, 30%  { transform: translateX(-16.666%); }
        33%, 46%  { transform: translateX(-33.333%); }
        49%, 63%  { transform: translateX(-50%); }
        66%, 80%  { transform: translateX(-66.666%); }
        83%, 96%  { transform: translateX(-83.333%); }
        100%      { transform: translateX(0); }
    }

    /* 指示器 */
    .carousel-dots {
        display: flex; justify-content: center; gap: 10px; margin-top: -20px; position: relative; z-index: 2;
    }
    .carousel-dot {
        width: 8px; height: 8px; border-radius: 50%; background: rgba(255,255,255,0.3);
        animation: dotPulse 18s ease-in-out infinite;
    }
    .carousel-dot:nth-child(1) { animation-delay: 0s; }
    .carousel-dot:nth-child(2) { animation-delay: 3s; }
    .carousel-dot:nth-child(3) { animation-delay: 6s; }
    .carousel-dot:nth-child(4) { animation-delay: 9s; }
    .carousel-dot:nth-child(5) { animation-delay: 12s; }
    .carousel-dot:nth-child(6) { animation-delay: 15s; }

    @keyframes dotPulse {
        0%, 13%   { background: rgba(255,255,255,0.9); transform: scale(1.3); }
        16%, 100% { background: rgba(255,255,255,0.3); transform: scale(1); }
    }
</style>

<div class="carousel">
    <div class="carousel-track">
        <div class="carousel-slide">
            <div class="carousel-icon">🏺</div>
            <div class="carousel-text"><h2>景泰蓝</h2><p>铜胎掐丝珐琅 · 北京代表性宫廷技艺 · 六百年传承</p></div>
        </div>
        <div class="carousel-slide">
            <div class="carousel-icon">🧵</div>
            <div class="carousel-text"><h2>苏绣</h2><p>四大名绣之首 · 精细雅洁 · 以针作画的东方美学</p></div>
        </div>
        <div class="carousel-slide">
            <div class="carousel-icon">🏺</div>
            <div class="carousel-text"><h2>龙泉青瓷</h2><p>中国青瓷巅峰 · 哥窑冰裂纹 · 粉青梅子青釉色传奇</p></div>
        </div>
        <div class="carousel-slide">
            <div class="carousel-icon">🫖</div>
            <div class="carousel-text"><h2>宜兴紫砂</h2><p>陶都瑰宝 · 一壶一世界 · 茶道精神的最佳载体</p></div>
        </div>
        <div class="carousel-slide">
            <div class="carousel-icon">🔨</div>
            <div class="carousel-text"><h2>芜湖铁画</h2><p>以锤代笔 · 以铁为墨 · 独一无二的金属工艺画</p></div>
        </div>
        <div class="carousel-slide">
            <div class="carousel-icon">🧣</div>
            <div class="carousel-text"><h2>蜀锦</h2><p>丝绸之路上的锦绣华章 · 两千年的织造智慧</p></div>
        </div>
    </div>
</div>
<div class="carousel-dots">
    <div class="carousel-dot"></div><div class="carousel-dot"></div><div class="carousel-dot"></div>
    <div class="carousel-dot"></div><div class="carousel-dot"></div><div class="carousel-dot"></div>
</div>
""", unsafe_allow_html=True)

# ===== Feature Cards =====
st.markdown("### 快速入口")
f1, f2, f3 = st.columns(3)

with f1:
    with st.container(border=True):
        st.markdown("##### 💬 AI 问答")
        st.markdown("多专家 Agent 协作回答，辩论引擎 + 知识缺口检测")
        if st.button("进入问答 →", key="goto_chat", use_container_width=True):
            st.switch_page("pages/1_Chat.py")

with f2:
    with st.container(border=True):
        st.markdown("##### 🕸️ 知识图谱")
        st.markdown("47 节点多维关联，交互式可视化探索")
        if st.button("探索图谱 →", key="goto_graph", use_container_width=True):
            st.switch_page("pages/2_Graph.py")

with f3:
    with st.container(border=True):
        st.markdown("##### ⚙️ 系统设置")
        st.markdown("切换 LLM 模型，配置 API Key")
        if st.button("前往设置 →", key="goto_settings", use_container_width=True):
            st.switch_page("pages/3_Settings.py")

st.markdown("<hr>", unsafe_allow_html=True)

# ===== Quick Start =====
st.markdown("### 💡 快速提问")
examples = [
    "景泰蓝的制作流程分为几步？",
    "苏绣有哪些著名传承人？",
    "龙泉青瓷的釉色形成原理是什么？",
]
cols = st.columns(3)
for i, q in enumerate(examples):
    with cols[i]:
        if st.button(q, key=f"hero_q_{i}", use_container_width=True):
            st.session_state["_pending_question"] = q
            st.switch_page("pages/1_Chat.py")

# ===== Stats Bar =====
stats = get_graph_stats()
nodes = stats.get("total_nodes", 47) if isinstance(stats, dict) else 47
edges = stats.get("total_edges", 41) if isinstance(stats, dict) else 41

st.markdown("<hr>", unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)
c1.metric("知识节点", f"{nodes}")
c2.metric("语义关联", f"{edges}")
c3.metric("非遗技艺", "6 种")
c4.metric("专家 Agent", "3 位")

# ===== Footer =====
st.markdown("""
<div style="text-align:center;padding:48px 0 24px;color:var(--text3);font-size:0.82rem">
    <p style="margin:0;font-weight:600">HeritageMind · 非遗知识平台</p>
    <p style="margin:4px 0 0;font-size:0.75rem">LangGraph · DeepSeek · ChromaDB · NetworkX</p>
</div>
""", unsafe_allow_html=True)
