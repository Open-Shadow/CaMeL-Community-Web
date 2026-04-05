import { createBrowserRouter } from 'react-router-dom'
import { Layout } from '@/components/layout/Layout'
import HomePage from '@/pages/HomePage'
import { LoginPage } from '@/pages/auth/login'
import { RegisterPage } from '@/pages/auth/register'
import MarketplacePage from '@/pages/marketplace/MarketplacePage'
import SkillDetailPage from '@/pages/marketplace/SkillDetailPage'
import CreateSkillPage from '@/pages/marketplace/CreateSkillPage'
import BountyListPage from '@/pages/bounty/BountyListPage'
import BountyDetailPage from '@/pages/bounty/BountyDetailPage'
import CreateBountyPage from '@/pages/bounty/CreateBountyPage'
import WorkshopPage from '@/pages/workshop/WorkshopPage'
import ArticleDetailPage from '@/pages/workshop/ArticleDetailPage'
import CreateArticlePage from '@/pages/workshop/CreateArticlePage'
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
      { path: 'marketplace', element: <MarketplacePage /> },
      { path: 'marketplace/create', element: <CreateSkillPage /> },
      { path: 'marketplace/:id', element: <SkillDetailPage /> },
      { path: 'bounty', element: <BountyListPage /> },
      { path: 'bounty/create', element: <CreateBountyPage /> },
      { path: 'bounty/:id', element: <BountyDetailPage /> },
      { path: 'workshop', element: <WorkshopPage /> },
      { path: 'workshop/create', element: <CreateArticlePage /> },
      { path: 'workshop/:id', element: <ArticleDetailPage /> },
      { path: 'profile/settings', element: <ProfileSettingsPage /> },
      { path: 'profile/:username', element: <ProfilePage /> },
      { path: 'admin', element: <AdminPage /> },
    ],
  },
])
