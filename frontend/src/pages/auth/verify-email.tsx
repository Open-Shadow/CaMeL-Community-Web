import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { useAuth } from '@/hooks/use-auth'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export function VerifyEmailPage() {
  const { verifyEmail } = useAuth()
  const [searchParams] = useSearchParams()
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [message, setMessage] = useState('正在验证邮箱...')

  useEffect(() => {
    const key = searchParams.get('key')
    if (!key) {
      setStatus('error')
      setMessage('邮箱验证链接无效')
      return
    }

    verifyEmail(key)
      .then(() => {
        setStatus('success')
        setMessage('邮箱验证成功，现在可以继续使用平台功能。')
      })
      .catch((err: any) => {
        setStatus('error')
        setMessage(err.response?.data?.message || '邮箱验证失败')
      })
  }, [searchParams, verifyEmail])

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">邮箱验证</CardTitle>
          <CardDescription>确认你的账号邮箱</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div
            className={`rounded-md p-3 text-sm ${
              status === 'success'
                ? 'bg-green-50 text-green-600'
                : status === 'error'
                  ? 'bg-red-50 text-red-500'
                  : 'bg-muted text-muted-foreground'
            }`}
          >
            {message}
          </div>
          <div className="text-center text-sm">
            <Link to="/login" className="text-primary hover:underline">
              返回登录
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
