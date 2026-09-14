import { describe, expect, it } from 'vitest'
import { buildDashboardMetrics } from './platform'

describe('buildDashboardMetrics', () => {
  it('uses API totals instead of hard-coded platform counts', () => {
    expect(buildDashboardMetrics(
      [{ id: 'jingtailan', name: '景泰蓝' }, { id: 'suxiu', name: '苏绣' }],
      { total_documents: 69 },
    )).toEqual([
      { value: '2', label: '已收录技艺', description: '来自服务端技艺目录' },
      { value: '69', label: '已加载文档', description: '来自服务端文档摘要' },
      { value: '可核查', label: '知识质量', description: '资料治理与检索评测均留有记录' },
    ])
  })

  it('shows an honest placeholder while a summary is unavailable', () => {
    expect(buildDashboardMetrics(undefined, undefined)[1].value).toBe('—')
  })
})
