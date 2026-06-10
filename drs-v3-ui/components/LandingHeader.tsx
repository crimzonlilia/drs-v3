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
          <span className="text-white font-serif font-bold text-base">d</span>
        </div>
        <span className="font-serif font-bold text-2xl tracking-wide text-themeText">
          drs<span className="text-accent-purple">.</span>v3
        </span>
      </Link>

      {/* Center Links */}
      <nav className="hidden md:flex items-center gap-8">
        <Link href="#features" className="text-sm font-medium text-themeMuted hover:text-accent-purple dark:hover:text-accent-violet transition-colors">
          Features
        </Link>
        <Link href="#pipeline" className="text-sm font-medium text-themeMuted hover:text-accent-purple dark:hover:text-accent-violet transition-colors">
          Workflow
        </Link>
        <Link href="#about" className="text-sm font-medium text-themeMuted hover:text-accent-purple dark:hover:text-accent-violet transition-colors">
          About
        </Link>
      </nav>

      {/* Right Buttons */}
      <div className="flex items-center gap-4">
        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className="p-2 hover:bg-slate-200/50 dark:hover:bg-slate-800/50 rounded-lg transition-colors"
          title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
        >
          {theme === 'light' ? (
            <Moon size={18} className="text-slate-700" />
          ) : (
            <Sun size={18} className="text-accent-cyan" />
          )}
        </button>

        <Link href="/login" className="px-4 py-2 border border-themeBorder rounded-lg text-sm font-medium hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors text-themeText">
          Log in
        </Link>
        <Link href="/login" className="px-4 py-2 bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 rounded-lg text-sm font-semibold hover:bg-slate-800 dark:hover:bg-slate-200 transition-colors">
          Sign up
        </Link>
      </div>
    </header>
  )
}
