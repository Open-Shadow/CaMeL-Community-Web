import { useEffect, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { api, useAuth } from '@/hooks/use-auth'
import { listActiveDisputes } from '@/lib/bounties'

interface ActiveDispute {
  id: number
  title: string
  status: string
  creator: { display_name: string }
  accepted_applicant: { display_name: string } | null
  arbitration: {
    creator_statement: string
    hunter_statement: string
  } | null
}

export default function AdminDisputesPage() {
  const { user } = useAuth()
  const [items, setItems] = useState<ActiveDispute[]>([])
  const [loading, setLoading] = useState(true)
  const [ratio, setRatio] = useState('0.5')

  const load = async () => {
    setLoading(true)
    try {
      setItems(await listActiveDisputes())
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  if (!user || !['MODERATOR', 'ADMIN'].includes(user.role)) {
    return <div className="py-12 text-center text-muted-foreground">需要版主或管理员权限。</div>
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">争议仲裁</h1>
        <p className="mt-2 text-sm text-muted-foreground">活跃争议列表与终审操作。</p>
      </div>
      {loading ? <div className="text-muted-foreground">加载中...</div> : null}
      <div className="space-y-4">
        {items.map((item) => (
          <Card key={item.id}>
            <CardHeader>
              <CardTitle>{item.title}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div>状态：{item.status}</div>
              <div>发布者：{item.creator.display_name}</div>
              <div>接单者：{item.accepted_applicant?.display_name || '未分配'}</div>
              <div className="rounded-lg border bg-muted/20 p-3">
                <div>发布者陈述：{item.arbitration?.creator_statement || '暂无'}</div>
                <div className="mt-2">接单者陈述：{item.arbitration?.hunter_statement || '暂无'}</div>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Input className="w-24" value={ratio} onChange={(event) => setRatio(event.target.value)} />
                <Button
                  variant="outline"
                  onClick={async () => {
                    await api.post(`/bounties/${item.id}/arbitration/admin-finalize`, { result: 'CREATOR_WIN', hunter_ratio: 0 })
                    await load()
                  }}
                >
                  终审发布者胜
                </Button>
                <Button
                  variant="outline"
                  onClick={async () => {
                    await api.post(`/bounties/${item.id}/arbitration/admin-finalize`, { result: 'HUNTER_WIN', hunter_ratio: 1 })
                    await load()
                  }}
                >
                  终审接单者胜
                </Button>
                <Button
                  onClick={async () => {
                    await api.post(`/bounties/${item.id}/arbitration/admin-finalize`, {
                      result: 'PARTIAL',
                      hunter_ratio: Number(ratio),
                    })
                    await load()
                  }}
                >
                  按比例终审
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
