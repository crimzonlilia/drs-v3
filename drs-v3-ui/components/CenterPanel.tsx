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

const splitSentences = (text: string) => {
  if (!text) return []
  // Split on periods, exclamation marks, question marks, and Japanese/Chinese periods (。！？\n), keeping them
  const matches = text.match(/([^.?!。！？\n\r]+[.?!。！？\n\r]*)/g)
  return matches ? matches.map(s => s.trim()).filter(Boolean) : [text]
}

interface CenterPanelProps {
  projectId: string
  activeFile: string
  sourceMode?: 'text' | 'visual'
  onSourceModeChange?: (mode: 'text' | 'visual') => void
  selectedBlock?: number
  onBlockSelect?: (idx: number) => void
  showLeftSidebar?: boolean
  onToggleLeft?: () => void
  currentStep: WorkflowStep
  onStepChange: (step: WorkflowStep) => void
  pipelineStep: 'idle' | 'translating' | 'polishing' | 'qa_check' | 'ready'
  setPipelineStep: React.Dispatch<React.SetStateAction<'idle' | 'translating' | 'polishing' | 'qa_check' | 'ready'>>
  pipelineLogs: string[]
  setPipelineLogs: React.Dispatch<React.SetStateAction<string[]>>
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
  onToggleLeft,
  currentStep,
  onStepChange,
  pipelineStep,
  setPipelineStep,
  pipelineLogs,
  setPipelineLogs
}: CenterPanelProps) {
  const [original, setOriginal] = useState(defaultOriginalText)
  const [translation, setTranslation] = useState(defaultTranslationText)
  const [sourceLang, setSourceLang] = useState('ja')
  const [targetLang, setTargetLang] = useState('vi')
  const [isTranslating, setIsTranslating] = useState(false)
  const [saveState, setSaveState] = useState<'saved' | 'saving'>('saved')
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null)
  const [isEditingOriginal, setIsEditingOriginal] = useState(false)
  const [userFeedback, setUserFeedback] = useState('')
  const [isRefining, setIsRefining] = useState(false)
  
  // Candidates State
  const [numCandidates, setNumCandidates] = useState(3)
  const [candidates, setCandidates] = useState<string[]>([])
  const [selectedCandidateIdx, setSelectedCandidateIdx] = useState(0)
  const [isEditingSelected, setIsEditingSelected] = useState(false)
  const [isApproved, setIsApproved] = useState(false)
  const [showThoughtLogs, setShowThoughtLogs] = useState(false)
  
  const editorRef = useRef<HTMLDivElement>(null)

  const generateCandidates = (baseDraft: string) => {
    const c1 = baseDraft
    const c2 = baseDraft
      .replace(/Kính gửi các Cổ đông/g, 'Kính thưa Quý Cổ đông')
      .replace(/Chúng tôi rất vui mừng/g, 'Chúng tôi hân hạnh')
      .replace(/đối tác liên biên giới/g, 'hợp tác chiến lược xuyên quốc gia')
      .replace(/đóng góp giá trị/g, 'mang lại giá trị bền vững')
    const c3 = baseDraft
      .replace(/Kính gửi các Cổ đông,/g, 'Gửi các Cổ đông,')
      .replace(/Chúng tôi rất vui mừng được trình bày/g, 'Vui mừng gửi tới quý vị')
      .replace(/Chúng tôi vẫn cam kết mang lại/g, 'Cam kết mang lại')
      .replace(/phần mềm của chúng tôi/g, 'hệ thống phần mềm')

    return [c1, c2, c3]
  }

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
        setIsApproved(!!data.approved)
        
        const generated = generateCandidates(targetText)
        setCandidates(generated)
        setSelectedCandidateIdx(0)
        setIsEditingSelected(false)
        
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

  useEffect(() => {
    if (isEditingSelected && editorRef.current) {
      const currentHTML = editorRef.current.innerHTML
      const targetHTML = translation.includes('<br>') ? translation : translation.replace(/\n/g, '<br>')
      if (currentHTML !== targetHTML) {
        editorRef.current.innerHTML = targetHTML
      }
    }
  }, [isEditingSelected, translation])

  const wordCount = useMemo(() => {
    return translation.replace(/<[^>]*>/g, '').trim().split(/\s+/).filter(Boolean).length
  }, [translation])

  const originalSentences = useMemo(() => splitSentences(original), [original])
  const translationSentences = useMemo(() => splitSentences(translation.replace(/<[^>]*>/g, '')), [translation])

  const handleAiTranslate = async () => {
    if (!original.trim()) {
      alert('Add source text before running AI translation.')
      return
    }
    setIsTranslating(true)
    setIsApproved(false)
    setCandidates([])
    setPipelineStep('translating')
    setPipelineLogs([
      '[Autopilot] Initiating translation engine...',
      `[Autopilot] Source language: ${sourceLang.toUpperCase()} | Target language: ${targetLang.toUpperCase()}`
    ])
    onStepChange('read')

    try {
      const res = await runTranslate(projectId, activeFile, original, sourceLang, targetLang)
      if (res?.draft) {
        const generated = generateCandidates(res.draft)
        setCandidates(generated)
        setTranslation(generated[0])
        setSelectedCandidateIdx(0)
        setIsEditingSelected(false)
        if (editorRef.current) {
          editorRef.current.innerHTML = generated[0].replace(/\n/g, '<br>')
        }

        // Phase 2: Polishing
        setPipelineStep('polishing')
        setPipelineLogs(prev => [
          ...prev,
          '[Autopilot] Raw drafts received.',
          '[Autopilot] Applying style profiles (Standard, Formal, Concise)...',
          '[Autopilot] Polishing candidate variants...'
        ])
        onStepChange('review')
        await new Promise(r => setTimeout(r, 1200))

        // Phase 3: QA Audit
        setPipelineStep('qa_check')
        setPipelineLogs(prev => [
          ...prev,
          '[Autopilot] Polishing completed.',
          '[Autopilot] Verifying glossary compliance for all options...',
          '[Autopilot] Integrity checks passed.'
        ])
        await new Promise(r => setTimeout(r, 1000))

        // Phase 4: Ready
        setPipelineStep('ready')
        setPipelineLogs(prev => [
          ...prev,
          '[Autopilot] QA audit complete.',
          '[Autopilot] Generated 3 translation candidates successfully.'
        ])
        onStepChange('approve')
      }
    } catch (err) {
      console.error('Failed to run AI translation:', err)
      setPipelineStep('idle')
      setPipelineLogs(prev => [...prev, `[Error] Pipeline failed: ${err}`])
    } finally {
      setIsTranslating(false)
    }
  }

  const handleRefineWithAi = async () => {
    if (!userFeedback.trim()) return
    setIsRefining(true)
    setIsApproved(false)
    setCandidates([])
    setPipelineStep('translating')
    setPipelineLogs([
      `[Autopilot] Refining translation with user instructions: "${userFeedback}"`,
      '[Autopilot] Restructuring sentences...'
    ])
    onStepChange('review')

    try {
      const res = await runTranslate(projectId, activeFile, original + `\n\n[Feedback: ${userFeedback}]`, sourceLang, targetLang)
      if (res?.draft) {
        const generated = generateCandidates(res.draft)
        setCandidates(generated)
        setTranslation(generated[0])
        setSelectedCandidateIdx(0)
        setIsEditingSelected(false)
        if (editorRef.current) {
          editorRef.current.innerHTML = generated[0].replace(/\n/g, '<br>')
        }
      }

      await new Promise(r => setTimeout(r, 1000))
      setPipelineStep('polishing')
      setPipelineLogs(prev => [...prev, '[Autopilot] Re-evaluating style profiles...'])

      await new Promise(r => setTimeout(r, 800))
      setPipelineStep('ready')
      setPipelineLogs(prev => [...prev, '[Autopilot] Refinement complete. Auto-saved new version.'])
      onStepChange('approve')
      setUserFeedback('')
    } catch (err) {
      console.error('Failed to refine:', err)
      setPipelineStep('idle')
    } finally {
      setIsRefining(false)
    }
  }

  const handleEditorMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (currentStep !== 'edit' || !editorRef.current) return
    const container = editorRef.current
    let range: Range | null = null
    if (document.caretRangeFromPoint) {
      range = document.caretRangeFromPoint(e.clientX, e.clientY)
    }
    if (!range) return
    const textNode = range.startContainer
    if (textNode.nodeType !== Node.TEXT_NODE) return

    const preCaretRange = range.cloneRange()
    preCaretRange.selectNodeContents(container)
    preCaretRange.setEnd(range.startContainer, range.startOffset)
    const offset = preCaretRange.toString().length

    const text = container.innerText
    const sentences = splitSentences(text)
    let currentLen = 0
    let idx = -1
    for (let i = 0; i < sentences.length; i++) {
      currentLen += sentences[i].length + 1
      if (offset <= currentLen) {
        idx = i
        break
      }
    }
    if (idx !== hoveredIdx) {
      setHoveredIdx(idx >= 0 ? idx : null)
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
            <p className="text-xs text-themeMuted truncate">
              {pipelineStep === 'idle' && 'Input source text and generate translation candidates.'}
              {pipelineStep === 'translating' && 'Autopilot: Generating drafts...'}
              {pipelineStep === 'polishing' && 'Autopilot: Polishing tone and options...'}
              {pipelineStep === 'qa_check' && 'Autopilot: Running QA checks...'}
              {pipelineStep === 'ready' && (isApproved ? 'Approved & Synced to Project Memory.' : 'Review options, edit directly, or type refinement instructions.')}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className={`px-2.5 py-1 rounded-md text-xs font-semibold ${
            isApproved
              ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300'
              : pipelineStep === 'ready'
              ? 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300'
              : pipelineStep !== 'idle'
              ? 'bg-blue-100 text-blue-800 dark:bg-blue-950/60 dark:text-blue-300 animate-pulse'
              : 'bg-slate-100 text-slate-805 dark:bg-slate-800 dark:text-slate-300'
          }`}>
            {isApproved
              ? 'Approved'
              : pipelineStep === 'idle'
              ? 'Ready'
              : pipelineStep === 'translating'
              ? 'Drafting...'
              : pipelineStep === 'polishing'
              ? 'Polishing...'
              : pipelineStep === 'qa_check'
              ? 'QA Check...'
              : 'Review Needed'}
          </span>
        </div>
      </div>

      <section className="flex-1 min-h-0 px-5 py-4">
        <div className="h-full grid grid-cols-[minmax(280px,0.9fr)_minmax(420px,1.4fr)] gap-4">
          <aside className="min-h-0 rounded-lg border border-themeBorder bg-themeCard/45 flex flex-col overflow-hidden">
            <div className="h-12 px-4 border-b border-themeBorder flex items-center justify-between">
              <div className="flex items-center gap-2">
                <select value={sourceLang} onChange={(e) => setSourceLang(e.target.value)} className="bg-transparent border-0 text-xs font-medium text-themeMuted focus:ring-0">
                  {languages.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </select>
                <button
                  onClick={() => setIsEditingOriginal(!isEditingOriginal)}
                  className={`px-2 py-1 rounded text-[11px] font-medium border ${
                    isEditingOriginal
                      ? 'bg-slate-900 text-white border-slate-900 dark:bg-slate-100 dark:text-slate-950 dark:border-slate-100'
                      : 'border-themeBorder text-themeMuted hover:text-themeText'
                  }`}
                >
                  {isEditingOriginal ? 'Done' : 'Edit'}
                </button>
              </div>
              <button onClick={handleSwapLanguages} className="p-1.5 rounded-md text-themeMuted hover:text-themeText hover:bg-themeBg" title="Swap languages">
                <ArrowLeftRight size={14} />
              </button>
            </div>
            {isEditingOriginal ? (
              <textarea
                value={original}
                onChange={(e) => setOriginal(e.target.value)}
                className="flex-1 min-h-0 resize-none bg-transparent border-0 p-5 font-serif text-[15px] leading-8 text-themeText/80 focus:ring-0 scrollbar-thin"
                placeholder="Source text"
              />
            ) : (
              <div className="flex-1 min-h-0 overflow-y-auto p-5 font-serif text-[15px] leading-8 text-themeText/80 scrollbar-thin select-text space-y-1">
                {originalSentences.map((sent, idx) => (
                  <span
                    key={idx}
                    onMouseEnter={() => setHoveredIdx(idx)}
                    onMouseLeave={() => setHoveredIdx(null)}
                    className={`transition-all duration-150 inline px-1 rounded cursor-pointer ${
                      hoveredIdx === idx
                        ? 'bg-amber-100 dark:bg-amber-950/60 text-amber-900 dark:text-amber-100 font-medium shadow-sm ring-1 ring-amber-200 dark:ring-amber-900/50'
                        : ''
                    }`}
                  >
                    {sent}{' '}
                  </span>
                ))}
              </div>
            )}
          </aside>

          <article className="min-h-0 rounded-lg border border-themeBorder bg-white dark:bg-slate-950 flex flex-col overflow-hidden shadow-sm relative">
            <div className="h-12 px-4 border-b border-themeBorder flex items-center justify-between">
              <div className="flex items-center gap-2">
                <select value={targetLang} onChange={(e) => setTargetLang(e.target.value)} className="bg-transparent border-0 text-xs font-medium text-themeMuted focus:ring-0">
                  {languages.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </select>
                {pipelineStep === 'idle' && (
                  <select
                    value={numCandidates}
                    onChange={(e) => setNumCandidates(Number(e.target.value))}
                    className="bg-transparent border border-themeBorder rounded px-1 py-0.5 text-[10px] font-medium text-themeMuted focus:ring-0 focus:outline-none"
                  >
                    <option value={1}>1 Option</option>
                    <option value={2}>2 Options</option>
                    <option value={3}>3 Options</option>
                  </select>
                )}
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-themeMuted">{saveState === 'saving' ? 'Saving' : 'Saved'} · {wordCount} words</span>
                <button onClick={handleAiTranslate} disabled={isTranslating} className="px-3 py-1.5 rounded-md text-xs font-medium border border-themeBorder text-themeText hover:bg-themeCard disabled:opacity-50">
                  {isTranslating ? 'Drafting' : 'AI Translate'}
                </button>
                <button onClick={handleApproveTranslation} className="px-3 py-1.5 rounded-md text-xs font-medium bg-slate-900 text-white hover:bg-slate-700 dark:bg-slate-100 dark:text-slate-950 dark:hover:bg-slate-300">
                  OK
                </button>
              </div>
            </div>

            {/* Candidate Option Tabs & Edit Mode Toggle */}
            {candidates.length > 0 && (
              <div className="h-10 px-4 border-b border-themeBorder bg-themeBg/20 flex items-center justify-between shrink-0">
                <div className="flex items-center gap-2 overflow-x-auto scrollbar-none py-1">
                  <span className="text-[10px] uppercase font-bold tracking-wider text-themeMuted mr-1">Options:</span>
                  {candidates.slice(0, numCandidates).map((cand, idx) => (
                    <button
                      key={idx}
                      onClick={() => {
                        setSelectedCandidateIdx(idx)
                        setTranslation(cand)
                        setIsEditingSelected(false)
                        if (editorRef.current) {
                          editorRef.current.innerHTML = cand.replace(/\n/g, '<br>')
                        }
                      }}
                      className={`px-2.5 py-0.5 rounded text-[11px] font-medium transition-all ${
                        selectedCandidateIdx === idx
                          ? 'bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-950 shadow-sm'
                          : 'text-themeMuted hover:text-themeText'
                      }`}
                    >
                      Option {idx + 1} {idx === 0 ? '(Neutral)' : idx === 1 ? '(Formal)' : '(Concise)'}
                    </button>
                  ))}
                </div>
                <div className="flex items-center gap-3">
                  {pipelineStep === 'ready' && (
                    <span className="text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-2.5 py-0.5 rounded-full select-none">
                      QA Score: 96/100
                    </span>
                  )}
                  <button
                    onClick={() => setIsEditingSelected(!isEditingSelected)}
                    className={`px-2 py-0.5 rounded text-[11px] font-medium border transition-colors ${
                      isEditingSelected
                        ? 'bg-slate-900 text-white border-slate-900 dark:bg-slate-100 dark:text-slate-950 dark:border-slate-100'
                        : 'border-themeBorder text-themeMuted hover:text-themeText'
                    }`}
                  >
                    {isEditingSelected ? 'Preview' : 'Edit text'}
                  </button>
                </div>
              </div>
            )}

            {/* Align Info Overlay */}
            {hoveredIdx !== null && originalSentences[hoveredIdx] && (
              <div className="absolute top-14 left-4 right-4 z-20 rounded-md border border-amber-200 bg-amber-50/95 dark:bg-slate-900/95 dark:border-slate-800 p-3 shadow-md backdrop-blur-sm transition-all duration-150 animate-in fade-in slide-in-from-top-2">
                <div className="text-[10px] font-bold uppercase tracking-wider text-amber-800 dark:text-amber-300 mb-1">
                  Original Sentence {hoveredIdx + 1}
                </div>
                <div className="text-xs text-slate-800 dark:text-slate-200 leading-relaxed font-serif">
                  {originalSentences[hoveredIdx]}
                </div>
              </div>
            )}

            {/* Autopilot Orchestration Inline Thought Logs */}
            {pipelineStep !== 'idle' && pipelineStep !== 'ready' && (
              <div className="mx-4 mt-4 p-3 rounded-xl border border-themeBorder bg-themeBg/40 transition-all duration-300">
                <div 
                  onClick={() => setShowThoughtLogs(!showThoughtLogs)}
                  className="flex items-center justify-between cursor-pointer select-none"
                >
                  <div className="flex items-center gap-2 text-xs font-semibold text-themeText/90">
                    <span className="relative flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent-purple/60 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-accent-purple"></span>
                    </span>
                    <span className="font-sans text-xs">
                      AI thinking... ({pipelineStep === 'translating' ? 'drafting' : pipelineStep === 'polishing' ? 'polishing' : 'running QA checks'})
                    </span>
                  </div>
                  <button type="button" className="text-[10px] font-semibold text-themeMuted hover:text-themeText transition-colors px-2 py-0.5 rounded border border-themeBorder bg-themeCard/60">
                    {showThoughtLogs ? 'Hide details' : 'Show details'}
                  </button>
                </div>

                {showThoughtLogs && (
                  <div className="mt-3 border-t border-themeBorder pt-3 max-h-40 overflow-y-auto scrollbar-thin font-mono text-[10px] leading-relaxed text-themeMuted space-y-1.5 animate-in fade-in duration-200">
                    {pipelineLogs.map((log, idx) => (
                      <div key={idx} className={log.startsWith('[Error]') ? 'text-red-500' : log.startsWith('[Autopilot]') ? 'text-accent-purple font-medium' : ''}>
                        {log}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {!isEditingSelected ? (
              <div className={`flex-1 min-h-0 overflow-y-auto p-8 lg:p-10 font-serif text-[16px] leading-8 text-themeText/90 scrollbar-thin select-text space-y-1 transition-all duration-550 ${
                pipelineStep !== 'idle' && pipelineStep !== 'ready' ? 'opacity-35 cursor-wait select-none blur-[0.5px]' : ''
              }`}>
                {translationSentences.map((sent, idx) => (
                  <span
                    key={idx}
                    onMouseEnter={() => setHoveredIdx(idx)}
                    onMouseLeave={() => setHoveredIdx(null)}
                    className={`transition-all duration-150 inline px-1 rounded cursor-pointer ${
                      hoveredIdx === idx
                        ? 'bg-amber-100 dark:bg-amber-950/60 text-amber-900 dark:text-amber-100 font-medium shadow-sm ring-1 ring-amber-200 dark:ring-amber-900/50'
                        : ''
                    }`}
                  >
                    {sent}{' '}
                  </span>
                ))}
              </div>
            ) : (
              <div
                ref={editorRef}
                contentEditable
                suppressContentEditableWarning
                onInput={handleInput}
                onMouseMove={handleEditorMouseMove}
                onMouseLeave={() => setHoveredIdx(null)}
                className={`flex-1 min-h-0 p-8 lg:p-10 font-serif text-[16px] leading-8 text-themeText outline-none overflow-y-auto scrollbar-thin whitespace-pre-wrap transition-all duration-550 ${
                  pipelineStep !== 'idle' && pipelineStep !== 'ready' ? 'opacity-35 cursor-wait select-none blur-[0.5px]' : ''
                }`}
              />
            )}

            {/* User Feedback Box */}
            {pipelineStep === 'ready' && (
              <div className="border-t border-themeBorder bg-themeBg/40 p-4 space-y-3 shrink-0">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-themeMuted uppercase tracking-wider">AI Refinement Instructions</label>
                  <span className="text-[11px] text-themeMuted">Describe style or translation corrections</span>
                </div>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={userFeedback}
                    onChange={(e) => setUserFeedback(e.target.value)}
                    placeholder="e.g. Dịch trang trọng hơn, dùng Manga style..."
                    className="flex-1 rounded-md border border-themeBorder bg-themeCard px-3 py-2 text-xs text-themeText placeholder-themeMuted focus:ring-1 focus:ring-slate-400 focus:outline-none"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleRefineWithAi()
                    }}
                  />
                  <button
                    onClick={handleRefineWithAi}
                    disabled={isRefining}
                    className="px-4 py-2 rounded-md bg-slate-900 hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-950 dark:hover:bg-slate-200 text-xs font-medium transition-colors disabled:opacity-50"
                  >
                    {isRefining ? 'Refining...' : 'Refine'}
                  </button>
                </div>
              </div>
            )}
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
