import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Copy, Gift, Link as LinkIcon, Sparkles, Users } from 'lucide-react';

import { api, useAuth } from '@/hooks/use-auth';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';

interface RecentInvite {
  id: number;
  code: string;
  invitee_display_name: string;
  invitee_email: string;
  used_at: string;
  risk_flags: string[];
}

interface InviteDashboard {
  code: string;
  share_path: string;
  total_codes_generated: number;
  registered_invites: number;
  rewarded_invites: number;
  delayed_reward_pending: number;
  monthly_credit_awarded: number;
  monthly_credit_remaining: number;
  active_window_days: number;
  recent_invites: RecentInvite[];
}

const initialDashboard: InviteDashboard = {
  code: '',
  share_path: '',
  total_codes_generated: 0,
  registered_invites: 0,
  rewarded_invites: 0,
  delayed_reward_pending: 0,
  monthly_credit_awarded: 0,
  monthly_credit_remaining: 0,
  active_window_days: 7,
  recent_invites: [],
};

export function ProfileInvitesPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();
  const [dashboard, setDashboard] = useState<InviteDashboard>(initialDashboard);
  const [pageLoading, setPageLoading] = useState(true);
  const [copyMessage, setCopyMessage] = useState('');

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      navigate('/login');
      return;
    }

    if (isAuthenticated) {
      void fetchDashboard();
    }
  }, [isAuthenticated, isLoading, navigate]);

  const fetchDashboard = async () => {
    setPageLoading(true);
    try {
      const response = await api.get<InviteDashboard>('/users/me/invite-code');
      setDashboard(response.data);
    } finally {
      setPageLoading(false);
    }
  };

  const shareLink = useMemo(() => {
    if (!dashboard.code || typeof window === 'undefined') return '';
    return `${window.location.origin}${dashboard.share_path}`;
  }, [dashboard.code, dashboard.share_path]);

  const copyText = async (value: string, successText: string) => {
    if (!value) return;
    await navigator.clipboard.writeText(value);
    setCopyMessage(successText);
    window.setTimeout(() => setCopyMessage(''), 2000);
  };

  if (isLoading || pageLoading) {
    return <div className="container mx-auto px-4 py-10">加载中...</div>;
  }

  return (
    <div className="min-h-screen bg-slate-50/60">
      <div className="container mx-auto max-w-6xl px-4 py-10">
        <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="mb-2 inline-flex items-center gap-2 rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-900">
              <Sparkles className="h-3.5 w-3.5" />
              邀请裂变基础版
            </p>
            <h1 className="text-3xl font-semibold text-slate-900">邀请好友</h1>
            <p className="mt-2 max-w-2xl text-sm text-slate-600">
              当前邀请码为单次使用。注册即时奖励已接入，首充和首月消费奖励保留了可扩展基础字段。
            </p>
          </div>
          <Button variant="outline" asChild>
            <Link to="/profile/settings">返回个人中心</Link>
          </Button>
        </div>

        <div className="grid gap-6 lg:grid-cols-[1.35fr_0.65fr]">
          <Card className="border-slate-200 bg-white shadow-sm">
            <CardHeader>
              <CardTitle>当前邀请码</CardTitle>
              <CardDescription>分享后首位成功注册者会消耗这张邀请码</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="rounded-2xl bg-slate-950 px-5 py-6 text-white">
                <div className="mb-2 text-xs uppercase tracking-[0.28em] text-slate-400">
                  Invite Code
                </div>
                <div className="text-3xl font-semibold tracking-[0.32em]">{dashboard.code}</div>
              </div>

              <div className="flex flex-col gap-3 md:flex-row">
                <div className="flex-1">
                  <label className="mb-2 block text-sm font-medium text-slate-700">分享链接</label>
                  <Input value={shareLink} readOnly />
                </div>
                <div className="flex gap-2 md:items-end">
                  <Button onClick={() => void copyText(dashboard.code, '邀请码已复制')}>
                    <Copy className="mr-2 h-4 w-4" />
                    复制邀请码
                  </Button>
                  <Button variant="outline" onClick={() => void copyText(shareLink, '分享链接已复制')}>
                    <LinkIcon className="mr-2 h-4 w-4" />
                    复制链接
                  </Button>
                </div>
              </div>

              {copyMessage && <p className="text-sm text-emerald-600">{copyMessage}</p>}
            </CardContent>
          </Card>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
            <StatCard icon={<Users className="h-4 w-4" />} label="成功注册" value={dashboard.registered_invites} help="已成功绑定邀请关系" />
            <StatCard icon={<Gift className="h-4 w-4" />} label="即时奖励" value={dashboard.rewarded_invites} help="邀请人已成功领取次数" />
            <StatCard icon={<Sparkles className="h-4 w-4" />} label="待延迟奖励" value={dashboard.delayed_reward_pending} help="首充奖励待后续接入" />
            <StatCard icon={<Gift className="h-4 w-4" />} label="本月剩余额度" value={dashboard.monthly_credit_remaining} help="邀请信用分月度上限剩余" />
          </div>
        </div>

        <Card className="mt-6 border-slate-200 bg-white shadow-sm">
          <CardHeader>
            <CardTitle>最近邀请</CardTitle>
            <CardDescription>
              基础反刷已启用：同 IP 或同设备仅首个邀请生效，{dashboard.active_window_days} 天活跃校验留了扩展窗口。
            </CardDescription>
          </CardHeader>
          <CardContent>
            {dashboard.recent_invites.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-6 py-10 text-center text-sm text-slate-500">
                还没有邀请记录。复制上面的链接发给朋友后，这里会显示最新绑定结果。
              </div>
            ) : (
              <div className="space-y-3">
                {dashboard.recent_invites.map((invite) => (
                  <div
                    key={invite.id}
                    className="flex flex-col gap-3 rounded-xl border border-slate-200 px-4 py-4 md:flex-row md:items-center md:justify-between"
                  >
                    <div>
                      <div className="font-medium text-slate-900">
                        {invite.invitee_display_name || invite.invitee_email}
                      </div>
                      <div className="mt-1 text-sm text-slate-500">
                        {invite.code}
                      </div>
                    </div>
                    <div className="flex flex-col items-start gap-2 md:items-end">
                      <div className="text-sm text-slate-500">
                        {new Date(invite.used_at).toLocaleString()}
                      </div>
                      {invite.risk_flags.length > 0 ? (
                        <div className="rounded-full bg-amber-100 px-3 py-1 text-xs text-amber-900">
                          风控标记：{invite.risk_flags.join(', ')}
                        </div>
                      ) : (
                        <div className="rounded-full bg-emerald-100 px-3 py-1 text-xs text-emerald-700">
                          即时奖励已生效
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  help,
}: {
  icon: ReactNode;
  label: string;
  value: number;
  help: string;
}) {
  return (
    <Card className="border-slate-200 bg-white shadow-sm">
      <CardContent className="flex items-start justify-between p-5">
        <div>
          <div className="text-sm text-slate-500">{label}</div>
          <div className="mt-2 text-2xl font-semibold text-slate-900">{value}</div>
          <div className="mt-1 text-xs text-slate-500">{help}</div>
        </div>
        <div className="rounded-full bg-slate-100 p-2 text-slate-700">{icon}</div>
      </CardContent>
    </Card>
  );
}
