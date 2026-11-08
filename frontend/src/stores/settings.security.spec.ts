// @vitest-environment jsdom

import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { useSettingsStore } from './settings'


describe('settings API key lifecycle', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    setActivePinia(createPinia())
  })

  it('deletes the legacy localStorage key instead of migrating it', () => {
    localStorage.setItem('hm_user_api_key', 'legacy-secret')

    const settings = useSettingsStore()

    expect(settings.userApiKey).toBe('')
    expect(localStorage.getItem('hm_user_api_key')).toBeNull()
    expect(sessionStorage.getItem('hm_user_api_key')).toBeNull()
  })

  it('keeps API keys only for the current browser session', () => {
    const settings = useSettingsStore()

    settings.setApiKey('session-secret')

    expect(sessionStorage.getItem('hm_user_api_key')).toBe('session-secret')
    expect(localStorage.getItem('hm_user_api_key')).toBeNull()
    expect(localStorage.getItem('hm_selected_model')).toBe('deepseek-chat')
  })

  it('clears the in-memory and session copies together', () => {
    const settings = useSettingsStore()
    settings.setApiKey('session-secret')

    settings.clearApiKey()

    expect(settings.userApiKey).toBe('')
    expect(settings.hasCustomKey).toBe(false)
    expect(sessionStorage.getItem('hm_user_api_key')).toBeNull()
  })
})
