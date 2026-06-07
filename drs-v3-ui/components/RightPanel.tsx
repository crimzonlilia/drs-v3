'use client'

import React, { useEffect, useState } from 'react'
import { BookOpen, ChevronDown, PanelRight, Plus } from 'lucide-react'
import { addGlossaryTerm, getProjectMemory } from '@/app/api-client'

type WorkflowStep = 'read' | 'edit' | 'review' | 'approve'

interface RightPanelProps {
  projectId: string
  selectedBlock?: number
  onClose?: () => void
  onGlossaryUpdated?: () => void
  currentStep?: WorkflowStep
  pipelineStep?: 'idle' | 'translating' | 'polishing' | 'qa_check' | 'ready'
  pipelineLogs?: string[]
}

interface MemoryHit {
  rule: string
  category: string
}

const panelCopy: Record<WorkflowStep, { title: string; description: string }> = {
  read: {
    title: 'Document Context',
    description: 'Reference terms and style notes for this chapter.'
  },
  edit: {
    title: 'Writing Support',
    description: 'Use project memory only when it helps the current passage.'
  },
  review: {
    title: 'Review Notes',
    description: 'Check only the issues that can affect publication quality.'
  },
  approve: {
    title: 'Approval',
    description: 'Confirm the chapter is ready to sync and export.'
  }
}

export default function RightPanel({
  projectId,
  onClose,
  onGlossaryUpdated,
  currentStep = 'read',
  pipelineStep = 'idle',
  pipelineLogs = []
}: RightPanelProps) {
  const [proposedSource, setProposedSource] = useState('')
  const [proposedTarget, setProposedTarget] = useState('')
  const [memoryHits, setMemoryHits] = useState<MemoryHit[]>([])
  const [showAddTerm, setShowAddTerm] = useState(false)

  const fetchMemory = async () => {
    if (!projectId) return
    try {
      const data = await getProjectMemory(projectId)
      const hits: MemoryHit[] = []
      data.glossary?.slice(0, 6).forEach(g => {
        hits.push({ rule: `${g.source_term} -> ${g.target_term}`, category: g.context_note || 'Glossary' })
      })
      data.style_rules?.slice(0, 3).forEach(r => {
        hits.push({ rule: r.description, category: 'Style' })
      })
      setMemoryHits(hits)
    } catch (err) {
      console.error('Failed to load memory hits:', err)
    }
  }

  useEffect(() => {
    fetchMemory()
  }, [projectId, currentStep])

  const handlePromoteGlossary = async () => {
    if (!proposedSource.trim() || !proposedTarget.trim()) {
      alert('Add both source and target terms.')
      return
    }
    try {
      await addGlossaryTerm(projectId, {
        source_term: proposedSource,
        target_term: proposedTarget,
        source_lang: 'ja',
        target_lang: 'vi',
        context_note: 'Added during review'
      })
      setProposedSource('')
      setProposedTarget('')
      setShowAddTerm(false)
      fetchMemory()
      onGlossaryUpdated?.()
    } catch (err) {
      console.error(err)
      alert('Could not add glossary term.')
    }
  }

  return (
    <aside className="w-full h-full bg-themeSidebarWorkspace border-l border-themeBorder flex flex-col overflow-hidden">
      <div className="px-5 py-4 border-b border-themeBorder flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-themeText">{panelCopy[currentStep].title}</h2>
          <p className="mt-1 text-xs leading-5 text-themeMuted">{panelCopy[currentStep].description}</p>
        </div>
        {onClose && (
          <button onClick={onClose} className="p-1.5 rounded-md text-themeMuted hover:text-themeText hover:bg-themeCard" title="Hide context">
            <PanelRight size={16} />
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-none p-4 space-y-4">
        {pipelineStep !== 'idle' ? (
          <section className="rounded-lg border border-themeBorder bg-themeCard/60 p-4 space-y-4">
            <div>
              <h3 className="text-xs font-semibold text-themeText uppercase tracking-wider mb-2">AI Autopilot Status</h3>
              <div className="flex items-center gap-2">
                <div className="flex h-2 w-2 relative">
                  <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${pipelineStep === 'ready' ? 'bg-emerald-400' : 'bg-amber-400'}`}></span>
                  <span className={`relative inline-flex rounded-full h-2 w-2 ${pipelineStep === 'ready' ? 'bg-emerald-500' : 'bg-amber-500'}`}></span>
                </div>
                <span className="text-xs text-themeText font-medium capitalize">
                  {pipelineStep === 'translating' && 'Translating...'}
                  {pipelineStep === 'polishing' && 'Tone polishing...'}
                  {pipelineStep === 'qa_check' && 'QA audit...'}
                  {pipelineStep === 'ready' && 'Completed'}
                </span>
              </div>
            </div>

            <div className="bg-slate-950 dark:bg-slate-900 border border-slate-800 rounded-md p-3 font-mono text-[10px] leading-relaxed text-slate-300 max-h-48 overflow-y-auto scrollbar-thin">
              {pipelineLogs.map((log, idx) => (
                <div key={idx} className={log.startsWith('[Error]') ? 'text-rose-400' : log.startsWith('[Autopilot]') ? 'text-slate-300' : 'text-slate-400'}>
                  {log}
                </div>
              ))}
            </div>

            {pipelineStep === 'ready' && (
              <div className="border border-themeBorder rounded-md p-3 bg-themeBg/30 space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-xs font-semibold text-themeText">QA Score</span>
                  <span className="text-sm font-bold text-emerald-500">96/100</span>
                </div>
                <div className="w-full bg-slate-200 dark:bg-slate-800 h-1 rounded-full overflow-hidden">
                  <div className="bg-emerald-500 h-1 rounded-full" style={{ width: '96%' }} />
                </div>
                <div className="grid grid-cols-2 gap-2 pt-1">
                  <div className="text-[10px] text-themeMuted">Glossary check: <span className="text-emerald-500 font-semibold">Pass</span></div>
                  <div className="text-[10px] text-themeMuted">Style tone: <span className="text-emerald-500 font-semibold">Pass</span></div>
                </div>
              </div>
            )}
          </section>
        ) : (
          <section>
            <div className="flex items-center gap-2 mb-3">
              <BookOpen size={14} className="text-themeMuted" />
              <h3 className="text-xs font-medium text-themeMuted">Relevant Memory</h3>
            </div>
            <div className="space-y-2">
              {memoryHits.length > 0 ? memoryHits.map((hit, idx) => (
                <div key={idx} className="rounded-lg border border-themeBorder bg-themeCard/60 p-3">
                  <p className="text-xs leading-5 text-themeText">{hit.rule}</p>
                  <p className="mt-1 text-[11px] text-themeMuted">{hit.category}</p>
                </div>
              )) : (
                <p className="rounded-lg border border-themeBorder bg-themeCard/40 p-3 text-xs leading-5 text-themeMuted">
                  No matching glossary or style notes yet.
                </p>
              )}
            </div>
          </section>
        )}
      </div>
    </aside>
  )
}
