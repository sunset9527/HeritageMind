import { describe, expect, it } from 'vitest'
import heroSource from './HeroBanner.vue?raw'
import statsSource from './StatsBar.vue?raw'
import craftsSource from './CraftCarousel.vue?raw'

describe('homepage editorial surface', () => {
  it('aligns the hero and its evidence band on one archival surface', () => {
    const hero = heroSource
    const stats = statsSource

    expect(hero).toContain('max-width:1120px')
    expect(stats).toContain('background: #1c2016')
  })

  it('keeps below-the-fold craft cards inside the same olive palette', () => {
    const crafts = craftsSource

    expect(crafts).toContain('background: #293025')
    expect(crafts).toContain('rgba(28, 32, 22')
  })
})
