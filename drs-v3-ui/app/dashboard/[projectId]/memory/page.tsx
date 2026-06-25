'use client'

import React, { useState, use, useEffect } from 'react'
import Link from 'next/link'
import {
  ArrowLeft,
  Plus,
  Trash2,
  Search,
  BookOpen,
  Users,
  Moon,
  Sun,
  Sparkles,
  Bookmark,
  Edit3
} from 'lucide-react'
import { useTheme } from '@/app/theme-provider'
import { showToast } from '@/components/toast'
import {
  getProjectMemory,
  addGlossaryTerm,
  deleteGlossaryTerm,
  addEntity,
  deleteEntity,
  addStyleRule,
  deleteStyleRule,
  getProject,
  ProjectInfo,
  GlossaryEntry,
  EntityEntry,
  StyleRuleEntry
} from '@/app/api-client'

interface PageProps {
  params: Promise<{ projectId: string }>
}

type TabType = 'glossary' | 'entities' | 'style_rules'

export default function ProjectMemoryPage({ params }: PageProps) {
  const { projectId } = use(params)
  const { theme, toggleTheme } = useTheme()
  
  // Project & Memory states
  const [projectInfo, setProjectInfo] = useState<ProjectInfo | null>(null)
  const [glossary, setGlossary] = useState<GlossaryEntry[]>([])
  const [entities, setEntities] = useState<EntityEntry[]>([])
  const [styleRules, setStyleRules] = useState<StyleRuleEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [activeTab, setActiveTab] = useState<TabType>('glossary')

  // Modals / Add forms state
  const [showAddGlossary, setShowAddGlossary] = useState(false)
  const [showAddEntity, setShowAddEntity] = useState(false)
  const [showAddRule, setShowAddRule] = useState(false)

  // Form Fields
  const [gSource, setGSource] = useState('')
  const [gTarget, setGTarget] = useState('')
  const [gNote, setGNote] = useState('')

  const [editingItem, setEditingItem] = useState<{
    type: 'glossary' | 'entity' | 'style_rule'
    originalKey: string
  } | null>(null)

  const [backHref, setBackHref] = useState(`/dashboard/${projectId}`)

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search)
      const from = params.get('from')
      if (from) {
        setBackHref(from)
      }
    }
  }, [projectId])

  const startEditGlossary = (entry: GlossaryEntry) => {
    setGSource(entry.source_term)
    setGTarget(entry.target_term)
    setGNote(entry.context_note || '')
    setEditingItem({ type: 'glossary', originalKey: entry.source_term })
    setShowAddGlossary(true)
  }

  const startEditEntity = (entry: EntityEntry) => {
    setEId(entry.entity_id)
    setECanonical(entry.canonical_name)
    setESource(entry.source_name)
    setEType(entry.entity_type)
    setEPronouns(entry.pronouns || '')
    setENotes(entry.notes || '')
    setEditingItem({ type: 'entity', originalKey: entry.entity_id })
    setShowAddEntity(true)
  }

  const startEditStyleRule = (entry: StyleRuleEntry) => {
    setRId(entry.rule_id)
    setRCategory(entry.category)
    setRDesc(entry.description)
    setRBefore(entry.example_before || '')
    setRAfter(entry.example_after || '')
    setEditingItem({ type: 'style_rule', originalKey: entry.rule_id })
    setShowAddRule(true)
  }

  const resetGlossaryForm = () => {
    setGSource('')
    setGTarget('')
    setGNote('')
    setEditingItem(null)
    setShowAddGlossary(false)
  }

  const resetEntityForm = () => {
    setEId('')
    setECanonical('')
    setESource('')
    setEType('person')
    setEPronouns('')
    setENotes('')
    setEditingItem(null)
    setShowAddEntity(false)
  }

  const resetStyleRuleForm = () => {
    setRId('')
    setRCategory('')
    setRDesc('')
    setRBefore('')
    setRAfter('')
    setEditingItem(null)
    setShowAddRule(false)
  }

  const [eId, setEId] = useState('')
  const [eCanonical, setECanonical] = useState('')
  const [eSource, setESource] = useState('')
  const [eType, setEType] = useState('person')
  const [ePronouns, setEPronouns] = useState('')
  const [eNotes, setENotes] = useState('')

  const [rId, setRId] = useState('')
  const [rCategory, setRCategory] = useState('')
  const [rDesc, setRDesc] = useState('')
  const [rBefore, setRBefore] = useState('')
  const [rAfter, setRAfter] = useState('')

  const loadMemory = async () => {
    try {
      setLoading(true)
      const proj = await getProject(projectId)
      setProjectInfo(proj)

      const data = await getProjectMemory(projectId)
      setGlossary(data.glossary || [])
      setEntities(data.entities || [])
      setStyleRules(data.style_rules || [])
    } catch (err) {
      console.error('Failed to load memory data:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadMemory()
  }, [projectId])

  // Handlers for Glossary
  const handleAddGlossary = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!gSource.trim() || !gTarget.trim()) return
    try {
      const data: any = {
        source_term: gSource.trim(),
        target_term: gTarget.trim(),
        source_lang: projectInfo?.source_lang || 'ja',
        target_lang: projectInfo?.target_lang || 'vi',
        context_note: gNote.trim() || undefined
      }
      if (editingItem && editingItem.type === 'glossary') {
        data.old_source_term = editingItem.originalKey
      }
      await addGlossaryTerm(projectId, data)
      showToast(editingItem ? 'Cập nhật thuật ngữ thành công!' : 'Thêm thuật ngữ thành công!', 'success')
      resetGlossaryForm()
      loadMemory()
    } catch (err) {
      showToast(`Lỗi: ${err}`, 'error')
    }
  }

  const handleDeleteGlossary = async (term: string) => {
    if (!confirm(`Delete glossary term "${term}"?`)) return
    setGlossary(prev => prev.filter(g => g.source_term !== term))
    try {
      await deleteGlossaryTerm(
        projectId,
        projectInfo?.source_lang || 'ja',
        projectInfo?.target_lang || 'vi',
        term
      )
      showToast('Đã xóa thuật ngữ thành công!', 'success')
      loadMemory()
    } catch (err) {
      showToast(`Không thể xóa thuật ngữ: ${err}`, 'error')
    }
  }

  const handleAddEntity = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!eId.trim() || !eCanonical.trim() || !eSource.trim()) return
    try {
      const data: any = {
        entity_id: eId.trim(),
        canonical_name: eCanonical.trim(),
        source_name: eSource.trim(),
        entity_type: eType,
        source_lang: projectInfo?.source_lang || 'ja',
        target_lang: projectInfo?.target_lang || 'vi',
        pronouns: ePronouns.trim() || undefined,
        notes: eNotes.trim() || undefined
      }
      if (editingItem && editingItem.type === 'entity') {
        data.old_entity_id = editingItem.originalKey
      }
      await addEntity(projectId, data)
      showToast(editingItem ? 'Cập nhật thực thể thành công!' : 'Thêm thực thể thành công!', 'success')
      resetEntityForm()
      loadMemory()
    } catch (err) {
      showToast(`Lỗi: ${err}`, 'error')
    }
  }

  const handleDeleteEntity = async (entityId: string) => {
    if (!confirm(`Delete entity "${entityId}"?`)) return
    setEntities(prev => prev.filter(e => e.entity_id !== entityId))
    try {
      await deleteEntity(projectId, entityId)
      showToast('Đã xóa thực thể thành công!', 'success')
      loadMemory()
    } catch (err) {
      showToast(`Không thể xóa thực thể: ${err}`, 'error')
      loadMemory()
    }
  }

  const handleAddRule = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!rId.trim() || !rCategory.trim() || !rDesc.trim()) return
    try {
      const data: any = {
        rule_id: rId.trim(),
        category: rCategory.trim(),
        description: rDesc.trim(),
        example_before: rBefore.trim() || undefined,
        example_after: rAfter.trim() || undefined,
        source_lang: projectInfo?.source_lang || 'ja',
        target_lang: projectInfo?.target_lang || 'vi'
      }
      if (editingItem && editingItem.type === 'style_rule') {
        data.old_rule_id = editingItem.originalKey
      }
      await addStyleRule(projectId, data)
      showToast(editingItem ? 'Cập nhật quy tắc thành công!' : 'Thêm quy tắc thành công!', 'success')
      resetStyleRuleForm()
      loadMemory()
    } catch (err) {
      showToast(`Lỗi: ${err}`, 'error')
    }
  }

  const handleDeleteRule = async (ruleId: string) => {
    if (!confirm(`Delete style rule "${ruleId}"?`)) return
    setStyleRules(prev => prev.filter(r => r.rule_id !== ruleId))
    try {
      await deleteStyleRule(projectId, ruleId)
      showToast('Đã xóa quy tắc thành công!', 'success')
      loadMemory()
    } catch (err) {
      showToast(`Không thể xóa quy tắc: ${err}`, 'error')
      loadMemory()
    }
  }

  const filteredGlossary = glossary.filter(
    (g) =>
      g.source_term.toLowerCase().includes(searchQuery.toLowerCase()) ||
      g.target_term.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (g.context_note && g.context_note.toLowerCase().includes(searchQuery.toLowerCase()))
  )

  const filteredEntities = entities.filter(
    (ent) =>
      ent.canonical_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ent.source_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (ent.notes && ent.notes.toLowerCase().includes(searchQuery.toLowerCase()))
  )

  const filteredStyleRules = styleRules.filter(
    (rule) =>
      rule.category.toLowerCase().includes(searchQuery.toLowerCase()) ||
      rule.description.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const projectName = projectInfo?.project_id === 'demo_project' ? 'Dự án Dịch thuật' : projectId

  return (
    <div className="w-screen h-screen flex overflow-hidden font-sans bg-themeBg text-themeText transition-colors duration-300">
      {/* Sidebar navigation */}
      <aside className="w-64 bg-themeSidebar text-slate-400 flex flex-col justify-between p-6 border-r border-slate-950/40 select-none transition-colors duration-300 shrink-0">
        <div className="space-y-8">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent-purple to-accent-violet flex items-center justify-center">
              <span className="text-white font-serif font-bold text-base">o</span>
            </div>
            <span className="font-serif font-bold text-2xl tracking-wide text-white relative">
              oneiros<span className="text-[9px] font-sans font-semibold uppercase tracking-wider text-accent-purple ml-1 absolute -top-1.5 -right-7 px-1.5 py-0.5 rounded-md bg-accent-purple/10">beta</span>
            </span>
          </div>

          <nav className="space-y-4">
            <Link
              href={backHref}
              className="py-2 px-3 flex items-center gap-3 hover:text-white transition-colors"
            >
              <ArrowLeft size={16} />
              <span>Quay lại Tài liệu</span>
            </Link>

            <div className="h-px bg-slate-800 my-4" />

            <button
              onClick={() => setActiveTab('glossary')}
              className={`w-full py-2 px-3 flex items-center gap-3 rounded-lg text-left transition-colors ${
                activeTab === 'glossary' ? 'bg-slate-900 text-white dark:bg-slate-800' : 'hover:text-white'
              }`}
            >
              <BookOpen size={16} />
              <span>Thuật ngữ ({glossary.length})</span>
            </button>

            <button
              onClick={() => setActiveTab('entities')}
              className={`w-full py-2 px-3 flex items-center gap-3 rounded-lg text-left transition-colors ${
                activeTab === 'entities' ? 'bg-slate-900 text-white dark:bg-slate-800' : 'hover:text-white'
              }`}
            >
              <Users size={16} />
              <span>Nhân vật & Thực thể ({entities.length})</span>
            </button>

            <button
              onClick={() => setActiveTab('style_rules')}
              className={`w-full py-2 px-3 flex items-center gap-3 rounded-lg text-left transition-colors ${
                activeTab === 'style_rules' ? 'bg-slate-900 text-white dark:bg-slate-800' : 'hover:text-white'
              }`}
            >
              <Sparkles size={16} />
              <span>Luật phong cách ({styleRules.length})</span>
            </button>
          </nav>
        </div>

        <div className="space-y-4">
          <button
            onClick={toggleTheme}
            className="flex items-center gap-3 py-2 px-3 w-full hover:text-white transition-colors text-left"
          >
            {theme === 'light' ? (
              <>
                <Moon size={18} />
                <span>Giao diện Tối</span>
              </>
            ) : (
              <>
                <Sun size={18} className="text-accent-cyan" />
                <span>Giao diện Sáng</span>
              </>
            )}
          </button>
          <div className="text-[10px] text-slate-650 font-mono pt-4 border-t border-slate-900">v1.0.0</div>
        </div>
      </aside>

      {/* Main panel */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <header className="px-8 py-6 border-b border-themeBorder bg-white/40 dark:bg-slate-950/20 backdrop-blur-md flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-serif font-bold text-slate-950 dark:text-slate-50">
              {projectName} &bull; Bộ nhớ Dự án
            </h1>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-800 dark:bg-purple-950/40 dark:text-purple-300 uppercase tracking-wider">
              Bộ nhớ chia sẻ
            </span>
          </div>

          <div className="flex items-center gap-4">
            <div className="relative">
              <Search size={16} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder={`Tìm kiếm trong ${activeTab === 'glossary' ? 'thuật ngữ' : activeTab === 'entities' ? 'thực thể' : 'luật phong cách'}...`}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 pr-4 py-1.5 w-60 bg-slate-200/40 dark:bg-slate-800/30 border border-slate-300/40 dark:border-slate-700/40 rounded-full text-xs focus:w-80 focus:outline-none focus:border-purple-500/50 transition-all duration-300"
              />
            </div>

            {activeTab === 'glossary' && (
              <button
                onClick={() => setShowAddGlossary(true)}
                className="px-4 py-1.5 bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-950 rounded-full text-xs font-semibold flex items-center gap-1.5 hover:opacity-90 transition-opacity"
              >
                <Plus size={14} /> Thêm thuật ngữ
              </button>
            )}

            {activeTab === 'entities' && (
              <button
                onClick={() => setShowAddEntity(true)}
                className="px-4 py-1.5 bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-950 rounded-full text-xs font-semibold flex items-center gap-1.5 hover:opacity-90 transition-opacity"
              >
                <Plus size={14} /> Thêm thực thể
              </button>
            )}

            {activeTab === 'style_rules' && (
              <button
                onClick={() => setShowAddRule(true)}
                className="px-4 py-1.5 bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-950 rounded-full text-xs font-semibold flex items-center gap-1.5 hover:opacity-90 transition-opacity"
              >
                <Plus size={14} /> Thêm quy tắc
              </button>
            )}
          </div>
        </header>

        <div className="flex-1 overflow-y-auto p-8 max-w-6xl w-full mx-auto scrollbar-thin">
          {loading ? (
            <div className="space-y-6 pt-4 animate-pulse select-none">
              <div className="h-12 bg-slate-250/20 dark:bg-slate-800/40 rounded-xl w-full"></div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {[1, 2, 3, 4].map((n) => (
                  <div key={n} className="bg-themeCard/65 border border-themeBorder/40 rounded-xl p-4 flex flex-col justify-between min-h-[120px]">
                    <div className="space-y-2">
                      <div className="h-4 bg-slate-250/20 dark:bg-slate-800/40 rounded w-1/3"></div>
                      <div className="h-3 bg-slate-250/20 dark:bg-slate-800/40 rounded w-1/2"></div>
                    </div>
                    <div className="h-3 bg-slate-250/20 dark:bg-slate-800/40 rounded w-full mt-4"></div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <>
              {/* Tab: Glossary */}
              {activeTab === 'glossary' && (
                <div className="space-y-4">
                  <div className="p-4 rounded-xl bg-themeCard/30 border border-themeBorder flex items-start gap-3 text-xs leading-relaxed text-themeMuted">
                    <BookOpen size={16} className="text-purple-500 shrink-0 mt-0.5" />
                    <div>
                      <strong>Bộ nhớ Thuật ngữ:</strong> Các thuật ngữ quy định tại đây sẽ tự động được áp dụng cứng trong quá trình dịch thuật của AI Agent và được kiểm tra chéo bởi Consistency Auditor.
                    </div>
                  </div>

                  {filteredGlossary.length === 0 ? (
                    <div className="py-12 text-center text-xs text-themeMuted">Không tìm thấy thuật ngữ nào phù hợp.</div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {filteredGlossary.map((entry) => (
                        <div
                          key={entry.source_term}
                          className="bg-themeCard border border-themeBorder rounded-xl p-4 flex justify-between items-start hover:border-slate-350 dark:hover:border-slate-750 transition-colors"
                        >
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-semibold text-sm text-themeText">{entry.source_term}</span>
                              <span className="text-[10px] font-mono text-themeMuted bg-themeBg px-1.5 py-0.5 rounded">
                                {entry.source_lang} ➔ {entry.target_lang}
                              </span>
                            </div>
                            <div className="text-sm font-semibold text-purple-600 dark:text-purple-400 mt-1">
                              {entry.target_term}
                            </div>
                            {entry.context_note && (
                              <p className="text-[11px] text-themeMuted mt-2 leading-relaxed bg-themeBg/50 p-2 rounded">
                                {entry.context_note}
                              </p>
                            )}
                          </div>

                          <div className="flex items-center gap-1 shrink-0">
                            <button
                              onClick={() => startEditGlossary(entry)}
                              className="p-1.5 rounded-lg text-themeMuted hover:text-indigo-500 hover:bg-indigo-500/10 transition-colors"
                              title="Sửa thuật ngữ"
                            >
                              <Edit3 size={14} />
                            </button>
                            <button
                              onClick={() => handleDeleteGlossary(entry.source_term)}
                              className="p-1.5 rounded-lg text-themeMuted hover:text-red-500 hover:bg-red-500/10 transition-colors"
                              title="Xóa thuật ngữ"
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Tab: Entities */}
              {activeTab === 'entities' && (
                <div className="space-y-4">
                  <div className="p-4 rounded-xl bg-themeCard/30 border border-themeBorder flex items-start gap-3 text-xs leading-relaxed text-themeMuted">
                    <Users size={16} className="text-purple-500 shrink-0 mt-0.5" />
                    <div>
                      <strong>Bộ nhớ Thực thể & Nhân vật:</strong> Quy định danh xưng, đại từ xưng hô, cách xưng hô và các danh từ riêng cụ thể cho nhân vật, địa danh và tổ chức.
                    </div>
                  </div>

                  {filteredEntities.length === 0 ? (
                    <div className="py-12 text-center text-xs text-themeMuted">Không tìm thấy thực thể nào phù hợp.</div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {filteredEntities.map((ent) => (
                        <div
                          key={ent.entity_id}
                          className="bg-themeCard border border-themeBorder rounded-xl p-4 flex justify-between items-start hover:border-slate-350 dark:hover:border-slate-750 transition-colors"
                        >
                          <div className="space-y-2">
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="font-semibold text-sm text-themeText">{ent.canonical_name}</span>
                                <span className="text-[10px] font-mono text-themeMuted bg-themeBg px-1.5 py-0.5 rounded capitalize">
                                  {ent.entity_type}
                                </span>
                              </div>
                              <div className="text-xs text-themeMuted mt-1">
                                ID: <span className="font-mono">{ent.entity_id}</span> &bull; Bản gốc: {ent.source_name}
                              </div>
                            </div>
                            {ent.pronouns && (
                              <div className="text-[11px] font-mono text-purple-600 dark:text-purple-400 bg-purple-500/10 inline-block px-1.5 py-0.5 rounded">
                                Đại từ/Danh xưng: {ent.pronouns}
                              </div>
                            )}
                            {ent.notes && (
                              <p className="text-[11px] text-themeMuted leading-relaxed bg-themeBg/50 p-2 rounded">
                                {ent.notes}
                              </p>
                            )}
                          </div>

                          <div className="flex items-center gap-1 shrink-0">
                            <button
                              onClick={() => startEditEntity(ent)}
                              className="p-1.5 rounded-lg text-themeMuted hover:text-indigo-500 hover:bg-indigo-500/10 transition-colors"
                              title="Sửa thực thể"
                            >
                              <Edit3 size={14} />
                            </button>
                            <button
                              onClick={() => handleDeleteEntity(ent.entity_id)}
                              className="p-1.5 rounded-lg text-themeMuted hover:text-red-500 hover:bg-red-500/10 transition-colors"
                              title="Xóa thực thể"
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Tab: Style Rules */}
              {activeTab === 'style_rules' && (
                <div className="space-y-4">
                  <div className="p-4 rounded-xl bg-themeCard/30 border border-themeBorder flex items-start gap-3 text-xs leading-relaxed text-themeMuted">
                    <Sparkles size={16} className="text-purple-500 shrink-0 mt-0.5" />
                    <div>
                      <strong>Bộ nhớ Luật phong cách:</strong> Áp dụng các quy tắc ngữ pháp, ràng buộc về giọng điệu, hướng dẫn dấu câu và cấm một số từ ngữ hoặc cấu trúc câu nhất định trong bản dịch cuối.
                    </div>
                  </div>

                  {filteredStyleRules.length === 0 ? (
                    <div className="py-12 text-center text-xs text-themeMuted">Không tìm thấy luật phong cách nào phù hợp.</div>
                  ) : (
                    <div className="space-y-4">
                      {filteredStyleRules.map((rule) => (
                        <div
                          key={rule.rule_id}
                          className="bg-themeCard border border-themeBorder rounded-xl p-5 flex justify-between items-start hover:border-slate-350 dark:hover:border-slate-750 transition-colors"
                        >
                          <div className="flex-1 grid grid-cols-[minmax(180px,0.8fr)_minmax(300px,1.5fr)] gap-6">
                            <div>
                              <div className="flex items-center gap-2 mb-1">
                                <span className="font-semibold text-sm text-themeText">{rule.category}</span>
                              </div>
                              <span className="text-[10px] font-mono text-themeMuted">ID: {rule.rule_id}</span>
                              <p className="text-xs text-themeMuted mt-2">{rule.description}</p>
                            </div>
                            
                            {(rule.example_before || rule.example_after) && (
                              <div className="grid grid-cols-2 gap-4 bg-themeBg/40 p-3 rounded-lg text-xs leading-relaxed font-mono">
                                <div>
                                  <div className="text-[9px] uppercase font-bold text-red-500 mb-1">Trước / Cần tránh</div>
                                  <div className="text-red-700 dark:text-red-400">{rule.example_before || '—'}</div>
                                </div>
                                <div>
                                  <div className="text-[9px] uppercase font-bold text-emerald-500 mb-1">Sau / Khuyên dùng</div>
                                  <div className="text-emerald-700 dark:text-emerald-400">{rule.example_after || '—'}</div>
                                </div>
                              </div>
                            )}
                          </div>

                          <div className="flex items-center gap-1 shrink-0 ml-4">
                            <button
                              onClick={() => startEditStyleRule(rule)}
                              className="p-1.5 rounded-lg text-themeMuted hover:text-indigo-500 hover:bg-indigo-500/10 transition-colors"
                              title="Sửa quy tắc"
                            >
                              <Edit3 size={14} />
                            </button>
                            <button
                              onClick={() => handleDeleteRule(rule.rule_id)}
                              className="p-1.5 rounded-lg text-themeMuted hover:text-red-500 hover:bg-red-500/10 transition-colors shrink-0 ml-4"
                              title="Xóa quy tắc"
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </main>

      {/* Add Glossary Modal */}
      {showAddGlossary && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <form onSubmit={handleAddGlossary} className="bg-themeCard border border-themeBorder rounded-2xl w-full max-w-md p-6 shadow-2xl animate-fade-in text-themeText space-y-4">
            <h3 className="text-lg font-serif font-bold">{editingItem ? 'Chỉnh sửa Thuật ngữ' : 'Thêm Thuật ngữ mới'}</h3>
            
            <div className="space-y-3">
              <div>
                <label className="text-[10px] uppercase font-bold text-themeMuted block mb-1">Từ nguồn ({projectInfo?.source_lang || 'ja'})</label>
                <input
                  type="text"
                  required
                  value={gSource}
                  onChange={(e) => setGSource(e.target.value)}
                  className="w-full rounded-xl bg-themeBg border border-themeBorder px-3 py-2 text-xs"
                  placeholder="Ví dụ: 仲間"
                />
              </div>

              <div>
                <label className="text-[10px] uppercase font-bold text-themeMuted block mb-1">Bản dịch được duyệt ({projectInfo?.target_lang || 'vi'})</label>
                <input
                  type="text"
                  required
                  value={gTarget}
                  onChange={(e) => setGTarget(e.target.value)}
                  className="w-full rounded-xl bg-themeBg border border-themeBorder px-3 py-2 text-xs"
                  placeholder="Ví dụ: Đồng đội"
                />
              </div>

              <div>
                <label className="text-[10px] uppercase font-bold text-themeMuted block mb-1">Ghi chú ngữ cảnh (Không bắt buộc)</label>
                <textarea
                  value={gNote}
                  onChange={(e) => setGNote(e.target.value)}
                  className="w-full rounded-xl bg-themeBg border border-themeBorder px-3 py-2 text-xs resize-none h-16"
                  placeholder="Ví dụ: Chỉ sử dụng trong bối cảnh thân mật giữa các nhân vật chính."
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button type="button" onClick={resetGlossaryForm} className="px-4 py-1.5 text-xs">Hủy</button>
              <button type="submit" className="px-4 py-1.5 bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-950 rounded-lg text-xs font-semibold">{editingItem ? 'Lưu thay đổi' : 'Thêm mới'}</button>
            </div>
          </form>
        </div>
      )}

      {/* Add Entity Modal */}
      {showAddEntity && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <form onSubmit={handleAddEntity} className="bg-themeCard border border-themeBorder rounded-2xl w-full max-w-md p-6 shadow-2xl animate-fade-in text-themeText space-y-4">
            <h3 className="text-lg font-serif font-bold">{editingItem ? 'Chỉnh sửa Thực thể' : 'Thêm Thực thể mới'}</h3>
            
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="col-span-2">
                <label className="text-[10px] uppercase font-bold text-themeMuted block mb-1">Mã định danh thực thể (ID duy nhất)</label>
                <input
                  type="text"
                  required
                  disabled={!!editingItem}
                  value={eId}
                  onChange={(e) => setEId(e.target.value)}
                  className="w-full rounded-xl bg-themeBg border border-themeBorder px-3 py-2 disabled:opacity-50"
                  placeholder="Ví dụ: char_lilia"
                />
              </div>

              <div>
                <label className="text-[10px] uppercase font-bold text-themeMuted block mb-1">Tên chuẩn hóa (Canonical Name)</label>
                <input
                  type="text"
                  required
                  value={eCanonical}
                  onChange={(e) => setECanonical(e.target.value)}
                  className="w-full rounded-xl bg-themeBg border border-themeBorder px-3 py-2"
                  placeholder="Ví dụ: Lilia"
                />
              </div>

              <div>
                <label className="text-[10px] uppercase font-bold text-themeMuted block mb-1">Tên gốc (Original Name)</label>
                <input
                  type="text"
                  required
                  value={eSource}
                  onChange={(e) => setESource(e.target.value)}
                  className="w-full rounded-xl bg-themeBg border border-themeBorder px-3 py-2"
                  placeholder="Ví dụ: リリア"
                />
              </div>

              <div>
                <label className="text-[10px] uppercase font-bold text-themeMuted block mb-1">Loại thực thể</label>
                <select
                  value={eType}
                  onChange={(e) => setEType(e.target.value)}
                  className="w-full rounded-xl bg-themeBg border border-themeBorder px-3 py-2"
                >
                  <option value="person">Nhân vật (Person)</option>
                  <option value="location">Địa danh (Location)</option>
                  <option value="organization">Tổ chức (Organization)</option>
                  <option value="item">Vật phẩm / Đồ vật (Item)</option>
                </select>
              </div>

              <div>
                <label className="text-[10px] uppercase font-bold text-themeMuted block mb-1">Đại từ nhân xưng (Không bắt buộc)</label>
                <input
                  type="text"
                  value={ePronouns}
                  onChange={(e) => setEPronouns(e.target.value)}
                  className="w-full rounded-xl bg-themeBg border border-themeBorder px-3 py-2"
                  placeholder="Ví dụ: cô ấy / she"
                />
              </div>

              <div className="col-span-2">
                <label className="text-[10px] uppercase font-bold text-themeMuted block mb-1">Mô tả / Ghi chú thực thể</label>
                <textarea
                  value={eNotes}
                  onChange={(e) => setENotes(e.target.value)}
                  className="w-full rounded-xl bg-themeBg border border-themeBorder px-3 py-2 resize-none h-16"
                  placeholder="Ví dụ: Công chúa vùng Crimzon, tính cách hướng ngoại."
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button type="button" onClick={resetEntityForm} className="px-4 py-1.5 text-xs">Hủy</button>
              <button type="submit" className="px-4 py-1.5 bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-950 rounded-lg text-xs font-semibold">{editingItem ? 'Lưu thay đổi' : 'Thêm mới'}</button>
            </div>
          </form>
        </div>
      )}

      {/* Add Style Rule Modal */}
      {showAddRule && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <form onSubmit={handleAddRule} className="bg-themeCard border border-themeBorder rounded-2xl w-full max-w-lg p-6 shadow-2xl animate-fade-in text-themeText space-y-4">
            <h3 className="text-lg font-serif font-bold">{editingItem ? 'Chỉnh sửa Luật phong cách' : 'Thêm Luật phong cách mới'}</h3>
            
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <label className="text-[10px] uppercase font-bold text-themeMuted block mb-1">Mã luật phong cách (ID duy nhất)</label>
                <input
                  type="text"
                  required
                  disabled={!!editingItem}
                  value={rId}
                  onChange={(e) => setRId(e.target.value)}
                  className="w-full rounded-xl bg-themeBg border border-themeBorder px-3 py-2 disabled:opacity-50"
                  placeholder="Ví dụ: rule_polite_pronoun"
                />
              </div>

              <div>
                <label className="text-[10px] uppercase font-bold text-themeMuted block mb-1">Phân loại / Nhãn</label>
                <input
                  type="text"
                  required
                  value={rCategory}
                  onChange={(e) => setRCategory(e.target.value)}
                  className="w-full rounded-xl bg-themeBg border border-themeBorder px-3 py-2"
                  placeholder="Ví dụ: Đại từ nhân xưng"
                />
              </div>

              <div className="col-span-2">
                <label className="text-[10px] uppercase font-bold text-themeMuted block mb-1">Mô tả luật phong cách</label>
                <input
                  type="text"
                  required
                  value={rDesc}
                  onChange={(e) => setRDesc(e.target.value)}
                  className="w-full rounded-xl bg-themeBg border border-themeBorder px-3 py-2"
                  placeholder="Ví dụ: Dùng kính ngữ và đại từ trang trọng khi nhân vật trò chuyện với cổ đông."
                />
              </div>

              <div>
                <label className="text-[10px] uppercase font-bold text-themeMuted block mb-1">Ví dụ cần tránh (Trước)</label>
                <textarea
                  value={rBefore}
                  onChange={(e) => setRBefore(e.target.value)}
                  className="w-full rounded-xl bg-themeBg border border-themeBorder px-3 py-2 resize-none h-16"
                  placeholder="Ví dụ: Tao gửi cho tụi mày bản báo cáo"
                />
              </div>

              <div>
                <label className="text-[10px] uppercase font-bold text-themeMuted block mb-1">Ví dụ khuyên dùng (Sau)</label>
                <textarea
                  value={rAfter}
                  onChange={(e) => setRAfter(e.target.value)}
                  className="w-full rounded-xl bg-themeBg border border-themeBorder px-3 py-2 resize-none h-16"
                  placeholder="Ví dụ: Kính gửi Quý Cổ đông bản báo cáo tài chính"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button type="button" onClick={resetStyleRuleForm} className="px-4 py-1.5 text-xs">Hủy</button>
              <button type="submit" className="px-4 py-1.5 bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-950 rounded-lg text-xs font-semibold">{editingItem ? 'Lưu thay đổi' : 'Thêm mới'}</button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}
