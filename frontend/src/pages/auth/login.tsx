import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
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
      setError(err.response?.data?.message || '登录失败');
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
    <div className="min-h-screen flex items-center justify-center px-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">登录</CardTitle>
          <CardDescription>欢迎回到 CaMeL Community</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && <div className="p-3 text-sm text-red-500 bg-red-50 rounded-md">{error}</div>}
            <div className="space-y-2">
              <label htmlFor="email" className="text-sm font-medium">邮箱</label>
              <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required placeholder="your@email.com" />
            </div>
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <label htmlFor="password" className="text-sm font-medium">密码</label>
                <Link to="/forgot-password" className="text-xs text-primary hover:underline">忘记密码？</Link>
              </div>
              <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required placeholder="••••••••" />
            </div>
            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? '登录中...' : '登录'}
            </Button>
          </form>
          <div className="mt-4 space-y-3">
            <div className="text-center text-xs uppercase tracking-[0.2em] text-muted-foreground">
              或使用社交账号登录
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
          </div>
          <div className="mt-4 text-center text-sm">
            还没有账号？{' '}
            <Link to="/register" className="text-primary hover:underline">立即注册</Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
