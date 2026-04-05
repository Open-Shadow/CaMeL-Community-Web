/**
 * CaMeL Community API Client
 *
 * Type-safe API client for all backend endpoints.
 * Uses the shared axios instance from use-auth for automatic JWT handling.
 *
 * Usage:
 *   import { adminApi, rankingsApi, paymentsApi } from '@/lib/api/client';
 *   const dashboard = await adminApi.getDashboard();
 */

import { api } from '@/hooks/use-auth';

// =============================================================================
// Common Types
// =============================================================================

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface MessageResponse {
  message: string;
}

// =============================================================================
// Auth Types
// =============================================================================

export interface AuthTokens {
  access: string;
  refresh: string;
  expires_in: number;
}

export interface UserProfile {
  id: number;
  email: string;
  username: string;
  display_name: string;
  bio: string;
  avatar_url: string;
  role: 'USER' | 'MODERATOR' | 'ADMIN';
  level: 'SEED' | 'CRAFTSMAN' | 'EXPERT' | 'MASTER' | 'GRANDMASTER';
  credit_score: number;
  balance: number;
  frozen_balance: number;
  created_at: string;
}

// =============================================================================
// Admin Types
// =============================================================================

export interface DashboardData {
  total_users: number;
  new_users_today: number;
  new_users_7d: number;
  total_skills: number;
  total_articles: number;
  total_bounties: number;
  total_deposits: number;
  total_fees: number;
  active_users_7d: number;
}

export interface AdminUser {
  id: number;
  username: string;
  email: string;
  display_name: string;
  role: string;
  level: string;
  credit_score: number;
  balance: number;
  frozen_balance: number;
  is_active: boolean;
  date_joined: string;
  last_login: string | null;
}

export interface AdminUserList {
  users: AdminUser[];
  total: number;
  page: number;
  page_size: number;
}

export interface AdminUserDetail extends AdminUser {
  bio: string;
  avatar_url: string;
  skills_count: number;
  articles_count: number;
  transactions_count: number;
  invitees_count: number;
}

export interface FinanceReport {
  total_deposits: number;
  total_fees: number;
  total_circulation: number;
  total_frozen: number;
  deposits_7d: number;
  fees_7d: number;
  deposits_30d: number;
  fees_30d: number;
  daily_deposits: { date: string; total: number; count: number }[];
  daily_fees: { date: string; total: number; count: number }[];
}

// =============================================================================
// Payment Types
// =============================================================================

export interface Balance {
  balance: number;
  frozen_balance: number;
  available: number;
}

export interface TransactionRecord {
  id: number;
  transaction_type: string;
  amount: number;
  balance_after: number;
  description: string;
  reference_id: string;
  created_at: string;
}

export interface IncomeSummary {
  total_income: number;
  transaction_count: number;
}

export interface CheckoutResult {
  checkout_url: string;
  session_id: string;
}

// =============================================================================
// Credit Types
// =============================================================================

export interface DiscountInfo {
  level: string;
  level_name: string;
  level_icon: string;
  credit_score: number;
  discount_rate: number;
}

export interface PriceCalcResult {
  base_price: number;
  discount_rate: number;
  discounted_price: number;
  level: string;
  level_name: string;
  savings: number;
}

export interface ThresholdCheck {
  allowed: boolean;
  reason: string;
  credit_score: number;
  required_score: number;
}

export interface CreditLog {
  id: number;
  action: string;
  amount: number;
  score_before: number;
  score_after: number;
  created_at: string;
}

// =============================================================================
// Rankings Types
// =============================================================================

export interface LeaderboardEntry {
  rank: number;
  user_id: number;
  username: string;
  display_name: string;
  avatar_url: string;
  level: string;
  credit_score: number;
}

export interface LeaderboardData {
  entries: LeaderboardEntry[];
  updated_at: string | null;
  my_rank: number | null;
  my_score: number | null;
}

// =============================================================================
// Notification Types
// =============================================================================

export interface Notification {
  id: number;
  notification_type: string;
  title: string;
  content: string;
  is_read: boolean;
  created_at: string;
}

// =============================================================================
// API Client Functions
// =============================================================================

export const authApi = {
  login: (email: string, password: string) =>
    api.post<AuthTokens>('/auth/login', { email, password }),
  register: (email: string, password: string, display_name?: string) =>
    api.post<AuthTokens>('/auth/register', { email, password, display_name }),
  logout: (refresh: string) =>
    api.post('/auth/logout', { refresh }),
  refresh: (refresh: string) =>
    api.post<AuthTokens>('/auth/refresh', { refresh }),
  me: () =>
    api.get<UserProfile>('/auth/me'),
};

export const adminApi = {
  getDashboard: () =>
    api.get<DashboardData>('/admin/dashboard'),
  listUsers: (params?: { page?: number; page_size?: number; search?: string; role?: string; level?: string; sort?: string }) =>
    api.get<AdminUserList>('/admin/users', { params }),
  getUserDetail: (userId: number) =>
    api.get<AdminUserDetail>(`/admin/users/${userId}`),
  updateRole: (userId: number, role: string) =>
    api.patch<MessageResponse>(`/admin/users/${userId}/role`, { role }),
  banUser: (userId: number, reason?: string) =>
    api.post<MessageResponse>(`/admin/users/${userId}/ban`, { reason }),
  unbanUser: (userId: number) =>
    api.post<MessageResponse>(`/admin/users/${userId}/unban`),
  adjustCredit: (userId: number, amount: number, reason?: string) =>
    api.post<MessageResponse>(`/admin/users/${userId}/credit-adjust`, { amount, reason }),
  getFinanceReport: () =>
    api.get<FinanceReport>('/admin/finance/report'),
};

export const paymentsApi = {
  deposit: (amount: number) =>
    api.post<CheckoutResult>('/payments/deposit', { amount }),
  getBalance: () =>
    api.get<Balance>('/payments/balance'),
  listTransactions: (params?: { limit?: number; offset?: number; tx_type?: string }) =>
    api.get<TransactionRecord[]>('/payments/transactions', { params }),
  getIncomeSummary: () =>
    api.get<IncomeSummary>('/payments/income-summary'),
};

export const creditsApi = {
  getDiscountInfo: () =>
    api.get<DiscountInfo>('/credits/discount-info'),
  calculatePrice: (base_price: number) =>
    api.post<PriceCalcResult>('/credits/calculate-price', { base_price }),
  checkBountyPost: () =>
    api.get<ThresholdCheck>('/credits/check/bounty-post'),
  checkBountyApply: () =>
    api.get<ThresholdCheck>('/credits/check/bounty-apply'),
  checkArbitration: () =>
    api.get<ThresholdCheck>('/credits/check/arbitration'),
};

export const rankingsApi = {
  getCreditLeaderboard: () =>
    api.get<LeaderboardData>('/rankings/credit'),
};

export const notificationsApi = {
  list: (params?: { limit?: number; offset?: number; unread_only?: boolean }) =>
    api.get<Notification[]>('/notifications/', { params }),
  markRead: (id: number) =>
    api.post<MessageResponse>(`/notifications/${id}/read`),
  markAllRead: () =>
    api.post<MessageResponse>('/notifications/read-all'),
  getUnreadCount: () =>
    api.get<{ count: number }>('/notifications/unread-count'),
};

export const usersApi = {
  getMe: () =>
    api.get<UserProfile>('/users/me'),
  updateMe: (data: { display_name?: string; bio?: string }) =>
    api.patch<UserProfile>('/users/me', data),
  uploadAvatar: (file: File) => {
    const formData = new FormData();
    formData.append('avatar', file);
    return api.post<{ avatar_url: string }>('/users/me/avatar', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  getPublicProfile: (username: string) =>
    api.get<UserProfile>(`/users/by-username/${username}`),
  getCreditHistory: () =>
    api.get<CreditLog[]>('/users/me/credit-history'),
};
