'use client'

import React, { useEffect, useState } from 'react'
import { FileText, PanelLeft, Plus } from 'lucide-react'
import { listChapters } from '@/app/api-client'

interface LeftSidebarProps {
  projectId: string
  activeFile: string
  onFileSelect: (file: string) => void
  projectName?: string
  onClose?: () => void
  glossaryRefreshKey?: number
}

const defaultFiles = ['ch001_draft.md', 'ch002_review.md', 'ch003_final.md']

export default function LeftSidebar({
  projectId,
  activeFile,
  onFileSelect,
  projectName = 'Translation Project',
  onClose
}: LeftSidebarProps) {
  const [fileList, setFileList] = useState<string[]>([])

  useEffect(() => {
    let active = true
    async function loadData() {
      try {
        const chapters = await listChapters(projectId)
        if (active) setFileList(chapters?.length ? chapters : defaultFiles)
      } catch (err) {
        console.error('Error listing chapters:', err)
        if (active) setFileList(defaultFiles)
      }
    }
    if (projectId) loadData()
    return () => {
      active = false
    }
  }, [projectId])

  const handleAddFile = () => {
    const filename = prompt('New document name')
    if (!filename?.trim()) return
    const cleanName = filename.endsWith('.md') ? filename : `${filename}.md`
    if (fileList.some(f => f.toLowerCase() === cleanName.toLowerCase())) {
      alert('A document with that name already exists.')
      return
    }
    setFileList([...fileList, cleanName])
    onFileSelect(cleanName)
  }

  return (
    <aside className="w-full h-full bg-themeSidebarWorkspace border-r border-themeBorder flex flex-col overflow-hidden">
      <div className="px-5 py-4 border-b border-themeBorder flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs text-themeMuted">Project</p>
          <h2 className="mt-1 text-sm font-semibold text-themeText truncate">{projectName}</h2>
        </div>
        {onClose && (
          <button onClick={onClose} className="p-1.5 rounded-md text-themeMuted hover:text-themeText hover:bg-themeCard" title="Hide documents">
            <PanelLeft size={16} />
          </button>
        )}
      </div>

      <div className="px-4 py-4 border-b border-themeBorder">
        <p className="text-xs text-themeMuted">Active document</p>
        <p className="mt-1 text-sm font-medium text-themeText truncate">{activeFile}</p>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto scrollbar-none px-3 py-4">
        <div className="mb-2 flex items-center justify-between px-2">
          <h3 className="text-xs font-medium text-themeMuted">Documents</h3>
          <button onClick={handleAddFile} className="p-1 rounded-md text-themeMuted hover:text-themeText hover:bg-themeCard" title="New document">
            <Plus size={14} />
          </button>
        </div>

        <div className="space-y-1">
          {fileList.map(file => (
            <button
              key={file}
              onClick={() => onFileSelect(file)}
              className={`w-full min-w-0 rounded-md px-2.5 py-2 text-left flex items-center gap-2 ${
                activeFile === file
                  ? 'bg-themeCard text-themeText'
                  : 'text-themeMuted hover:bg-themeCard/60 hover:text-themeText'
              }`}
            >
              <FileText size={14} className="shrink-0" />
              <span className="truncate text-sm">{file}</span>
            </button>
          ))}
        </div>
      </div>
    </aside>
  )
}
