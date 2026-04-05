import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Users, Sparkles, FileText, DollarSign, TrendingUp, UserPlus, Activity } from 'lucide-react';
import { api } from '@/hooks/use-auth';

interface DashboardData {
  total_users: number;
  new_users_today: number;
  new_users_7d: number;
  total_skills: number;
  total_articles: number;
  total_bounties: number;
  total_deposits: number;
  total_fees: number;
  active_users_7d: number;
}

export default function AdminPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    api.get('/admin/dashboard')
      .then((res) => setData(res.data))
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, []);

  const stats = [
    {
      title: '总用户数',
      value: data?.total_users ?? '--',
      sub: `今日新增 ${data?.new_users_today ?? 0}`,
      icon: Users,
      color: 'text-blue-600',
    },
    {
      title: '7日活跃用户',
      value: data?.active_users_7d ?? '--',
      sub: `7日新注册 ${data?.new_users_7d ?? 0}`,
      icon: Activity,
      color: 'text-green-600',
    },
    {
      title: 'Skill 总数',
      value: data?.total_skills ?? '--',
      sub: '',
      icon: Sparkles,
      color: 'text-purple-600',
    },
    {
      title: '文章总数',
      value: data?.total_articles ?? '--',
      sub: '',
      icon: FileText,
      color: 'text-orange-600',
    },
    {
      title: '悬赏总数',
      value: data?.total_bounties ?? '--',
      sub: '',
      icon: TrendingUp,
      color: 'text-cyan-600',
    },
    {
      title: '累计充值',
      value: data ? `$${data.total_deposits.toFixed(2)}` : '--',
      sub: '',
      icon: DollarSign,
      color: 'text-emerald-600',
    },
    {
      title: '平台手续费',
      value: data ? `$${data.total_fees.toFixed(2)}` : '--',
      sub: '',
      icon: DollarSign,
      color: 'text-amber-600',
    },
    {
      title: '今日新增',
      value: data?.new_users_today ?? '--',
      sub: '',
      icon: UserPlus,
      color: 'text-rose-600',
    },
  ];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">仪表盘</h1>

      {isLoading ? (
        <p className="text-muted-foreground">加载中...</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {stats.map((stat) => (
            <Card key={stat.title}>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  {stat.title}
                </CardTitle>
                <stat.icon className={`h-4 w-4 ${stat.color}`} />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stat.value}</div>
                {stat.sub && (
                  <p className="text-xs text-muted-foreground mt-1">{stat.sub}</p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
