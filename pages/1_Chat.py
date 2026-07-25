"""
HeritageMind · AI 问答
"""
import streamlit as st
import time
from datetime import datetime
from ui_components import (
    inject_css, init_session, query_api, agent_card, gap_notice,
    get_user_history, login_user, register_user, get_profiles, get_crafts, get_graph_stats, API_BASE_URL
)

st.set_page_config(page_title="AI 问答", page_icon="💬", layout="wide", initial_sidebar_state="expanded")
inject_css()
init_session()

# 处理从首页跳转来的问题
if "_pending_question" in st.session_state and st.session_state["_pending_question"]:
    pending = st.session_state.pop("_pending_question")
    st.session_state.messages.append({"role": "user", "content": pending, "timestamp": datetime.now().strftime("%H:%M")})

# ===== 侧边栏 =====
with st.sidebar:
    st.markdown('<div style="padding:8px 0 20px;text-align:center"><div style="font-size:2rem">🏺</div><div style="font-weight:800;font-size:1.1rem">HeritageMind</div></div>', unsafe_allow_html=True)

    # 用户
    if st.session_state.auth_token and st.session_state.current_user:
        u = st.session_state.current_user
        st.markdown(f'<div style="background:var(--card);border-radius:12px;padding:12px 16px;margin-bottom:12px;border:1px solid var(--border)"><div style="font-weight:600;font-size:0.88rem">{u.get("username","?")}</div></div>', unsafe_allow_html=True)
        if st.button("退出", use_container_width=True):
            st.session_state.auth_token = None
            st.session_state.current_user = None
            st.session_state.messages = []
            st.rerun()

        st.markdown("##### 历史对话")
        hist = get_user_history(st.session_state.auth_token, limit=8)
        for item in hist.get("items", []):
            pre = item.get("question", "")[:30]
            st.button(pre + "…", key=f"h_{item['id']}", use_container_width=True)
        st.markdown("---")
    else:
        # 登录
        if st.session_state.show_register:
            st.markdown("##### 注册")
            ru = st.text_input("用户名", key="r_u")
            re = st.text_input("邮箱", key="r_e")
            rp = st.text_input("密码", type="password", key="r_p")
            if st.button("注册", use_container_width=True, type="primary"):
                if ru and re and rp and len(rp) >= 6:
                    r = register_user(ru, re, rp)
                    if "access_token" in r:
                        st.session_state.auth_token = r["access_token"]
                        st.session_state.current_user = r.get("user", {})
                        st.session_state.show_register = False
                        st.rerun()
                    else:
                        st.error(r.get("detail", "注册失败"))
                else:
                    st.error("请完整填写（密码≥6位）")
            if st.button("← 登录", use_container_width=True):
                st.session_state.show_register = False
                st.rerun()
        else:
            st.markdown("##### 登录")
            lu = st.text_input("用户名", key="l_u")
            lp = st.text_input("密码", type="password", key="l_p")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("登录", use_container_width=True, type="primary"):
                    if lu and lp:
                        r = login_user(lu, lp)
                        if "access_token" in r:
                            st.session_state.auth_token = r["access_token"]
                            st.session_state.current_user = r.get("user", {})
                            st.rerun()
                        else:
                            st.error("用户名或密码错误")
            with c2:
                if st.button("注册", use_container_width=True):
                    st.session_state.show_register = True
                    st.rerun()
        st.markdown("---")

    # 画像
    st.markdown("##### 学习深度")
    profiles = get_profiles() or [{"id": "curious", "name": "好奇者"}, {"id": "learner", "name": "学习者"}, {"id": "researcher", "name": "研究者"}]
    pn = {p["id"]: p["name"] for p in profiles}
    pk = list(pn.keys())
    idx = pk.index(st.session_state.user_profile) if st.session_state.user_profile in pk else 0
    sel = st.selectbox("", pk, format_func=lambda x: pn[x], index=idx, label_visibility="collapsed")
    if sel != st.session_state.user_profile:
        st.session_state.user_profile = sel
        st.rerun()

    st.markdown("---")
    st.markdown("##### 技艺")
    crafts = get_crafts() or [{"name": n} for n in ["景泰蓝","苏绣","龙泉青瓷","宜兴紫砂","芜湖铁画","蜀锦"]]
    opts = ["全部"] + [c["name"] for c in crafts]
    ci = opts.index(st.session_state.current_craft) if st.session_state.current_craft and st.session_state.current_craft in opts else 0
    sel2 = st.selectbox("", opts, index=ci, label_visibility="collapsed")
    st.session_state.current_craft = sel2 if sel2 != "全部" else None

    st.markdown("---")
    st.markdown("##### 模式")
    inc = st.checkbox("传承人口吻", value=st.session_state.include_narrative)
    if inc != st.session_state.include_narrative:
        st.session_state.include_narrative = inc

    # 导航
    st.markdown("---")
    if st.button("🏠 首页", key="nav_home", use_container_width=True):
        st.switch_page("main.py")
    if st.button("💬 AI 问答", key="nav_chat", use_container_width=True, disabled=True):
        pass
    if st.button("🕸️ 知识图谱", key="nav_graph", use_container_width=True):
        st.switch_page("pages/2_Graph.py")
    if st.button("⚙️ 设置", key="nav_settings", use_container_width=True):
        st.switch_page("pages/3_Settings.py")

# ===== 主内容 =====
st.markdown('<div style="padding:16px 0 8px"><h2 style="font-weight:800;letter-spacing:-0.03em;margin:0">AI 问答</h2><p style="color:var(--text2);margin:4px 0 0">多专家 Agent 协作 · 当前模型：' + st.session_state.selected_model + '</p></div>', unsafe_allow_html=True)

left, right = st.columns([3, 2])

with left:
    # 快捷问题
    examples = [
        "景泰蓝的制作流程是什么？",
        "苏绣有哪些针法特点？",
        "龙泉青瓷的釉色如何形成？",
        "宜兴紫砂壶为什么适合泡茶？",
        "芜湖铁画的传承现状如何？",
        "蜀锦与宋锦有什么区别？",
    ]
    cols = st.columns(3)
    for i, q in enumerate(examples):
        with cols[i % 3]:
            if st.button(q, key=f"qc_{i}", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": q, "timestamp": datetime.now().strftime("%H:%M")})
                st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)

    # 聊天历史
    for msg in st.session_state.messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        ts = msg.get("timestamp", "")
        meta = msg.get("metadata", {})

        if role == "user":
            with st.chat_message("user"):
                st.markdown(content)
        else:
            source_agents = meta.get("source_agents", [])
            debate = meta.get("debate_session")

            if source_agents:
                for a in source_agents:
                    at = a.get("type", "synthesis")
                    ac = a.get("content", "")
                    if ac:
                        agent_card(at, ac[:500] + ("…" if len(ac) > 500 else ""), ts)
            else:
                agent_card("synthesis", content[:500], ts)

            if debate:
                st.session_state.debate_session = debate

            if meta.get("has_gaps"):
                gap_notice(meta.get("gap_report", ""))

            if meta.get("citations"):
                with st.expander("📎 引用"):
                    for c in meta["citations"][:3]:
                        st.markdown(f"- *{c.get('title','来源')}*")

    # 输入
    if prompt := st.chat_input("提出你的问题…"):
        st.session_state.messages.append({"role": "user", "content": prompt, "timestamp": datetime.now().strftime("%H:%M")})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Agent 协作思考中…"):
                t0 = time.time()
                resp = query_api(prompt)
                elapsed = time.time() - t0
                if "error" in resp:
                    st.error(resp["error"])
                else:
                    answer = resp.get("answer", "")
                    source_agents = resp.get("source_agents", [])
                    debate = resp.get("debate_session")
                    has_gaps = resp.get("has_gaps", False)
                    gap_report = resp.get("gap_report", "")

                    if source_agents:
                        for a in source_agents:
                            at = a.get("type", "synthesis")
                            ac = a.get("content", "")
                            if ac:
                                agent_card(at, ac[:500] + ("…" if len(ac) > 500 else ""), datetime.now().strftime("%H:%M"))
                    else:
                        agent_card("synthesis", answer[:500], datetime.now().strftime("%H:%M"))

                    if debate:
                        st.session_state.debate_session = debate
                    if has_gaps:
                        gap_notice(gap_report)

                    st.caption(f"⏱ {elapsed:.1f}s · {st.session_state.selected_model}")

                    st.session_state.messages.append({
                        "role": "assistant", "content": answer,
                        "timestamp": datetime.now().strftime("%H:%M"),
                        "metadata": {
                            "source_agents": source_agents,
                            "debate_session": debate,
                            "has_gaps": has_gaps,
                            "gap_report": gap_report,
                            "citations": resp.get("citations", [])
                        }
                    })

with right:
    st.markdown('<div style="background:var(--card);border-radius:20px;padding:24px;box-shadow:var(--shadow1);border:1px solid var(--border)">', unsafe_allow_html=True)
    t1, t2 = st.tabs(["⚔️ 辩论", "📚 引用"])

    with t1:
        if st.session_state.debate_session:
            rounds = st.session_state.debate_session.get("rounds", [])
            st.markdown('<div class="tl">', unsafe_allow_html=True)
            agi = {"craft_expert": "🎨", "history_expert": "📜", "heritage_expert": "🏛️"}
            agn = {"craft_expert": "技艺", "history_expert": "历史", "heritage_expert": "传承"}
            for i, rnd in enumerate(rounds):
                agent = rnd.get("agent", "")
                st.markdown(f"""
                <div class="tl-n"><div class="tl-nh">{agi.get(agent,'💬')} {agn.get(agent,'专家')}</div>
                <div style="font-size:0.82rem;color:var(--text2)">{rnd.get('content','')[:150]}{'…' if len(rnd.get('content',''))>150 else ''}</div></div>
                """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("提问后展示辩论过程")

    with t2:
        cits = []
        for m in st.session_state.messages:
            if m.get("role") == "assistant" and m.get("metadata"):
                cits.extend(m["metadata"].get("citations", []))
        if cits:
            for c in cits:
                st.markdown(f"- *{c.get('title','来源')}*")
        else:
            st.info("提问后展示引用来源")
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("🗑️ 清空对话", use_container_width=True):
        st.session_state.messages = []
        st.session_state.debate_session = None
        st.rerun()
