import { Link } from 'react-router-dom'

export function Header() {
  return (
    <header className="border-b">
      <div className="container mx-auto px-4 h-16 flex items-center justify-between">
        <Link to="/" className="font-bold text-xl">CaMeL Community</Link>
        <nav className="flex gap-6">
          <Link to="/marketplace">技能市场</Link>
          <Link to="/bounty">悬赏任务</Link>
          <Link to="/workshop">知识工坊</Link>
        </nav>
        <div className="flex gap-2">
          <Link to="/login">登录</Link>
          <Link to="/register">注册</Link>
        </div>
      </div>
    </header>
  )
}
