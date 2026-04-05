import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent } from '@/components/ui/card'

const MOCK_SKILLS: Record<number, any> = {
  1: { id: 1, name: 'Python 数据分析助手', description: '自动分析数据集，生成可视化报告和统计摘要。支持 CSV、JSON 格式输入，输出 Markdown 格式报告。', category: 'DATA_ANALYTICS', tags: ['Python', '数据'], pricing_model: 'FREE', price_per_use: null, avg_rating: 4.8, total_calls: 312, review_count: 45, creator_name: 'Alice', system_prompt: '你是一个专业的数据分析师...', example_input: '分析以下销售数据：Q1: 100, Q2: 150, Q3: 120, Q4: 200', example_output: '## 销售数据分析报告\n- 全年总销售：570\n- 最高季度：Q4 (200)\n- 环比增长：Q4 vs Q3 +66.7%' },
  2: { id: 2, name: 'React 代码审查', description: '自动审查 React 代码，提供优化建议、性能分析和最佳实践指导。', category: 'CODE_DEV', tags: ['React', 'TypeScript'], pricing_model: 'PER_USE', price_per_use: 0.05, avg_rating: 4.9, total_calls: 218, review_count: 32, creator_name: 'Bob', example_input: 'const App = () => { const [data, setData] = useState([]); useEffect(() => { fetch("/api").then(r=>r.json()).then(setData) }, []) }', example_output: '## 代码审查结果\n✅ 基本结构正确\n⚠️ 建议添加错误处理\n⚠️ useEffect 缺少清理函数' },
}

export default function SkillDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const skill = MOCK_SKILLS[Number(id)] || MOCK_SKILLS[1]
  const [input, setInput] = useState(skill.example_input || '')
  const [output, setOutput] = useState('')
  const [loading, setLoading] = useState(false)

  const handleCall = async () => {
    if (!input.trim()) return
    setLoading(true)
    await new Promise(r => setTimeout(r, 800))
    setOutput(`[模拟输出]\n\n基于您的输入「${input.slice(0, 30)}...」\n\n${skill.example_output || '处理完成，结果已生成。'}`)
    setLoading(false)
  }

  return (
    <div className="max-w-3xl mx-auto py-8 px-4">
      <Button variant="ghost" className="mb-4" onClick={() => navigate('/marketplace')}>← 返回市场</Button>

      <div className="mb-6">
        <div className="flex flex-wrap gap-2 mb-2">
          {skill.tags.map((t: string) => <Badge key={t} variant="secondary">{t}</Badge>)}
        </div>
        <h1 className="text-2xl font-bold mb-2">{skill.name}</h1>
        <p className="text-muted-foreground mb-3">{skill.description}</p>
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <span>by {skill.creator_name}</span>
          <span>⭐ {skill.avg_rating} ({skill.review_count}条评价)</span>
          <span>{skill.total_calls} 次调用</span>
          <span className="font-semibold text-amber-500 text-base">
            {skill.pricing_model === 'FREE' ? '免费' : `$${skill.price_per_use}/次`}
          </span>
        </div>
      </div>

      <Card className="mb-6">
        <CardContent className="p-4">
          <h2 className="font-semibold mb-3">试用技能</h2>
          <Textarea
            placeholder="输入内容..."
            value={input}
            onChange={e => setInput(e.target.value)}
            rows={4}
            className="mb-3"
          />
          <Button onClick={handleCall} disabled={loading || !input.trim()}>
            {loading ? '处理中...' : '运行'}
          </Button>
          {output && (
            <pre className="mt-4 p-3 bg-muted rounded text-sm whitespace-pre-wrap">{output}</pre>
          )}
        </CardContent>
      </Card>

      {skill.example_output && (
        <Card>
          <CardContent className="p-4">
            <h2 className="font-semibold mb-2">示例输出</h2>
            <pre className="text-sm bg-muted p-3 rounded whitespace-pre-wrap">{skill.example_output}</pre>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
