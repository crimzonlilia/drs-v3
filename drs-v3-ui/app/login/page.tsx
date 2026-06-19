'use client'

import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { login, register } from '@/app/api-client'
import { showToast } from '@/components/toast'

export default function LoginPage() {
  const router = useRouter()
  const [isLogin, setIsLogin] = useState(true)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [email, setEmail] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

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

  return (
    <div className="w-screen h-screen flex items-center justify-center bg-slate-900 text-white font-sans">
      <div className="w-full max-w-md p-8 bg-slate-800 rounded-2xl border border-slate-700 shadow-xl">
        <h2 className="text-2xl font-bold mb-6 text-center">
          {isLogin ? 'Đăng Nhập' : 'Đăng Ký Tài Khoản'}
        </h2>

        {error && (
          <div className="p-3 mb-4 bg-rose-500/20 border border-rose-500 rounded-xl text-rose-300 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-bold text-slate-400 mb-1.5 uppercase">Tên tài khoản</label>
            <input
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-2.5 bg-slate-900 border border-slate-700 rounded-xl focus:outline-none focus:border-violet-500 text-white text-sm"
              placeholder="Nhập tên đăng nhập"
            />
          </div>

          {!isLogin && (
            <div>
              <label className="block text-xs font-bold text-slate-400 mb-1.5 uppercase">Email (Không bắt buộc)</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-2.5 bg-slate-900 border border-slate-700 rounded-xl focus:outline-none focus:border-violet-500 text-white text-sm"
                placeholder="email@example.com"
              />
            </div>
          )}

          <div>
            <label className="block text-xs font-bold text-slate-400 mb-1.5 uppercase">Mật khẩu</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2.5 bg-slate-900 border border-slate-700 rounded-xl focus:outline-none focus:border-violet-500 text-white text-sm"
              placeholder="Nhập mật khẩu"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 mt-4 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white rounded-xl text-sm font-semibold transition-all shadow-md"
          >
            {loading ? 'Đang xử lý...' : isLogin ? 'Đăng Nhập' : 'Đăng Ký'}
          </button>
        </form>

        <div className="mt-6 text-center text-sm text-slate-400">
          {isLogin ? (
            <p>
              Chưa có tài khoản?{' '}
              <button onClick={() => setIsLogin(false)} className="text-violet-400 hover:underline">
                Đăng ký ngay
              </button>
            </p>
          ) : (
            <p>
              Đã có tài khoản?{' '}
              <button onClick={() => setIsLogin(true)} className="text-violet-400 hover:underline">
                Đăng nhập
              </button>
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
