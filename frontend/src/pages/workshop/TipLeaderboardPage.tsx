import { useState, useEffect } from 'react'
import axios from 'axios'

interface LeaderboardEntry {
  rank: number
  user_id: number
  display_name: string
  avatar_url: string
  total_tips: number
}

export default function TipLeaderboardPage() {
  const [entries, setEntries] = useState<LeaderboardEntry[]>([])

  useEffect(() => {
    axios.get('/api/workshop/tips/leaderboard').then(r => setEntries(r.data)).catch(() => {})
  }, [])

  return (
    <div className="container mx-auto px-4 py-8 max-w-2xl">
      <h1 className="text-2xl font-bold mb-6">打赏排行榜</h1>
      <div className="space-y-3">
        {entries.map(e => (
          <div key={e.user_id} className="flex items-center gap-4 p-3 border rounded-lg">
            <span className="text-lg font-bold w-8 text-center text-muted-foreground">#{e.rank}</span>
            <div className="flex-1">
              <p className="font-medium">{e.display_name}</p>
            </div>
            <span className="font-semibold">${e.total_tips.toFixed(2)}</span>
          </div>
        ))}
        {entries.length === 0 && (
          <p className="text-center text-muted-foreground py-8">暂无数据</p>
        )}
      </div>
    </div>
  )
}
