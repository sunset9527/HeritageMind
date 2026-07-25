"""
HeritageMind · 知识图谱
"""
import streamlit as st
from ui_components import inject_css, init_session, get_graph_html, get_graph_stats

st.set_page_config(page_title="知识图谱", page_icon="🕸️", layout="wide", initial_sidebar_state="collapsed")
inject_css()
init_session()

st.markdown('<h2 style="font-weight:800;letter-spacing:-0.03em;margin-bottom:4px">知识图谱</h2><p style="color:var(--text2);margin-top:0">非遗技艺 · 材料 · 工具 · 传承人 · 地域 · 朝代 多维关联</p>', unsafe_allow_html=True)

# Stats bar
stats = get_graph_stats()
if isinstance(stats, dict) and "total_nodes" in stats:
    c1, c2, c3 = st.columns(3)
    c1.metric("节点总数", stats.get("total_nodes", 0))
    c2.metric("关系边数", stats.get("total_edges", 0))
    node_types = stats.get("node_types", {})
    tn = {"craft": "技艺", "material": "材料", "tool": "工具", "inheritor": "传承人", "region": "地域", "dynasty": "朝代"}
    type_str = "、".join([f"{tn.get(k,k)}:{v}" for k, v in node_types.items()])
    c3.metric("节点类型", f"{len(node_types)} 种")

st.markdown("<br>", unsafe_allow_html=True)

# Controls
ctl1, ctl2 = st.columns([1, 1])
with ctl1:
    layout = st.selectbox("布局方式", ["force", "circular"], format_func=lambda x: "力导向布局" if x == "force" else "圆形布局")
with ctl2:
    filters = [None, "craft", "material", "tool", "inheritor", "region", "dynasty"]
    flabels = ["全部类型", "技艺", "材料", "工具", "传承人", "地域", "朝代"]
    fi = st.selectbox("节点筛选", range(len(filters)), format_func=lambda x: flabels[x])

# Graph display
with st.spinner("加载知识图谱…"):
    html = get_graph_html(filter_type=filters[fi], layout=layout)

if html and html.startswith("<!"):
    st.components.v1.html(html, height=620, scrolling=True)
elif "pyvis未安装" in html:
    st.warning("pyvis 未安装，请执行 `pip install pyvis>=2.1.0`")
else:
    st.info("图谱加载中…")

# Node type legend
st.markdown("---")
st.markdown("##### 节点颜色图例")
colors = {
    "技艺": ("#FF6B6B", "craft"),
    "材料": ("#4ECDC4", "material"),
    "工具": ("#45B7D1", "tool"),
    "传承人": ("#96CEB4", "inheritor"),
    "地域": ("#FFEAA7", "region"),
    "朝代": ("#DDA0DD", "dynasty"),
}
leg_cols = st.columns(6)
for i, (name, (color, _)) in enumerate(colors.items()):
    with leg_cols[i]:
        st.markdown(f'<div style="display:flex;align-items:center;gap:8px"><div style="width:16px;height:16px;border-radius:4px;background:{color}"></div><span style="font-size:0.82rem;color:var(--text2)">{name}</span></div>', unsafe_allow_html=True)

# Nav
st.markdown("---")
if st.button("🏠 首页", key="nav_home", use_container_width=True):
    st.switch_page("main.py")
if st.button("💬 AI 问答", key="nav_chat", use_container_width=True):
    st.switch_page("pages/1_Chat.py")
if st.button("🕸️ 知识图谱", key="nav_graph", use_container_width=True, disabled=True):
    pass
if st.button("⚙️ 设置", key="nav_settings", use_container_width=True):
    st.switch_page("pages/3_Settings.py")
