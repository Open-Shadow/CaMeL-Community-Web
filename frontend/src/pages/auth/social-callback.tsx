import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { useAuth } from '@/hooks/use-auth'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export function SocialCallbackPage() {
  const { completeSocialLogin } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [message, setMessage] = useState('正在完成社交登录...')

  useEffect(() => {
    const error = searchParams.get('error')
    const code = searchParams.get('code')

    if (error) {
      setMessage('社交登录失败，请稍后重试。')
      return
    }

    if (!code) {
      setMessage('缺少社交登录兑换码。')
      return
    }

    completeSocialLogin(code)
      .then(() => {
        navigate('/')
      })
      .catch((err: any) => {
        setMessage(err.response?.data?.message || '社交登录失败，请稍后重试。')
      })
  }, [completeSocialLogin, navigate, searchParams])

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">社交登录</CardTitle>
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
