'use client'

import React, { useState, useEffect, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { login, register, API_BASE } from '@/app/api-client'
import { showToast } from '@/components/toast'
import { useTheme } from '@/app/theme-provider'
import { Moon, Sun } from 'lucide-react'

function LoginForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const mode = searchParams.get('mode')

  const { theme, toggleTheme } = useTheme()
  const [isLogin, setIsLogin] = useState(true)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [email, setEmail] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  // Parse mode from URL search query
  useEffect(() => {
    if (mode === 'register') {
      setIsLogin(false)
    } else {
      setIsLogin(true)
    }
  }, [mode])

  // Redirect to dashboard if token exists
  useEffect(() => {
    const token = localStorage.getItem('drs_token')
    if (token) {
      router.push('/dashboard')
    }
  }, [router])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      if (isLogin) {
        await login(username, password)
        showToast('Đăng nhập thành công!', 'success')
        router.push('/dashboard')
      } else {
        await register(username, password, email || undefined)
        showToast('Đăng ký thành công! Hãy đăng nhập.', 'success')
        setIsLogin(true)
        setEmail('')
        setPassword('')
      }
    } catch (err: any) {
      console.error(err)
      setError(err.message || 'Có lỗi xảy ra!')
    } finally {
      setLoading(false)
    }
  }

  const handleGoogleLogin = async () => {
    setError('')
    try {
      const res = await fetch(`${API_BASE}/api/auth/google/login`)
      if (!res.ok) {
        throw new Error(`Lỗi khởi tạo SSO: ${res.statusText}`)
      }
      const data = await res.json()
      if (data.url) {
        window.location.href = data.url
      } else {
        throw new Error('Không nhận được URL đăng nhập từ server')
      }
    } catch (err: any) {
      console.error(err)
      setError(err.message || 'Lỗi kết nối tới SSO')
    }
  }

  return (
    <div className="w-screen h-screen flex items-center justify-center bg-themeBg text-themeText font-sans transition-colors duration-300 relative overflow-hidden">
      {/* Floating Letters Background */}
      <div className="absolute inset-0 pointer-events-none select-none overflow-hidden opacity-10 dark:opacity-5 z-0">
        <span className="absolute text-[12px] font-mono text-slate-500 top-[15%] left-[20%]">a</span>
        <span className="absolute text-[14px] font-mono text-slate-500 top-[10%] left-[45%]">f</span>
        <span className="absolute text-[11px] font-mono text-slate-500 top-[8%] left-[70%]">y</span>
        <span className="absolute text-[16px] font-mono text-slate-500 top-[20%] left-[80%]">w</span>
        <span className="absolute text-[13px] font-mono text-slate-500 top-[35%] left-[10%]">t</span>
        <span className="absolute text-[15px] font-mono text-slate-500 top-[40%] left-[30%]">s</span>
        <span className="absolute text-[12px] font-mono text-slate-500 top-[45%] left-[55%]">b</span>
        <span className="absolute text-[14px] font-mono text-slate-500 top-[38%] left-[85%]">q</span>
      </div>

      {/* Floating Theme Toggle */}
      <button
        onClick={toggleTheme}
        className="absolute top-6 right-6 p-2.5 hover:bg-slate-200/50 dark:hover:bg-slate-800/50 rounded-xl border border-themeBorder backdrop-blur-md transition-colors z-50"
        title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
      >
        {theme === 'light' ? (
          <Moon size={18} className="text-slate-700" />
        ) : (
          <Sun size={18} className="text-accent-cyan" />
        )}
      </button>

      {/* Main Form Container */}
      <div className="w-full max-w-md p-8 bg-themeCard/60 border border-themeBorder rounded-2xl shadow-xl backdrop-blur-md relative z-10 mx-4">
        {/* Logo and Greeting */}
        <div className="flex flex-col items-center mb-6">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent-purple to-accent-violet flex items-center justify-center mb-3">
            <span className="text-white font-serif font-bold text-lg">d</span>
          </div>
          <h1 className="font-serif font-bold text-2xl tracking-wide text-themeText">
            drs<span className="text-accent-purple">.</span>v3
          </h1>
          <p className="text-xs text-themeMuted mt-1">
            {isLogin ? 'Welcome back. Sign in to your workspace.' : 'Create an account to get started.'}
          </p>
        </div>

        {error && (
          <div className="p-3.5 mb-4 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-500 dark:text-rose-400 text-xs leading-relaxed">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-[10px] uppercase font-bold text-themeMuted tracking-wider mb-1.5">Tên tài khoản</label>
            <input
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl focus:outline-none focus:ring-2 focus:ring-accent-purple/20 transition-all text-sm"
              placeholder="Nhập tên đăng nhập"
            />
          </div>

          {!isLogin && (
            <div>
              <label className="block text-[10px] uppercase font-bold text-themeMuted tracking-wider mb-1.5">Email (Không bắt buộc)</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl focus:outline-none focus:ring-2 focus:ring-accent-purple/20 transition-all text-sm"
                placeholder="email@example.com"
              />
            </div>
          )}

          <div>
            <label className="block text-[10px] uppercase font-bold text-themeMuted tracking-wider mb-1.5">Mật khẩu</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl focus:outline-none focus:ring-2 focus:ring-accent-purple/20 transition-all text-sm"
              placeholder="Nhập mật khẩu"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 mt-4 bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 rounded-xl text-sm font-semibold hover:opacity-90 disabled:opacity-50 transition-all shadow-md flex items-center justify-center"
          >
            {loading ? 'Đang xử lý...' : isLogin ? 'Đăng Nhập' : 'Đăng Ký'}
          </button>
        </form>

        <div className="relative flex py-5 items-center">
          <div className="flex-grow border-t border-themeBorder"></div>
          <span className="flex-shrink mx-4 text-themeMuted text-[10px] font-bold uppercase tracking-wider">Hoặc</span>
          <div className="flex-grow border-t border-themeBorder"></div>
        </div>

        <button
          type="button"
          onClick={handleGoogleLogin}
          className="w-full py-3 bg-white dark:bg-slate-950 border border-themeBorder hover:bg-slate-50 dark:hover:bg-slate-900/60 text-themeText rounded-xl text-sm font-semibold transition-all shadow-sm flex items-center justify-center gap-3"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.56-2.77c-.98.66-2.23 1.06-3.72 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
          </svg>
          Tiếp tục với Google
        </button>

        <div className="mt-6 text-center text-sm text-themeMuted">
          {isLogin ? (
            <p>
              Chưa có tài khoản?{' '}
              <button onClick={() => setIsLogin(false)} className="text-accent-purple hover:underline font-medium ml-1">
                Đăng ký ngay
              </button>
            </p>
          ) : (
            <p>
              Đã có tài khoản?{' '}
              <button onClick={() => setIsLogin(true)} className="text-accent-purple hover:underline font-medium ml-1">
                Đăng nhập
              </button>
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center bg-themeBg text-themeText text-sm">Loading login...</div>}>
      <LoginForm />
    </Suspense>
  )
}
