import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
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
      className="text-sm font-medium bg-muted px-2.5 py-1 rounded-md hover:bg-muted/80 transition-colors"
    >
      ${balance.toFixed(2)}
    </Link>
  );
}
