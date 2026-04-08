import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { api } from '@/hooks/use-auth';

interface Balance {
  balance: number;
  frozen_balance: number;
  available: number;
}

interface TransactionRecord {
  id: number;
  transaction_type: string;
  amount: number;
  balance_after: number;
  description: string;
  reference_id?: string;
  created_at: string;
}

interface IncomeSummary {
  total_income: number;
  transaction_count: number;
}

interface TransactionListResponse {
  items: TransactionRecord[];
  total: number;
  limit: number;
  offset: number;
}

const QUICK_AMOUNTS = [5, 10, 20, 50, 100];

export function WalletPage() {
  const [searchParams] = useSearchParams();
  const status = searchParams.get('status');

  const [balance, setBalance] = useState<Balance | null>(null);
  const [transactions, setTransactions] = useState<TransactionRecord[]>([]);
  const [income, setIncome] = useState<IncomeSummary | null>(null);
  const [depositAmount, setDepositAmount] = useState('10');
  const [isDepositing, setIsDepositing] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;

    const fetchWallet = async () => {
      setError('');
      try {
        const [b, t, i] = await Promise.all([
          api.get<Balance>('/payments/balance'),
          api.get<TransactionListResponse>('/payments/transactions'),
          api.get<IncomeSummary>('/payments/income-summary'),
        ]);
        if (!active) return;
        setBalance(b.data);
        setTransactions(t.data.items || []);
        setIncome(i.data);
      } catch (err: any) {
        if (!active) return;
        setError(err.response?.data?.message || err.response?.data?.detail || '钱包数据加载失败');
      }
    };

    void fetchWallet();
    return () => {
      active = false;
    };
  }, []);

  const handleDeposit = async () => {
    const amount = parseFloat(depositAmount);
    if (isNaN(amount) || amount < 1) { setError('最低充值 $1.00'); return; }
    setError(''); setIsDepositing(true);
    try {
      const res = await api.post<{ checkout_url: string; session_id: string }>('/payments/checkout', { amount });
      if (!res.data?.checkout_url) {
        throw new Error('未获取到支付跳转链接');
      }
      window.location.href = res.data.checkout_url;
    } catch (err: any) {
      setError(err.response?.data?.message || err.response?.data?.detail || err.message || '充值失败');
      setIsDepositing(false);
    }
  };

  return (
    <div className="container mx-auto py-8 max-w-3xl space-y-6">
      <h1 className="text-2xl font-bold">我的钱包</h1>

      {status === 'success' && (
        <div className="p-3 bg-green-50 text-green-600 rounded-md text-sm">充值成功，余额已更新</div>
      )}
      {status === 'cancelled' && (
        <div className="p-3 bg-yellow-50 text-yellow-600 rounded-md text-sm">充值已取消</div>
      )}

      {/* Balance Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-4 text-center">
            <p className="text-3xl font-bold">${balance?.available?.toFixed(2) ?? '0.00'}</p>
            <p className="text-xs text-muted-foreground mt-1">可用余额</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            <p className="text-3xl font-bold text-orange-500">${balance?.frozen_balance?.toFixed(2) ?? '0.00'}</p>
            <p className="text-xs text-muted-foreground mt-1">冻结金额</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 text-center">
            <p className="text-3xl font-bold text-green-600">${income?.total_income?.toFixed(2) ?? '0.00'}</p>
            <p className="text-xs text-muted-foreground mt-1">累计收入</p>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="deposit">
        <TabsList>
          <TabsTrigger value="deposit">充值</TabsTrigger>
          <TabsTrigger value="history">交易记录</TabsTrigger>
        </TabsList>

        <TabsContent value="deposit" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>充值</CardTitle>
              <CardDescription>选择金额或自定义输入</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap gap-2">
                {QUICK_AMOUNTS.map((a) => (
                  <Button
                    key={a}
                    variant={depositAmount === String(a) ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setDepositAmount(String(a))}
                  >
                    ${a}
                  </Button>
                ))}
              </div>
              <div className="flex gap-2 items-center">
                <span className="text-lg font-medium">$</span>
                <Input
                  type="number"
                  min="1"
                  max="500"
                  step="0.01"
                  value={depositAmount}
                  onChange={(e) => setDepositAmount(e.target.value)}
                  className="max-w-32"
                />
                <Button onClick={handleDeposit} disabled={isDepositing}>
                  {isDepositing ? '跳转中...' : '去充值'}
                </Button>
              </div>
              {error && <p className="text-sm text-red-500">{error}</p>}
              <p className="text-xs text-muted-foreground">支付由 Stripe 安全处理，最低 $1.00，单次最高 $500.00</p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="history" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle>交易记录</CardTitle>
            </CardHeader>
            <CardContent>
              {transactions.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">暂无交易记录</p>
              ) : (
                <div className="space-y-3">
                  {transactions.map((tx) => (
                    <div key={tx.id} className="flex items-center justify-between py-2 border-b last:border-0">
                      <div>
                        <p className="text-sm font-medium">{tx.description || tx.transaction_type}</p>
                        <p className="text-xs text-muted-foreground">
                          {new Date(tx.created_at).toLocaleString('zh-CN')}
                        </p>
                      </div>
                      <div className="text-right">
                        <Badge variant={tx.amount >= 0 ? 'default' : 'destructive'}>
                          {tx.amount >= 0 ? '+' : ''}{tx.amount.toFixed(2)}
                        </Badge>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          余额 ${tx.balance_after.toFixed(2)}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
