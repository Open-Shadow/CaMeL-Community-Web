import { useState } from 'react'
import { Link } from 'react-router-dom'

import { useAuth } from '@/hooks/use-auth'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'

export function ForgotPasswordPage() {
  const { requestPasswordReset } = useAuth()
  const [email, setEmail] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setMessage('')
    setIsLoading(true)

    try {
      await requestPasswordReset(email)
      setMessage('如果该邮箱已注册，我们已发送重置密码邮件。')
    } catch (err: any) {
      setError(err.response?.data?.message || '发送重置邮件失败')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">找回密码</CardTitle>
          <CardDescription>输入注册邮箱，我们会发送重置链接</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && <div className="rounded-md bg-red-50 p-3 text-sm text-red-500">{error}</div>}
            {message && <div className="rounded-md bg-green-50 p-3 text-sm text-green-600">{message}</div>}
            <div className="space-y-2">
              <label htmlFor="email" className="text-sm font-medium">
                邮箱
              </label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="your@email.com"
              />
            </div>
            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? '发送中...' : '发送重置邮件'}
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
