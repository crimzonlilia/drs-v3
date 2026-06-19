'use client'

import { useEffect, useState, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { API_BASE } from '@/app/api-client'
import { showToast } from '@/components/toast'

function CallbackHandler() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [error, setError] = useState('')

  useEffect(() => {
    const code = searchParams.get('code')

    if (!code) {
      setError('Mã xác thực không hợp lệ hoặc thiếu.')
      return
    }

    const exchangeCode = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/auth/google/callback`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ code })
        })

        if (!res.ok) {
          const detail = await res.json().catch(() => ({}))
          throw new Error(detail.detail || 'Xác thực với server thất bại.')
        }

        const data = await res.json()
        if (data.access_token) {
          localStorage.setItem('drs_token', data.access_token)
          showToast('Đăng nhập thành công!', 'success')
          router.push('/dashboard')
        } else {
          throw new Error('Server không phản hồi mã truy cập hợp lệ.')
        }
      } catch (err: any) {
        console.error(err)
        setError(err.message || 'Lỗi xử lý đăng nhập.')
      }
    }

    exchangeCode()
  }, [searchParams, router])

  return (
    <div className="w-full max-w-md p-8 bg-slate-800 rounded-2xl border border-slate-700 shadow-xl text-center">
      {error ? (
        <div>
          <h2 className="text-xl font-bold text-rose-400 mb-4">Lỗi Đăng Nhập</h2>
          <p className="text-slate-300 text-sm mb-6">{error}</p>
          <button
            onClick={() => router.push('/login')}
            className="px-6 py-2.5 bg-violet-600 hover:bg-violet-500 text-white rounded-xl text-sm font-semibold transition-all"
          >
            Quay lại Đăng nhập
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-violet-500 mx-auto"></div>
          <h2 className="text-lg font-semibold text-slate-200">Đang đồng bộ tài khoản...</h2>
          <p className="text-slate-400 text-xs">Vui lòng chờ trong giây lát.</p>
        </div>
      )}
    </div>
  )
}

export default function CallbackPage() {
  return (
    <div className="w-screen h-screen flex items-center justify-center bg-slate-900 text-white font-sans">
      <Suspense fallback={
        <div className="w-full max-w-md p-8 bg-slate-800 rounded-2xl border border-slate-700 shadow-xl text-center">
          <div className="space-y-4">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-violet-500 mx-auto"></div>
            <h2 className="text-lg font-semibold text-slate-200">Đang tải...</h2>
          </div>
        </div>
      }>
        <CallbackHandler />
      </Suspense>
    </div>
  )
}
