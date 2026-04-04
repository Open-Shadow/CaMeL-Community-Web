import { createBrowserRouter } from 'react-router-dom'
import { Layout } from '@/components/layout/Layout'
import HomePage from '@/pages/HomePage'
import LoginPage from '@/pages/auth/LoginPage'
import RegisterPage from '@/pages/auth/RegisterPage'
import MarketplacePage from '@/pages/marketplace/MarketplacePage'
import SkillDetailPage from '@/pages/marketplace/SkillDetailPage'
import BountyListPage from '@/pages/bounty/BountyListPage'
import BountyDetailPage from '@/pages/bounty/BountyDetailPage'
import WorkshopPage from '@/pages/workshop/WorkshopPage'
import ArticleDetailPage from '@/pages/workshop/ArticleDetailPage'
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
      { path: 'marketplace/:id', element: <SkillDetailPage /> },
      { path: 'bounty', element: <BountyListPage /> },
      { path: 'bounty/:id', element: <BountyDetailPage /> },
      { path: 'workshop', element: <WorkshopPage /> },
      { path: 'workshop/:id', element: <ArticleDetailPage /> },
      { path: 'profile/:username', element: <ProfilePage /> },
      { path: 'admin', element: <AdminPage /> },
    ],
  },
])
