import { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { api } from '@/hooks/use-auth';

export function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (!token) { setStatus('error'); setMessage('验证链接无效'); return; }
    api.post('/auth/verify-email', { token })
      .then(() => setStatus('success'))
      .catch((err) => { setStatus('error'); setMessage(err.response?.data?.message || '验证失败'); });
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center space-y-4">
        {status === 'loading' && <p className="text-muted-foreground">正在验证邮箱...</p>}
        {status === 'success' && (
          <>
            <p className="text-green-600 font-medium">邮箱验证成功！</p>
            <Link to="/login" className="text-primary hover:underline text-sm">前往登录</Link>
          </>
        )}
        {status === 'error' && (
          <>
            <p className="text-red-500">{message}</p>
            <Link to="/login" className="text-primary hover:underline text-sm">返回登录</Link>
          </>
        )}
      </div>
    </div>
  );
}
