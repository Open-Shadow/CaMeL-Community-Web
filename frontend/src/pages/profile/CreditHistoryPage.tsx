import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { EmptyState } from '@/components/shared/empty-state';
import { CreditHistoryItem, CreditHistoryList } from '@/components/user/credit-history-list';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { api, useAuth } from '@/hooks/use-auth';

interface CreditHistoryResponse {
  items: CreditHistoryItem[];
  total: number;
}

const PAGE_SIZE = 20;

export function CreditHistoryPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [data, setData] = useState<CreditHistoryResponse>({ items: [], total: 0 });
  const [isLoading, setIsLoading] = useState(true);

  const fetchHistory = async (reset = true) => {
    const offset = reset ? 0 : data.items.length;
    const response = await api.get('/users/me/credit-history', {
      params: { limit: PAGE_SIZE, offset },
    });

    setData((current) => ({
      items: reset ? response.data.items : [...current.items, ...response.data.items],
      total: response.data.total,
    }));
  };

  useEffect(() => {
    if (authLoading) return;
    if (!isAuthenticated) {
      setIsLoading(false);
      return;
    }

    const load = async () => {
      setIsLoading(true);
      try {
        await fetchHistory(true);
      } finally {
        setIsLoading(false);
      }
    };

    void load();
  }, [authLoading, isAuthenticated]);

  if (!isAuthenticated && !authLoading) {
    return (
      <EmptyState
        title="需要先登录"
        description="登录后才能查看完整的信用分历史。"
        action={
          <Button asChild>
            <Link to="/login">前往登录</Link>
          </Button>
        }
      />
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="space-y-2">
        <p className="text-sm uppercase tracking-[0.24em] text-muted-foreground">Credit</p>
        <h1 className="text-3xl font-bold tracking-tight">信用分历史</h1>
        <p className="text-muted-foreground">查看每次奖励、惩罚和等级变化的明细记录。</p>
      </div>

      <Card>
        <CardHeader className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <CardTitle>变动记录</CardTitle>
            <CardDescription>当前展示 {data.items.length} / {data.total} 条记录</CardDescription>
          </div>
          <Button asChild variant="outline">
            <Link to="/profile/settings">返回设置页</Link>
          </Button>
        </CardHeader>
        <CardContent>
          <CreditHistoryList
            items={data.items}
            total={data.total}
            isLoading={isLoading}
            onLoadMore={() => void fetchHistory(false)}
          />
        </CardContent>
      </Card>
    </div>
  );
}
