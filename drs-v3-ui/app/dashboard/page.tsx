'use client'

import React, { useState } from 'react'
import Link from 'next/link'
import { 
  Home, 
  Settings, 
  HelpCircle, 
  Search, 
  MoreHorizontal, 
  Clock, 
  FileText, 
  Plus,
  Moon,
  Sun,
  Globe
} from 'lucide-react'
import { useTheme } from '@/app/theme-provider'
import { useLanguage } from '@/app/i18n'
import { listProjects, listChapters, createProject, getProject } from '@/app/api-client'
import { showToast } from '@/components/toast'

const LANGUAGES = [
  { code: 'auto', name: 'Tự động nhận diện (Auto Detect)' },
  { code: 'multi', name: 'Đa ngôn ngữ (Multilingual)' },
  { code: 'ja', name: 'Japanese (Tiếng Nhật)' },
  { code: 'en', name: 'English (Tiếng Anh)' },
  { code: 'vi', name: 'Vietnamese (Tiếng Việt)' },
  { code: 'zh', name: 'Chinese (Tiếng Trung)' },
  { code: 'ko', name: 'Korean (Tiếng Hàn)' },
  { code: 'lo', name: 'Lao (Tiếng Lào)' },
  { code: 'es', name: 'Spanish (Tiếng Tây Ban Nha)' },
  { code: 'fr', name: 'French (Tiếng Pháp)' },
  { code: 'de', name: 'German (Tiếng Đức)' },
  { code: 'it', name: 'Italian (Tiếng Ý)' },
  { code: 'ru', name: 'Russian (Tiếng Nga)' },
  { code: 'pt', name: 'Portuguese (Tiếng Bồ Đào Nha)' },
  { code: 'th', name: 'Thai (Tiếng Thái)' },
  { code: 'id', name: 'Indonesian (Tiếng Indonesia)' },
  { code: 'ms', name: 'Malay (Tiếng Mã Lai)' },
  { code: 'ar', name: 'Arabic (Tiếng Ả Rập)' },
  { code: 'hi', name: 'Hindi (Tiếng Ấn Độ)' },
  { code: 'tl', name: 'Tagalog (Tiếng Tagalog)' }
]

interface Project {
  slug: string;
  title: string;
  updatedAt: string;
  pages?: number;
  branches?: number;
}

export default function DashboardHome() {
  const { theme, toggleTheme } = useTheme()
  const { language, setLanguage, t } = useLanguage()
  const [searchQuery, setSearchQuery] = useState('')
  const [projectsList, setProjectsList] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)

  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [newProjId, setNewProjId] = useState('')
  const [newProjSource, setNewProjSource] = useState('auto')
  const [newProjTarget, setNewProjTarget] = useState('vi')
  const [showAdvancedCreate, setShowAdvancedCreate] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  const [activeView, setActiveView] = useState<'projects' | 'shared' | 'settings'>('projects')
  const [activeSettingsTab, setActiveSettingsTab] = useState<'account' | 'themes' | 'billing'>('account')
  const [settingsName, setSettingsName] = useState('master')
  const [settingsEmail, setSettingsEmail] = useState('linh304204@gmail.com')

  const handleCreateProject = () => {
    setNewProjId('')
    setNewProjSource('auto')
    setNewProjTarget('vi')
    setShowAdvancedCreate(false)
    setIsCreateOpen(true)
  }

  const slugify = (text: string) => {
    return text
      .toString()
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[đĐ]/g, 'd')
      .replace(/[^a-z0-9\s-]/g, '')
      .replace(/\s+/g, '_')
      .replace(/-+/g, '_')
      .trim();
  };

  const loadProjects = async () => {
    setLoading(true);
    try {
      const slugs = await listProjects();
      const list = await Promise.all(
        slugs.map(async (slug) => {
          try {
            const [chapters, info] = await Promise.all([
              listChapters(slug),
              getProject(slug)
            ]);
            return {
              slug,
              title: info.description || (slug === 'demo_project' ? 'Dự án Dịch thuật' : slug),
              updatedAt: 'Just now',
              pages: chapters.length
            };
          } catch (err) {
            return {
              slug,
              title: slug === 'demo_project' ? 'Dự án Dịch thuật' : slug,
              updatedAt: 'Just now',
              pages: 0
            };
          }
        })
      );
      setProjectsList(list);
    } catch (err) {
      console.error('Failed to load projects:', err);
    } finally {
      setLoading(false);
    }
  };

  const submitCreateProject = async () => {
    if (!newProjId || newProjId.trim() === '') {
      showToast(t('enterProjNameWarning'), 'warning');
      return;
    }
    
    setIsCreating(true);
    try {
      const name = newProjId.trim();
      let slugId = slugify(name);
      if (!slugId) {
        slugId = 'project_' + Date.now();
      } else {
        slugId = `${slugId}_${Math.random().toString(36).substring(2, 6)}`;
      }

      await createProject({
        project_id: slugId,
        description: name,
        source_lang: newProjSource,
        target_lang: newProjTarget,
        content_type: 'novel',
        tone_note: 'Dịch mượt mà'
      });
      setIsCreateOpen(false);
      setNewProjId('');
      await loadProjects();
      showToast(t('createProjSuccess'), 'success');
    } catch (err) {
      showToast(`${t('createProjError')} ${err}`, 'error');
    } finally {
      setIsCreating(false);
    }
  };

  React.useEffect(() => {
    loadProjects();
  }, []);

  const filteredProjects = projectsList.filter(p => 
    p.title.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="w-screen h-screen flex overflow-hidden font-sans bg-themeBg text-themeText transition-colors duration-300">
      {/* Left Sidebar - Theme Aware dark violet-black sidebar */}
      <aside className="w-64 bg-themeSidebar text-slate-400 flex flex-col justify-between p-6 border-r border-slate-950/40 select-none transition-colors duration-300">
        <div className="space-y-8">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent-purple to-accent-violet flex items-center justify-center">
              <span className="text-white font-serif font-bold text-base">o</span>
            </div>
            <span className="font-serif font-bold text-2xl tracking-wide text-white relative">
              oneiros<span className="text-[9px] font-sans font-semibold uppercase tracking-wider text-accent-purple ml-1 absolute -top-1.5 -right-7 px-1.5 py-0.5 rounded-md bg-accent-purple/10">beta</span>
            </span>
          </Link>

          {/* Navigation Links */}
          <nav className="space-y-4">
            <div 
              onClick={() => setActiveView('projects')}
              className={`relative py-2 px-3 flex items-center gap-3 cursor-pointer font-medium transition-colors ${
                activeView === 'projects' ? 'text-white' : 'text-slate-400 hover:text-white'
              }`}
            >
              {activeView === 'projects' && (
                <svg className="absolute inset-0 w-full h-full text-accent-purple/60 dark:text-accent-violet/60 pointer-events-none" viewBox="0 0 170 46" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M6 22C6 11 35 3.5 85 3.5C135 3.5 164 11 164 22C164 33 135 41.5 85 41.5C35 41.5 6 33 6 22Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              )}
              <Home size={18} />
              <span>{t('selectProject')}</span>
            </div>

            <div 
              onClick={() => setActiveView('settings')}
              className={`relative py-2 px-3 flex items-center gap-3 cursor-pointer font-medium transition-colors ${
                activeView === 'settings' ? 'text-white' : 'text-slate-400 hover:text-white'
              }`}
            >
              {activeView === 'settings' && (
                <svg className="absolute inset-0 w-full h-full text-accent-purple/60 dark:text-accent-violet/60 pointer-events-none" viewBox="0 0 170 46" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M6 22C6 11 35 3.5 85 3.5C135 3.5 164 11 164 22C164 33 135 41.5 85 41.5C35 41.5 6 33 6 22Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              )}
              <Settings size={18} />
              <span>{t('sidebarSettings')}</span>
            </div>
          </nav>
        </div>

        {/* Sidebar Footer */}
        <div className="space-y-3">
          <button
            onClick={() => setLanguage(language === 'en' ? 'vi' : 'en')}
            className="flex items-center gap-3 py-2 px-3 w-full hover:text-white transition-colors text-left"
            title="Switch Language"
          >
            <Globe size={18} className="text-accent-purple dark:text-accent-violet" />
            <span>{language === 'en' ? 'Tiếng Việt' : 'English'}</span>
          </button>

          <button
            onClick={toggleTheme}
            className="flex items-center gap-3 py-2 px-3 w-full hover:text-white transition-colors text-left"
          >
            {theme === 'light' ? (
              <>
                <Moon size={18} />
                <span>{t('themeDark')}</span>
              </>
            ) : (
              <>
                <Sun size={18} className="text-accent-cyan" />
                <span>{t('themeLight')}</span>
              </>
            )}
          </button>

          <div className="flex items-center justify-between pt-4 border-t border-slate-900">
            <div className="flex items-center gap-4">
              <HelpCircle size={20} className="hover:text-white cursor-pointer transition-colors" />
              {/* Hand-drawn symbol replica */}
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="hover:text-white cursor-pointer stroke-current transition-colors">
                <path d="M12 4C8 4 4 8 4 12C4 16 8 20 12 20M12 4L16 8M12 4L8 8M12 20L16 16M12 20L8 16" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <span className="text-[10px] text-slate-650 font-mono">v1.0.0</span>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {activeView === 'projects' && (
          <>
            {/* Top Header Bar */}
            <header className="px-8 py-6 flex items-center justify-between border-b border-themeBorder bg-white/40 dark:bg-slate-950/20 backdrop-blur-md">
              {/* Title & Add New Button */}
              <div className="flex items-center gap-4">
                <h1 className="text-2xl font-serif font-bold text-slate-950 dark:text-slate-50">
                  {t('selectProject')} <span className="text-slate-400 font-sans font-normal text-lg">({filteredProjects.length})</span>
                </h1>
                <button 
                  onClick={handleCreateProject}
                  className="px-4 py-1.5 bg-slate-950 hover:bg-slate-850 dark:bg-slate-100 dark:hover:bg-slate-200 text-white dark:text-slate-900 rounded-full text-xs font-semibold flex items-center gap-1.5 shadow-sm transition-all"
                >
                  <Plus size={14} />
                  {t('createProjectBtn')}
                </button>
              </div>

              {/* Action Utilities (Search, Filter, Notification) */}
              <div className="flex items-center gap-4">
                {/* Search Input Box */}
                <div className="relative">
                  <Search size={16} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
                  <input
                    type="text"
                    placeholder={t('searchProjects')}
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-9 pr-4 py-1.5 w-48 bg-slate-200/40 dark:bg-slate-800/30 border border-slate-300/40 dark:border-slate-700/40 rounded-full text-xs focus:w-64 focus:border-accent-purple/50 focus:outline-none transition-all duration-300"
                  />
                </div>

              </div>
            </header>

            {/* Projects Grid */}
            <div className="flex-1 overflow-y-auto p-8 max-w-5xl w-full mx-auto animate-fade-in">
              {loading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-12 pt-4 animate-pulse select-none">
                  {[1, 2, 3, 4].map((n) => (
                    <div key={n} className="relative">
                      <div className="absolute -top-3 left-0 w-24 h-4 bg-themeCard/60 rounded-t-lg border-t border-l border-r border-themeBorder/40" />
                      <div className="relative w-full min-h-[140px] bg-themeCard/60 rounded-b-xl rounded-tr-xl border border-themeBorder/40 p-5 flex flex-col justify-between">
                        <div className="space-y-3">
                          <div className="h-4 bg-slate-200 dark:bg-slate-800 rounded-md w-3/4 animate-pulse"></div>
                          <div className="h-3 bg-slate-200 dark:bg-slate-800 rounded-md w-1/2 animate-pulse"></div>
                        </div>
                        <div className="flex items-center justify-between mt-6 pt-4 border-t border-themeBorder/30">
                          <div className="h-3 bg-slate-200 dark:bg-slate-800 rounded-md w-1/4 animate-pulse"></div>
                          <div className="h-3 bg-slate-200 dark:bg-slate-800 rounded-md w-1/4 animate-pulse"></div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-12 pt-4">
                  {filteredProjects.map((project) => (
                    <div key={project.slug} className="relative group">
                      <div className="absolute -top-3 left-0 w-24 h-4 bg-themeCard rounded-t-lg border-t border-l border-r border-themeBorder transition-colors duration-200" />
                      <div className="relative w-full min-h-[140px] bg-themeCard rounded-b-xl rounded-tr-xl border border-themeBorder p-5 flex flex-col justify-between shadow-sm hover:shadow-md hover:border-accent-purple/65 dark:hover:border-slate-750 transition-all duration-200">
                        <div className="flex items-start justify-between gap-4">
                          <Link href={`/dashboard/${project.slug}`} className="block flex-1 group-hover:opacity-90">
                            <h2 className="text-lg font-serif font-semibold text-slate-900 dark:text-slate-100 line-clamp-1">
                              {project.title}
                            </h2>
                          </Link>
                          <button className="p-1 hover:bg-slate-300/40 dark:hover:bg-slate-800 rounded transition-colors text-slate-400 dark:text-slate-500">
                            <MoreHorizontal size={16} />
                          </button>
                        </div>
                        <div className="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400 pt-4 mt-auto border-t border-slate-200/20">
                          <div className="flex items-center gap-1">
                            <Clock size={12} className="text-slate-400" />
                            <span>{project.updatedAt}</span>
                          </div>
                          <div className="flex items-center gap-3">
                            <div className="flex items-center gap-3 font-medium">
                              {project.pages && (
                                <div className="flex items-center gap-1">
                                  <FileText size={12} className="text-slate-400" />
                                  <span>{project.pages}</span>
                                </div>
                              )}
                            </div>
                            <Link href={`/dashboard/${project.slug}`} className="px-3 py-1 bg-accent-purple/10 hover:bg-accent-purple/20 text-accent-purple dark:text-accent-violet rounded-full font-semibold transition-all">
                              {language === 'en' ? 'Open →' : 'Mở →'}
                            </Link>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}

        {activeView === 'shared' && (
          <>
            {/* Shared Header */}
            <header className="px-8 py-6 flex items-center justify-between border-b border-themeBorder bg-white/40 dark:bg-slate-950/20 backdrop-blur-md">
              <h1 className="text-2xl font-serif font-bold text-slate-950 dark:text-slate-50">
                {language === 'en' ? 'Shared with me' : 'Được chia sẻ với tôi'}
              </h1>
            </header>

            {/* Shared Projects Grid */}
            <div className="flex-1 overflow-y-auto p-8 max-w-5xl w-full mx-auto animate-fade-in">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-12 pt-4">
                {/* Mock Project 1 */}
                <div className="relative group">
                  <div className="absolute -top-3 left-0 w-24 h-4 bg-themeCard rounded-t-lg border-t border-l border-r border-themeBorder transition-colors duration-200" />
                  <div className="relative w-full min-h-[140px] bg-themeCard rounded-b-xl rounded-tr-xl border border-themeBorder p-5 flex flex-col justify-between shadow-sm hover:shadow-md hover:border-accent-purple/65 dark:hover:border-slate-750 transition-all duration-200">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <h2 className="text-lg font-serif font-semibold text-slate-900 dark:text-slate-100 line-clamp-1">
                          Tech Specs: API Gateway Architecture
                        </h2>
                        <p className="text-[11px] text-themeMuted mt-1">
                          {language === 'en' ? 'Owner: Alex (alex@agency.com)' : 'Sở hữu: Alex (alex@agency.com)'} &bull; <span className="text-emerald-500 font-semibold">{language === 'en' ? 'Editor access' : 'Quyền biên tập'}</span>
                        </p>
                      </div>
                      <button className="p-1 hover:bg-slate-300/40 dark:hover:bg-slate-800 rounded transition-colors text-slate-400 dark:text-slate-500">
                        <MoreHorizontal size={16} />
                      </button>
                    </div>
                    <div className="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400 pt-4 mt-auto border-t border-slate-200/20">
                      <div className="flex items-center gap-1">
                        <Clock size={12} className="text-slate-400" />
                        <span>2 {language === 'en' ? 'hours ago' : 'giờ trước'}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="flex items-center gap-1">
                          <FileText size={12} className="text-slate-400" />
                          <span>3</span>
                        </div>
                        <button 
                          onClick={() => showToast(language === 'en' ? 'Opening shared project...' : 'Đang mở dự án được chia sẻ...', 'info')}
                          className="px-3 py-1 bg-accent-purple/10 hover:bg-accent-purple/20 text-accent-purple dark:text-accent-violet rounded-full font-semibold transition-all"
                        >
                          {language === 'en' ? 'Open →' : 'Mở →'}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Mock Project 2 */}
                <div className="relative group">
                  <div className="absolute -top-3 left-0 w-24 h-4 bg-themeCard rounded-t-lg border-t border-l border-r border-themeBorder transition-colors duration-200" />
                  <div className="relative w-full min-h-[140px] bg-themeCard rounded-b-xl rounded-tr-xl border border-themeBorder p-5 flex flex-col justify-between shadow-sm hover:shadow-md hover:border-accent-purple/65 dark:hover:border-slate-750 transition-all duration-200">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <h2 className="text-lg font-serif font-semibold text-slate-900 dark:text-slate-100 line-clamp-1">
                          Annual Report: Q4 Financial Overview
                        </h2>
                        <p className="text-[11px] text-themeMuted mt-1">
                          {language === 'en' ? 'Owner: Sarah (sarah@corp.com)' : 'Sở hữu: Sarah (sarah@corp.com)'} &bull; <span className="text-blue-500 font-semibold">{language === 'en' ? 'Reviewer access' : 'Quyền kiểm tra'}</span>
                        </p>
                      </div>
                      <button className="p-1 hover:bg-slate-300/40 dark:hover:bg-slate-800 rounded transition-colors text-slate-400 dark:text-slate-500">
                        <MoreHorizontal size={16} />
                      </button>
                    </div>
                    <div className="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400 pt-4 mt-auto border-t border-slate-200/20">
                      <div className="flex items-center gap-1">
                        <Clock size={12} className="text-slate-400" />
                        <span>{language === 'en' ? 'Yesterday' : 'Hôm qua'}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="flex items-center gap-1">
                          <FileText size={12} className="text-slate-400" />
                          <span>1</span>
                        </div>
                        <button 
                          onClick={() => showToast(language === 'en' ? 'Opening shared project...' : 'Đang mở dự án được chia sẻ...', 'info')}
                          className="px-3 py-1 bg-accent-purple/10 hover:bg-accent-purple/20 text-accent-purple dark:text-accent-violet rounded-full font-semibold transition-all"
                        >
                          {language === 'en' ? 'Open →' : 'Mở →'}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </>
        )}

        {activeView === 'settings' && (
          <>
            {/* Settings Header */}
            <header className="px-8 py-6 flex items-center justify-between border-b border-themeBorder bg-white/40 dark:bg-slate-950/20 backdrop-blur-md">
              <h1 className="text-2xl font-serif font-bold text-slate-950 dark:text-slate-50">
                {language === 'en' ? 'Settings' : 'Cài đặt'}
              </h1>
              <div className="flex items-center gap-4">
                <button 
                  onClick={() => {
                    localStorage.removeItem('drs_token');
                    window.location.href = '/login';
                  }}
                  className="px-4 py-1.5 bg-rose-500/10 hover:bg-rose-500/20 text-rose-500 dark:text-rose-400 border border-rose-500/20 rounded-full text-xs font-semibold transition-all"
                >
                  {language === 'en' ? 'Logout' : 'Đăng xuất'}
                </button>
              </div>
            </header>

            {/* 3-Column Settings Panel */}
            <div className="flex-1 overflow-hidden flex animate-fade-in">
              {/* Column 1: Navigation Tabs */}
              <div className="w-56 border-r border-themeBorder bg-slate-50/20 dark:bg-slate-950/10 p-4 space-y-1.5 select-none">
                <div 
                  onClick={() => setActiveSettingsTab('account')}
                  className={`px-3 py-2 rounded-xl text-xs font-semibold cursor-pointer transition-all ${
                    activeSettingsTab === 'account' 
                      ? 'bg-accent-purple/10 text-accent-purple dark:text-accent-violet' 
                      : 'text-slate-500 hover:bg-slate-200/40 dark:hover:bg-slate-900/40 hover:text-slate-800 dark:hover:text-slate-200'
                  }`}
                >
                  {language === 'en' ? 'User account' : 'Tài khoản người dùng'}
                </div>
                <div 
                  className="px-3 py-2 rounded-xl text-xs font-semibold text-slate-400 dark:text-slate-650 cursor-not-allowed opacity-60"
                  title="Coming soon"
                >
                  {language === 'en' ? 'Themes (Disabled)' : 'Giao diện (Chưa khả dụng)'}
                </div>
                <div 
                  className="px-3 py-2 rounded-xl text-xs font-semibold text-slate-400 dark:text-slate-650 cursor-not-allowed opacity-60"
                  title="Coming soon"
                >
                  {language === 'en' ? 'Billing & plans' : 'Gói dịch vụ & Hóa đơn'}
                </div>
              </div>

              {/* Column 2: Profile Summary Card */}
              <div className="w-64 border-r border-themeBorder p-6 flex flex-col items-center justify-start text-center">
                <div className="w-24 h-24 rounded-full bg-slate-100 dark:bg-slate-900 border border-themeBorder flex items-center justify-center mb-4">
                  {/* Cute coffee cup sketch avatar */}
                  <svg className="w-14 h-14 text-accent-purple/80 dark:text-accent-violet/85 stroke-current" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M40 25Q43 20 40 15T45 8" strokeWidth="1.5" strokeLinecap="round" />
                    <path d="M50 25Q53 20 50 15T55 8" strokeWidth="1.5" strokeLinecap="round" />
                    <path d="M25 35H75C75 60 70 75 50 75C30 75 25 60 25 35Z" strokeWidth="2" strokeLinejoin="round" />
                    <path d="M75 42C83 42 85 53 73 57" strokeWidth="2" strokeLinecap="round" />
                    <path d="M20 80H80" strokeWidth="2" strokeLinecap="round" />
                  </svg>
                </div>
                <h3 className="font-serif font-bold text-slate-900 dark:text-slate-100 text-lg mb-0.5">
                  {settingsName}
                </h3>
                <p className="text-xs text-themeMuted mb-6">{settingsEmail}</p>

                <button 
                  onClick={() => showToast(language === 'en' ? 'Logs downloaded successfully!' : 'Đã tải nhật ký hệ thống thành công!', 'success')}
                  className="w-full py-1.5 border border-slate-300 dark:border-slate-800 hover:bg-slate-100/50 dark:hover:bg-slate-900/50 rounded-xl text-xs font-semibold transition-all text-slate-650 dark:text-slate-400"
                >
                  {language === 'en' ? 'Download logs' : 'Tải xuống nhật ký'}
                </button>
              </div>

              {/* Column 3: Edit Details Form */}
              <div className="flex-1 overflow-y-auto p-8 space-y-8 max-w-lg">
                {/* About Section */}
                <div className="space-y-4">
                  <h2 className="text-base font-serif font-bold text-slate-950 dark:text-slate-50 border-b border-themeBorder pb-2">
                    {language === 'en' ? 'About you' : 'Về bạn'}
                  </h2>
                  <div className="space-y-2">
                    <label className="text-xs font-bold text-themeMuted uppercase tracking-wider block">
                      {language === 'en' ? 'What should we call you?' : 'Chúng tôi nên gọi bạn là gì?'}
                    </label>
                    <input 
                      type="text"
                      value={settingsName}
                      onChange={(e) => setSettingsName(e.target.value)}
                      className="w-full px-4 py-2 bg-themeCard border border-themeBorder rounded-xl text-sm focus:border-accent-purple/50 focus:outline-none transition-colors"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-xs font-bold text-themeMuted uppercase tracking-wider block">
                      {language === 'en' ? 'Email Address' : 'Địa chỉ Email'}
                    </label>
                    <input 
                      type="email"
                      value={settingsEmail}
                      onChange={(e) => setSettingsEmail(e.target.value)}
                      className="w-full px-4 py-2 bg-themeCard border border-themeBorder rounded-xl text-sm focus:border-accent-purple/50 focus:outline-none transition-colors"
                    />
                  </div>
                  <button 
                    onClick={() => showToast(language === 'en' ? 'Profile updated successfully!' : 'Đã cập nhật thông tin tài khoản thành công!', 'success')}
                    className="px-5 py-2 bg-accent-purple hover:bg-accent-purple/90 text-white rounded-xl text-xs font-semibold shadow-sm transition-all"
                  >
                    {language === 'en' ? 'Save changes' : 'Lưu Thay đổi'}
                  </button>
                </div>

                {/* Account Details Section */}
                <div className="space-y-4 pt-4">
                  <h2 className="text-base font-serif font-bold text-slate-950 dark:text-slate-50 border-b border-themeBorder pb-2">
                    {language === 'en' ? 'Account details' : 'Chi tiết tài khoản'}
                  </h2>
                  <div className="flex items-center justify-between p-3 bg-themeCard border border-themeBorder rounded-xl">
                    <div>
                      <h4 className="text-xs font-bold text-themeMuted uppercase tracking-wider">
                        {language === 'en' ? 'Password' : 'Mật khẩu'}
                      </h4>
                      <p className="text-sm font-semibold mt-1">••••••••</p>
                    </div>
                    <button 
                      onClick={() => showToast(language === 'en' ? 'Password change feature is disabled for beta' : 'Tính năng thay đổi mật khẩu bị khóa ở bản beta', 'warning')}
                      className="px-3.5 py-1.5 border border-slate-350 dark:border-slate-800 hover:bg-slate-100/50 dark:hover:bg-slate-900/50 rounded-xl text-xs font-semibold transition-all text-slate-655 dark:text-slate-400"
                    >
                      {language === 'en' ? 'Change password' : 'Đổi mật khẩu'}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </>
        )}
      </main>

      {/* Create Project Modal */}
      {isCreateOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-themeCard border border-themeBorder rounded-2xl w-full max-w-md p-6 shadow-2xl animate-fade-in text-themeText">
            <h3 className="text-xl font-serif font-bold mb-4">{t('createNewProjectTitle')}</h3>
            
            <div className="space-y-4">
              <div>
                <label className="text-xs font-bold text-themeMuted uppercase tracking-wider block mb-2">
                  {t('projectNameLabel')}
                </label>
                <input
                  type="text"
                  placeholder={language === 'en' ? 'Enter project name' : 'Nhập tên dự án'}
                  value={newProjId}
                  onChange={(e) => setNewProjId(e.target.value)}
                  className="w-full px-4 py-2.5 bg-themeBg border border-themeBorder rounded-xl text-sm focus:border-accent-purple/50 focus:outline-none transition-colors"
                />
              </div>

              <div>
                <button
                  type="button"
                  onClick={() => setShowAdvancedCreate(!showAdvancedCreate)}
                  className="flex items-center gap-1.5 text-xs font-semibold text-accent-purple dark:text-accent-violet hover:underline focus:outline-none"
                >
                  <svg
                    className={`w-3 h-3 transition-transform duration-200 ${showAdvancedCreate ? 'rotate-90' : ''}`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M9 5l7 7-7 7" />
                  </svg>
                  <span>{language === 'en' ? 'Advanced settings' : 'Cài đặt nâng cao'}</span>
                </button>
              </div>

              {showAdvancedCreate && (
                <div className="grid grid-cols-2 gap-4 animate-fade-in">
                  <div>
                    <label className="text-xs font-bold text-themeMuted uppercase tracking-wider block mb-2">
                      {t('sourceLang')}
                    </label>
                    <select
                      value={newProjSource}
                      onChange={(e) => setNewProjSource(e.target.value)}
                      className="w-full px-3 py-2.5 bg-themeBg border border-themeBorder rounded-xl text-xs focus:border-accent-purple/50 focus:outline-none transition-colors text-themeText"
                    >
                      {LANGUAGES.map((lang) => (
                        <option key={lang.code} value={lang.code}>
                          {lang.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs font-bold text-themeMuted uppercase tracking-wider block mb-2">
                      {t('targetLangLabel')}
                    </label>
                    <select
                      value={newProjTarget}
                      onChange={(e) => setNewProjTarget(e.target.value)}
                      className="w-full px-3 py-2.5 bg-themeBg border border-themeBorder rounded-xl text-xs focus:border-accent-purple/50 focus:outline-none transition-colors text-themeText"
                    >
                      {LANGUAGES.filter(l => l.code !== 'auto' && l.code !== 'multi').map((lang) => (
                        <option key={lang.code} value={lang.code}>
                          {lang.name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-3 mt-6">
              <button
                onClick={() => setIsCreateOpen(false)}
                className="px-4 py-2 hover:bg-themeBg rounded-xl text-sm font-medium transition-colors"
              >
                {t('cancel')}
              </button>
              <button
                onClick={submitCreateProject}
                disabled={isCreating}
                className="px-5 py-2 bg-accent-purple hover:bg-accent-purple/90 disabled:opacity-50 text-white rounded-xl text-sm font-semibold transition-colors"
              >
                {isCreating ? t('creating') : t('create')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
