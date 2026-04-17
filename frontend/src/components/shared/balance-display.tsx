import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Wallet } from 'lucide-react';
import { api } from '@/hooks/use-auth';

export function BalanceDisplay() {
  const [balance, setBalance] = useState<number | null>(null);

  useEffect(() => {
    api.get('/payments/balance')
      .then((res) => setBalance(res.data.available))
      .catch(() => {});
  }, []);

  if (balance === null) return null;

  return (
    <Link
      to="/wallet"
      className="inline-flex items-center gap-1.5 rounded-lg bg-muted px-2.5 py-1.5 text-sm font-medium transition-colors hover:bg-muted/80"
    >
      <Wallet className="h-3.5 w-3.5 text-muted-foreground" />
      ${balance.toFixed(2)}
    </Link>
  );
}
