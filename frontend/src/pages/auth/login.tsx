import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAuth } from '@/hooks/use-auth';
import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';

export function LoginPage() {
  const { login, getSocialAuthorizationUrl, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [socialLoading, setSocialLoading] = useState<'github' | 'google' | null>(null);

  if (isAuthenticated) {
    navigate('/');
    return null;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);
    try {
      await login(email, password);
      navigate('/');
    } catch (err: any) {
      if (err.code === 'ECONNABORTED') {
        setError('登录请求超时，请稍后重试');
      } else if (err.response?.data?.message) {
        setError(err.response.data.message);
      } else if (err.response?.status) {
        setError(`登录失败 (${err.response.status})，请稍后重试`);
      } else if (err.request) {
        setError('无法连接到服务器，请检查网络连接');
      } else {
        setError('登录失败，请稍后重试');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleSocialLogin = async (provider: 'github' | 'google') => {
    setError('');
    setSocialLoading(provider);
    try {
      const authorizationUrl = await getSocialAuthorizationUrl(provider);
      window.location.href = authorizationUrl;
    } catch (err: any) {
      setError(err.response?.data?.message || '社交登录暂时不可用');
      setSocialLoading(null);
    }
  };

  return (
    <div className="flex min-h-[80vh] items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-lg font-black text-white">
            C
          </div>
          <h1 className="text-2xl font-bold">登录 CaMeL</h1>
          <p className="mt-1 text-sm text-muted-foreground">欢迎回来</p>
        </div>
        <Card>
          <CardContent className="space-y-4 pt-6">
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-3 text-sm text-destructive">{error}</div>}
              <div className="space-y-2">
                <label htmlFor="email" className="text-sm font-medium">邮箱</label>
                <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required placeholder="your@email.com" />
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label htmlFor="password" className="text-sm font-medium">密码</label>
                  <Link to="/forgot-password" className="text-xs text-primary hover:underline">忘记密码？</Link>
                </div>
                <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required placeholder="••••••••" />
              </div>
              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading ? '登录中...' : '登录'}
              </Button>
            </form>
            <div className="relative py-2">
              <div className="absolute inset-0 flex items-center"><div className="w-full border-t" /></div>
              <div className="relative flex justify-center">
                <span className="bg-card px-3 text-xs text-muted-foreground">或使用社交账号</span>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Button
                type="button"
                variant="outline"
                disabled={socialLoading !== null}
                onClick={() => handleSocialLogin('github')}
              >
                {socialLoading === 'github' ? '跳转中...' : 'GitHub'}
              </Button>
              <Button
                type="button"
                variant="outline"
                disabled={socialLoading !== null}
                onClick={() => handleSocialLogin('google')}
              >
                {socialLoading === 'google' ? '跳转中...' : 'Google'}
              </Button>
            </div>
            <p className="text-center text-sm text-muted-foreground">
              还没有账号？{' '}
              <Link to="/register" className="font-medium text-primary hover:underline">立即注册</Link>
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
