import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'

const CATEGORIES = [
  { value: '', label: '全部' },
  { value: 'CODE_DEV', label: '代码开发' },
  { value: 'WRITING', label: '文案写作' },
  { value: 'DATA_ANALYTICS', label: '数据分析' },
  { value: 'ACADEMIC', label: '学术研究' },
  { value: 'TRANSLATION', label: '翻译' },
  { value: 'CREATIVE', label: '创意设计' },
  { value: 'AGENT', label: 'Agent 工具' },
  { value: 'PRODUCTIVITY', label: '办公效率' },
]

// Mock data for display without backend
const MOCK_SKILLS = [
  { id: 1, name: 'Python 数据分析助手', description: '自动分析数据集，生成可视化报告', category: 'DATA_ANALYTICS', tags: ['Python', '数据'], pricing_model: 'FREE', price_per_use: null, avg_rating: 4.8, total_calls: 312, creator_name: 'Alice', status: 'APPROVED' },
  { id: 2, name: 'React 代码审查', description: '自动审查 React 代码，提供优化建议', category: 'CODE_DEV', tags: ['React', 'TypeScript'], pricing_model: 'PER_USE', price_per_use: 0.05, avg_rating: 4.9, total_calls: 218, creator_name: 'Bob', status: 'APPROVED' },
  { id: 3, name: 'Stable Diffusion 提示词优化', description: '优化 SD 提示词，提升图像质量', category: 'CREATIVE', tags: ['AI', '绘画'], pricing_model: 'FREE', price_per_use: null, avg_rating: 4.7, total_calls: 540, creator_name: 'Carol', status: 'APPROVED' },
  { id: 4, name: '学术论文润色', description: '英文学术论文语言润色与格式规范', category: 'ACADEMIC', tags: ['论文', '英文'], pricing_model: 'PER_USE', price_per_use: 0.1, avg_rating: 4.6, total_calls: 89, creator_name: 'Dave', status: 'APPROVED' },
  { id: 5, name: 'SEO 文章生成', description: '根据关键词生成 SEO 友好的文章', category: 'WRITING', tags: ['SEO', '内容'], pricing_model: 'PER_USE', price_per_use: 0.08, avg_rating: 4.5, total_calls: 176, creator_name: 'Eve', status: 'APPROVED' },
  { id: 6, name: 'ChatGPT 提示工程师', description: '帮你设计高效的 ChatGPT 提示词', category: 'PRODUCTIVITY', tags: ['GPT', '提示词'], pricing_model: 'FREE', price_per_use: null, avg_rating: 4.9, total_calls: 623, creator_name: 'Frank', status: 'APPROVED' },
]

export default function MarketplacePage() {
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  const [category, setCategory] = useState('')

  const filtered = MOCK_SKILLS.filter(s =>
    (!category || s.category === category) &&
    (!q || s.name.includes(q) || s.tags.some(t => t.includes(q)))
  )

  return (
    <div className="max-w-5xl mx-auto py-8 px-4">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">技能市场</h1>
        <Button onClick={() => navigate('/marketplace/create')}>+ 上架技能</Button>
      </div>

      <div className="flex gap-3 mb-4 flex-wrap">
        <Input placeholder="搜索技能..." value={q} onChange={e => setQ(e.target.value)} className="w-56" />
        {CATEGORIES.map(c => (
          <Button key={c.value} variant={category === c.value ? 'default' : 'outline'} size="sm"
            onClick={() => setCategory(c.value)}>{c.label}</Button>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map(skill => (
          <Card key={skill.id} className="cursor-pointer hover:shadow-md transition-shadow"
            onClick={() => navigate(`/marketplace/${skill.id}`)}>
            <CardContent className="p-4">
              <div className="flex flex-wrap gap-1 mb-2">
                {skill.tags.map(t => <Badge key={t} variant="secondary" className="text-xs">{t}</Badge>)}
              </div>
              <h3 className="font-semibold mb-1">{skill.name}</h3>
              <p className="text-sm text-muted-foreground mb-3 line-clamp-2">{skill.description}</p>
              <div className="text-xs text-muted-foreground mb-3">
                by {skill.creator_name} · ⭐{skill.avg_rating} · {skill.total_calls}次调用
              </div>
              <div className="flex items-center justify-between">
                <span className="font-bold text-amber-500">
                  {skill.pricing_model === 'FREE' ? '免费' : `$${skill.price_per_use}/次`}
                </span>
                <Button size="sm" onClick={e => { e.stopPropagation(); navigate(`/marketplace/${skill.id}`) }}>
                  查看详情
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
