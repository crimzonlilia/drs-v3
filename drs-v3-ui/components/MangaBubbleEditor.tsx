'use client'

import React from 'react'
import { Check, CheckCircle2, Loader2 } from 'lucide-react'
import { getAssetViewUrl, getRenderedViewUrl } from '@/app/api-client'

interface MangaBubbleEditorProps {
  projectId: string
  activeFile: string
  msg: any
  mangaViewMode: 'original' | 'rendered'
  setViewMode: (mode: 'original' | 'rendered') => void
  handleSegmentChange: (msgId: string, assetId: string, segmentId: string, newText: string) => void
  handleApproveAndRender: (msgId: string, sessionId: string, assetId: string) => void
  selectedFont: string
  fontSize: number
  isApproving?: boolean
}

export default function MangaBubbleEditor({
  projectId,
  activeFile,
  msg,
  mangaViewMode,
  setViewMode,
  handleSegmentChange,
  handleApproveAndRender,
  selectedFont,
  fontSize,
  isApproving = false
}: MangaBubbleEditorProps) {
  return (
    <div className="w-full space-y-4">
      {msg.status === 'processing' && (
        <div className="p-4 bg-slate-50 dark:bg-slate-900/30 rounded-xl space-y-3">
          <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
            <Loader2 size={12} className="animate-spin text-indigo-500" />
            <span>Đang chạy OCR & Trích xuất khung hội thoại...</span>
          </div>
        </div>
      )}

      {msg.segments && msg.segments.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-start w-full">
          
          {/* Left Side: Image display */}
          <div className="border border-slate-200 dark:border-slate-850 rounded-xl overflow-hidden bg-slate-50 dark:bg-slate-900 p-2 flex flex-col items-center">
            <div className="relative w-full max-h-[450px] overflow-auto flex items-center justify-center">
              <img 
                src={
                  mangaViewMode === 'rendered'
                    ? getRenderedViewUrl(projectId, activeFile, msg.assetId || '')
                    : getAssetViewUrl(projectId, activeFile, msg.assetId || '')
                } 
                alt="Manga page preview" 
                className="max-w-full h-auto rounded shadow-sm object-contain"
              />
            </div>
            <div className="flex items-center justify-center gap-2 mt-3 select-none w-full border-t pt-2 border-slate-200 dark:border-slate-800">
              <button
                onClick={() => setViewMode('original')}
                className={`px-3 py-1 text-[10px] font-bold rounded-lg transition-colors ${
                  mangaViewMode !== 'rendered'
                    ? 'bg-indigo-650 text-white'
                    : 'bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400'
                }`}
              >
                Ảnh Gốc
              </button>
              <button
                onClick={() => setViewMode('rendered')}
                className={`px-3 py-1 text-[10px] font-bold rounded-lg transition-colors ${
                  mangaViewMode === 'rendered'
                    ? 'bg-indigo-650 text-white'
                    : 'bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400'
                }`}
              >
                Ảnh Đã Vẽ Dịch
              </button>
            </div>
          </div>

          {/* Right Side: Text areas */}
          <div className="border border-slate-200 dark:border-slate-850 rounded-xl p-3 bg-white dark:bg-slate-950 max-h-[450px] overflow-y-auto space-y-3.5 scrollbar-thin">
            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1 select-none">
              Bản dịch các hội thoại ({msg.segments.length})
            </div>
            {msg.segments.map((seg: any, sIdx: number) => (
              <div key={seg.segment_id || sIdx} className="space-y-1.5 pb-3 border-b border-slate-100 dark:border-slate-900 last:border-0 last:pb-0">
                <div className="flex items-center justify-between text-[10px]">
                  <span className="font-bold text-indigo-500">Bubble {sIdx + 1}</span>
                  <span className="text-slate-400 font-serif italic">{seg.source_text}</span>
                </div>
                <textarea
                  value={seg.target_text || ''}
                  onChange={(e) => handleSegmentChange(msg.id, msg.assetId || '', seg.segment_id, e.target.value)}
                  className="w-full bg-slate-50/50 dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 rounded-lg p-2 text-xs text-slate-800 dark:text-slate-200 leading-relaxed font-sans focus:outline-none focus:ring-1 focus:ring-indigo-400/50 resize-none h-14"
                  placeholder="Nhập bản dịch..."
                />
              </div>
            ))}
            
            <div className="pt-2 border-t border-slate-100 dark:border-slate-900 flex justify-end">
              <button
                disabled={msg.isApproved || isApproving}
                onClick={() => handleApproveAndRender(msg.id, msg.sessionId || '', msg.assetId || '')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                  msg.isApproved
                    ? 'bg-emerald-500/10 text-emerald-600'
                    : isApproving
                      ? 'bg-slate-200 dark:bg-slate-800 text-slate-400 cursor-not-allowed'
                      : 'bg-emerald-600 text-white hover:bg-emerald-700'
                }`}
              >
                {isApproving ? (
                  <Loader2 size={13} className="animate-spin" />
                ) : msg.isApproved ? (
                  <Check size={13} />
                ) : (
                  <CheckCircle2 size={13} />
                )}
                <span>
                  {isApproving
                    ? 'Đang duyệt & vẽ...'
                    : msg.isApproved
                      ? 'Đã Chốt & Vẽ'
                      : 'Duyệt & Vẽ Ảnh'}
                </span>
              </button>
            </div>
          </div>

        </div>
      )}
    </div>
  )
}
