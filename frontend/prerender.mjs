import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'

const root = process.cwd()
const dist = resolve(root, 'dist')
const manifest = JSON.parse(await readFile(resolve(root, 'prerender-manifest.json'), 'utf8'))
const template = await readFile(resolve(dist, 'index.html'), 'utf8')
const baseUrl = (process.env.VITE_SITE_URL || '').replace(/\/$/, '')

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]))
}

function renderDocument(item, path, kind) {
  const title = `${item.name}｜${kind}｜HeritageMind`
  const description = item.summary || `${item.name}的非遗资料与公开来源。`
  const canonical = baseUrl ? `<link rel="canonical" href="${escapeHtml(`${baseUrl}${path}`)}">` : ''
  return template
    .replace(/<title>.*?<\/title>/, `<title>${escapeHtml(title)}</title>`)
    .replace('</head>', `<meta name="description" content="${escapeHtml(description)}">${canonical}</head>`)
}

async function prerender(items, prefix, kind) {
  for (const item of items) {
    const path = `${prefix}/${encodeURIComponent(item.slug)}`
    const destination = resolve(dist, prefix.slice(1), item.slug, 'index.html')
    await mkdir(resolve(destination, '..'), { recursive: true })
    await writeFile(destination, renderDocument(item, path, kind), 'utf8')
  }
}

await prerender(manifest.crafts || [], '/encyclopedia', '技艺百科')
await prerender(manifest.inheritors || [], '/inheritors', '传承人档案')
console.log(`Pre-rendered ${(manifest.crafts || []).length + (manifest.inheritors || []).length} public detail pages.`)
