'use client'

import React, { useEffect, useMemo, useRef, useState } from 'react'
import {
  ArrowLeftRight,
  Bold,
  Download,
  Italic,
  PanelLeft,
  PanelRight,
  RotateCcw,
  RotateCw,
  Underline
} from 'lucide-react'
import {
  approveTranslation,
  exportChapter,
  getChapter,
  runTranslate,
  saveChapter
} from '@/app/api-client'

type WorkflowStep = 'read' | 'edit' | 'review' | 'approve'

interface CenterPanelProps {
  projectId: string
  activeFile: string
  sourceMode?: 'text' | 'visual'
  onSourceModeChange?: (mode: 'text' | 'visual') => void
  selectedBlock?: number
  onBlockSelect?: (idx: number) => void
  showLeftSidebar?: boolean
  showRightPanel?: boolean
  onToggleLeft?: () => void
  onToggleRight?: () => void
  currentStep: WorkflowStep
  onStepChange: (step: WorkflowStep) => void
}

const defaultOriginalText = `Dear Shareholders,

We are pleased to present the annual performance review for the fiscal year. Over the past year, our team has focused on optimizing our core services, expanding global market outreach, and improving overall operational efficiency.

Our software integration processes have achieved significant milestones, particularly in deploying the new orchestration layers and securing backend APIs against unauthorized requests.

We remain committed to delivering sustainable growth, fostering cross-border collaboration, and enhancing user experiences across all platforms.`

const defaultTranslationText = `Kinh gui cac Co dong,

Chung toi rat vui mung duoc trinh bay bao cao danh gia ket qua hoat dong thuong nien cho nam tai chinh vua qua. Trong nam qua, doi ngu cua chung toi da tap trung vao viec toi uu hoa cac dich vu cot loi, mo rong pham vi tiep can thi truong toan cau va nang cao hieu qua hoat dong tong the.

Chung toi van cam ket mang lai su tang truong ben vung, thuc day hop tac xuyen bien gioi va nang cao trai nghiem nguoi dung tren tat ca cac nen tang.`

const languages = [
  ['ja', 'Japanese'],
  ['vi', 'Vietnamese'],
  ['en', 'English'],
  ['zh', 'Chinese'],
  ['ko', 'Korean'],
  ['fr', 'French'],
  ['de', 'German'],
  ['es', 'Spanish']
] as const

const stepMeta: Record<WorkflowStep, { label: string; action: string }> = {
  read: { label: 'Read', action: 'Review the source and confirm direction.' },
  edit: { label: 'Edit', action: 'Refine the translation in the editor.' },
  review: { label: 'Review', action: 'Check terminology, tone, and structure.' },
  approve: { label: 'Approve', action: 'Approve the finished chapter.' }
}

export default function CenterPanel({
  projectId,
  activeFile,
  showLeftSidebar = true,
  showRightPanel = true,
  onToggleLeft,
  onToggleRight,
  currentStep,
  onStepChange
}: CenterPanelProps) {
  const [original, setOriginal] = useState(defaultOriginalText)
  const [translation, setTranslation] = useState(defaultTranslationText)
  const [sourceLang, setSourceLang] = useState('ja')
  const [targetLang, setTargetLang] = useState('vi')
  const [isTranslating, setIsTranslating] = useState(false)
  const [saveState, setSaveState] = useState<'saved' | 'saving'>('saved')
  const editorRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let active = true
    async function load() {
      if (!projectId || !activeFile) return
      try {
        const data = await getChapter(projectId, activeFile)
        if (!active) return
        const sourceText = data.draft || defaultOriginalText
        const targetText = data.approved || data.draft || defaultTranslationText
        setOriginal(sourceText)
        setTranslation(targetText)
        if (editorRef.current) {
          editorRef.current.innerHTML = targetText.replace(/\n/g, '<br>')
        }
      } catch (err) {
        console.error('Failed to load chapter content:', err)
      }
    }
    load()
    return () => {
      active = false
    }
  }, [projectId, activeFile])

  useEffect(() => {
    if (!projectId || !activeFile) return
    setSaveState('saving')
    const timer = setTimeout(async () => {
      try {
        await saveChapter(projectId, activeFile, { draft: translation })
      } catch (err) {
        console.error('Failed to auto-save:', err)
      } finally {
        setSaveState('saved')
      }
    }, 1200)
    return () => clearTimeout(timer)
  }, [translation, projectId, activeFile])

  const wordCount = useMemo(() => {
    return translation.replace(/<[^>]*>/g, '').trim().split(/\s+/).filter(Boolean).length
  }, [translation])

  const handleAiTranslate = async () => {
    if (!original.trim()) {
      alert('Add source text before running AI draft.')
      return
    }
    setIsTranslating(true)
    try {
      const res = await runTranslate(projectId, activeFile, original, sourceLang, targetLang)
      if (res?.draft) {
        setTranslation(res.draft)
        if (editorRef.current) editorRef.current.innerHTML = res.draft.replace(/\n/g, '<br>')
        onStepChange('edit')
      }
    } catch (err) {
      console.error('Failed to run AI translation:', err)
    } finally {
      setIsTranslating(false)
    }
  }

  const handleApproveTranslation = async () => {
    try {
      const confirmed = confirm('Approve this chapter and sync accepted changes to project memory?')
      if (!confirmed) return
      await approveTranslation(projectId, 'current_session', translation, [])
      onStepChange('approve')
      alert('Chapter approved.')
    } catch (err) {
      console.error('Failed to approve translation:', err)
      alert('Could not approve this chapter.')
    }
  }

  const handleInput = () => {
    if (editorRef.current) setTranslation(editorRef.current.innerHTML)
  }

  const applyFormatting = (formatType: 'bold' | 'italic' | 'underline' | 'undo' | 'redo') => {
    if (!editorRef.current) return
    editorRef.current.focus()
    document.execCommand(formatType === 'underline' ? 'underline' : formatType, false)
    handleInput()
  }

  const handleSwapLanguages = () => {
    setSourceLang(targetLang)
    setTargetLang(sourceLang)
  }

  const handleExport = async () => {
    try {
      await exportChapter(projectId, activeFile)
    } catch (err) {
      console.error('Export failed:', err)
    }
  }

  return (
    <main className="flex-1 flex flex-col h-full bg-themeBg overflow-hidden">
      <div className="h-14 px-5 border-b border-themeBorder bg-themeBg flex items-center justify-between">
        <div className="flex items-center gap-3 min-w-0">
          {!showLeftSidebar && onToggleLeft && (
            <button onClick={onToggleLeft} className="p-1.5 rounded-md text-themeMuted hover:text-themeText hover:bg-themeCard" title="Show documents">
              <PanelLeft size={16} />
            </button>
          )}
          <div className="min-w-0">
            <h1 className="text-sm font-semibold text-themeText truncate">{activeFile}</h1>
            <p className="text-xs text-themeMuted truncate">{stepMeta[currentStep].action}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {(['read', 'edit', 'review', 'approve'] as WorkflowStep[]).map(step => (
            <button
              key={step}
              onClick={() => onStepChange(step)}
              className={`px-2.5 py-1.5 rounded-md text-xs font-medium ${
                currentStep === step
                  ? 'bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-950'
                  : 'text-themeMuted hover:text-themeText hover:bg-themeCard'
              }`}
            >
              {stepMeta[step].label}
            </button>
          ))}
          {!showRightPanel && onToggleRight && (
            <button onClick={onToggleRight} className="p-1.5 rounded-md text-themeMuted hover:text-themeText hover:bg-themeCard" title="Show context">
              <PanelRight size={16} />
            </button>
          )}
        </div>
      </div>

      <section className="flex-1 min-h-0 px-5 py-4">
        <div className="h-full grid grid-cols-[minmax(280px,0.9fr)_minmax(420px,1.4fr)] gap-4">
          <aside className="min-h-0 rounded-lg border border-themeBorder bg-themeCard/45 flex flex-col overflow-hidden">
            <div className="h-12 px-4 border-b border-themeBorder flex items-center justify-between">
              <select value={sourceLang} onChange={(e) => setSourceLang(e.target.value)} className="bg-transparent border-0 text-xs font-medium text-themeMuted focus:ring-0">
                {languages.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
              <button onClick={handleSwapLanguages} className="p-1.5 rounded-md text-themeMuted hover:text-themeText hover:bg-themeBg" title="Swap languages">
                <ArrowLeftRight size={14} />
              </button>
            </div>
            <textarea
              value={original}
              onChange={(e) => setOriginal(e.target.value)}
              className="flex-1 min-h-0 resize-none bg-transparent border-0 p-5 font-serif text-[15px] leading-8 text-themeText/80 focus:ring-0 scrollbar-thin"
              placeholder="Source text"
            />
          </aside>

          <article className="min-h-0 rounded-lg border border-themeBorder bg-white dark:bg-slate-950 flex flex-col overflow-hidden shadow-sm">
            <div className="h-12 px-4 border-b border-themeBorder flex items-center justify-between">
              <select value={targetLang} onChange={(e) => setTargetLang(e.target.value)} className="bg-transparent border-0 text-xs font-medium text-themeMuted focus:ring-0">
                {languages.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
              <div className="flex items-center gap-2">
                <span className="text-xs text-themeMuted">{saveState === 'saving' ? 'Saving' : 'Saved'} · {wordCount} words</span>
                <button onClick={handleAiTranslate} disabled={isTranslating} className="px-3 py-1.5 rounded-md text-xs font-medium border border-themeBorder text-themeText hover:bg-themeCard disabled:opacity-50">
                  {isTranslating ? 'Drafting' : 'AI draft'}
                </button>
                <button onClick={handleApproveTranslation} className="px-3 py-1.5 rounded-md text-xs font-medium bg-slate-900 text-white hover:bg-slate-700 dark:bg-slate-100 dark:text-slate-950 dark:hover:bg-slate-300">
                  Approve
                </button>
              </div>
            </div>

            <div
              ref={editorRef}
              contentEditable
              suppressContentEditableWarning
              onInput={handleInput}
              className="flex-1 min-h-0 p-8 lg:p-10 font-serif text-[16px] leading-8 text-themeText outline-none overflow-y-auto scrollbar-thin whitespace-pre-wrap"
            />
          </article>
        </div>
      </section>

      <div className="h-12 px-5 border-t border-themeBorder bg-themeBg flex items-center justify-center">
        <div className="flex items-center gap-1 rounded-lg border border-themeBorder bg-themeCard/70 px-2 py-1">
          <button onClick={() => applyFormatting('undo')} className="p-1.5 rounded-md text-themeMuted hover:text-themeText hover:bg-themeBg" title="Undo"><RotateCcw size={14} /></button>
          <button onClick={() => applyFormatting('redo')} className="p-1.5 rounded-md text-themeMuted hover:text-themeText hover:bg-themeBg" title="Redo"><RotateCw size={14} /></button>
          <div className="w-px h-4 bg-themeBorder mx-1" />
          <button onClick={() => applyFormatting('bold')} className="p-1.5 rounded-md text-themeMuted hover:text-themeText hover:bg-themeBg" title="Bold"><Bold size={14} /></button>
          <button onClick={() => applyFormatting('italic')} className="p-1.5 rounded-md text-themeMuted hover:text-themeText hover:bg-themeBg" title="Italic"><Italic size={14} /></button>
          <button onClick={() => applyFormatting('underline')} className="p-1.5 rounded-md text-themeMuted hover:text-themeText hover:bg-themeBg" title="Underline"><Underline size={14} /></button>
          <div className="w-px h-4 bg-themeBorder mx-1" />
          <button onClick={handleExport} className="p-1.5 rounded-md text-themeMuted hover:text-themeText hover:bg-themeBg" title="Export"><Download size={14} /></button>
        </div>
      </div>
    </main>
  )
}
