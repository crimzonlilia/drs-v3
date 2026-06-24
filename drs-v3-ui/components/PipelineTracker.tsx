'use client'

import React from 'react'
import { ChevronRight, Check, Loader2 } from 'lucide-react'
import { useLanguage } from '@/app/i18n'

interface PipelineTrackerProps {
  pipelineStatus: Record<string, string>
  isImageDoc: boolean
}

export default function PipelineTracker({ pipelineStatus, isImageDoc }: PipelineTrackerProps) {
  const { t } = useLanguage()

  const steps = [
    { key: 'upload', label: t('stepUpload') },
    { key: 'ocr', label: t('stepOcr'), cond: isImageDoc },
    { key: 'context_retrieval', label: t('stepContext') },
    { key: 'draft_translation', label: t('stepDraft') },
    { key: 'review', label: t('stepReview') },
    { key: 'approve', label: t('stepApprove') },
    { key: 'render', label: t('stepRender'), cond: isImageDoc }
  ]

  const visibleSteps = steps.filter(s => s.cond !== false)

  return (
    <div className="w-full py-2 bg-slate-50 dark:bg-slate-900/40 border-b border-slate-200 dark:border-slate-800 px-5 select-none overflow-x-auto">
      <div className="flex items-center justify-between max-w-4xl mx-auto">
        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mr-4 shrink-0">{t('pipelineProgress')}</span>
        <div className="flex items-center gap-1.5 flex-1 justify-end">
          {visibleSteps.map((step, idx) => {
            const status = pipelineStatus[step.key] || 'idle'
            let bgClass = 'bg-slate-200 text-slate-500 dark:bg-slate-800 dark:text-slate-500'
            let ringClass = ''

            if (status === 'success') {
              bgClass = 'bg-emerald-500 text-white'
            } else if (status === 'running') {
              bgClass = 'bg-blue-600 text-white animate-pulse'
              ringClass = 'ring-2 ring-blue-500/20'
            } else if (status === 'failed') {
              bgClass = 'bg-red-500 text-white'
            }

            return (
              <React.Fragment key={step.key}>
                {idx > 0 && <ChevronRight size={12} className="text-slate-300 dark:text-slate-700 shrink-0" />}
                <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-semibold ${bgClass} ${ringClass} transition-all duration-300 shrink-0`}>
                  {status === 'success' && <Check size={10} />}
                  {status === 'running' && <Loader2 size={10} className="animate-spin" />}
                  <span>{step.label}</span>
                </div>
              </React.Fragment>
            )
          })}
        </div>
      </div>
    </div>
  )
}
