import { useEffect, useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { api } from '@/hooks/use-auth';

interface CreditLog {
  id: number;
  action: string;
  amount: number;
  score_before: number;
  score_after: number;
  created_at: string;
}

export function CreditHistoryPage() {
  const [logs, setLogs] = useState<CreditLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    api.get('/users/me/credit-history')
      .then((res) => setLogs(res.data))
      .finally(() => setIsLoading(false));
  }, []);

  return (
    <div className="container mx-auto py-8 max-w-2xl">
      <h1 className="text-2xl font-bold mb-6">信用分历史</h1>
      {isLoading ? (
        <p className="text-muted-foreground text-center py-8">加载中...</p>
      ) : logs.length === 0 ? (
        <p className="text-muted-foreground text-center py-8">暂无记录</p>
      ) : (
        <div className="space-y-3">
          {logs.map((log) => (
            <Card key={log.id}>
              <CardContent className="flex items-center justify-between py-4">
                <div>
                  <p className="text-sm font-medium">{log.action}</p>
                  <p className="text-xs text-muted-foreground">
                    {new Date(log.created_at).toLocaleString('zh-CN')}
                  </p>
                </div>
                <div className="text-right">
                  <Badge variant={log.amount >= 0 ? 'default' : 'destructive'}>
                    {log.amount >= 0 ? '+' : ''}{log.amount}
                  </Badge>
                  <p className="text-xs text-muted-foreground mt-1">
                    {log.score_before} → {log.score_after}
                  </p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
