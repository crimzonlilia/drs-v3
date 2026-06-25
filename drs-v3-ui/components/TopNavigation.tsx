'use client'

import React, { useState } from 'react'
import { ArrowLeft, ChevronDown, Moon, Sun, Globe } from 'lucide-react'
import { useTheme } from '@/app/theme-provider'
import { useLanguage } from '@/app/i18n'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

interface TopNavigationProps {
  projectId?: string
  currentProject: string
  onProjectChange: (project: string) => void
}

const projects = [
  'Richard I Historiography',
  'Ancient Rome Chronicles',
  'Medieval European Studies',
  'Victorian Era Documents'
]

export default function TopNavigation({
  projectId,
  currentProject,
  onProjectChange
}: TopNavigationProps) {
  const [isProjectOpen, setIsProjectOpen] = useState(false)
  const { theme, toggleTheme } = useTheme()
  const { language, setLanguage, t } = useLanguage()
  const pathname = usePathname()

  return (
    <header className="h-14 border-b border-themeBorder bg-themeBg px-5 flex items-center justify-between">
      <div className="flex items-center gap-3 min-w-0">
        {projectId && (
          <Link
            href={`/dashboard/${projectId}`}
            className="p-1.5 rounded-md text-themeMuted hover:text-themeText hover:bg-themeCard"
            title={t('backToChapters')}
          >
            <ArrowLeft size={17} />
          </Link>
        )}
        <button
          onClick={() => window.location.href = '/dashboard'}
          className="text-sm font-semibold text-themeText hover:text-themeText"
        >
          Lilia
        </button>
      </div>

      <div className="relative z-50">
        <button
          onClick={() => setIsProjectOpen(!isProjectOpen)}
          className="max-w-[42vw] rounded-md px-3 py-1.5 flex items-center gap-2 text-sm text-themeText hover:bg-themeCard"
        >
          <span className="truncate">{currentProject}</span>
          <ChevronDown size={15} className={`shrink-0 text-themeMuted transition-transform ${isProjectOpen ? 'rotate-180' : ''}`} />
        </button>

        {isProjectOpen && (
          <div className="absolute top-full mt-2 left-1/2 -translate-x-1/2 w-72 rounded-lg border border-themeBorder bg-themeBg shadow-lg overflow-hidden">
            {projects.map(project => (
              <button
                key={project}
                onClick={() => {
                  onProjectChange(project)
                  setIsProjectOpen(false)
                }}
                className={`w-full px-4 py-3 text-left text-sm hover:bg-themeCard ${
                  project === currentProject ? 'text-themeText font-medium' : 'text-themeMuted'
                }`}
              >
                {project}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="flex items-center gap-2">
        {projectId && (
          <Link
            href={`/dashboard/${projectId}/memory?from=${encodeURIComponent(pathname)}`}
            className="px-2.5 py-1.5 rounded-md border border-themeBorder text-xs font-medium text-themeText hover:bg-themeCard transition-colors"
            title={t('projectMemoryTooltip')}
          >
            {t('projectMemory')}
          </Link>
        )}
        <button
          onClick={() => setLanguage(language === 'en' ? 'vi' : 'en')}
          className="p-1.5 rounded-md text-themeMuted hover:text-themeText hover:bg-themeCard flex items-center gap-1"
          title={t('switchLanguage')}
        >
          <Globe size={17} />
          <span className="text-[10px] font-bold uppercase">{language}</span>
        </button>
        <button
          onClick={toggleTheme}
          className="p-1.5 rounded-md text-themeMuted hover:text-themeText hover:bg-themeCard"
          title={theme === 'light' ? t('themeDark') : t('themeLight')}
        >
          {theme === 'light' ? <Moon size={17} /> : <Sun size={17} />}
        </button>
      </div>
    </header>
  )
}
