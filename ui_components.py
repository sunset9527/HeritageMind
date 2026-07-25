"""
HeritageMind · 共享 UI 组件
所有页面共用的 CSS、API 函数、会话初始化、渲染函数
"""
import streamlit as st
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime

API_BASE_URL = "http://localhost:8000"

# ============================================================================
# 全局 CSS（每个页面调用一次）
# ============================================================================

def inject_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

        :root {
            --bg: #F5F5F7; --card: #FFFFFF; --text: #1D1D1F; --text2: #6E6E73; --text3: #86868B;
            --accent: #BF4800; --craft: #2E7D32; --history: #1565C0; --heritage: #E65100; --synth: #6A1B9A;
            --border: rgba(0,0,0,0.06); --shadow1: 0 1px 3px rgba(0,0,0,0.04);
            --shadow2: 0 4px 20px rgba(0,0,0,0.06); --radius: 16px;
        }

        .stApp { background: var(--bg); }
        .stApp * {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif !important;
            -webkit-font-smoothing: antialiased;
        }
        #MainMenu, footer { visibility: hidden; }
        header[data-testid="stHeader"] { background: transparent; }

        /* 侧边栏 */
        [data-testid="stSidebar"] {
            background: rgba(255,255,255,0.65) !important;
            backdrop-filter: saturate(180%) blur(20px);
            -webkit-backdrop-filter: saturate(180%) blur(20px);
            border-right: 1px solid rgba(0,0,0,0.04);
        }

        /* Hero */
        .hero { text-align: center; padding: 56px 24px 40px; }
        .hero h1 { font-size: 3rem; font-weight: 800; letter-spacing: -0.04em; color: var(--text); margin: 0; line-height: 1.1; }
        .hero h1 span { background: linear-gradient(135deg, #BF4800, #E8734A); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .hero p { font-size: 1.1rem; color: var(--text2); margin-top: 12px; font-weight: 400; }

        /* Stats */
        .stat-card {
            background: var(--card); border-radius: var(--radius); padding: 24px 28px;
            box-shadow: var(--shadow1); border: 1px solid var(--border); text-align: center;
            transition: all 0.25s ease;
        }
        .stat-card:hover { box-shadow: var(--shadow2); transform: translateY(-2px); }
        .stat-num { font-size: 2.4rem; font-weight: 800; color: var(--text); letter-spacing: -0.03em; }
        .stat-label { font-size: 0.85rem; color: var(--text3); margin-top: 4px; }

        /* Feature cards */
        .feat {
            background: var(--card); border-radius: var(--radius); padding: 28px 24px;
            box-shadow: var(--shadow1); border: 1px solid var(--border); cursor: pointer;
            transition: all 0.25s ease; text-decoration: none; display: block;
        }
        .feat:hover { box-shadow: var(--shadow2); transform: translateY(-2px); }
        .feat-icon { font-size: 2rem; margin-bottom: 12px; }
        .feat-title { font-weight: 700; font-size: 1.05rem; color: var(--text); margin-bottom: 4px; }
        .feat-desc { font-size: 0.85rem; color: var(--text2); line-height: 1.5; }

        /* Agent card */
        .ac {
            background: var(--card); border-radius: var(--radius); padding: 20px 24px;
            margin: 12px 0; box-shadow: var(--shadow1); border: 1px solid var(--border);
            position: relative; overflow: hidden; transition: all 0.25s ease;
        }
        .ac:hover { box-shadow: var(--shadow2); transform: translateY(-1px); }
        .ac::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 4px; border-radius: 4px 0 0 4px; }
        .ac.craft::before { background: var(--craft); }
        .ac.history::before { background: var(--history); }
        .ac.heritage::before { background: var(--heritage); }
        .ac.synthesis::before { background: var(--synth); }
        .ac-top { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
        .ac-avatar { width: 30px; height: 30px; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: white; font-size: 0.85rem; font-weight: 700; }
        .ac-avatar.craft { background: var(--craft); } .ac-avatar.history { background: var(--history); }
        .ac-avatar.heritage { background: var(--heritage); } .ac-avatar.synthesis { background: var(--synth); }
        .ac-name { font-weight: 600; font-size: 0.88rem; color: var(--text); }
        .ac-time { margin-left: auto; font-size: 0.75rem; color: var(--text3); }
        .ac-body { font-size: 0.92rem; line-height: 1.72; color: var(--text); }

        /* User message */
        .um {
            background: linear-gradient(135deg, #1D1D1F, #2D2D30); color: #FFF;
            border-radius: var(--radius); padding: 16px 20px; margin: 12px 0 12px auto;
            max-width: 80%; font-size: 0.92rem; line-height: 1.65; box-shadow: var(--shadow2);
        }

        /* Timeline */
        .tl { position: relative; padding-left: 28px; }
        .tl::before { content: ''; position: absolute; left: 8px; top: 4px; bottom: 4px; width: 2px; background: linear-gradient(180deg, var(--accent), rgba(191,72,0,0.08)); border-radius: 1px; }
        .tl-n { position: relative; margin-bottom: 16px; padding: 14px 16px; background: var(--card); border-radius: 10px; box-shadow: var(--shadow1); border: 1px solid var(--border); }
        .tl-n::before { content: ''; position: absolute; left: -22px; top: 16px; width: 10px; height: 10px; background: var(--card); border: 2px solid var(--accent); border-radius: 50%; }
        .tl-nh { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; font-weight: 600; font-size: 0.85rem; }

        /* Gap */
        .gap { background: #FFFBEB; border: 1px solid rgba(230,160,30,0.15); border-radius: 10px; padding: 14px 18px; margin: 12px 0; font-size: 0.85rem; color: #8B6914; }

        /* Buttons */
        .stButton > button {
            border-radius: 100px !important; font-weight: 600 !important; font-size: 0.85rem !important;
            padding: 8px 20px !important; transition: all 0.25s ease !important; border: none !important;
        }
        .stButton > button:hover { transform: translateY(-1px); box-shadow: var(--shadow2); }

        /* Chat input */
        .stChatInput textarea {
            border-radius: 100px !important; border: 1px solid var(--border) !important;
            padding: 12px 20px !important; font-size: 0.92rem !important; box-shadow: var(--shadow1) !important;
        }

        /* Inputs */
        input, textarea, select {
            border-radius: 10px !important; border: 1px solid var(--border) !important;
        }
        input:focus, textarea:focus, select:focus {
            border-color: var(--accent) !important; box-shadow: 0 0 0 3px rgba(191,72,0,0.1) !important;
        }

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] { gap: 4px; background: transparent; padding: 4px; border-radius: 10px; }
        .stTabs [data-baseweb="tab"] { border-radius: 8px; font-weight: 500; font-size: 0.84rem; padding: 6px 16px; border: none; color: var(--text2); }
        .stTabs [data-baseweb="tab"][aria-selected="true"] { background: var(--text); color: white; }

        /* Metrics */
        [data-testid="stMetricValue"] { font-weight: 700 !important; font-size: 1.5rem !important; }

        /* Scrollbar */
        ::-webkit-scrollbar { width: 6px; } ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.12); border-radius: 3px; }

        hr { border: none; border-top: 1px solid var(--border); margin: 24px 0; }

        /* Settings form */
        .setting-section {
            background: var(--card); border-radius: var(--radius); padding: 24px 28px;
            margin-bottom: 16px; box-shadow: var(--shadow1); border: 1px solid var(--border);
        }
        .setting-section h3 { font-size: 1rem; font-weight: 700; color: var(--text); margin-bottom: 16px; }

        /* Nav */
        .nav-link {
            display: inline-flex; align-items: center; gap: 6px;
            padding: 8px 18px; border-radius: 100px; font-weight: 500; font-size: 0.85rem;
            color: var(--text2); text-decoration: none; transition: all 0.2s ease;
        }
        .nav-link:hover { background: var(--border); color: var(--text); }
        .nav-link.active { background: var(--text); color: white; }
    </style>
    """, unsafe_allow_html=True)


# ============================================================================
# 会话初始化
# ============================================================================

def init_session():
    """初始化共享会话状态（所有页面调用）"""
    defaults = {
        "messages": [],
        "user_profile": "curious",
        "include_narrative": False,
        "current_craft": None,
        "debate_session": None,
        # 认证
        "auth_token": None,
        "current_user": None,
        "show_register": False,
        # 设置
        "selected_model": "deepseek-chat",
        "user_api_key": "",
        "user_base_url": "https://api.deepseek.com/v1",
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


# ============================================================================
# API 函数
# ============================================================================

def call_api(endpoint: str, data: Dict = None, method: str = "GET") -> Dict:
    headers = {}
    if st.session_state.auth_token:
        headers["Authorization"] = f"Bearer {st.session_state.auth_token}"
    if st.session_state.user_api_key:
        headers["X-API-Key"] = st.session_state.user_api_key
        headers["X-API-Base"] = st.session_state.user_base_url
        headers["X-Model"] = st.session_state.selected_model
    try:
        if method == "GET":
            r = requests.get(f"{API_BASE_URL}{endpoint}", params=data, headers=headers, timeout=300)
        else:
            r = requests.post(f"{API_BASE_URL}{endpoint}", json=data, headers=headers, timeout=300)
        return r.json()
    except requests.exceptions.ConnectionError:
        return {"error": "API 服务未启动"}
    except Exception as e:
        return {"error": str(e)}


def login_user(username: str, password: str) -> Dict:
    try:
        r = requests.post(f"{API_BASE_URL}/auth/login", data={"username": username, "password": password}, timeout=30)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def register_user(username: str, email: str, password: str) -> Dict:
    try:
        r = requests.post(f"{API_BASE_URL}/auth/register", json={"username": username, "email": email, "password": password}, timeout=30)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def get_user_history(token: str, limit: int = 20) -> Dict:
    try:
        r = requests.get(f"{API_BASE_URL}/chat/history", params={"limit": limit}, headers={"Authorization": f"Bearer {token}"}, timeout=30)
        return r.json()
    except Exception:
        return {"items": [], "total": 0}


def query_api(question: str) -> Dict:
    return call_api("/query", {
        "question": question,
        "user_profile": st.session_state.user_profile,
        "include_narrative": st.session_state.include_narrative,
    }, "POST")


def get_graph_html(filter_type: str = None, layout: str = "force") -> str:
    params = {"layout": layout}
    if filter_type:
        params["filter_type"] = filter_type
    return call_api("/graph/visualize", params).get("html", "")


def get_graph_stats() -> Dict:
    return call_api("/graph/stats")


def get_crafts() -> List[Dict]:
    return call_api("/crafts").get("crafts", [])


def get_profiles() -> List[Dict]:
    return call_api("/profiles").get("profiles", [])


# ============================================================================
# Agent 卡片渲染
# ============================================================================

AGENT_META = {
    "craft_expert": ("🎨", "技艺专家", "craft"),
    "history_expert": ("📜", "历史专家", "history"),
    "heritage_expert": ("🏛️", "传承专家", "heritage"),
    "synthesis": ("✨", "综合分析", "synthesis"),
}


def agent_card(agent_type: str, content: str, timestamp: str = None):
    icon, name, cls = AGENT_META.get(agent_type, ("💬", "专家", "synthesis"))
    ts = timestamp or datetime.now().strftime("%H:%M")
    st.markdown(f"""
    <div class="ac {cls}">
        <div class="ac-top">
            <div class="ac-avatar {cls}">{icon}</div>
            <span class="ac-name">{name}</span>
            <span class="ac-time">{ts}</span>
        </div>
        <div class="ac-body">{content}</div>
    </div>
    """, unsafe_allow_html=True)


def user_bubble(content: str):
    st.markdown(f'<div class="um">{content}</div>', unsafe_allow_html=True)


def gap_notice(text: str):
    st.markdown(f'<div class="gap">⚠️ <b>知识缺口</b>：{text}</div>', unsafe_allow_html=True)
