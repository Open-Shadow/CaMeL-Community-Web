import { useNotifications } from '@/hooks/use-notifications';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

export function NotificationsPage() {
  const { notifications, unreadCount, markAsRead, markAllRead } = useNotifications();

  return (
    <div className="container mx-auto py-8 max-w-2xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">通知中心</h1>
        {unreadCount > 0 && (
          <Button variant="outline" size="sm" onClick={markAllRead}>
            全部标为已读 ({unreadCount})
          </Button>
        )}
      </div>

      {notifications.length === 0 ? (
        <p className="text-muted-foreground text-center py-8">暂无通知</p>
      ) : (
        <div className="space-y-3">
          {notifications.map((n) => (
            <Card
              key={n.id}
              className={`cursor-pointer ${!n.is_read ? 'border-primary/30 bg-primary/5' : ''}`}
              onClick={() => { if (!n.is_read) markAsRead(n.id); }}
            >
              <CardContent className="flex items-start gap-3 py-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium">{n.title}</p>
                    {!n.is_read && <Badge variant="default" className="text-xs h-5">新</Badge>}
                  </div>
                  {n.content && (
                    <p className="text-sm text-muted-foreground mt-1">{n.content}</p>
                  )}
                  <p className="text-xs text-muted-foreground mt-2">
                    {new Date(n.created_at).toLocaleString('zh-CN')}
                  </p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
