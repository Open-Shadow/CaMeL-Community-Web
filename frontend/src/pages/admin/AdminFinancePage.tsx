import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { DollarSign, TrendingUp, Wallet, Lock } from 'lucide-react';
import { api } from '@/hooks/use-auth';

interface FinanceReport {
  total_deposits: number;
  total_fees: number;
  total_circulation: number;
  total_frozen: number;
  deposits_7d: number;
  fees_7d: number;
  deposits_30d: number;
  fees_30d: number;
  daily_deposits: { date: string; total: number; count: number }[];
  daily_fees: { date: string; total: number; count: number }[];
}

export default function AdminFinancePage() {
  const [report, setReport] = useState<FinanceReport | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    api.get('/admin/finance/report')
      .then((res) => setReport(res.data))
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, []);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">财务管理</h1>
        <p className="text-muted-foreground">加载中...</p>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">财务管理</h1>
        <p className="text-muted-foreground">暂无数据</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">财务管理</h1>

      {/* Summary cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">累计充值</CardTitle>
            <DollarSign className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${report.total_deposits.toFixed(2)}</div>
            <p className="text-xs text-muted-foreground mt-1">30日: ${report.deposits_30d.toFixed(2)}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">平台手续费</CardTitle>
            <TrendingUp className="h-4 w-4 text-amber-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${report.total_fees.toFixed(2)}</div>
            <p className="text-xs text-muted-foreground mt-1">30日: ${report.fees_30d.toFixed(2)}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">流通余额</CardTitle>
            <Wallet className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${report.total_circulation.toFixed(2)}</div>
            <p className="text-xs text-muted-foreground mt-1">用户可用余额总计</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">冻结金额</CardTitle>
            <Lock className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${report.total_frozen.toFixed(2)}</div>
            <p className="text-xs text-muted-foreground mt-1">悬赏冻结中</p>
          </CardContent>
        </Card>
      </div>

      {/* 7-day vs 30-day comparison */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">充值趋势</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex justify-between mb-4">
              <div>
                <p className="text-xs text-muted-foreground">近 7 日</p>
                <p className="text-lg font-bold">${report.deposits_7d.toFixed(2)}</p>
              </div>
              <div className="text-right">
                <p className="text-xs text-muted-foreground">近 30 日</p>
                <p className="text-lg font-bold">${report.deposits_30d.toFixed(2)}</p>
              </div>
            </div>
            {report.daily_deposits.length > 0 ? (
              <div className="space-y-1 max-h-64 overflow-y-auto">
                {report.daily_deposits.slice(-14).map((d) => (
                  <div key={d.date} className="flex items-center justify-between text-sm py-1 border-b last:border-0">
                    <span className="text-muted-foreground">{d.date}</span>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="text-xs">{d.count} 笔</Badge>
                      <span className="font-mono font-medium">${d.total.toFixed(2)}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-4">暂无充值记录</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">手续费趋势</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex justify-between mb-4">
              <div>
                <p className="text-xs text-muted-foreground">近 7 日</p>
                <p className="text-lg font-bold">${report.fees_7d.toFixed(2)}</p>
              </div>
              <div className="text-right">
                <p className="text-xs text-muted-foreground">近 30 日</p>
                <p className="text-lg font-bold">${report.fees_30d.toFixed(2)}</p>
              </div>
            </div>
            {report.daily_fees.length > 0 ? (
              <div className="space-y-1 max-h-64 overflow-y-auto">
                {report.daily_fees.slice(-14).map((d) => (
                  <div key={d.date} className="flex items-center justify-between text-sm py-1 border-b last:border-0">
                    <span className="text-muted-foreground">{d.date}</span>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="text-xs">{d.count} 笔</Badge>
                      <span className="font-mono font-medium">${d.total.toFixed(2)}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-4">暂无手续费记录</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
