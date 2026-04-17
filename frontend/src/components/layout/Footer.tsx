import { Link } from 'react-router-dom'

const FOOTER_LINKS = [
  {
    title: '平台',
    links: [
      { label: '技能市场', to: '/marketplace' },
      { label: '悬赏任务', to: '/bounty' },
      { label: '知识工坊', to: '/workshop' },
      { label: '排行榜', to: '/rankings/credit' },
    ],
  },
  {
    title: '社区',
    links: [
      { label: '关于我们', to: '#' },
      { label: '使用条款', to: '#' },
      { label: '隐私政策', to: '#' },
    ],
  },
]

export function Footer() {
  return (
    <footer className="border-t bg-muted/30">
      <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
        <div className="grid gap-8 sm:grid-cols-3">
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-lg font-bold">
              <span className="inline-flex h-6 w-6 items-center justify-center rounded-md bg-primary text-[10px] font-black text-white">C</span>
              CaMeL Community
            </div>
            <p className="text-sm leading-6 text-muted-foreground">
              AI 社区平台 — 技能交易、悬赏任务、知识沉淀
            </p>
          </div>
          {FOOTER_LINKS.map((group) => (
            <div key={group.title}>
              <h3 className="mb-3 text-sm font-semibold">{group.title}</h3>
              <ul className="space-y-2">
                {group.links.map((link) => (
                  <li key={link.label}>
                    <Link
                      to={link.to}
                      className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="mt-8 border-t pt-6 text-center text-xs text-muted-foreground">
          &copy; {new Date().getFullYear()} CaMeL Community. All rights reserved.
        </div>
      </div>
    </footer>
  )
}
