import { useEffect, useState } from 'react';
import { Bell, BellRing } from 'lucide-react';
import { Link } from 'react-router-dom';

import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { api } from '@/hooks/use-auth';
import { formatRelativeTime } from '@/lib/utils';

interface NotificationItem {
  id: number;
  title: string;
  content: string;
  is_read: boolean;
  created_at: string;
}

export function NotificationBell() {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);

  const fetchUnreadCount = async () => {
    try {
      const response = await api.get('/notifications/unread-count');
      setUnreadCount(response.data.count);
    } catch {
      setUnreadCount(0);
    }
  };

  const fetchPreview = async () => {
    setIsLoading(true);
    try {
      const response = await api.get('/notifications', {
        params: { limit: 5, offset: 0 },
      });
      setItems(response.data.items);
      setUnreadCount(response.data.unread_count);
    } finally {
      setIsLoading(false);
    }
  };

  const handleMarkAllRead = async () => {
    await api.post('/notifications/read-all');
    setItems((current) => current.map((item) => ({ ...item, is_read: true })));
    setUnreadCount(0);
  };

  useEffect(() => {
    void fetchUnreadCount();
    const timer = window.setInterval(() => {
      void fetchUnreadCount();
    }, 60000);

    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (isOpen) {
      void fetchPreview();
    }
  }, [isOpen]);

  return (
    <DropdownMenu open={isOpen} onOpenChange={setIsOpen}>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          className="relative inline-flex h-10 w-10 items-center justify-center rounded-full border border-border bg-background text-foreground transition hover:bg-accent"
          aria-label="查看通知"
        >
          {unreadCount > 0 ? <BellRing className="h-4 w-4" /> : <Bell className="h-4 w-4" />}
          {unreadCount > 0 ? (
            <span className="absolute -right-1 -top-1 inline-flex min-w-5 items-center justify-center rounded-full bg-destructive px-1.5 py-0.5 text-[11px] font-semibold text-destructive-foreground">
              {unreadCount > 99 ? '99+' : unreadCount}
            </span>
          ) : null}
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        <DropdownMenuLabel className="flex items-center justify-between">
          <span>站内通知</span>
          <span className="text-xs text-muted-foreground">未读 {unreadCount}</span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />

        {isLoading ? (
          <div className="px-2 py-4 text-sm text-muted-foreground">加载中...</div>
        ) : items.length === 0 ? (
          <div className="px-2 py-4 text-sm text-muted-foreground">暂时没有通知</div>
        ) : (
          items.map((item) => (
            <DropdownMenuItem key={item.id} asChild>
              <Link to="/notifications" className="flex flex-col items-start gap-1 py-3">
                <div className="flex w-full items-center justify-between gap-3">
                  <span className="line-clamp-1 font-medium">{item.title}</span>
                  {!item.is_read ? <span className="h-2 w-2 rounded-full bg-primary" /> : null}
                </div>
                <p className="line-clamp-2 text-xs text-muted-foreground">
                  {item.content || '点击进入通知中心查看详情'}
                </p>
                <span className="text-[11px] text-muted-foreground">
                  {formatRelativeTime(item.created_at)}
                </span>
              </Link>
            </DropdownMenuItem>
          ))
        )}

        <DropdownMenuSeparator />
        <div className="flex items-center justify-between gap-2 px-1">
          <Button variant="ghost" size="sm" onClick={() => void handleMarkAllRead()}>
            全部已读
          </Button>
          <Button asChild variant="ghost" size="sm">
            <Link to="/notifications">查看全部</Link>
          </Button>
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
