<template>
  <section class="platform-links">
    <router-link to="/chat"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5.5h16v10H8l-4 3v-13Z" /></svg><div><strong>智能问答</strong><span>带着问题，进入多智能体协作链路</span></div></router-link>
    <router-link to="/encyclopedia"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 0-3 3V4Z" /><path d="M8 8h7M8 12h7" /></svg><div><strong>技艺百科</strong><span>沿着条目阅读一门手艺的脉络</span></div></router-link>
    <router-link to="/graph"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="6" cy="12" r="2" /><circle cx="18" cy="6" r="2" /><circle cx="18" cy="18" r="2" /><path d="m8 11 8-4M8 13l8 4" /></svg><div><strong>知识图谱</strong><span>探索技艺、地域与传承的关联</span></div></router-link>
  </section>
</template>
<style scoped>
.platform-links{display:grid;grid-template-columns:repeat(3,1fr);max-width:1120px;margin:0 auto 82px;padding:0 24px;gap:14px}.platform-links a{display:flex;gap:15px;align-items:flex-start;padding:22px;background:#fffaf0;border:1px solid rgba(82,61,36,.17);color:var(--text);text-decoration:none;transition:.2s ease}.platform-links a:hover{border-color:var(--accent);transform:translateY(-2px)}svg{width:26px;height:26px;flex:0 0 auto;fill:none;stroke:var(--accent);stroke-width:1.45}strong,span{display:block}strong{font-family:var(--font-brush);font-size:1.55rem;font-weight:400;letter-spacing:.09em}span{margin-top:4px;color:var(--text-secondary);font-size:.72rem;line-height:1.6}@media(max-width:760px){.platform-links{grid-template-columns:1fr;margin-bottom:55px;padding:0 18px}}
</style>
