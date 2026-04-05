import { useEffect, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useAuth } from '@/hooks/use-auth';
import { api } from '@/hooks/use-auth';

export function OAuthCallbackPage() {
  const { provider } = useParams<{ provider: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { loginWithTokens } = useAuth();
  const [error, setError] = useState('');

  useEffect(() => {
    const code = searchParams.get('code');
    if (!code || !provider) { setError('OAuth 回调参数缺失'); return; }

    api.post('/auth/oauth/callback', { code, provider })
      .then((res) => loginWithTokens(res.data).then(() => navigate('/')))
      .catch((err) => setError(err.response?.data?.message || 'OAuth 登录失败'));
  }, []);

  if (error) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center space-y-4">
        <p className="text-red-500">{error}</p>
        <a href="/login" className="text-primary hover:underline">返回登录</a>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen flex items-center justify-center">
      <p className="text-muted-foreground">正在登录，请稍候...</p>
    </div>
  );
}
