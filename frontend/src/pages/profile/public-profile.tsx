import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { api } from '@/hooks/use-auth';

interface UserProfile {
  id: number;
  username: string;
  display_name: string;
  bio: string;
  avatar_url: string;
  role: string;
  level: string;
  credit_score: number;
  created_at: string;
}

interface UserStats {
  skills_count: number;
  articles_count: number;
  bounties_posted: number;
  bounties_completed: number;
  total_earned: number;
}

const LEVEL_LABELS: Record<string, string> = {
  SEED: '🌱 新芽', CRAFTSMAN: '🔧 工匠', EXPERT: '⚡ 专家',
  MASTER: '🏆 大师', GRANDMASTER: '👑 宗师',
};

export function PublicProfilePage() {
  const { username } = useParams<{ username: string }>();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [stats, setStats] = useState<UserStats | null>(null);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    if (!username) return;
    Promise.all([
      api.get(`/users/by-username/${username}`),
      api.get(`/users/by-username/${username}/stats`),
    ])
      .then(([p, s]) => { setProfile(p.data); setStats(s.data); })
      .catch(() => setNotFound(true));
  }, [username]);

  if (notFound) return (
    <div className="container mx-auto py-16 text-center text-muted-foreground">用户不存在</div>
  );
  if (!profile) return (
    <div className="container mx-auto py-16 text-center text-muted-foreground">加载中...</div>
  );

  return (
    <div className="container mx-auto py-8 max-w-2xl space-y-6">
      <Card>
        <CardHeader className="flex flex-row items-center gap-4">
          <Avatar className="h-16 w-16">
            <AvatarImage src={profile.avatar_url} />
            <AvatarFallback>{profile.display_name?.[0]?.toUpperCase()}</AvatarFallback>
          </Avatar>
          <div className="flex-1">
            <h1 className="text-xl font-bold">{profile.display_name || profile.username}</h1>
            <p className="text-sm text-muted-foreground">@{profile.username}</p>
            <div className="flex gap-2 mt-1">
              <Badge variant="secondary">{LEVEL_LABELS[profile.level] || profile.level}</Badge>
              <Badge variant="outline">{profile.credit_score} 信用分</Badge>
            </div>
          </div>
        </CardHeader>
        {profile.bio && (
          <CardContent>
            <p className="text-sm text-muted-foreground">{profile.bio}</p>
          </CardContent>
        )}
      </Card>

      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            { label: 'Skill', value: stats.skills_count },
            { label: '文章', value: stats.articles_count },
            { label: '发布悬赏', value: stats.bounties_posted },
            { label: '完成悬赏', value: stats.bounties_completed },
          ].map(({ label, value }) => (
            <Card key={label}>
              <CardContent className="pt-4 text-center">
                <p className="text-2xl font-bold">{value}</p>
                <p className="text-xs text-muted-foreground">{label}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
