'use client'

import React, { useEffect, useState } from 'react'
import { BookOpen, Check, ChevronDown, PanelRight, Plus } from 'lucide-react'
import { addGlossaryTerm, getProjectMemory } from '@/app/api-client'

type WorkflowStep = 'read' | 'edit' | 'review' | 'approve'

interface RightPanelProps {
  projectId: string
  selectedBlock?: number
  onClose?: () => void
  onGlossaryUpdated?: () => void
  currentStep?: WorkflowStep
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
  currentStep = 'read'
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
        {(currentStep === 'read' || currentStep === 'edit') && (
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

        {currentStep === 'review' && (
          <>
            <section className="rounded-lg border border-themeBorder bg-themeCard/60 p-4">
              <h3 className="text-sm font-medium text-themeText">Review Checklist</h3>
              <div className="mt-3 space-y-3 text-xs leading-5 text-themeMuted">
                <p className="flex gap-2"><Check size={14} className="mt-0.5 shrink-0" /> Terminology follows the project glossary.</p>
                <p className="flex gap-2"><Check size={14} className="mt-0.5 shrink-0" /> Tone matches the intended register.</p>
                <p className="flex gap-2"><Check size={14} className="mt-0.5 shrink-0" /> Formatting is clean after editing.</p>
              </div>
            </section>

            <section className="rounded-lg border border-themeBorder bg-themeCard/60">
              <button
                onClick={() => setShowAddTerm(!showAddTerm)}
                className="w-full px-4 py-3 flex items-center justify-between text-left"
              >
                <span className="text-sm font-medium text-themeText">Add glossary term</span>
                <ChevronDown size={15} className={`text-themeMuted transition-transform ${showAddTerm ? 'rotate-180' : ''}`} />
              </button>
              {showAddTerm && (
                <div className="px-4 pb-4 space-y-3">
                  <input
                    type="text"
                    placeholder="Source term"
                    value={proposedSource}
                    onChange={(e) => setProposedSource(e.target.value)}
                    className="w-full rounded-md border border-themeBorder bg-themeBg px-3 py-2 text-xs"
                  />
                  <input
                    type="text"
                    placeholder="Approved translation"
                    value={proposedTarget}
                    onChange={(e) => setProposedTarget(e.target.value)}
                    className="w-full rounded-md border border-themeBorder bg-themeBg px-3 py-2 text-xs"
                  />
                  <button onClick={handlePromoteGlossary} className="inline-flex items-center gap-1.5 rounded-md bg-slate-900 px-3 py-2 text-xs font-medium text-white dark:bg-slate-100 dark:text-slate-950">
                    <Plus size={13} /> Add term
                  </button>
                </div>
              )}
            </section>
          </>
        )}

        {currentStep === 'approve' && (
          <section className="rounded-lg border border-themeBorder bg-themeCard/60 p-4">
            <h3 className="text-sm font-medium text-themeText">Before Approval</h3>
            <div className="mt-3 space-y-3 text-xs leading-5 text-themeMuted">
              <p className="flex gap-2"><Check size={14} className="mt-0.5 shrink-0" /> The translated chapter has been reviewed end to end.</p>
              <p className="flex gap-2"><Check size={14} className="mt-0.5 shrink-0" /> Accepted terms should be added to memory.</p>
              <p className="flex gap-2"><Check size={14} className="mt-0.5 shrink-0" /> Export after approval if this is the final handoff.</p>
            </div>
          </section>
        )}
      </div>
    </aside>
  )
}
