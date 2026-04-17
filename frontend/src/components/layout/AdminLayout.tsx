import { NavLink, Outlet, Navigate } from 'react-router-dom';
import { useAuth } from '@/hooks/use-auth';
import {
  LayoutDashboard,
  Users,
  Sparkles,
  FileText,
  Target,
  DollarSign,
  Star,
  ShieldAlert,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const NAV_ITEMS = [
  { to: '/admin', icon: LayoutDashboard, label: '仪表盘', end: true },
  { to: '/admin/users', icon: Users, label: '用户管理' },
  { to: '/admin/skills', icon: Sparkles, label: 'Skill 审核' },
  { to: '/admin/articles', icon: FileText, label: '文章管理' },
  { to: '/admin/bounties', icon: Target, label: '悬赏管理' },
  { to: '/admin/finance', icon: DollarSign, label: '财务管理' },
  { to: '/admin/featured', icon: Star, label: '精选管理' },
  { to: '/admin/disputes', icon: ShieldAlert, label: '争议仲裁' },
];

export function AdminLayout() {
  const { user, isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (user?.role !== 'ADMIN' && user?.role !== 'MODERATOR') {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="space-y-3 text-center">
          <ShieldAlert className="mx-auto h-12 w-12 text-muted-foreground" />
          <h1 className="text-xl font-bold">权限不足</h1>
          <p className="text-sm text-muted-foreground">
            您没有访问管理后台的权限，请联系管理员。
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-[calc(100vh-8rem)]">
      <aside className="w-52 shrink-0 border-r bg-muted/20">
        <div className="border-b p-4">
          <h2 className="text-sm font-semibold">管理后台</h2>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {user?.role === 'ADMIN' ? '管理员' : '版主'}
          </p>
        </div>
        <nav className="space-y-0.5 p-2">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors',
                  isActive
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-muted hover:text-foreground',
                )
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="flex-1 overflow-auto p-6">
        <Outlet />
      </div>
    </div>
  );
}
