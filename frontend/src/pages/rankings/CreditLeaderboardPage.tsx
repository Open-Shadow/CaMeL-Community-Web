import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { api } from '@/hooks/use-auth';
import { useAuth } from '@/hooks/use-auth';
import { Trophy, Medal, Award } from 'lucide-react';

interface LeaderboardEntry {
  rank: number;
  user_id: number;
  username: string;
  display_name: string;
  avatar_url: string;
  level: string;
  credit_score: number;
}

interface LeaderboardData {
  entries: LeaderboardEntry[];
  updated_at: string | null;
  my_rank: number | null;
  my_score: number | null;
}

const LEVEL_LABELS: Record<string, string> = {
  SEED: '🌱 新芽', CRAFTSMAN: '🔧 工匠', EXPERT: '⚡ 专家',
  MASTER: '🏆 大师', GRANDMASTER: '👑 宗师',
};

function RankIcon({ rank }: { rank: number }) {
  if (rank === 1) return <Trophy className="h-5 w-5 text-yellow-500" />;
  if (rank === 2) return <Medal className="h-5 w-5 text-gray-400" />;
  if (rank === 3) return <Award className="h-5 w-5 text-amber-600" />;
  return <span className="w-5 text-center text-sm font-mono text-muted-foreground">{rank}</span>;
}

export function CreditLeaderboardPage() {
  const { user } = useAuth();
  const [data, setData] = useState<LeaderboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    api.get('/rankings/credit')
      .then((res) => setData(res.data))
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, []);

  return (
    <div className="container mx-auto py-8 max-w-2xl space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">信用分排行榜</h1>
        {data?.updated_at && (
          <p className="text-xs text-muted-foreground">
            更新于 {new Date(data.updated_at).toLocaleString('zh-CN')}
          </p>
        )}
      </div>

      {/* My rank card */}
      {user && data?.my_rank && (
        <Card className="bg-primary/5 border-primary/20">
          <CardContent className="flex items-center justify-between py-4">
            <div className="flex items-center gap-3">
              <span className="text-sm text-muted-foreground">我的排名</span>
              <span className="text-2xl font-bold">#{data.my_rank}</span>
            </div>
            <div className="text-right">
              <p className="text-lg font-bold">{data.my_score} 分</p>
              <p className="text-xs text-muted-foreground">{LEVEL_LABELS[user.level] || user.level}</p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Leaderboard */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Top 50</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <p className="text-center py-8 text-muted-foreground">加载中...</p>
          ) : !data || data.entries.length === 0 ? (
            <p className="text-center py-8 text-muted-foreground">暂无数据</p>
          ) : (
            <div className="divide-y">
              {data.entries.map((entry) => (
                <div
                  key={entry.user_id}
                  className={`flex items-center gap-3 px-4 py-3 hover:bg-muted/30 transition-colors ${
                    user?.id === entry.user_id ? 'bg-primary/5' : ''
                  } ${entry.rank <= 3 ? 'bg-gradient-to-r from-yellow-50/50 to-transparent' : ''}`}
                >
                  <div className="w-8 flex justify-center">
                    <RankIcon rank={entry.rank} />
                  </div>
                  <Avatar className="h-9 w-9">
                    <AvatarImage src={entry.avatar_url} />
                    <AvatarFallback>{(entry.display_name || entry.username)[0]?.toUpperCase()}</AvatarFallback>
                  </Avatar>
                  <div className="flex-1 min-w-0">
                    <Link
                      to={`/u/${entry.username}`}
                      className="text-sm font-medium hover:underline truncate block"
                    >
                      {entry.display_name || entry.username}
                    </Link>
                    <p className="text-xs text-muted-foreground">
                      {LEVEL_LABELS[entry.level] || entry.level}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold font-mono">{entry.credit_score}</p>
                    <p className="text-xs text-muted-foreground">信用分</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default CreditLeaderboardPage;
