import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['var(--font-sans)', 'sans-serif'],
        serif: ['var(--font-serif)', 'serif'],
      },
      colors: {
        themeBg: 'var(--bg-primary)',
        themeCard: 'var(--bg-secondary)',
        themeSidebar: 'var(--bg-sidebar)',
        themeSidebarWorkspace: 'var(--bg-sidebar-workspace)',
        themeText: 'var(--text-primary)',
        themeMuted: 'var(--text-secondary)',
        themeBorder: 'var(--border-primary)',
        themePurple: 'var(--color-accent-purple)',
        themeCyan: 'var(--color-accent-cyan)',

        background: {
          light: '#f8fafc',
          dark: '#0f172a',
        },
        foreground: {
          light: '#1e293b',
          dark: '#f1f5f9',
        },
        'slate-dark': {
          light: '#e2e8f0',
          dark: '#1e293b',
        },
        'slate-darker': {
          light: '#f1f5f9',
          dark: '#0f172a',
        },
        'accent-violet': '#a78bfa',
        'accent-cyan': '#06b6d4',
        'accent-purple': '#7c3aed',
      },
      boxShadow: {
        'glow-violet': '0 0 12px rgba(167, 139, 250, 0.15)',
        'glow-cyan': '0 0 12px rgba(6, 182, 212, 0.15)',
        'glow-purple': '0 0 16px rgba(124, 58, 237, 0.12)',
      },
      backdropBlur: {
        'md': '12px',
        'lg': '16px',
      },
      borderRadius: {
        'lg': '12px',
        'xl': '16px',
      },
    },
  },
  plugins: [],
}
export default config
