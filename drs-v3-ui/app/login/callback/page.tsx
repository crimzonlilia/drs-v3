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
    <div className="w-full max-w-md p-8 bg-themeCard/60 border border-themeBorder rounded-2xl shadow-xl backdrop-blur-md relative z-10 text-center mx-4">
      {error ? (
        <div>
          <h2 className="text-xl font-serif font-bold text-rose-500 mb-4">Lỗi Đăng Nhập</h2>
          <p className="text-themeMuted text-sm mb-6">{error}</p>
          <button
            onClick={() => router.push('/login')}
            className="px-6 py-2.5 bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 rounded-xl text-sm font-semibold hover:opacity-90 transition-all shadow-md"
          >
            Quay lại Đăng nhập
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent-purple mx-auto"></div>
          <h2 className="text-lg font-semibold text-themeText">Đang đồng bộ tài khoản...</h2>
          <p className="text-themeMuted text-xs">Vui lòng chờ trong giây lát.</p>
        </div>
      )}
    </div>
  )
}

export default function CallbackPage() {
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

      <Suspense fallback={
        <div className="w-full max-w-md p-8 bg-themeCard/60 border border-themeBorder rounded-2xl shadow-xl backdrop-blur-md text-center mx-4">
          <div className="space-y-4">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent-purple mx-auto"></div>
            <h2 className="text-lg font-semibold text-themeText">Đang tải...</h2>
          </div>
        </div>
      }>
        <CallbackHandler />
      </Suspense>
    </div>
  )
}
