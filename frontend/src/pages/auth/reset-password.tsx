import { useState } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { api } from '@/hooks/use-auth';

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token') || '';
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirm) { setError('两次密码不一致'); return; }
    setError(''); setIsLoading(true);
    try {
      await api.post('/auth/reset-password', { token, new_password: password });
      navigate('/login');
    } catch (err: any) {
      setError(err.response?.data?.message || '重置失败');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">重置密码</CardTitle>
          <CardDescription>请输入新密码</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && <div className="p-3 text-sm text-red-500 bg-red-50 rounded-md">{error}</div>}
            <div className="space-y-2">
              <label className="text-sm font-medium">新密码</label>
              <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required placeholder="至少 8 位" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">确认密码</label>
              <Input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required placeholder="再次输入密码" />
            </div>
            <Button type="submit" className="w-full" disabled={isLoading || !token}>
              {isLoading ? '重置中...' : '重置密码'}
            </Button>
            <div className="text-center text-sm">
              <Link to="/login" className="text-primary hover:underline">返回登录</Link>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
