import { useState } from 'react';
import { useNotifications } from '@/hooks/use-notifications';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

export function NotificationBell() {
  const { notifications, unreadCount, markAsRead, markAllRead } = useNotifications();
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <Button variant="ghost" size="sm" className="relative" onClick={() => setOpen(!open)}>
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
          <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
        </svg>
        {unreadCount > 0 && (
          <Badge variant="destructive" className="absolute -top-1 -right-1 h-5 min-w-[20px] px-1 text-xs">
            {unreadCount > 99 ? '99+' : unreadCount}
          </Badge>
        )}
      </Button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-10 z-50 w-80 bg-background border rounded-lg shadow-lg">
            <div className="flex items-center justify-between p-3 border-b">
              <span className="font-medium text-sm">通知</span>
              {unreadCount > 0 && (
                <Button variant="ghost" size="sm" className="text-xs h-6" onClick={markAllRead}>
                  全部已读
                </Button>
              )}
            </div>
            <div className="max-h-80 overflow-y-auto">
              {notifications.length === 0 ? (
                <p className="text-sm text-muted-foreground p-4 text-center">暂无通知</p>
              ) : (
                notifications.slice(0, 10).map((n) => (
                  <div
                    key={n.id}
                    className={`p-3 border-b last:border-0 cursor-pointer hover:bg-muted/50 ${!n.is_read ? 'bg-primary/5' : ''}`}
                    onClick={() => { if (!n.is_read) markAsRead(n.id); }}
                  >
                    <p className="text-sm font-medium">{n.title}</p>
                    {n.content && <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{n.content}</p>}
                    <p className="text-xs text-muted-foreground mt-1">
                      {new Date(n.created_at).toLocaleString('zh-CN')}
                    </p>
                  </div>
                ))
              )}
            </div>
            <div className="p-2 border-t text-center">
              <a href="/notifications" className="text-xs text-primary hover:underline">查看全部</a>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
