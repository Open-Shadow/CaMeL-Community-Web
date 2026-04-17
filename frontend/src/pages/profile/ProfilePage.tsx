import { useEffect, useState } from 'react';
import { ArrowRight, ExternalLink, Sparkles } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';

import { EmptyState } from '@/components/shared/empty-state';
import { CreditBadge } from '@/components/user/credit-badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { api } from '@/hooks/use-auth';
import { formatDateTime, getInitials } from '@/lib/utils';

interface PublicUserProfile {
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

interface PublicUserStats {
  skills_count: number;
  articles_count: number;
  bounties_posted: number;
  bounties_completed: number;
  total_earned: number;
  total_spent: number;
}

interface ContributionItem {
  id: number;
  kind: string;
  title: string;
  subtitle: string;
  href: string;
  created_at: string;
}

interface PublicUserOverview {
  profile: PublicUserProfile;
  stats: PublicUserStats;
  recent_contributions: ContributionItem[];
}

const ENTRY_SECTIONS = [
  { title: '技能市场', description: '查看该创作者发布的 Skill', href: '/marketplace' },
  { title: '知识工坊', description: '浏览相关教程与实践文章', href: '/workshop' },
  { title: '悬赏任务', description: '查看参与的需求与任务', href: '/bounty' },
];

export default function ProfilePage() {
  const { username } = useParams();
  const [data, setData] = useState<PublicUserOverview | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!username) {
      setError('无效的用户地址');
      setIsLoading(false);
      return;
    }

    const load = async () => {
      setIsLoading(true);
      setError('');
      try {
        const response = await api.get(`/users/public/${encodeURIComponent(username)}/overview`);
        setData(response.data);
      } catch (loadError: any) {
        setError(loadError.response?.data?.detail || '公开用户资料加载失败');
      } finally {
        setIsLoading(false);
      }
    };

    void load();
  }, [username]);

  if (isLoading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6">
        <EmptyState
          icon={<Sparkles className="h-10 w-10" />}
          title="未找到该用户"
          description={error || '该用户还没有公开资料。'}
          action={
            <Button asChild variant="outline">
              <Link to="/">返回首页</Link>
            </Button>
          }
        />
      </div>
    );
  }

  const { profile, stats, recent_contributions: contributions } = data;

  return (
    <div className="mx-auto max-w-7xl space-y-8 px-4 py-8 sm:px-6">
      <section className="overflow-hidden rounded-2xl border bg-gradient-to-br from-primary/5 via-white to-red-50/50">
        <div className="grid gap-6 p-8 md:grid-cols-[auto,1fr]">
          <Avatar className="h-24 w-24 border-4 border-white shadow-lg">
            <AvatarImage src={profile.avatar_url} alt={profile.display_name} />
            <AvatarFallback className="text-2xl">
              {getInitials(profile.display_name || profile.username)}
            </AvatarFallback>
          </Avatar>
          <div className="space-y-3">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <h1 className="text-2xl font-bold tracking-tight">{profile.display_name}</h1>
                <p className="text-sm text-muted-foreground">@{profile.username}</p>
              </div>
              <CreditBadge level={profile.level} score={profile.credit_score} showScore />
            </div>
            <p className="max-w-2xl text-sm leading-relaxed text-muted-foreground">
              {profile.bio || '这个用户暂时还没有留下公开简介。'}
            </p>
            <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
              <span>信用分 {profile.credit_score}</span>
              <span>加入于 {formatDateTime(profile.created_at)}</span>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-4">
        <StatCard label="公开 Skill" value={stats.skills_count} />
        <StatCard label="公开文章" value={stats.articles_count} />
        <StatCard label="发布悬赏" value={stats.bounties_posted} />
        <StatCard label="完成任务" value={stats.bounties_completed} />
      </section>

      <section className="grid gap-4 sm:grid-cols-3">
        {ENTRY_SECTIONS.map((entry) => (
          <Card key={entry.title} className="transition-all hover:-translate-y-0.5 hover:shadow-md">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center justify-between text-base">
                {entry.title}
                <ExternalLink className="h-4 w-4 text-muted-foreground" />
              </CardTitle>
              <CardDescription className="text-xs">{entry.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild variant="outline" size="sm" className="w-full justify-between">
                <Link to={entry.href}>
                  进入 {entry.title}
                  <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </Button>
            </CardContent>
          </Card>
        ))}
      </section>

      <section className="space-y-4">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">最近贡献</h2>
          <p className="text-sm text-muted-foreground">最近公开可见的内容入口</p>
        </div>

        {contributions.length === 0 ? (
          <EmptyState
            title="暂时还没有公开贡献"
            description="当这个用户发布 Skill、文章或悬赏后，这里会展示对应入口。"
            className="rounded-xl border"
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {contributions.map((item) => (
              <Card key={`${item.kind}-${item.id}`} className="transition-all hover:-translate-y-0.5 hover:shadow-md">
                <CardHeader className="pb-2">
                  <CardTitle className="line-clamp-1 text-base">{item.title}</CardTitle>
                  <CardDescription className="text-xs">
                    {item.kind.toUpperCase()} · {item.subtitle}
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex items-center justify-between gap-4">
                  <p className="text-xs text-muted-foreground">{formatDateTime(item.created_at)}</p>
                  <Button asChild variant="ghost" size="sm">
                    <Link to={item.href}>
                      查看
                      <ArrowRight className="ml-1 h-3.5 w-3.5" />
                    </Link>
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <Card>
      <CardContent className="space-y-1 p-5">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="text-2xl font-semibold tracking-tight">{value}</p>
      </CardContent>
    </Card>
  );
}
