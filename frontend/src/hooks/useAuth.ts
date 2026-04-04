import { useAuthStore } from '@/stores/authStore'

export function useAuth() {
  const { user, token, login, logout } = useAuthStore()
  return { user, token, login, logout, isAuthenticated: !!user }
}
