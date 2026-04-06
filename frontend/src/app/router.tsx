import { createBrowserRouter } from 'react-router-dom'
import { Layout } from '@/components/layout/Layout'
import { AdminLayout } from '@/components/layout/AdminLayout'
import HomePage from '@/pages/HomePage'
import { LoginPage } from '@/pages/auth/login'
import { RegisterPage } from '@/pages/auth/register'
import { OAuthCallbackPage } from '@/pages/auth/oauth-callback'
import { ForgotPasswordPage } from '@/pages/auth/forgot-password'
import { ResetPasswordPage } from '@/pages/auth/reset-password'
import { SocialCallbackPage } from '@/pages/auth/social-callback'
import { VerifyEmailPage } from '@/pages/auth/verify-email'
import MarketplacePage from '@/pages/marketplace/MarketplacePage'
import SkillDetailPage from '@/pages/marketplace/SkillDetailPage'
import CreateSkillPage from '@/pages/marketplace/CreateSkillPage'
import MySkillsPage from '@/pages/marketplace/MySkillsPage'
import BountyListPage from '@/pages/bounty/BountyListPage'
import BountyDetailPage from '@/pages/bounty/BountyDetailPage'
import CreateBountyPage from '@/pages/bounty/CreateBountyPage'
import WorkshopPage from '@/pages/workshop/WorkshopPage'
import ArticleDetailPage from '@/pages/workshop/ArticleDetailPage'
import CreateArticlePage from '@/pages/workshop/CreateArticlePage'
import TipLeaderboardPage from '@/pages/workshop/TipLeaderboardPage'
import SeriesDetailPage from '@/pages/workshop/SeriesDetailPage'
import CreditLeaderboardPage from '@/pages/rankings/CreditLeaderboardPage'
import NotificationsPage from '@/pages/notifications/NotificationsPage'
import { ProfileSettingsPage } from '@/pages/profile/settings'
import { PublicProfilePage } from '@/pages/profile/public-profile'
import { CreditHistoryPage } from '@/pages/profile/credit-history'
import { InvitationPage } from '@/pages/profile/invitation'
import { ProfileInvitesPage } from '@/pages/profile/invites'
import { WalletPage } from '@/pages/wallet/WalletPage'
import AdminPage from '@/pages/admin/AdminPage'
import AdminUsersPage from '@/pages/admin/AdminUsersPage'
import AdminSkillsPage from '@/pages/admin/AdminSkillsPage'
import AdminArticlesPage from '@/pages/admin/AdminArticlesPage'
import AdminBountiesPage from '@/pages/admin/AdminBountiesPage'
import AdminFinancePage from '@/pages/admin/AdminFinancePage'
import AdminFeaturedPage from '@/pages/admin/AdminFeaturedPage'
import AdminDisputesPage from '@/pages/admin/AdminDisputesPage'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'login', element: <LoginPage /> },
      { path: 'register', element: <RegisterPage /> },
      { path: 'auth/callback/:provider', element: <OAuthCallbackPage /> },
      { path: 'auth/social/callback', element: <SocialCallbackPage /> },
      { path: 'forgot-password', element: <ForgotPasswordPage /> },
      { path: 'reset-password', element: <ResetPasswordPage /> },
      { path: 'reset-password/:uid/:token', element: <ResetPasswordPage /> },
      { path: 'verify-email', element: <VerifyEmailPage /> },
      { path: 'marketplace', element: <MarketplacePage /> },
      { path: 'marketplace/create', element: <CreateSkillPage /> },
      { path: 'marketplace/mine', element: <MySkillsPage /> },
      { path: 'marketplace/:id', element: <SkillDetailPage /> },
      { path: 'bounty', element: <BountyListPage /> },
      { path: 'bounty/mine', element: <BountyListPage /> },
      { path: 'bounty/create', element: <CreateBountyPage /> },
      { path: 'bounty/:id', element: <BountyDetailPage /> },
      { path: 'workshop', element: <WorkshopPage /> },
      { path: 'workshop/create', element: <CreateArticlePage /> },
      { path: 'workshop/series/:id', element: <SeriesDetailPage /> },
      { path: 'workshop/:id', element: <ArticleDetailPage /> },
      { path: 'workshop/tips/leaderboard', element: <TipLeaderboardPage /> },
      { path: 'rankings/credit', element: <CreditLeaderboardPage /> },
      { path: 'notifications', element: <NotificationsPage /> },
      { path: 'wallet', element: <WalletPage /> },
      { path: 'profile/settings', element: <ProfileSettingsPage /> },
      { path: 'profile/credit-history', element: <CreditHistoryPage /> },
      { path: 'profile/invitation', element: <InvitationPage /> },
      { path: 'profile/invites', element: <ProfileInvitesPage /> },
      { path: 'u/:username', element: <PublicProfilePage /> },
      {
        path: 'admin',
        element: <AdminLayout />,
        children: [
          { index: true, element: <AdminPage /> },
          { path: 'users', element: <AdminUsersPage /> },
          { path: 'skills', element: <AdminSkillsPage /> },
          { path: 'articles', element: <AdminArticlesPage /> },
          { path: 'bounties', element: <AdminBountiesPage /> },
          { path: 'finance', element: <AdminFinancePage /> },
          { path: 'featured', element: <AdminFeaturedPage /> },
          { path: 'disputes', element: <AdminDisputesPage /> },
        ],
      },
    ],
  },
])
