import { useState, useEffect } from 'react';
import { useAuth } from '@/hooks/use-auth';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { CreditProgress } from '@/components/user/credit-progress';
import { api } from '@/hooks/use-auth';

interface UserProfile {
  id: number;
  username: string;
  email: string;
  display_name: string;
  bio: string;
  avatar_url: string;
  role: string;
  level: string;
  credit_score: number;
  balance: number;
  created_at: string;
}

export function ProfileSettingsPage() {
  useAuth(); // ensure user is authenticated
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState('');

  // Form state
  const [displayName, setDisplayName] = useState('');
  const [bio, setBio] = useState('');

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    try {
      const response = await api.get('/users/me');
      setProfile(response.data);
      setDisplayName(response.data.display_name);
      setBio(response.data.bio);
    } catch (error) {
      console.error('Failed to fetch profile:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    setMessage('');

    try {
      await api.patch('/users/me', {
        display_name: displayName,
        bio: bio,
      });
      setMessage('保存成功');
      fetchProfile();
    } catch (error: any) {
      setMessage(error.response?.data?.message || '保存失败');
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading || !profile) {
    return <div className="p-8">加载中...</div>;
  }

  return (
    <div className="container max-w-4xl mx-auto py-8 px-4">
      <h1 className="text-3xl font-bold mb-8">个人中心</h1>

      <Tabs defaultValue="profile" className="space-y-6">
        <TabsList>
          <TabsTrigger value="profile">个人资料</TabsTrigger>
          <TabsTrigger value="credit">信用分</TabsTrigger>
          <TabsTrigger value="security">安全设置</TabsTrigger>
        </TabsList>

        <TabsContent value="profile" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>基本信息</CardTitle>
              <CardDescription>管理您的个人资料</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Avatar */}
              <div className="flex items-center gap-4">
                <Avatar className="h-20 w-20">
                  <AvatarImage src={profile.avatar_url} />
                  <AvatarFallback className="text-2xl">
                    {profile.display_name?.[0]?.toUpperCase() || 'U'}
                  </AvatarFallback>
                </Avatar>
                <div>
                  <Button variant="outline" size="sm">
                    更换头像
                  </Button>
                  <p className="text-xs text-muted-foreground mt-1">
                    支持 JPG、PNG 格式，最大 5MB
                  </p>
                </div>
              </div>

              {/* Form */}
              <div className="grid gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">邮箱</label>
                  <Input value={profile.email} disabled />
                  <p className="text-xs text-muted-foreground">邮箱不可更改</p>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">显示名称</label>
                  <Input
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                    placeholder="您的昵称"
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">个人简介</label>
                  <Textarea
                    value={bio}
                    onChange={(e) => setBio(e.target.value)}
                    placeholder="介绍一下自己..."
                    rows={4}
                  />
                </div>
              </div>

              {message && (
                <div className={`p-3 rounded-md text-sm ${
                  message.includes('成功')
                    ? 'bg-green-50 text-green-600'
                    : 'bg-red-50 text-red-600'
                }`}>
                  {message}
                </div>
              )}

              <Button onClick={handleSave} disabled={isSaving}>
                {isSaving ? '保存中...' : '保存更改'}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="credit">
          <CreditProgress score={profile.credit_score} />

          <Card className="mt-6">
            <CardHeader>
              <CardTitle>信用分历史</CardTitle>
              <CardDescription>最近的信用分变动记录</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">暂无记录</p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="security">
          <Card>
            <CardHeader>
              <CardTitle>修改密码</CardTitle>
              <CardDescription>定期更换密码可以保护账号安全</CardDescription>
            </CardHeader>
            <CardContent>
              <ChangePasswordForm />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function ChangePasswordForm() {
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (newPassword !== confirmPassword) {
      setMessage('两次输入的密码不一致');
      return;
    }

    if (newPassword.length < 8) {
      setMessage('新密码至少需要8个字符');
      return;
    }

    setIsLoading(true);
    setMessage('');

    try {
      await api.post('/users/me/password', {
        old_password: oldPassword,
        new_password: newPassword,
      });
      setMessage('密码修改成功');
      setOldPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (error: any) {
      setMessage(error.response?.data?.message || '密码修改失败');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 max-w-md">
      <div className="space-y-2">
        <label className="text-sm font-medium">当前密码</label>
        <Input
          type="password"
          value={oldPassword}
          onChange={(e) => setOldPassword(e.target.value)}
          required
        />
      </div>

      <div className="space-y-2">
        <label className="text-sm font-medium">新密码</label>
        <Input
          type="password"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          required
        />
      </div>

      <div className="space-y-2">
        <label className="text-sm font-medium">确认新密码</label>
        <Input
          type="password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          required
        />
      </div>

      {message && (
        <div className={`p-3 rounded-md text-sm ${
          message.includes('成功')
            ? 'bg-green-50 text-green-600'
            : 'bg-red-50 text-red-600'
        }`}>
          {message}
        </div>
      )}

      <Button type="submit" disabled={isLoading}>
        {isLoading ? '修改中...' : '修改密码'}
      </Button>
    </form>
  );
}
