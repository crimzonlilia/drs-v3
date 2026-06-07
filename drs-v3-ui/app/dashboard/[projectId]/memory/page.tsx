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
  Bookmark
} from 'lucide-react'
import { useTheme } from '@/app/theme-provider'
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
      await addGlossaryTerm(projectId, {
        source_term: gSource.trim(),
        target_term: gTarget.trim(),
        source_lang: projectInfo?.source_lang || 'ja',
        target_lang: projectInfo?.target_lang || 'vi',
        context_note: gNote.trim() || undefined
      })
      setGSource('')
      setGTarget('')
      setGNote('')
      setShowAddGlossary(false)
      loadMemory()
    } catch (err) {
      alert(`Error adding term: ${err}`)
    }
  }

  const handleDeleteGlossary = async (term: string) => {
    if (!confirm(`Delete glossary term "${term}"?`)) return
    try {
      await deleteGlossaryTerm(
        projectId,
        projectInfo?.source_lang || 'ja',
        projectInfo?.target_lang || 'vi',
        term
      )
      loadMemory()
    } catch (err) {
      alert(`Error deleting term: ${err}`)
    }
  }

  // Handlers for Entities
  const handleAddEntity = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!eId.trim() || !eCanonical.trim() || !eSource.trim()) return
    try {
      await addEntity(projectId, {
        entity_id: eId.trim(),
        canonical_name: eCanonical.trim(),
        source_name: eSource.trim(),
        entity_type: eType,
        source_lang: projectInfo?.source_lang || 'ja',
        target_lang: projectInfo?.target_lang || 'vi',
        pronouns: ePronouns.trim() || undefined,
        notes: eNotes.trim() || undefined
      })
      setEId('')
      setECanonical('')
      setESource('')
      setEPronouns('')
      setENotes('')
      setShowAddEntity(false)
      loadMemory()
    } catch (err) {
      alert(`Error adding entity: ${err}`)
    }
  }

  const handleDeleteEntity = async (entityId: string) => {
    if (!confirm(`Delete entity "${entityId}"?`)) return
    try {
      await deleteEntity(projectId, entityId)
      loadMemory()
    } catch (err) {
      alert(`Error deleting entity: ${err}`)
    }
  }

  // Handlers for Style Rules
  const handleAddRule = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!rId.trim() || !rCategory.trim() || !rDesc.trim()) return
    try {
      await addStyleRule(projectId, {
        rule_id: rId.trim(),
        category: rCategory.trim(),
        description: rDesc.trim(),
        example_before: rBefore.trim() || undefined,
        example_after: rAfter.trim() || undefined,
        source_lang: projectInfo?.source_lang || 'ja',
        target_lang: projectInfo?.target_lang || 'vi'
      })
      setRId('')
      setRCategory('')
      setRDesc('')
      setRBefore('')
      setRAfter('')
      setShowAddRule(false)
      loadMemory()
    } catch (err) {
      alert(`Error adding style rule: ${err}`)
    }
  }

  const handleDeleteRule = async (ruleId: string) => {
    if (!confirm(`Delete style rule "${ruleId}"?`)) return
    try {
      await deleteStyleRule(projectId, ruleId)
      loadMemory()
    } catch (err) {
      alert(`Error deleting style rule: ${err}`)
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
              <span className="text-white font-serif font-bold text-base">d</span>
            </div>
            <span className="font-serif font-bold text-2xl tracking-wide text-white">drs.v3</span>
          </div>

          <nav className="space-y-4">
            <Link
              href={`/dashboard/${projectId}`}
              className="py-2 px-3 flex items-center gap-3 hover:text-white transition-colors"
            >
              <ArrowLeft size={16} />
              <span>Back to Documents</span>
            </Link>

            <div className="h-px bg-slate-800 my-4" />

            <button
              onClick={() => setActiveTab('glossary')}
              className={`w-full py-2 px-3 flex items-center gap-3 rounded-lg text-left transition-colors ${
                activeTab === 'glossary' ? 'bg-slate-900 text-white dark:bg-slate-800' : 'hover:text-white'
              }`}
            >
              <Bookmark size={16} />
              <span>Glossary ({glossary.length})</span>
            </button>

            <button
              onClick={() => setActiveTab('entities')}
              className={`w-full py-2 px-3 flex items-center gap-3 rounded-lg text-left transition-colors ${
                activeTab === 'entities' ? 'bg-slate-900 text-white dark:bg-slate-800' : 'hover:text-white'
              }`}
            >
              <Users size={16} />
              <span>Entities ({entities.length})</span>
            </button>

            <button
              onClick={() => setActiveTab('style_rules')}
              className={`w-full py-2 px-3 flex items-center gap-3 rounded-lg text-left transition-colors ${
                activeTab === 'style_rules' ? 'bg-slate-900 text-white dark:bg-slate-800' : 'hover:text-white'
              }`}
            >
              <Sparkles size={16} />
              <span>Style Rules ({styleRules.length})</span>
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
                <span>Dark Mode</span>
              </>
            ) : (
              <>
                <Sun size={18} className="text-accent-cyan" />
                <span>Light Mode</span>
              </>
            )}
          </button>
          <div className="text-[10px] text-slate-600 font-mono pt-4 border-t border-slate-900">v3.0.4</div>
        </div>
      </aside>

      {/* Main panel */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <header className="px-8 py-6 border-b border-themeBorder bg-white/40 dark:bg-slate-950/20 backdrop-blur-md flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-serif font-bold text-slate-950 dark:text-slate-50">
              {projectName} &bull; Project Memory
            </h1>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-800 dark:bg-purple-950/40 dark:text-purple-300 uppercase tracking-wider">
              Shared Cache
            </span>
          </div>

          <div className="flex items-center gap-4">
            <div className="relative">
              <Search size={16} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder={`Search ${activeTab}...`}
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
                <Plus size={14} /> Add term
              </button>
            )}

            {activeTab === 'entities' && (
              <button
                onClick={() => setShowAddEntity(true)}
                className="px-4 py-1.5 bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-950 rounded-full text-xs font-semibold flex items-center gap-1.5 hover:opacity-90 transition-opacity"
              >
                <Plus size={14} /> Add entity
              </button>
            )}

            {activeTab === 'style_rules' && (
              <button
                onClick={() => setShowAddRule(true)}
                className="px-4 py-1.5 bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-950 rounded-full text-xs font-semibold flex items-center gap-1.5 hover:opacity-90 transition-opacity"
              >
                <Plus size={14} /> Add rule
              </button>
            )}
          </div>
        </header>

        <div className="flex-1 overflow-y-auto p-8 max-w-6xl w-full mx-auto scrollbar-thin">
          {loading ? (
            <div className="text-sm text-themeMuted">Loading workspace memory...</div>
          ) : (
            <>
              {/* Tab: Glossary */}
              {activeTab === 'glossary' && (
                <div className="space-y-4">
                  <div className="p-4 rounded-xl bg-themeCard/30 border border-themeBorder flex items-start gap-3 text-xs leading-relaxed text-themeMuted">
                    <BookOpen size={16} className="text-purple-500 shrink-0 mt-0.5" />
                    <div>
                      <strong>Glossary Memory:</strong> Terminology specified here will be automatically forced by the translation refiner during candidates generation and verified by the checksuite.
                    </div>
                  </div>

                  {filteredGlossary.length === 0 ? (
                    <div className="py-12 text-center text-xs text-themeMuted">No glossary terms matched.</div>
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

                          <button
                            onClick={() => handleDeleteGlossary(entry.source_term)}
                            className="p-1.5 rounded-lg text-themeMuted hover:text-red-500 hover:bg-red-500/10 transition-colors"
                            title="Delete term"
                          >
                            <Trash2 size={14} />
                          </button>
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
                      <strong>Entity Memory:</strong> Dictates honorifics, pronouns, gender representation, and specific proper names for characters, places, and organizations.
                    </div>
                  </div>

                  {filteredEntities.length === 0 ? (
                    <div className="py-12 text-center text-xs text-themeMuted">No entities matched.</div>
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
                                ID: <span className="font-mono">{ent.entity_id}</span> &bull; Original: {ent.source_name}
                              </div>
                            </div>
                            {ent.pronouns && (
                              <div className="text-[11px] font-mono text-purple-600 dark:text-purple-400 bg-purple-500/10 inline-block px-1.5 py-0.5 rounded">
                                Pronouns: {ent.pronouns}
                              </div>
                            )}
                            {ent.notes && (
                              <p className="text-[11px] text-themeMuted leading-relaxed bg-themeBg/50 p-2 rounded">
                                {ent.notes}
                              </p>
                            )}
                          </div>

                          <button
                            onClick={() => handleDeleteEntity(ent.entity_id)}
                            className="p-1.5 rounded-lg text-themeMuted hover:text-red-500 hover:bg-red-500/10 transition-colors"
                            title="Delete entity"
                          >
                            <Trash2 size={14} />
                          </button>
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
                      <strong>Style Rules Memory:</strong> Enforces grammatical rules, tone constraints, punctuation guidelines, and bans certain words or constructions from final publications.
                    </div>
                  </div>

                  {filteredStyleRules.length === 0 ? (
                    <div className="py-12 text-center text-xs text-themeMuted">No style rules matched.</div>
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
                                  <div className="text-[9px] uppercase font-bold text-red-500 mb-1">Before / Avoid</div>
                                  <div className="text-red-700 dark:text-red-400">{rule.example_before || '—'}</div>
                                </div>
                                <div>
                                  <div className="text-[9px] uppercase font-bold text-emerald-500 mb-1">After / Preferred</div>
                                  <div className="text-emerald-700 dark:text-emerald-400">{rule.example_after || '—'}</div>
                                </div>
                              </div>
                            )}
                          </div>

                          <button
                            onClick={() => handleDeleteRule(rule.rule_id)}
                            className="p-1.5 rounded-lg text-themeMuted hover:text-red-500 hover:bg-red-500/10 transition-colors shrink-0 ml-4"
                            title="Delete rule"
                          >
                            <Trash2 size={14} />
                          </button>
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
            <h3 className="text-lg font-serif font-bold">Add Glossary Term</h3>
            
            <div className="space-y-3">
              <div>
                <label className="text-[10px] uppercase font-bold text-themeMuted block mb-1">Source Term ({projectInfo?.source_lang || 'ja'})</label>
                <input
                  type="text"
                  required
                  value={gSource}
                  onChange={(e) => setGSource(e.target.value)}
                  className="w-full rounded-xl bg-themeBg border border-themeBorder px-3 py-2 text-xs"
                  placeholder="e.g. 仲間"
                />
              </div>

              <div>
                <label className="text-[10px] uppercase font-bold text-themeMuted block mb-1">Approved Translation ({projectInfo?.target_lang || 'vi'})</label>
                <input
                  type="text"
                  required
                  value={gTarget}
                  onChange={(e) => setGTarget(e.target.value)}
                  className="w-full rounded-xl bg-themeBg border border-themeBorder px-3 py-2 text-xs"
                  placeholder="e.g. Đồng đội"
                />
              </div>

              <div>
                <label className="text-[10px] uppercase font-bold text-themeMuted block mb-1">Context Note (Optional)</label>
                <textarea
                  value={gNote}
                  onChange={(e) => setGNote(e.target.value)}
                  className="w-full rounded-xl bg-themeBg border border-themeBorder px-3 py-2 text-xs resize-none h-16"
                  placeholder="e.g. Chỉ sử dụng trong bối cảnh thân mật giữa các nhân vật chính."
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button type="button" onClick={() => setShowAddGlossary(false)} className="px-4 py-1.5 text-xs">Cancel</button>
              <button type="submit" className="px-4 py-1.5 bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-950 rounded-lg text-xs font-semibold">Add</button>
            </div>
          </form>
        </div>
      )}

      {/* Add Entity Modal */}
      {showAddEntity && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <form onSubmit={handleAddEntity} className="bg-themeCard border border-themeBorder rounded-2xl w-full max-w-md p-6 shadow-2xl animate-fade-in text-themeText space-y-4">
            <h3 className="text-lg font-serif font-bold">Add Project Entity</h3>
            
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="col-span-2">
                <label className="text-[10px] uppercase font-bold text-themeMuted block mb-1">Entity ID (Unique)</label>
                <input
                  type="text"
                  required
                  value={eId}
                  onChange={(e) => setEId(e.target.value)}
                  className="w-full rounded-xl bg-themeBg border border-themeBorder px-3 py-2"
                  placeholder="e.g. char_lilia"
                />
              </div>

              <div>
                <label className="text-[10px] uppercase font-bold text-themeMuted block mb-1">Canonical Name</label>
                <input
                  type="text"
                  required
                  value={eCanonical}
                  onChange={(e) => setECanonical(e.target.value)}
                  className="w-full rounded-xl bg-themeBg border border-themeBorder px-3 py-2"
                  placeholder="e.g. Lilia"
                />
              </div>

              <div>
                <label className="text-[10px] uppercase font-bold text-themeMuted block mb-1">Original Name</label>
                <input
                  type="text"
                  required
                  value={eSource}
                  onChange={(e) => setESource(e.target.value)}
                  className="w-full rounded-xl bg-themeBg border border-themeBorder px-3 py-2"
                  placeholder="e.g. リリア"
                />
              </div>

              <div>
                <label className="text-[10px] uppercase font-bold text-themeMuted block mb-1">Type</label>
                <select
                  value={eType}
                  onChange={(e) => setEType(e.target.value)}
                  className="w-full rounded-xl bg-themeBg border border-themeBorder px-3 py-2"
                >
                  <option value="person">Person (Nhân vật)</option>
                  <option value="location">Location (Địa danh)</option>
                  <option value="organization">Organization (Tổ chức)</option>
                  <option value="item">Object/Item (Vật phẩm)</option>
                </select>
              </div>

              <div>
                <label className="text-[10px] uppercase font-bold text-themeMuted block mb-1">Pronouns (Optional)</label>
                <input
                  type="text"
                  value={ePronouns}
                  onChange={(e) => setEPronouns(e.target.value)}
                  className="w-full rounded-xl bg-themeBg border border-themeBorder px-3 py-2"
                  placeholder="e.g. cô ấy / she"
                />
              </div>

              <div className="col-span-2">
                <label className="text-[10px] uppercase font-bold text-themeMuted block mb-1">Entity Notes</label>
                <textarea
                  value={eNotes}
                  onChange={(e) => setENotes(e.target.value)}
                  className="w-full rounded-xl bg-themeBg border border-themeBorder px-3 py-2 resize-none h-16"
                  placeholder="e.g. Công chúa vùng Crimzon, tính cách hướng ngoại."
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button type="button" onClick={() => setShowAddEntity(false)} className="px-4 py-1.5 text-xs">Cancel</button>
              <button type="submit" className="px-4 py-1.5 bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-950 rounded-lg text-xs font-semibold">Add</button>
            </div>
          </form>
        </div>
      )}

      {/* Add Style Rule Modal */}
      {showAddRule && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <form onSubmit={handleAddRule} className="bg-themeCard border border-themeBorder rounded-2xl w-full max-w-lg p-6 shadow-2xl animate-fade-in text-themeText space-y-4">
            <h3 className="text-lg font-serif font-bold">Add Style Rule</h3>
            
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <label className="text-[10px] uppercase font-bold text-themeMuted block mb-1">Rule ID (Unique)</label>
                <input
                  type="text"
                  required
                  value={rId}
                  onChange={(e) => setRId(e.target.value)}
                  className="w-full rounded-xl bg-themeBg border border-themeBorder px-3 py-2"
                  placeholder="e.g. rule_polite_pronoun"
                />
              </div>

              <div>
                <label className="text-[10px] uppercase font-bold text-themeMuted block mb-1">Category / Label</label>
                <input
                  type="text"
                  required
                  value={rCategory}
                  onChange={(e) => setRCategory(e.target.value)}
                  className="w-full rounded-xl bg-themeBg border border-themeBorder px-3 py-2"
                  placeholder="e.g. Pronouns"
                />
              </div>

              <div className="col-span-2">
                <label className="text-[10px] uppercase font-bold text-themeMuted block mb-1">Rule Description</label>
                <input
                  type="text"
                  required
                  value={rDesc}
                  onChange={(e) => setRDesc(e.target.value)}
                  className="w-full rounded-xl bg-themeBg border border-themeBorder px-3 py-2"
                  placeholder="e.g. Dùng kính ngữ và đại từ trang trọng khi nhân vật trò chuyện với cổ đông."
                />
              </div>

              <div>
                <label className="text-[10px] uppercase font-bold text-themeMuted block mb-1">Avoid Example (Before)</label>
                <textarea
                  value={rBefore}
                  onChange={(e) => setRBefore(e.target.value)}
                  className="w-full rounded-xl bg-themeBg border border-themeBorder px-3 py-2 resize-none h-16"
                  placeholder="e.g. Tao gửi cho tụi mày bản báo cáo"
                />
              </div>

              <div>
                <label className="text-[10px] uppercase font-bold text-themeMuted block mb-1">Preferred Example (After)</label>
                <textarea
                  value={rAfter}
                  onChange={(e) => setRAfter(e.target.value)}
                  className="w-full rounded-xl bg-themeBg border border-themeBorder px-3 py-2 resize-none h-16"
                  placeholder="e.g. Kính gửi Quý Cổ đông bản báo cáo tài chính"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button type="button" onClick={() => setShowAddRule(false)} className="px-4 py-1.5 text-xs">Cancel</button>
              <button type="submit" className="px-4 py-1.5 bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-950 rounded-lg text-xs font-semibold">Add</button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}
