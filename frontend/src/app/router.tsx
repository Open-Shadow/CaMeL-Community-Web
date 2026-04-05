import { createBrowserRouter } from 'react-router-dom'
import { Layout } from '@/components/layout/Layout'
import HomePage from '@/pages/HomePage'
import { LoginPage } from '@/pages/auth/login'
import { RegisterPage } from '@/pages/auth/register'
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
import SeriesDetailPage from '@/pages/workshop/SeriesDetailPage'
import NotificationsPage from '@/pages/notifications/NotificationsPage'
import { CreditHistoryPage } from '@/pages/profile/CreditHistoryPage'
import { ProfileInvitesPage } from '@/pages/profile/invites'
import { ProfileSettingsPage } from '@/pages/profile/settings'
import ProfilePage from '@/pages/profile/ProfilePage'
import AdminPage from '@/pages/admin/AdminPage'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'login', element: <LoginPage /> },
      { path: 'register', element: <RegisterPage /> },
      { path: 'forgot-password', element: <ForgotPasswordPage /> },
      { path: 'reset-password', element: <ResetPasswordPage /> },
      { path: 'verify-email', element: <VerifyEmailPage /> },
      { path: 'auth/social/callback', element: <SocialCallbackPage /> },
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
      { path: 'notifications', element: <NotificationsPage /> },
      { path: 'profile/settings', element: <ProfileSettingsPage /> },
      { path: 'profile/credit-history', element: <CreditHistoryPage /> },
      { path: 'profile/invites', element: <ProfileInvitesPage /> },
      { path: 'u/:username', element: <ProfilePage /> },
      { path: 'profile/:username', element: <ProfilePage /> },
      { path: 'admin', element: <AdminPage /> },
    ],
  },
])
