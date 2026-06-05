'use client'

import React, { useState, use } from 'react'
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
  Folder,
  ArrowLeft,
  Plus,
  Moon,
  Sun
} from 'lucide-react'
import { useTheme } from '@/app/theme-provider'
import { listChapters, getProject, getChapter, saveChapter, ProjectInfo } from '@/app/api-client'
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
  const [searchQuery, setSearchQuery] = useState('')
  const [chapters, setChapters] = useState<Chapter[]>([])
  const [projectInfo, setProjectInfo] = useState<ProjectInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [newChapterTitle, setNewChapterTitle] = useState('')
  const [newChapterType, setNewChapterType] = useState<'text' | 'image'>('text')
  const [isCreating, setIsCreating] = useState(false)
  const [activeModal, setActiveModal] = useState<'shared' | 'settings' | null>(null)

  useEffect(() => {
    let active = true;
    async function loadData() {
      try {
        const info = await getProject(projectId);
        if (active) {
          setProjectInfo(info);
        }
      } catch (err) {
        console.error('Error loading project details info:', err);
      }

      try {
        const slugs = await listChapters(projectId);
        if (!active) return;
        const list = await Promise.all(
          slugs.map(async (slug) => {
            try {
              const data = await getChapter(projectId, slug);
              const preview = data.draft ? data.draft.slice(0, 100) : "No draft content yet.";
              return {
                slug,
                title: slug,
                previewText: preview,
                updatedAt: 'Just now'
              };
            } catch (e) {
              return {
                slug,
                title: slug,
                previewText: "Start editing translation...",
                updatedAt: 'Just now'
              };
            }
          })
        );
        if (active) {
          setChapters(list);
          setLoading(false);
        }
      } catch (err) {
        console.error('Error loading project chapters:', err);
        if (active) setLoading(false);
      }
    }

    loadData();
    return () => { active = false; };
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
    setIsModalOpen(true);
  };

  const handleSubmitChapter = async () => {
    if (!newChapterTitle.trim()) {
      alert('Please enter a document title.');
      return;
    }

    setIsCreating(true);
    try {
      const nextId = generateNextChapterId(chapters);
      const content = `# ${newChapterTitle.trim()}\n\nBắt đầu bản dịch mới tại đây...`;
      await saveChapter(projectId, nextId, { draft: content });
      
      setIsModalOpen(false);
      setNewChapterTitle('');
      setNewChapterType('text');
      
      window.location.reload();
    } catch (err) {
      alert(`Failed to create chapter: ${err}`);
    } finally {
      setIsCreating(false);
    }
  };

  const projectName = projectInfo ? (projectInfo.project_id === 'demo_project' ? 'Dự án Dịch thuật' : projectInfo.project_id) : projectId

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
              <span className="text-white font-serif font-bold text-base">d</span>
            </div>
            <span className="font-serif font-bold text-2xl tracking-wide text-white">
              drs<span className="text-accent-purple">.</span>v3
            </span>
          </Link>

          {/* Navigation Links */}
          <nav className="space-y-4">
            <Link href="/dashboard" className="relative py-2 px-3 flex items-center gap-3 text-white cursor-pointer font-medium block">
              <svg className="absolute inset-0 w-full h-full text-accent-purple/60 dark:text-accent-violet/60 pointer-events-none" viewBox="0 0 170 46" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M6 22C6 11 35 3.5 85 3.5C135 3.5 164 11 164 22C164 33 135 41.5 85 41.5C35 41.5 6 33 6 22Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <Home size={18} className="text-white" />
              <span>My work</span>
            </Link>

            <div 
              onClick={() => setActiveModal('shared')}
              className="py-2 px-3 flex items-center gap-3 hover:text-white cursor-pointer transition-colors"
            >
              <Users size={18} />
              <span>Shared w/ me</span>
            </div>

            <div 
              onClick={() => setActiveModal('settings')}
              className="py-2 px-3 flex items-center gap-3 hover:text-white cursor-pointer transition-colors"
            >
              <Settings size={18} />
              <span>Settings</span>
            </div>
          </nav>
        </div>

        {/* Sidebar Footer */}
        <div className="space-y-4">
          <button
            onClick={toggleTheme}
            className="flex items-center gap-3 py-2 px-3 w-full hover:text-white transition-colors text-left"
          >
            {theme === 'light' ? (
              <>
                <Moon size={18} />
                <span>Dark Mode</span>
              </>
            ) : (
              <>
                <Sun size={18} className="text-accent-cyan" />
                <span>Light Mode</span>
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
            <span className="text-[10px] text-slate-650 font-mono">v3.0.4</span>
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
            </div>

            {/* New Button */}
            <button 
              onClick={handleCreateChapter}
              className="ml-2 px-4 py-1.5 bg-slate-950 hover:bg-slate-850 dark:bg-slate-100 dark:hover:bg-slate-200 text-white dark:text-slate-900 rounded-full text-xs font-semibold flex items-center gap-1.5 shadow-sm transition-all"
            >
              <Plus size={14} />
              New
            </button>
          </div>

          {/* Action Utilities (Search, Filter, Notification) */}
          <div className="flex items-center gap-4">
            <div className="relative">
              <Search size={16} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Search chapters..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 pr-4 py-1.5 w-48 bg-slate-200/40 dark:bg-slate-800/30 border border-slate-300/40 dark:border-slate-700/40 rounded-full text-xs focus:w-64 focus:border-accent-purple/50 focus:outline-none transition-all duration-300"
              />
            </div>

            <button className="p-2 hover:bg-slate-200/50 dark:hover:bg-slate-800/50 rounded-lg transition-colors text-slate-500 dark:text-slate-400">
              <SlidersHorizontal size={16} />
            </button>

            <button className="p-2 hover:bg-slate-200/50 dark:hover:bg-slate-800/50 rounded-lg transition-colors text-slate-500 dark:text-slate-400">
              <Bell size={16} />
            </button>
          </div>
        </header>

        {/* Chapters Cards Grid Container - Scrollable */}
        <div className="flex-1 overflow-y-auto p-8 max-w-5xl w-full mx-auto">
          {loading && (
            <div className="pt-4 text-sm text-themeMuted">Loading documents...</div>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pt-4">
            {filteredChapters.map((chapter) => (
              <div 
                key={chapter.slug} 
                className="relative bg-themeCard border border-themeBorder rounded-2xl p-5 flex flex-col justify-between shadow-sm hover:shadow-md hover:border-slate-350 dark:hover:border-slate-750 transition-all duration-200 min-h-[160px]"
              >
                {/* Chapter Title & Action Button */}
                <div className="flex items-start justify-between gap-4 mb-3">
                  <Link href={`/dashboard/${projectId}/${chapter.slug}`} className="block flex-1 group">
                    <span className="text-[10px] font-bold text-accent-purple dark:text-accent-violet uppercase tracking-wider block mb-1">
                      {chapter.title}
                    </span>
                    <h2 className="text-base font-serif leading-relaxed text-slate-800 dark:text-slate-200 group-hover:text-accent-purple dark:group-hover:text-accent-violet transition-colors line-clamp-2">
                      "{chapter.previewText}..."
                    </h2>
                  </Link>
                  <button className="p-1 hover:bg-slate-100 dark:hover:bg-slate-800 rounded transition-colors text-slate-400 dark:text-slate-500 shrink-0">
                    <MoreHorizontal size={16} />
                  </button>
                </div>

                {/* Updated Timestamp at Bottom */}
                <div className="flex items-center justify-between text-[11px] text-slate-400 mt-auto pt-4 border-t border-slate-100/50 dark:border-slate-800/20">
                  <div className="flex items-center gap-1">
                    <Clock size={12} className="text-slate-300 dark:text-slate-600" />
                    <span>{chapter.updatedAt}</span>
                  </div>
                  <Link href={`/dashboard/${projectId}/${chapter.slug}`} className="px-3 py-1 bg-accent-purple/10 hover:bg-accent-purple/20 text-accent-purple dark:text-accent-violet rounded-full font-semibold transition-all">
                    Dịch →
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>

      {/* Create Chapter Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-themeCard border border-themeBorder rounded-2xl w-full max-w-md p-6 shadow-2xl animate-fade-in text-themeText">
            <h3 className="text-xl font-serif font-bold mb-4">Create New Document</h3>
            
            <div className="space-y-4">
              {/* Title Input */}
              <div>
                <label className="text-xs font-bold text-themeMuted uppercase tracking-wider block mb-2">
                  Document / Chapter Title
                </label>
                <input
                  type="text"
                  placeholder="e.g. Chapter 4: The Revelation"
                  value={newChapterTitle}
                  onChange={(e) => setNewChapterTitle(e.target.value)}
                  className="w-full px-4 py-2.5 bg-themeBg border border-themeBorder rounded-xl text-sm focus:border-accent-purple/50 focus:outline-none transition-colors"
                />
              </div>

              {/* Type Selection */}
              <div>
                <label className="text-xs font-bold text-themeMuted uppercase tracking-wider block mb-2">
                  Type
                </label>
                <div className="grid grid-cols-2 gap-4">
                  {/* Text Option */}
                  <div 
                    onClick={() => setNewChapterType('text')}
                    className={`p-4 border rounded-xl cursor-pointer transition-all ${
                      newChapterType === 'text' 
                        ? 'border-accent-purple bg-accent-purple/5' 
                        : 'border-themeBorder hover:border-accent-purple/20'
                    }`}
                  >
                    <span className="text-sm font-bold block mb-1">Text (Chữ)</span>
                    <span className="text-xs text-themeMuted">Documents, articles, books</span>
                  </div>

                  {/* Image Option */}
                  <div 
                    onClick={() => setNewChapterType('image')}
                    className={`p-4 border rounded-xl cursor-pointer transition-all relative ${
                      newChapterType === 'image' 
                        ? 'border-accent-purple bg-accent-purple/5' 
                        : 'border-themeBorder hover:border-accent-purple/20'
                    }`}
                  >
                    <span className="text-sm font-bold block mb-1">Image (Ảnh)</span>
                    <span className="text-xs text-themeMuted">Scans, presentations, screenshots, etc.</span>
                    <span className="absolute top-2 right-2 text-[9px] font-bold text-amber-500 bg-amber-500/10 px-1.5 py-0.5 rounded uppercase">
                      Soon
                    </span>
                  </div>
                </div>
              </div>

              {/* Warning/Notice for Image Type */}
              {newChapterType === 'image' && (
                <div className="p-3 bg-amber-500/10 border border-amber-500/20 text-amber-600 dark:text-amber-500 rounded-xl text-xs leading-relaxed">
                  <strong>Notice:</strong> Image translation mode is currently under development. Creating this will set up a placeholder translation workspace.
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-3 mt-6">
              <button
                onClick={() => setIsModalOpen(false)}
                className="px-4 py-2 hover:bg-themeBg rounded-xl text-sm font-medium transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmitChapter}
                disabled={isCreating}
                className="px-5 py-2 bg-accent-purple hover:bg-accent-purple/90 disabled:opacity-50 text-white rounded-xl text-sm font-semibold transition-colors"
              >
                {isCreating ? 'Creating...' : 'Create'}
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

              {/* Project Memory Portal */}
              <div className="p-4 bg-purple-500/10 border border-purple-500/20 rounded-xl flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-semibold text-purple-700 dark:text-purple-300">Project Memory Cache</h4>
                  <p className="text-xs text-themeMuted mt-0.5">Manage glossary terms, entities, and style constraints shared across all chapters.</p>
                </div>
                <Link
                  href={`/dashboard/${projectId}/memory`}
                  className="px-3 py-1.5 bg-purple-600 hover:bg-purple-700 dark:bg-purple-550 dark:hover:bg-purple-650 text-white rounded-lg text-xs font-semibold transition-colors"
                >
                  Manage Memory
                </Link>
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
                  alert("Settings saved successfully!");
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
    </div>
  )
}
