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

  // Route guard: require admin role
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (user?.role !== 'ADMIN' && user?.role !== 'MODERATOR') {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center space-y-4">
          <ShieldAlert className="h-16 w-16 mx-auto text-muted-foreground" />
          <h1 className="text-2xl font-bold">权限不足</h1>
          <p className="text-muted-foreground">
            您没有访问管理后台的权限，请联系管理员。
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-[calc(100vh-8rem)]">
      {/* Sidebar */}
      <aside className="w-56 border-r bg-muted/30 shrink-0">
        <div className="p-4 border-b">
          <h2 className="font-semibold text-lg">管理后台</h2>
          <p className="text-xs text-muted-foreground mt-1">
            {user?.role === 'ADMIN' ? '管理员' : '版主'}
          </p>
        </div>
        <nav className="p-2 space-y-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors',
                  isActive
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted',
                )
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      {/* Main content */}
      <div className="flex-1 p-6 overflow-auto">
        <Outlet />
      </div>
    </div>
  );
}
