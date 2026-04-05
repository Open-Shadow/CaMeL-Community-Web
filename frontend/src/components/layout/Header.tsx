import { Link } from 'react-router-dom'
import { useAuth } from '@/hooks/use-auth'
import { NotificationBell } from '@/components/shared/notification-bell'
import { BalanceDisplay } from '@/components/shared/balance-display'

export function Header() {
  const { user, isAuthenticated, logout } = useAuth();

  return (
    <header className="border-b">
      <div className="container mx-auto px-4 h-16 flex items-center justify-between">
        <Link to="/" className="font-bold text-xl">CaMeL Community</Link>
        <nav className="flex gap-6">
          <Link to="/marketplace">技能市场</Link>
          <Link to="/bounty">悬赏任务</Link>
          <Link to="/workshop">知识工坊</Link>
          <Link to="/rankings/credit">排行榜</Link>
        </nav>
        <div className="flex items-center gap-3">
          {isAuthenticated ? (
            <>
              <BalanceDisplay />
              <NotificationBell />
              <Link to="/profile/invitation" className="text-sm hover:underline">邀请</Link>
              {(user?.role === 'ADMIN' || user?.role === 'MODERATOR') && (
                <Link to="/admin" className="text-sm font-medium text-primary hover:underline">管理</Link>
              )}
              <Link to="/profile/settings" className="text-sm hover:underline">
                {user?.display_name || '个人中心'}
              </Link>
              <button onClick={() => logout()} className="text-sm text-muted-foreground hover:underline">
                登出
              </button>
            </>
          ) : (
            <>
              <Link to="/login">登录</Link>
              <Link to="/register">注册</Link>
            </>
          )}
        </div>
      </div>
    </header>
  )
}

