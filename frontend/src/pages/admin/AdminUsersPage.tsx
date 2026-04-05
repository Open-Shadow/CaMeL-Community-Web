import { useEffect, useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { api } from '@/hooks/use-auth';

interface UserItem {
  id: number;
  username: string;
  email: string;
  display_name: string;
  role: string;
  level: string;
  credit_score: number;
  balance: number;
  frozen_balance: number;
  is_active: boolean;
  date_joined: string;
  last_login: string | null;
}

const LEVEL_LABELS: Record<string, string> = {
  SEED: '🌱 新芽', CRAFTSMAN: '🔧 工匠', EXPERT: '⚡ 专家',
  MASTER: '🏆 大师', GRANDMASTER: '👑 宗师',
};

const ROLE_LABELS: Record<string, string> = {
  USER: '用户', MODERATOR: '版主', ADMIN: '管理员',
};

export default function AdminUsersPage() {
  const [users, setUsers] = useState<UserItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  // Dialog states
  const [roleDialog, setRoleDialog] = useState<{ open: boolean; user: UserItem | null; newRole: string }>({
    open: false, user: null, newRole: '',
  });
  const [banDialog, setBanDialog] = useState<{ open: boolean; user: UserItem | null; reason: string }>({
    open: false, user: null, reason: '',
  });
  const [creditDialog, setCreditDialog] = useState<{ open: boolean; user: UserItem | null; amount: string; reason: string }>({
    open: false, user: null, amount: '', reason: '',
  });

  const fetchUsers = () => {
    setIsLoading(true);
    const params = new URLSearchParams({
      page: String(page),
      page_size: '20',
    });
    if (search) params.set('search', search);
    if (roleFilter) params.set('role', roleFilter);

    api.get(`/admin/users?${params}`)
      .then((res) => {
        setUsers(res.data.users);
        setTotal(res.data.total);
      })
      .finally(() => setIsLoading(false));
  };

  useEffect(() => { fetchUsers(); }, [page, roleFilter]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchUsers();
  };

  const handleRoleChange = async () => {
    if (!roleDialog.user) return;
    await api.patch(`/admin/users/${roleDialog.user.id}/role`, { role: roleDialog.newRole });
    setRoleDialog({ open: false, user: null, newRole: '' });
    fetchUsers();
  };

  const handleBan = async () => {
    if (!banDialog.user) return;
    if (banDialog.user.is_active) {
      await api.post(`/admin/users/${banDialog.user.id}/ban`, { reason: banDialog.reason });
    } else {
      await api.post(`/admin/users/${banDialog.user.id}/unban`);
    }
    setBanDialog({ open: false, user: null, reason: '' });
    fetchUsers();
  };

  const handleCreditAdjust = async () => {
    if (!creditDialog.user) return;
    const amount = parseInt(creditDialog.amount);
    if (isNaN(amount) || amount === 0) return;
    await api.post(`/admin/users/${creditDialog.user.id}/credit-adjust`, {
      amount, reason: creditDialog.reason || '管理员调整',
    });
    setCreditDialog({ open: false, user: null, amount: '', reason: '' });
    fetchUsers();
  };

  const totalPages = Math.ceil(total / 20);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">用户管理</h1>

      {/* Search and filters */}
      <div className="flex gap-3 items-center">
        <form onSubmit={handleSearch} className="flex gap-2 flex-1">
          <Input
            placeholder="搜索用户名、邮箱、昵称..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="max-w-sm"
          />
          <Button type="submit" variant="outline" size="sm">搜索</Button>
        </form>
        <Select value={roleFilter} onValueChange={(v) => { setRoleFilter(v === 'ALL' ? '' : v); setPage(1); }}>
          <SelectTrigger className="w-32">
            <SelectValue placeholder="全部角色" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ALL">全部角色</SelectItem>
            <SelectItem value="USER">用户</SelectItem>
            <SelectItem value="MODERATOR">版主</SelectItem>
            <SelectItem value="ADMIN">管理员</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* User table */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="text-left p-3">用户</th>
                  <th className="text-left p-3">角色</th>
                  <th className="text-left p-3">等级</th>
                  <th className="text-right p-3">信用分</th>
                  <th className="text-right p-3">余额</th>
                  <th className="text-left p-3">状态</th>
                  <th className="text-left p-3">注册时间</th>
                  <th className="text-right p-3">操作</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <tr><td colSpan={8} className="text-center py-8 text-muted-foreground">加载中...</td></tr>
                ) : users.length === 0 ? (
                  <tr><td colSpan={8} className="text-center py-8 text-muted-foreground">暂无用户</td></tr>
                ) : users.map((u) => (
                  <tr key={u.id} className="border-b hover:bg-muted/30">
                    <td className="p-3">
                      <div>
                        <p className="font-medium">{u.display_name || u.username}</p>
                        <p className="text-xs text-muted-foreground">{u.email}</p>
                      </div>
                    </td>
                    <td className="p-3">
                      <Badge variant={u.role === 'ADMIN' ? 'default' : u.role === 'MODERATOR' ? 'secondary' : 'outline'}>
                        {ROLE_LABELS[u.role] || u.role}
                      </Badge>
                    </td>
                    <td className="p-3 text-xs">{LEVEL_LABELS[u.level] || u.level}</td>
                    <td className="p-3 text-right font-mono">{u.credit_score}</td>
                    <td className="p-3 text-right font-mono">${u.balance.toFixed(2)}</td>
                    <td className="p-3">
                      {u.is_active ? (
                        <Badge variant="outline" className="text-green-600 border-green-300">正常</Badge>
                      ) : (
                        <Badge variant="destructive">封禁</Badge>
                      )}
                    </td>
                    <td className="p-3 text-xs text-muted-foreground">
                      {new Date(u.date_joined).toLocaleDateString('zh-CN')}
                    </td>
                    <td className="p-3 text-right">
                      <div className="flex gap-1 justify-end">
                        <Button
                          variant="ghost" size="sm"
                          onClick={() => setRoleDialog({ open: true, user: u, newRole: u.role })}
                        >
                          角色
                        </Button>
                        <Button
                          variant="ghost" size="sm"
                          onClick={() => setCreditDialog({ open: true, user: u, amount: '', reason: '' })}
                        >
                          信用分
                        </Button>
                        <Button
                          variant={u.is_active ? 'ghost' : 'outline'} size="sm"
                          className={u.is_active ? 'text-red-600 hover:text-red-700' : 'text-green-600'}
                          onClick={() => setBanDialog({ open: true, user: u, reason: '' })}
                        >
                          {u.is_active ? '封禁' : '解封'}
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">共 {total} 个用户</p>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>
              上一页
            </Button>
            <span className="text-sm py-1.5 px-2">{page} / {totalPages}</span>
            <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>
              下一页
            </Button>
          </div>
        </div>
      )}

      {/* Role change dialog */}
      <Dialog open={roleDialog.open} onOpenChange={(open) => !open && setRoleDialog({ open: false, user: null, newRole: '' })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>修改角色 - {roleDialog.user?.display_name || roleDialog.user?.username}</DialogTitle>
          </DialogHeader>
          <Select value={roleDialog.newRole} onValueChange={(v) => setRoleDialog({ ...roleDialog, newRole: v })}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="USER">用户</SelectItem>
              <SelectItem value="MODERATOR">版主</SelectItem>
              <SelectItem value="ADMIN">管理员</SelectItem>
            </SelectContent>
          </Select>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRoleDialog({ open: false, user: null, newRole: '' })}>取消</Button>
            <Button onClick={handleRoleChange}>确认</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Ban dialog */}
      <Dialog open={banDialog.open} onOpenChange={(open) => !open && setBanDialog({ open: false, user: null, reason: '' })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {banDialog.user?.is_active ? '封禁' : '解封'}用户 - {banDialog.user?.display_name || banDialog.user?.username}
            </DialogTitle>
          </DialogHeader>
          {banDialog.user?.is_active && (
            <Input
              placeholder="封禁原因（可选）"
              value={banDialog.reason}
              onChange={(e) => setBanDialog({ ...banDialog, reason: e.target.value })}
            />
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setBanDialog({ open: false, user: null, reason: '' })}>取消</Button>
            <Button variant={banDialog.user?.is_active ? 'destructive' : 'default'} onClick={handleBan}>
              确认{banDialog.user?.is_active ? '封禁' : '解封'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Credit adjust dialog */}
      <Dialog open={creditDialog.open} onOpenChange={(open) => !open && setCreditDialog({ open: false, user: null, amount: '', reason: '' })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              调整信用分 - {creditDialog.user?.display_name || creditDialog.user?.username}
              （当前 {creditDialog.user?.credit_score} 分）
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <Input
              type="number"
              placeholder="调整数值（正数增加，负数扣除）"
              value={creditDialog.amount}
              onChange={(e) => setCreditDialog({ ...creditDialog, amount: e.target.value })}
            />
            <Input
              placeholder="调整原因"
              value={creditDialog.reason}
              onChange={(e) => setCreditDialog({ ...creditDialog, reason: e.target.value })}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreditDialog({ open: false, user: null, amount: '', reason: '' })}>取消</Button>
            <Button onClick={handleCreditAdjust}>确认调整</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
