import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import chatSource from './views/ChatView.vue?raw'
import settingsSource from './views/SettingsView.vue?raw'
import heroSource from './components/dashboard/HeroBanner.vue?raw'
import statsSource from './components/dashboard/StatsBar.vue?raw'

const styles = readFileSync(new URL('./assets/styles/main.css', import.meta.url), 'utf8')

describe('public-page typography', () => {
  it('sets a 14px minimum for shared captions and page introductions', () => {
    expect(styles).toContain('.caption {\n  font-size: 0.875rem;')
    expect(styles).toContain('font-size: .94rem;')
  })

  it('does not leave 11px labels in the chat workspace', () => {
    expect(chatSource).not.toContain('text-[11px]')
  })

  it('uses defined text colors for settings labels', () => {
    expect(settingsSource).not.toContain('var(--text2)')
    expect(settingsSource).not.toContain('var(--text3)')
  })

  it('enlarges the homepage metric labels and descriptions', () => {
    expect(heroSource).toContain('font-size:.8rem')
    expect(statsSource).toContain('font-size: .88rem')
    expect(statsSource).toContain('font-size: .78rem')
  })
})
