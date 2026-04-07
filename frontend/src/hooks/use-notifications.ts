import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '@/hooks/use-auth';
import { API_BASE_URL } from '@/lib/env';

interface Notification {
  id: number;
  notification_type: string;
  title: string;
  content: string;
  reference_id: string;
  is_read: boolean;
  created_at: string;
}

export function useNotifications() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const eventSourceRef = useRef<EventSource | null>(null);

  const fetchNotifications = useCallback(async (unreadOnly = false) => {
    try {
      const res = await api.get('/notifications/', { params: { unread_only: unreadOnly } });
      setNotifications(res.data);
    } catch { /* ignore */ }
  }, []);

  const fetchUnreadCount = useCallback(async () => {
    try {
      const res = await api.get('/notifications/unread-count');
      setUnreadCount(res.data.count);
    } catch { /* ignore */ }
  }, []);

  const markAsRead = useCallback(async (id: number) => {
    await api.post(`/notifications/${id}/read`);
    setNotifications((prev) => prev.map((n) => n.id === id ? { ...n, is_read: true } : n));
    setUnreadCount((c) => Math.max(0, c - 1));
  }, []);

  const markAllRead = useCallback(async () => {
    await api.post('/notifications/read-all');
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    setUnreadCount(0);
  }, []);

  // SSE connection
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    fetchNotifications();
    fetchUnreadCount();
    setIsLoading(false);

    const es = new EventSource(`${API_BASE_URL}/notifications/stream?token=${token}`);
    eventSourceRef.current = es;

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'count') {
          setUnreadCount(data.count);
        } else if (data.type === 'new') {
          setUnreadCount(data.count);
          fetchNotifications();
        }
      } catch { /* ignore */ }
    };

    es.onerror = () => {
      // Reconnect handled by browser EventSource
    };

    return () => { es.close(); eventSourceRef.current = null; };
  }, []);

  return { notifications, unreadCount, isLoading, markAsRead, markAllRead, fetchNotifications };
}
