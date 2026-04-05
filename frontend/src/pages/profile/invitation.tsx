import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { api } from '@/hooks/use-auth';

interface InviteStats {
  total_codes: number;
  used_codes: number;
  remaining_this_month: number;
}

interface InvitationRecord {
  id: number;
  code: string;
  used_by_name: string;
  used_at: string;
  created_at: string;
}

export function InvitationPage() {
  const [code, setCode] = useState('');
  const [stats, setStats] = useState<InviteStats | null>(null);
  const [invitations, setInvitations] = useState<InvitationRecord[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState('');

  const fetchData = async () => {
    const [statsRes, listRes] = await Promise.all([
      api.get('/invitations/stats'),
      api.get('/invitations/list'),
    ]);
    setStats(statsRes.data);
    setInvitations(listRes.data);
    // Show latest unused code
    const unused = (listRes.data as InvitationRecord[]).find((i) => !i.used_by_name);
    if (unused) setCode(unused.code);
  };

  useEffect(() => { fetchData(); }, []);

  const handleGenerate = async () => {
    setIsLoading(true);
    setError('');
    try {
      const res = await api.post('/invitations/generate');
      setCode(res.data.code);
      fetchData();
    } catch (err: any) {
      setError(err.response?.data?.message || '生成失败');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopy = () => {
    const shareUrl = `${window.location.origin}/register?invite=${code}`;
    navigator.clipboard.writeText(shareUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="container mx-auto py-8 max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold">邀请好友</h1>

      <Card>
        <CardHeader>
          <CardTitle>我的邀请码</CardTitle>
          <CardDescription>分享邀请码给好友，双方均可获得奖励</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {code ? (
            <div className="flex items-center gap-3">
              <code className="flex-1 bg-muted px-4 py-3 rounded-lg text-center text-lg font-mono tracking-widest">
                {code}
              </code>
              <Button onClick={handleCopy} variant="outline">
                {copied ? '已复制' : '复制链接'}
              </Button>
            </div>
          ) : (
            <Button onClick={handleGenerate} disabled={isLoading}>
              {isLoading ? '生成中...' : '生成邀请码'}
            </Button>
          )}
          {error && <p className="text-sm text-red-500">{error}</p>}
        </CardContent>
      </Card>

      {stats && (
        <div className="grid grid-cols-3 gap-4">
          <Card>
            <CardContent className="pt-4 text-center">
              <p className="text-2xl font-bold">{stats.total_codes}</p>
              <p className="text-xs text-muted-foreground">总邀请</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4 text-center">
              <p className="text-2xl font-bold">{stats.used_codes}</p>
              <p className="text-xs text-muted-foreground">已使用</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4 text-center">
              <p className="text-2xl font-bold">{stats.remaining_this_month}</p>
              <p className="text-xs text-muted-foreground">本月剩余</p>
            </CardContent>
          </Card>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>邀请记录</CardTitle>
        </CardHeader>
        <CardContent>
          {invitations.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">暂无邀请记录</p>
          ) : (
            <div className="space-y-3">
              {invitations.map((inv) => (
                <div key={inv.id} className="flex items-center justify-between py-2 border-b last:border-0">
                  <div>
                    <code className="text-sm font-mono">{inv.code}</code>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {new Date(inv.created_at).toLocaleDateString('zh-CN')}
                    </p>
                  </div>
                  {inv.used_by_name ? (
                    <Badge variant="default">{inv.used_by_name}</Badge>
                  ) : (
                    <Badge variant="secondary">未使用</Badge>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-4">
          <h3 className="font-medium mb-2">邀请奖励规则</h3>
          <ul className="text-sm text-muted-foreground space-y-1">
            <li>- 好友注册：邀请人 +10 信用分</li>
            <li>- 好友首充：邀请人 +$0.50 额度</li>
            <li>- 每月最多邀请 20 人</li>
            <li>- 被邀请人需在 7 天内活跃才算有效</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
