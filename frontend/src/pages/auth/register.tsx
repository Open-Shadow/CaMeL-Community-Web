import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { api, useAuth } from '@/hooks/use-auth';
import { useEffect, useState } from 'react';
import { useNavigate, Link, useSearchParams } from 'react-router-dom';

interface InviteValidationResponse {
  code: string;
  inviter_display_name: string;
  message: string;
}

export function RegisterPage() {
  const { register, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [inviteCode, setInviteCode] = useState(searchParams.get('invite')?.toUpperCase() || '');
  const [inviteMessage, setInviteMessage] = useState('');
  const [inviteValid, setInviteValid] = useState<boolean | null>(null);
  const [isCheckingInvite, setIsCheckingInvite] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/');
    }
  }, [isAuthenticated, navigate]);

  const validateInviteCode = async (code: string): Promise<boolean> => {
    const normalizedCode = code.trim().toUpperCase();
    if (!normalizedCode) {
      setInviteMessage('');
      setInviteValid(null);
      return false;
    }

    setIsCheckingInvite(true);
    try {
      const response = await api.get<InviteValidationResponse>(`/auth/invite-codes/${normalizedCode}/validate`);
      setInviteCode(response.data.code);
      setInviteMessage(response.data.message);
      setInviteValid(true);
      return true;
    } catch (err: any) {
      setInviteMessage(err.response?.data?.message || '邀请码不可用');
      setInviteValid(false);
      return false;
    } finally {
      setIsCheckingInvite(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError('两次输入的密码不一致');
      return;
    }

    if (password.length < 8) {
      setError('密码至少需要8个字符');
      return;
    }

    const normalizedInviteCode = inviteCode.trim().toUpperCase();
    if (normalizedInviteCode) {
      if (inviteValid === false) {
        setError('请输入有效的邀请码');
        return;
      }

      if (inviteValid === null) {
        const isValid = await validateInviteCode(normalizedInviteCode);
        if (!isValid) {
          setError('请输入有效的邀请码');
          return;
        }
      }
    }

    setIsLoading(true);

    try {
      await register(email, password, displayName || undefined, normalizedInviteCode || undefined);
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.message || '注册失败');
    } finally {
      setIsLoading(false);
    }
  };

  if (isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">注册账号</CardTitle>
          <CardDescription>加入 CaMeL Community</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="p-3 text-sm text-red-500 bg-red-50 rounded-md">
                {error}
              </div>
            )}
            <div className="space-y-2">
              <label htmlFor="email" className="text-sm font-medium">
                邮箱
              </label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="your@email.com"
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="displayName" className="text-sm font-medium">
                显示名称（可选）
              </label>
              <Input
                id="displayName"
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="您的昵称"
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="inviteCode" className="text-sm font-medium">
                邀请码（可选）
              </label>
              <Input
                id="inviteCode"
                type="text"
                value={inviteCode}
                onChange={(e) => {
                  setInviteCode(e.target.value.toUpperCase());
                  setInviteValid(null);
                  setInviteMessage('');
                }}
                onBlur={() => void validateInviteCode(inviteCode)}
                placeholder="输入好友分享的邀请码"
              />
              {inviteMessage && (
                <p className={`text-xs ${inviteValid ? 'text-emerald-600' : 'text-red-500'}`}>
                  {isCheckingInvite ? '验证邀请码中...' : inviteMessage}
                </p>
              )}
            </div>
            <div className="space-y-2">
              <label htmlFor="password" className="text-sm font-medium">
                密码
              </label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder="至少8个字符"
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="confirmPassword" className="text-sm font-medium">
                确认密码
              </label>
              <Input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                placeholder="再次输入密码"
              />
            </div>
            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? '注册中...' : '注册'}
            </Button>
          </form>
          <div className="mt-4 text-center text-sm">
            已有账号？{' '}
            <Link to="/login" className="text-primary hover:underline">
              立即登录
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
