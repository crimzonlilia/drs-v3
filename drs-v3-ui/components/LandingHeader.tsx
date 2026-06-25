'use client'

import React from 'react'
import Link from 'next/link'
import { Moon, Sun } from 'lucide-react'
import { useTheme } from '@/app/theme-provider'

export default function LandingHeader() {
  const { theme, toggleTheme } = useTheme()

  return (
    <header className="fixed top-0 left-0 w-full z-50 bg-themeBg/80 border-b border-themeBorder backdrop-blur-md px-6 py-4 flex items-center justify-between transition-colors duration-300">
      {/* Logo */}
      <Link href="/" className="flex items-center gap-2">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent-purple to-accent-violet flex items-center justify-center">
          <span className="text-white font-serif font-bold text-base">o</span>
        </div>
        <span className="font-serif font-bold text-2xl tracking-wide text-themeText relative">
          oneiros<span className="text-[9px] font-sans font-semibold uppercase tracking-wider text-accent-purple ml-1 absolute -top-1.5 -right-7 px-1.5 py-0.5 rounded-md bg-accent-purple/10">beta</span>
        </span>
      </Link>

      {/* Center Links */}
      <nav className="hidden md:flex items-center gap-8">
        <Link href="#features" className="text-sm font-medium text-themeMuted hover:text-accent-purple dark:hover:text-accent-violet transition-colors">
          Tính năng
        </Link>
        <Link href="#pipeline" className="text-sm font-medium text-themeMuted hover:text-accent-purple dark:hover:text-accent-violet transition-colors">
          Quy trình
        </Link>
        <Link href="#about" className="text-sm font-medium text-themeMuted hover:text-accent-purple dark:hover:text-accent-violet transition-colors">
          Giới thiệu
        </Link>
      </nav>

      {/* Right Buttons */}
      <div className="flex items-center gap-4">
        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className="p-2 hover:bg-slate-200/50 dark:hover:bg-slate-800/50 rounded-lg transition-colors"
          title={`Chuyển sang giao diện ${theme === 'light' ? 'tối' : 'sáng'}`}
        >
          {theme === 'light' ? (
            <Moon size={18} className="text-slate-700" />
          ) : (
            <Sun size={18} className="text-accent-cyan" />
          )}
        </button>
        <Link href="/login" className="px-4 py-2 border border-themeBorder rounded-lg text-sm font-medium hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors text-themeText">
          Đăng nhập
        </Link>
        <Link href="/login?mode=register" className="px-4 py-2 bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 rounded-lg text-sm font-semibold hover:bg-slate-800 dark:hover:bg-slate-200 transition-colors">
          Đăng ký
        </Link>
      </div>
    </header>
  )
}
