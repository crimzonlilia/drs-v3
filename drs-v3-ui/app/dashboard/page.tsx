'use client'

import React, { useState } from 'react'
import Link from 'next/link'
import { 
  Home, 
  Users, 
  Settings, 
  HelpCircle, 
  SlidersHorizontal, 
  Search, 
  Bell, 
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
  const [isCreating, setIsCreating] = useState(false)
  const [activeModal, setActiveModal] = useState<'shared' | 'settings' | null>(null)

  const handleCreateProject = () => {
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
              <span className="text-white font-serif font-bold text-base">d</span>
            </div>
            <span className="font-serif font-bold text-2xl tracking-wide text-white">
              drs<span className="text-accent-purple">.</span>v3
            </span>
          </Link>

          {/* Navigation Links */}
          <nav className="space-y-4">
            {/* Active Link: My Work with Hand-drawn Loop border */}
            <div className="relative py-2 px-3 flex items-center gap-3 text-white cursor-pointer font-medium">
              {/* Custom hand-drawn outline SVG */}
              <svg className="absolute inset-0 w-full h-full text-accent-purple/60 dark:text-accent-violet/60 pointer-events-none" viewBox="0 0 170 46" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M6 22C6 11 35 3.5 85 3.5C135 3.5 164 11 164 22C164 33 135 41.5 85 41.5C35 41.5 6 33 6 22Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <Home size={18} className="text-white" />
              <span>{t('selectProject')}</span>
            </div>

            <div 
              onClick={() => setActiveModal('shared')}
              className="py-2 px-3 flex items-center gap-3 hover:text-white cursor-pointer transition-colors"
            >
              <Users size={18} />
              <span>{language === 'en' ? 'Shared with me' : 'Được chia sẻ'}</span>
            </div>

            <div 
              onClick={() => setActiveModal('settings')}
              className="py-2 px-3 flex items-center gap-3 hover:text-white cursor-pointer transition-colors"
            >
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
            <span className="text-[10px] text-slate-650 font-mono">v3.0.4</span>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-hidden">
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

            <button className="p-2 hover:bg-slate-200/50 dark:hover:bg-slate-800/50 rounded-lg transition-colors text-slate-500 dark:text-slate-400" title="Filter options">
              <SlidersHorizontal size={16} />
            </button>

            <button className="p-2 hover:bg-slate-200/50 dark:hover:bg-slate-800/50 rounded-lg transition-colors text-slate-500 dark:text-slate-400" title="Notifications">
              <Bell size={16} />
            </button>
          </div>
        </header>

        {/* Projects Folders Grid Container - Scrollable */}
        <div className="flex-1 overflow-y-auto p-8 max-w-5xl w-full mx-auto">
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
                  {/* Folder Tab Shape */}
                  <div className="absolute -top-3 left-0 w-24 h-4 bg-themeCard rounded-t-lg border-t border-l border-r border-themeBorder transition-colors duration-200" />

                  {/* Folder Body */}
                  <div className="relative w-full min-h-[140px] bg-themeCard rounded-b-xl rounded-tr-xl border border-themeBorder p-5 flex flex-col justify-between shadow-sm hover:shadow-md hover:border-accent-purple/65 dark:hover:border-slate-750 transition-all duration-200">
                    {/* Top line of folder */}
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

                    {/* Bottom line with metadata */}
                    <div className="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400 pt-4 mt-auto border-t border-slate-200/20">
                      {/* Timestamp */}
                      <div className="flex items-center gap-1">
                        <Clock size={12} className="text-slate-400" />
                        <span>{project.updatedAt}</span>
                      </div>

                      {/* File count & Translate CTA */}
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
      </main>

      {/* Shared with Me Modal */}
      {activeModal === 'shared' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-themeCard border border-themeBorder rounded-2xl w-full max-w-lg p-6 shadow-2xl animate-fade-in text-themeText">
            <h3 className="text-xl font-serif font-bold mb-2">Shared Projects</h3>
            <p className="text-xs text-themeMuted mb-4">Projects shared with you by other workspace translators.</p>
            
            <div className="space-y-3 max-h-60 overflow-y-auto pr-1">
              <div className="p-4 bg-themeBg border border-themeBorder rounded-xl flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-bold">Tech Specs: API Gateway Architecture</h4>
                  <p className="text-xs text-themeMuted mt-0.5">Owner: Alex (alex@agency.com) &bull; Editor access</p>
                </div>
                <span className="text-[10px] bg-emerald-500/10 text-emerald-500 px-2 py-0.5 rounded font-semibold uppercase">Active</span>
              </div>
              <div className="p-4 bg-themeBg border border-themeBorder rounded-xl flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-bold">Annual Report: Q4 Financial Overview</h4>
                  <p className="text-xs text-themeMuted mt-0.5">Owner: Sarah (sarah@corp.com) &bull; Reviewer access</p>
                </div>
                <span className="text-[10px] bg-emerald-500/10 text-emerald-500 px-2 py-0.5 rounded font-semibold uppercase">Active</span>
              </div>
            </div>

            <div className="flex justify-end mt-6">
              <button
                onClick={() => setActiveModal(null)}
                className="px-5 py-2 bg-accent-purple hover:bg-accent-purple/90 text-white rounded-xl text-sm font-semibold transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Settings Modal */}
      {activeModal === 'settings' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-themeCard border border-themeBorder rounded-2xl w-full max-w-lg p-6 shadow-2xl animate-fade-in text-themeText">
            <h3 className="text-xl font-serif font-bold mb-2">Workspace Settings</h3>
            <p className="text-xs text-themeMuted mb-4">Configure your active localization pipeline settings.</p>
            
            <div className="space-y-4">
              {/* API Configuration */}
              <div>
                <label className="text-xs font-bold text-themeMuted uppercase tracking-wider block mb-1.5">
                  AI Translation Engine
                </label>
                <select className="w-full px-3 py-2 bg-themeBg border border-themeBorder rounded-xl text-sm focus:outline-none focus:border-accent-purple/50">
                  <option>OpenAI GPT-4o (Recommended)</option>
                  <option>Claude 3.5 Sonnet</option>
                  <option>DeepL Translator API</option>
                </select>
              </div>

              {/* Translation Tone */}
              <div>
                <label className="text-xs font-bold text-themeMuted uppercase tracking-wider block mb-1.5">
                  Default Translation Tone
                </label>
                <input
                  type="text"
                  placeholder="e.g. Chữ nghĩa mượt mà, văn phong cổ điển"
                  defaultValue="Chữ nghĩa mượt mà, giữ nguyên các kính ngữ tiếng Nhật"
                  className="w-full px-3 py-2 bg-themeBg border border-themeBorder rounded-xl text-sm focus:outline-none focus:border-accent-purple/50"
                />
              </div>

              {/* Auto-save */}
              <div className="flex items-center justify-between p-3 bg-themeBg border border-themeBorder rounded-xl">
                <div>
                  <h4 className="text-sm font-semibold">Enable Realtime Auto-Save</h4>
                  <p className="text-xs text-themeMuted mt-0.5">Saves translation changes instantly to the backend.</p>
                </div>
                <input type="checkbox" defaultChecked className="w-4 h-4 accent-accent-purple" />
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setActiveModal(null)}
                className="px-4 py-2 hover:bg-themeBg rounded-xl text-sm font-medium transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  showToast("Lưu cấu hình thành công!", "success");
                  setActiveModal(null);
                }}
                className="px-5 py-2 bg-accent-purple hover:bg-accent-purple/90 text-white rounded-xl text-sm font-semibold transition-colors"
              >
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}

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
                  placeholder={language === 'en' ? 'e.g. Richard I Crusade Campaign' : 'Ví dụ: Chiến dịch Thập tự chinh Richard I'}
                  value={newProjId}
                  onChange={(e) => setNewProjId(e.target.value)}
                  className="w-full px-4 py-2.5 bg-themeBg border border-themeBorder rounded-xl text-sm focus:border-accent-purple/50 focus:outline-none transition-colors"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
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
