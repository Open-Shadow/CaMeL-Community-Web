import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { useAuth } from '@/hooks/use-auth'
import { api } from '@/hooks/use-auth'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export function SSOCallbackPage() {
  const { loginWithTokens } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [message, setMessage] = useState('正在通过 CaMeL 账号登录...')

  useEffect(() => {
    const token = searchParams.get('token')

    if (!token) {
      setMessage('缺少 SSO 令牌。')
      return
    }

    api
      .post('/auth/sso/callback', { token })
      .then((res) => {
        return loginWithTokens(res.data)
      })
      .then(() => {
        navigate('/')
      })
      .catch((err: any) => {
        setMessage(err.response?.data?.message || 'SSO 登录失败，请稍后重试。')
      })
  }, [loginWithTokens, navigate, searchParams])

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">CaMeL SSO 登录</CardTitle>
          <CardDescription>正在同步你的账号状态</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-md bg-slate-50 p-3 text-sm text-slate-600">{message}</div>
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
