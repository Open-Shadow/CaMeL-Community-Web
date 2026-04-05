/**
 * CaMeL Community API Client
 *
 * Typed API client for all backend endpoints.
 *
 * Usage:
 *   import { adminApi, paymentsApi } from '@/lib/api';
 *
 * For OpenAPI codegen (when backend is running):
 *   pnpm generate-api
 */
export {
  // API client namespaces
  authApi,
  adminApi,
  paymentsApi,
  creditsApi,
  rankingsApi,
  notificationsApi,
  usersApi,
  // Types
  type AuthTokens,
  type UserProfile,
  type DashboardData,
  type AdminUser,
  type AdminUserList,
  type AdminUserDetail,
  type FinanceReport,
  type Balance,
  type TransactionRecord,
  type IncomeSummary,
  type CheckoutResult,
  type DiscountInfo,
  type PriceCalcResult,
  type ThresholdCheck,
  type CreditLog,
  type LeaderboardEntry,
  type LeaderboardData,
  type Notification,
  type MessageResponse,
} from './client';
