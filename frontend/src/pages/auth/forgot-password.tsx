import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Link } from 'react-router-dom';
import { api } from '@/hooks/use-auth';

export function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      await api.post('/auth/forgot-password', { email });
      setSent(true);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">忘记密码</CardTitle>
          <CardDescription>输入邮箱，我们将发送重置链接</CardDescription>
        </CardHeader>
        <CardContent>
          {sent ? (
            <div className="text-center space-y-4">
              <p className="text-sm text-muted-foreground">如果该邮箱已注册，重置邮件已发送，请查收。</p>
              <Link to="/login" className="text-primary hover:underline text-sm">返回登录</Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <label htmlFor="email" className="text-sm font-medium">邮箱</label>
                <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required placeholder="your@email.com" />
              </div>
              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading ? '发送中...' : '发送重置邮件'}
              </Button>
              <div className="text-center text-sm">
                <Link to="/login" className="text-primary hover:underline">返回登录</Link>
              </div>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
