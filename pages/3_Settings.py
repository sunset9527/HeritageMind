"""
HeritageMind · 系统设置
"""
import streamlit as st
from ui_components import inject_css, init_session

st.set_page_config(page_title="设置", page_icon="⚙️", layout="wide", initial_sidebar_state="collapsed")
inject_css()
init_session()

st.markdown('<h2 style="font-weight:800;letter-spacing:-0.03em;margin-bottom:4px">系统设置</h2><p style="color:var(--text2);margin-top:0">模型选择 · API Key · 偏好配置</p>', unsafe_allow_html=True)

# ===== 模型选择 =====
st.markdown('<div class="setting-section"><h3>🤖 模型选择</h3>', unsafe_allow_html=True)

MODELS = {
    "DeepSeek": {
        "deepseek-chat": "DeepSeek V3 (推荐，性价比最高)",
        "deepseek-reasoner": "DeepSeek R1 (深度推理)",
    },
    "OpenAI": {
        "gpt-4o": "GPT-4o (综合能力强)",
        "gpt-4o-mini": "GPT-4o Mini (轻量快速)",
    },
    "Qwen (通义千问)": {
        "qwen-max": "Qwen Max (阿里云旗舰)",
        "qwen-plus": "Qwen Plus (均衡性能)",
    },
    "Claude": {
        "claude-sonnet-5": "Claude Sonnet 5 (均衡推荐)",
        "claude-opus-4-8": "Claude Opus 4.8 (最强能力)",
    },
}

BASE_URLS = {
    "DeepSeek": "https://api.deepseek.com/v1",
    "OpenAI": "https://api.openai.com/v1",
    "Qwen (通义千问)": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "Claude": "https://api.anthropic.com/v1",
}

provider = st.selectbox("模型提供商", list(MODELS.keys()))
model = st.selectbox("模型", list(MODELS[provider].values()), format_func=lambda x: x)

# Extract actual model key from display string
model_key = list(MODELS[provider].keys())[list(MODELS[provider].values()).index(model)]
base_url = BASE_URLS[provider]

if st.button("应用模型设置", type="primary"):
    st.session_state.selected_model = model_key
    st.session_state.user_base_url = base_url
    st.success(f"已切换至 {provider} / {model}")

st.caption(f"当前使用：**{st.session_state.selected_model}** @ {st.session_state.user_base_url}")

st.markdown('</div>', unsafe_allow_html=True)

# ===== API Key =====
st.markdown('<div class="setting-section"><h3>🔑 API Key</h3>', unsafe_allow_html=True)

st.markdown(f"""
<div style="font-size:0.85rem;color:var(--text2);margin-bottom:12px">
    输入你自己的 API Key，系统将使用你的额度进行调用。<br>
    Key 仅存储在会话中，<b>不会保存到服务器或磁盘</b>，刷新页面后需重新输入。
</div>
""", unsafe_allow_html=True)

api_key = st.text_input(
    "API Key",
    type="password",
    value=st.session_state.user_api_key,
    placeholder="sk-..."
)

if api_key != st.session_state.user_api_key:
    st.session_state.user_api_key = api_key
    st.success("API Key 已更新")

if st.session_state.user_api_key:
    masked = st.session_state.user_api_key[:8] + "..." + st.session_state.user_api_key[-4:]
    st.caption(f"当前 Key：{masked}")
else:
    st.caption("未设置 API Key（将使用服务器默认配置）")

st.markdown('</div>', unsafe_allow_html=True)

# ===== 用户偏好 =====
st.markdown('<div class="setting-section"><h3>👤 用户偏好</h3>', unsafe_allow_html=True)

profile = st.selectbox(
    "默认学习深度",
    ["curious", "learner", "researcher"],
    format_func=lambda x: {"curious": "好奇者（300-500字）", "learner": "学习者（800-1500字）", "researcher": "研究者（2000+字）"}[x],
    index=["curious", "learner", "researcher"].index(st.session_state.user_profile)
)
if profile != st.session_state.user_profile:
    st.session_state.user_profile = profile
    st.success(f"已切换至 {profile} 画像")

narrative = st.checkbox("默认使用传承人口吻叙事", value=st.session_state.include_narrative)
if narrative != st.session_state.include_narrative:
    st.session_state.include_narrative = narrative

st.markdown('</div>', unsafe_allow_html=True)

# ===== 关于 =====
st.markdown('<div class="setting-section"><h3>📦 关于 HeritageMind</h3>', unsafe_allow_html=True)
st.markdown(f"""
<div style="font-size:0.88rem;color:var(--text2);line-height:1.8">
    <b>版本</b>：v1.0.0<br>
    <b>架构</b>：FastAPI + LangGraph + Streamlit<br>
    <b>向量库</b>：ChromaDB + BM25 + RRF<br>
    <b>知识图谱</b>：NetworkX + pyvis<br>
    <b>LLM</b>：当前 {st.session_state.selected_model}<br>
    <b>GitHub</b>：<a href="https://github.com/sunset9527/HeritageMind" target="_blank">sunset9527/HeritageMind</a>
</div>
""", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# Nav
st.markdown("---")
if st.button("🏠 首页", key="nav_home", use_container_width=True):
    st.switch_page("main.py")
if st.button("💬 AI 问答", key="nav_chat", use_container_width=True):
    st.switch_page("pages/1_Chat.py")
if st.button("🕸️ 知识图谱", key="nav_graph", use_container_width=True):
    st.switch_page("pages/2_Graph.py")
if st.button("⚙️ 设置", key="nav_settings", use_container_width=True, disabled=True):
    pass
