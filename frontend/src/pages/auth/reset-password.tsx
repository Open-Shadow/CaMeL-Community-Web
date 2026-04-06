import { useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'

import { useAuth } from '@/hooks/use-auth'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'

export function ResetPasswordPage() {
  const { resetPassword } = useAuth()
  const routeParams = useParams<{ uid?: string; token?: string }>()
  const [searchParams] = useSearchParams()
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const normalizedSearchParams = useMemo(() => {
    const rawSearch = window.location.search || ''
    return new URLSearchParams(rawSearch.replace(/&amp;/gi, '&'))
  }, [])

  const hashParams = useMemo(() => {
    const rawHash = window.location.hash?.startsWith('#') ? window.location.hash.slice(1) : window.location.hash || ''
    return new URLSearchParams(rawHash.replace(/&amp;/gi, '&'))
  }, [])

  const pickParam = (name: 'uid' | 'token') => {
    return (
      routeParams[name] ||
      searchParams.get(name) ||
      normalizedSearchParams.get(name) ||
      searchParams.get(`amp;${name}`) ||
      normalizedSearchParams.get(`amp;${name}`) ||
      hashParams.get(name) ||
      hashParams.get(`amp;${name}`) ||
      ''
    )
  }

  const uid = pickParam('uid')
  const token = pickParam('token')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setMessage('')

    if (!uid || !token) {
      setError('重置链接无效或不完整')
      return
    }

    if (password.length < 8) {
      setError('密码至少需要8个字符')
      return
    }

    if (password !== confirmPassword) {
      setError('两次输入的密码不一致')
      return
    }

    setIsLoading(true)

    try {
      await resetPassword(uid, token, password)
      setMessage('密码已重置，请使用新密码登录。')
    } catch (err: any) {
      setError(err.response?.data?.message || '密码重置失败')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">重置密码</CardTitle>
          <CardDescription>设置你的新密码</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && <div className="rounded-md bg-red-50 p-3 text-sm text-red-500">{error}</div>}
            {message && <div className="rounded-md bg-green-50 p-3 text-sm text-green-600">{message}</div>}
            <div className="space-y-2">
              <label htmlFor="password" className="text-sm font-medium">
                新密码
              </label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder="至少8个字符"
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="confirmPassword" className="text-sm font-medium">
                确认新密码
              </label>
              <Input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                placeholder="再次输入新密码"
              />
            </div>
            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? '提交中...' : '重置密码'}
            </Button>
          </form>
          <div className="mt-4 text-center text-sm">
            <Link to="/login" className="text-primary hover:underline">
              返回登录
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
