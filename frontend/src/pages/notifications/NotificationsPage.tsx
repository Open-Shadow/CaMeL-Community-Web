import { useEffect, useState } from 'react';
import { Bell, RadioTower, RefreshCcw } from 'lucide-react';
import { Link } from 'react-router-dom';

import { EmptyState } from '@/components/shared/empty-state';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { api, useAuth } from '@/hooks/use-auth';
import { cn, formatDateTime, formatRelativeTime } from '@/lib/utils';

interface NotificationItem {
  id: number;
  notification_type: string;
  title: string;
  content: string;
  reference_id: string;
  is_read: boolean;
  created_at: string;
}

interface NotificationResponse {
  items: NotificationItem[];
  total: number;
  unread_count: number;
}

const PAGE_SIZE = 20;

export default function NotificationsPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [total, setTotal] = useState(0);
  const [unreadCount, setUnreadCount] = useState(0);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [streamMessage, setStreamMessage] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchNotifications = async (reset = true) => {
    const offset = reset ? 0 : items.length;
    const response = await api.get('/notifications', {
      params: { limit: PAGE_SIZE, offset, unread_only: unreadOnly },
    });
    const payload: NotificationResponse = response.data;

    setItems((current) => (reset ? payload.items : [...current, ...payload.items]));
    setTotal(payload.total);
    setUnreadCount(payload.unread_count);
  };

  const fetchStreamStatus = async () => {
    try {
      const response = await api.get('/notifications/stream-status');
      setStreamMessage(response.data.message);
    } catch {
      setStreamMessage('SSE 状态暂时不可用，当前以前端手动刷新为主。');
    }
  };

  useEffect(() => {
    if (authLoading) return;
    if (!isAuthenticated) {
      setIsLoading(false);
      return;
    }

    const load = async () => {
      setIsLoading(true);
      try {
        await Promise.all([fetchNotifications(true), fetchStreamStatus()]);
      } finally {
        setIsLoading(false);
      }
    };

    void load();
  }, [authLoading, isAuthenticated, unreadOnly]);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await fetchNotifications(true);
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleMarkRead = async (notificationId: number) => {
    await api.post(`/notifications/${notificationId}/read`);
    await fetchNotifications(true);
  };

  const handleMarkAllRead = async () => {
    await api.post('/notifications/read-all');
    await fetchNotifications(true);
  };

  if (!isAuthenticated && !authLoading) {
    return (
      <EmptyState
        icon={<Bell className="h-10 w-10" />}
        title="需要先登录"
        description="登录后才能查看站内通知、未读数和信用分提醒。"
        action={
          <Button asChild>
            <Link to="/login">前往登录</Link>
          </Button>
        }
      />
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="space-y-2">
        <p className="text-sm uppercase tracking-[0.24em] text-muted-foreground">Notifications</p>
        <h1 className="text-3xl font-bold tracking-tight">通知中心</h1>
        <p className="text-muted-foreground">查看站内消息、信用分变化提醒，以及当前 SSE 接入状态。</p>
      </div>

      <Card className="border-dashed bg-sky-50/60">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <RadioTower className="h-5 w-5 text-sky-600" />
            实时推送状态
          </CardTitle>
          <CardDescription>{streamMessage || '读取中...'}</CardDescription>
        </CardHeader>
      </Card>

      <Card>
        <CardHeader className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <CardTitle>站内通知</CardTitle>
            <CardDescription>
              当前未读 {unreadCount} 条，共 {total} 条
            </CardDescription>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant={unreadOnly ? 'default' : 'outline'}
              onClick={() => setUnreadOnly((current) => !current)}
            >
              {unreadOnly ? '显示全部' : '只看未读'}
            </Button>
            <Button variant="outline" onClick={() => void handleMarkAllRead()}>
              全部标记已读
            </Button>
            <Button variant="outline" onClick={() => void handleRefresh()} disabled={isRefreshing}>
              <RefreshCcw className={cn('h-4 w-4', isRefreshing ? 'animate-spin' : '')} />
              刷新
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="py-10 text-center text-muted-foreground">加载通知中...</div>
          ) : items.length === 0 ? (
            <EmptyState
              icon={<Bell className="h-10 w-10" />}
              title="通知箱是空的"
              description="后端通知服务已经接入，后续触发事件后会在这里展示。"
            />
          ) : (
            <div className="space-y-3">
              {items.map((item) => (
                <div
                  key={item.id}
                  className={cn(
                    'rounded-2xl border px-4 py-4 shadow-sm transition',
                    item.is_read ? 'bg-background' : 'border-sky-200 bg-sky-50/50'
                  )}
                >
                  <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                    <div className="space-y-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="rounded-full bg-muted px-2.5 py-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                          {item.notification_type}
                        </span>
                        {!item.is_read ? (
                          <span className="rounded-full bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary">
                            未读
                          </span>
                        ) : null}
                      </div>
                      <h3 className="text-base font-semibold">{item.title}</h3>
                      <p className="text-sm leading-6 text-muted-foreground">
                        {item.content || '这条通知暂无补充说明。'}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {formatRelativeTime(item.created_at)} · {formatDateTime(item.created_at)}
                      </p>
                    </div>
                    <div className="flex shrink-0 gap-2">
                      {!item.is_read ? (
                        <Button variant="outline" size="sm" onClick={() => void handleMarkRead(item.id)}>
                          标记已读
                        </Button>
                      ) : null}
                    </div>
                  </div>
                </div>
              ))}

              {items.length < total ? (
                <div className="flex justify-center pt-2">
                  <Button variant="outline" onClick={() => void fetchNotifications(false)}>
                    加载更多
                  </Button>
                </div>
              ) : null}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
