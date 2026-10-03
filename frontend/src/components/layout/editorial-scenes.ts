export type EditorialScene = 'indigo' | 'ink' | 'bamboo' | 'clay'

export interface EditorialSceneDefinition {
  artwork: string
  alt: string
}

export const editorialScenes: Record<EditorialScene, EditorialSceneDefinition> = {
  indigo: {
    artwork: '/editorial/hero-archive-textile-v1.png',
    alt: '靛染线轴和织物越出乡村织造照片的编辑式艺术主视觉',
  },
  ink: {
    artwork: '/editorial/scene-ink-print-v1.png',
    alt: '纸墨木刻越出传统造纸工坊照片的编辑式艺术主视觉',
  },
  bamboo: {
    artwork: '/editorial/scene-bamboo-workshop-v1.png',
    alt: '竹篾编器越出传统竹编工坊照片的编辑式艺术主视觉',
  },
  clay: {
    artwork: '/editorial/scene-clay-workshop-v1.png',
    alt: '陶器和工具越出制陶工坊照片的编辑式艺术主视觉',
  },
}
