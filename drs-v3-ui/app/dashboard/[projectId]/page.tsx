'use client'

import React, { useState, use } from 'react'
import Link from 'next/link'
import { 
  Home, 
  Settings, 
  HelpCircle, 
  Search, 
  MoreHorizontal, 
  Clock, 
  Folder,
  ArrowLeft,
  Plus,
  Moon,
  Sun,
  Globe,
  Edit3
} from 'lucide-react'
import { useTheme } from '@/app/theme-provider'
import { useLanguage } from '@/app/i18n'
import { listChapters, getProject, getChapter, saveChapter, deleteChapter, renameDocument, patchProject, ProjectInfo } from '@/app/api-client'
import { showToast } from '@/components/toast'
import { useEffect } from 'react'

interface Chapter {
  slug: string
  title: string
  previewText: string
  updatedAt: string
}

interface PageProps {
  params: Promise<{ projectId: string }>
}

export default function ProjectDetails({ params }: PageProps) {
  const { projectId } = use(params)
  const { theme, toggleTheme } = useTheme()
  const { language, setLanguage, t } = useLanguage()
  const [searchQuery, setSearchQuery] = useState('')
  const [chapters, setChapters] = useState<Chapter[]>([])
  const [projectInfo, setProjectInfo] = useState<ProjectInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [newChapterTitle, setNewChapterTitle] = useState('')
  const [newChapterDescription, setNewChapterDescription] = useState('')
  const [isNewDropdownOpen, setIsNewDropdownOpen] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  const [activeModal, setActiveModal] = useState<'shared' | 'settings' | null>(null)
  const [activeDropdownChapter, setActiveDropdownChapter] = useState<string | null>(null)
  const [editDisplayName, setEditDisplayName] = useState('')

  const loadData = async () => {
    try {
      const info = await getProject(projectId);
      setProjectInfo(info);
      setEditDisplayName(info.description || '');
    } catch (err) {
      console.error('Error loading project details info:', err);
    }

    try {
      const slugs = await listChapters(projectId);
      const list = await Promise.all(
        slugs.map(async (slug) => {
          try {
            const data = await getChapter(projectId, slug);
            
            // Extract the first heading of the draft as the title (fallback to slug if not present)
            const titleMatch = data.draft ? data.draft.match(/^#\s+(.+)$/m) : null;
            const title = (titleMatch ? titleMatch[1].trim() : slug).replace(/\.md$/, '');
            
            // Extract a clean preview by removing the heading line
            let preview = language === 'en' ? "Empty translation..." : "Bản dịch trống...";
            if (data.draft) {
              const withoutTitle = data.draft.replace(/^#\s+.+$/m, '').trim();
              preview = withoutTitle ? withoutTitle.slice(0, 120) : (language === 'en' ? "Empty translation..." : "Bản dịch trống...");
            }

            return {
              slug,
              title,
              previewText: preview,
              updatedAt: language === 'en' ? 'Just now' : 'Vừa xong'
            };
          } catch (e) {
            return {
              slug,
              title: slug.replace(/\.md$/, ''),
              previewText: language === 'en' ? "Start editing translation..." : "Bắt đầu chỉnh sửa bản dịch...",
              updatedAt: language === 'en' ? 'Just now' : 'Vừa xong'
            };
          }
        })
      );
      setChapters(list);
      setLoading(false);
    } catch (err) {
      console.error('Error loading project chapters:', err);
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [projectId]);

  const generateNextChapterId = (existingChapters: Chapter[]) => {
    const chNumbers = existingChapters
      .map(c => {
        const match = c.slug.match(/^ch(\d+)$/i);
        return match ? parseInt(match[1], 10) : null;
      })
      .filter((num): num is number => num !== null);
    
    if (chNumbers.length === 0) {
      return 'ch001';
    }
    
    const maxNum = Math.max(...chNumbers);
    const nextNum = maxNum + 1;
    return `ch${String(nextNum).padStart(3, '0')}`;
  };

  const handleCreateChapter = () => {
    setIsNewDropdownOpen(!isNewDropdownOpen);
  };

  const handleSubmitChapter = async () => {
    if (!newChapterTitle.trim()) {
      showToast(t('enterDocTitleWarning'), 'warning');
      return;
    }

    setIsCreating(true);
    try {
      const nextId = generateNextChapterId(chapters);
      const content = `# ${newChapterTitle.trim()}\n\n${language === 'en' ? 'Start editing translation...' : 'Bắt đầu bản dịch mới tại đây...'}`;
      await saveChapter(projectId, nextId, { draft: content });
      
      setIsModalOpen(false);
      setNewChapterTitle('');
      setNewChapterDescription('');
      
      await loadData();
      showToast(t('createDocSuccess'), 'success');
    } catch (err) {
      showToast(`${t('createDocError')} ${err}`, 'error');
    } finally {
      setIsCreating(false);
    }
  };

  const handleSaveSettings = async () => {
    try {
      await patchProject(projectId, { display_name: editDisplayName, description: editDisplayName });
      showToast("Cập nhật dự án thành công!", "success");
      await loadData();
      setActiveModal(null);
    } catch (err: any) {
      showToast(`Không thể cập nhật dự án: ${err.message}`, 'error');
    }
  };

  const handleDeleteChapter = async (slug: string) => {
    const confirmMsg = t('deleteDocConfirm').replace('this document', `"${slug}"`).replace('tài liệu này', `"${slug}"`);
    if (!confirm(confirmMsg)) return;
    try {
      await deleteChapter(projectId, slug);
      showToast('Xóa tài liệu thành công!', 'success');
      loadData();
    } catch (err: any) {
      showToast(`Lỗi khi xóa tài liệu: ${err.message}`, 'error');
    }
  };

  const handleRenameChapter = async (slug: string) => {
    const cleanSlug = slug.replace(/\.md$/, '');
    const newName = prompt(t('newDocPrompt') || 'Nhập tên tài liệu mới:', cleanSlug);
    if (!newName || !newName.trim()) return;
    const cleanNewName = newName.trim().endsWith('.md') ? newName.trim() : `${newName.trim()}.md`;
    if (cleanNewName === slug) return;

    // Optimistic update
    const oldChapters = [...chapters];
    setChapters(chapters.map(c => {
      if (c.slug === slug) {
        return {
          ...c,
          slug: cleanNewName,
          title: newName.trim()
        };
      }
      return c;
    }));

    try {
      await renameDocument(projectId, slug, cleanNewName);
      showToast('Đổi tên tài liệu thành công!', 'success');
      await loadData();
    } catch (err: any) {
      showToast(`Lỗi khi đổi tên tài liệu: ${err.message}`, 'error');
      setChapters(oldChapters);
    }
  };

  const projectName = projectInfo ? (projectInfo.description || (projectInfo.project_id === 'demo_project' ? 'Dự án Dịch thuật' : projectInfo.project_id)) : projectId

  const filteredChapters = chapters.filter(c => 
    c.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    c.previewText.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="w-screen h-screen flex overflow-hidden font-sans bg-themeBg text-themeText transition-colors duration-300">
      {/* Left Sidebar - Same as dashboard main page */}
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
            <Link href="/dashboard" className="relative py-2 px-3 flex items-center gap-3 text-white cursor-pointer font-medium block">
              <svg className="absolute inset-0 w-full h-full text-accent-purple/60 dark:text-accent-violet/60 pointer-events-none" viewBox="0 0 170 46" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M6 22C6 11 35 3.5 85 3.5C135 3.5 164 11 164 22C164 33 135 41.5 85 41.5C35 41.5 6 33 6 22Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <Home size={18} className="text-white" />
              <span>{t('selectProject')}</span>
            </Link>

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
        {/* Header Bar matching second screenshot */}
        <header className="px-8 py-6 flex items-center justify-between border-b border-themeBorder bg-white/40 dark:bg-slate-950/20 backdrop-blur-md">
          {/* Navigation Title & Folder Name */}
          <div className="flex items-center gap-3">
            {/* Back Button Arrow */}
            <Link 
              href="/dashboard" 
              className="p-1 hover:bg-slate-200/50 dark:hover:bg-slate-800/50 rounded transition-colors text-slate-600 dark:text-slate-300"
              title="Back to my work"
            >
              <ArrowLeft size={20} />
            </Link>

            <button className="p-1 hover:bg-slate-200/50 dark:hover:bg-slate-800/50 rounded transition-colors text-slate-400 dark:text-slate-500">
              <MoreHorizontal size={18} />
            </button>

            {/* Folder Icon & Project Title */}
            <div className="flex items-center gap-2">
              <Folder size={18} className="text-slate-400 mt-0.5" />
              <h1 className="text-2xl font-serif font-bold text-slate-950 dark:text-slate-50 leading-none">
                {projectName}
              </h1>
              <button 
                onClick={() => setActiveModal('settings')}
                className="p-1 hover:bg-slate-200/50 dark:hover:bg-slate-800/50 rounded transition-colors text-slate-400 hover:text-slate-600"
                title="Đổi tên dự án"
              >
                <Edit3 size={15} />
              </button>
            </div>

            {/* New Button & Dropdown */}
            <div className="relative">
              <button 
                onClick={handleCreateChapter}
                className="ml-2 px-4 py-1.5 bg-orange-500 hover:bg-orange-600 dark:bg-orange-600 dark:hover:bg-orange-700 text-white rounded-full text-xs font-semibold flex items-center gap-1.5 shadow-sm transition-all"
              >
                <Plus size={14} />
                {language === 'en' ? 'New' : 'Tạo mới'}
              </button>

              {isNewDropdownOpen && (
                <>
                  <div 
                    className="fixed inset-0 z-10" 
                    onClick={() => setIsNewDropdownOpen(false)}
                  />
                  <div className="absolute right-0 mt-2 w-56 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-lg z-20 py-2 overflow-hidden select-none animate-in fade-in slide-in-from-top-1 text-slate-700 dark:text-slate-200 text-left">
                    <div className="px-3 py-1 text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
                      {language === 'en' ? 'Documents' : 'Tài liệu'}
                    </div>
                    <button
                      onClick={() => {
                        setIsNewDropdownOpen(false);
                        setNewChapterTitle('Untitled');
                        setNewChapterDescription('');
                        setIsModalOpen(true);
                      }}
                      className="w-full text-left px-4 py-2 text-xs hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors flex items-center gap-2"
                    >
                      <span className="w-1.5 h-1.5 rounded-full bg-orange-500"></span>
                      {language === 'en' ? 'Blank document' : 'Tài liệu trống'}
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Action Utilities (Search, Filter, Notification) */}
          <div className="flex items-center gap-4">
            <div className="relative">
              <Search size={16} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder={t('searchDocs')}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 pr-4 py-1.5 w-48 bg-slate-200/40 dark:bg-slate-800/30 border border-slate-300/40 dark:border-slate-700/40 rounded-full text-xs focus:w-64 focus:border-accent-purple/50 focus:outline-none transition-all duration-300"
              />
            </div>

          </div>
        </header>

        {/* Chapters Cards Grid Container - Scrollable */}
        <div className="flex-1 overflow-y-auto p-8 max-w-5xl w-full mx-auto">
          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pt-4 animate-pulse select-none">
              {[1, 2, 3, 4, 5, 6].map((n) => (
                <div key={n} className="bg-themeCard/60 border border-themeBorder/40 rounded-2xl p-5 flex flex-col justify-between min-h-[160px]">
                  <div className="space-y-3">
                    <div className="h-4 bg-slate-200 dark:bg-slate-800 rounded-md w-3/4 animate-pulse"></div>
                    <div className="h-3 bg-slate-200 dark:bg-slate-800 rounded-md w-full animate-pulse"></div>
                    <div className="h-3 bg-slate-200 dark:bg-slate-800 rounded-md w-5/6 animate-pulse"></div>
                  </div>
                  <div className="flex items-center justify-between mt-6 pt-4 border-t border-themeBorder/30">
                    <div className="h-3 bg-slate-200 dark:bg-slate-800 rounded-md w-1/4 animate-pulse"></div>
                    <div className="h-6 bg-slate-200 dark:bg-slate-800 rounded-full w-1/4 animate-pulse"></div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pt-4">
              {filteredChapters.map((chapter) => (
                <div 
                  key={chapter.slug} 
                  className="relative bg-themeCard border border-themeBorder rounded-2xl p-5 flex flex-col justify-between shadow-sm hover:shadow-md hover:border-slate-350 dark:hover:border-slate-750 transition-all duration-200 min-h-[160px]"
                >
                  {/* Chapter Title & Action Button */}
                  <div className="flex items-start justify-between gap-4 mb-3">
                    <Link href={`/dashboard/${projectId}/${chapter.slug}`} className="block flex-1 group">
                      <h2 className="text-base font-serif font-semibold leading-relaxed text-slate-800 dark:text-slate-200 group-hover:text-accent-purple dark:group-hover:text-accent-violet transition-colors line-clamp-1 mb-1.5">
                        {chapter.title}
                      </h2>
                      <p className="text-xs text-themeMuted line-clamp-2 leading-relaxed">
                        {chapter.previewText}
                      </p>
                    </Link>
                    <div className="relative shrink-0">
                      <button 
                        onClick={(e) => {
                          e.stopPropagation();
                          setActiveDropdownChapter(activeDropdownChapter === chapter.slug ? null : chapter.slug);
                        }}
                        className="p-1 hover:bg-slate-100 dark:hover:bg-slate-800 rounded transition-colors text-slate-400 dark:text-slate-500"
                      >
                        <MoreHorizontal size={16} />
                      </button>
                      {activeDropdownChapter === chapter.slug && (
                        <>
                          <div 
                            className="fixed inset-0 z-10" 
                            onClick={() => setActiveDropdownChapter(null)}
                          />
                          <div className="absolute right-0 mt-1 w-32 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-lg z-20 py-1 overflow-hidden select-none animate-in fade-in slide-in-from-top-1">
                            <button
                              onClick={() => {
                                handleRenameChapter(chapter.slug);
                                setActiveDropdownChapter(null);
                              }}
                              className="w-full text-left px-4 py-2 text-xs font-semibold text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                            >
                              Đổi tên
                            </button>
                            <button
                              onClick={() => {
                                handleDeleteChapter(chapter.slug);
                                setActiveDropdownChapter(null);
                              }}
                              className="w-full text-left px-4 py-2 text-xs font-semibold text-red-600 hover:bg-red-50 dark:hover:bg-red-950/20 transition-colors"
                            >
                              Xóa
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Updated Timestamp at Bottom */}
                  <div className="flex items-center justify-between text-[11px] text-slate-400 mt-auto pt-4 border-t border-slate-100/50 dark:border-slate-800/20">
                    <div className="flex items-center gap-1">
                      <Clock size={12} className="text-slate-300 dark:text-slate-600" />
                      <span>{chapter.updatedAt}</span>
                    </div>
                    <Link href={`/dashboard/${projectId}/${chapter.slug}`} className="px-3 py-1 bg-accent-purple/10 hover:bg-accent-purple/20 text-accent-purple dark:text-accent-violet rounded-full font-semibold transition-all">
                      {t('translateCTA')} →
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>

      {/* Create Chapter Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 shadow-2xl animate-fade-in text-slate-100">
            <h3 className="text-xl font-serif font-bold mb-4 text-slate-50">
              {language === 'en' ? 'Create New Document' : 'Tạo tài liệu mới'}
            </h3>
            
            <div className="space-y-4">
              {/* Document Name Input */}
              <div>
                <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-2">
                  {language === 'en' ? 'Document name*' : 'Tên tài liệu*'}
                </label>
                <input
                  type="text"
                  placeholder={language === 'en' ? 'Enter document name' : 'Nhập tên tài liệu'}
                  value={newChapterTitle}
                  onChange={(e) => setNewChapterTitle(e.target.value)}
                  className="w-full px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:border-orange-500/50 focus:outline-none transition-colors"
                />
              </div>

              {/* Description Input */}
              <div>
                <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-2">
                  {language === 'en' ? 'Description' : 'Mô tả'}
                </label>
                <textarea
                  placeholder={language === 'en' ? 'Enter document description...' : 'Nhập mô tả tài liệu...'}
                  value={newChapterDescription}
                  onChange={(e) => setNewChapterDescription(e.target.value)}
                  className="w-full h-24 px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:border-orange-500/50 focus:outline-none transition-colors resize-none"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 mt-6">
              <button
                onClick={() => setIsModalOpen(false)}
                className="px-4 py-2 hover:bg-slate-800 rounded-xl text-sm font-medium transition-colors text-slate-350"
              >
                {t('cancel')}
              </button>
              <button
                onClick={handleSubmitChapter}
                disabled={isCreating}
                className="px-5 py-2 bg-orange-500 hover:bg-orange-600 disabled:opacity-50 text-white rounded-xl text-sm font-semibold transition-colors"
              >
                {isCreating ? t('creating') : (language === 'en' ? 'Create' : 'Tạo')}
              </button>
            </div>
          </div>
        </div>
      )}

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
            <h3 className="text-xl font-serif font-bold mb-2">
              {language === 'en' ? 'Workspace Settings' : 'Cấu hình không gian làm việc'}
            </h3>
            <p className="text-xs text-themeMuted mb-4">
              {language === 'en' ? 'Configure your active localization pipeline settings.' : 'Cấu hình các thiết lập cho quy trình dịch thuật đang hoạt động.'}
            </p>
            
            <div className="space-y-4">
              {/* Project Display Name */}
              <div>
                <label className="text-xs font-bold text-themeMuted uppercase tracking-wider block mb-1.5">
                  {language === 'en' ? 'Project Display Name' : 'Tên hiển thị dự án'}
                </label>
                <input
                  type="text"
                  placeholder={language === 'en' ? 'Enter project display name...' : 'Nhập tên hiển thị dự án...'}
                  value={editDisplayName}
                  onChange={(e) => setEditDisplayName(e.target.value)}
                  className="w-full px-3 py-2 bg-themeBg border border-themeBorder rounded-xl text-sm focus:outline-none focus:border-accent-purple/50 text-themeText"
                />
              </div>

              {/* API Configuration */}
              <div>
                <label className="text-xs font-bold text-themeMuted uppercase tracking-wider block mb-1.5">
                  {language === 'en' ? 'AI Translation Engine' : 'Công cụ dịch thuật AI'}
                </label>
                <select className="w-full px-3 py-2 bg-themeBg border border-themeBorder rounded-xl text-sm focus:outline-none focus:border-accent-purple/50 text-themeText">
                  <option>{language === 'en' ? 'OpenAI GPT-4o (Recommended)' : 'OpenAI GPT-4o (Khuyên dùng)'}</option>
                  <option>Claude 3.5 Sonnet</option>
                  <option>DeepL Translator API</option>
                </select>
              </div>

              {/* Translation Tone */}
              <div>
                <label className="text-xs font-bold text-themeMuted uppercase tracking-wider block mb-1.5">
                  {language === 'en' ? 'Default Translation Tone' : 'Văn phong dịch mặc định'}
                </label>
                <input
                  type="text"
                  placeholder={language === 'en' ? 'Enter translation tone' : 'Nhập văn phong dịch'}
                  defaultValue={language === 'en' ? 'Smooth wordings, preserve Japanese honorifics' : 'Chữ nghĩa mượt mà, giữ nguyên các kính ngữ tiếng Nhật'}
                  className="w-full px-3 py-2 bg-themeBg border border-themeBorder rounded-xl text-sm focus:outline-none focus:border-accent-purple/50"
                />
              </div>

              {/* Auto-save */}
              <div className="flex items-center justify-between p-3 bg-themeBg border border-themeBorder rounded-xl">
                <div>
                  <h4 className="text-sm font-semibold">
                    {language === 'en' ? 'Enable Realtime Auto-Save' : 'Bật Tự động lưu thời gian thực'}
                  </h4>
                  <p className="text-xs text-themeMuted mt-0.5">
                    {language === 'en' ? 'Saves translation changes instantly to the backend.' : 'Lưu các thay đổi dịch thuật ngay lập tức lên máy chủ.'}
                  </p>
                </div>
                <input type="checkbox" defaultChecked className="w-4 h-4 accent-accent-purple" />
              </div>

              {/* Project Memory Portal */}
              <div className="p-4 bg-purple-500/10 border border-purple-500/20 rounded-xl flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-semibold text-purple-700 dark:text-purple-300">
                    {language === 'en' ? 'Project Memory Cache' : 'Bộ nhớ đệm dự án'}
                  </h4>
                  <p className="text-xs text-themeMuted mt-0.5">
                    {language === 'en' ? 'Manage glossary terms, entities, and style constraints shared across all chapters.' : 'Quản lý các thuật ngữ, thực thể và ràng buộc phong cách được chia sẻ giữa các tài liệu.'}
                  </p>
                </div>
                <Link
                  href={`/dashboard/${projectId}/memory?from=${encodeURIComponent(typeof window !== 'undefined' ? window.location.pathname : '')}`}
                  className="px-3 py-1.5 bg-purple-600 hover:bg-purple-700 dark:bg-purple-550 dark:hover:bg-purple-650 text-white rounded-lg text-xs font-semibold transition-colors"
                >
                  {language === 'en' ? 'Manage Memory' : 'Quản lý bộ nhớ'}
                </Link>
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setActiveModal(null)}
                className="px-4 py-2 hover:bg-themeBg rounded-xl text-sm font-medium transition-colors"
              >
                {t('cancel')}
              </button>
              <button
                onClick={handleSaveSettings}
                className="px-5 py-2 bg-accent-purple hover:bg-accent-purple/90 text-white rounded-xl text-sm font-semibold transition-colors"
              >
                {language === 'en' ? 'Save Changes' : 'Lưu thay đổi'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
