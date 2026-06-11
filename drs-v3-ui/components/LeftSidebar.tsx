'use client'

import React, { useEffect, useState } from 'react'
import { FileText, PanelLeft, Plus, Trash2 } from 'lucide-react'
import { listChapters, deleteChapter } from '@/app/api-client'

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

  const handleDeleteFile = async (filename: string) => {
    if (!confirm(`Bạn có chắc chắn muốn xóa tài liệu "${filename}" không? Thao tác này sẽ xóa vĩnh viễn dữ liệu trên hệ thống.`)) {
      return
    }
    try {
      await deleteChapter(projectId, filename)
      const newList = fileList.filter(f => f !== filename)
      setFileList(newList)
      if (activeFile === filename) {
        if (newList.length > 0) {
          onFileSelect(newList[0])
        } else {
          onFileSelect('')
        }
      }
      alert(`Đã xóa tài liệu "${filename}" thành công.`)
    } catch (err: any) {
      alert(`Lỗi khi xóa tài liệu: ${err.message}`)
    }
  }

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
          {fileList.map(file => {
            const isActive = activeFile === file
            return (
              <div
                key={file}
                className={`group w-full min-w-0 rounded-md px-2.5 py-1.5 flex items-center justify-between gap-2 transition-colors ${
                  isActive
                    ? 'bg-themeCard text-themeText font-medium'
                    : 'text-themeMuted hover:bg-themeCard/60 hover:text-themeText'
                }`}
              >
                <button
                  onClick={() => onFileSelect(file)}
                  className="flex items-center gap-2 min-w-0 flex-1 text-left select-none"
                >
                  <FileText size={14} className="shrink-0" />
                  <span className="truncate text-sm">{file}</span>
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    handleDeleteFile(file)
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-400 hover:text-red-500 transition-all shrink-0"
                  title="Xóa tài liệu"
                >
                  <Trash2 size={13} />
                </button>
              </div>
            )
          })}
        </div>
      </div>
    </aside>
  )
}
