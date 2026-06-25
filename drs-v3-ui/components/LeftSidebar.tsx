'use client'

import React, { useState, useEffect, useRef } from 'react'
import { showToast } from './toast'
import { FileText, PanelLeft, Plus, Trash2, UploadCloud, Edit3 } from 'lucide-react'
import { listChapters, deleteChapter, saveChapter, uploadTextBulk, getChapter, renameDocument } from '@/app/api-client'
import { useLanguage } from '@/app/i18n'

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
  const [chapterTitles, setChapterTitles] = useState<Record<string, string>>({})
  const { language, t } = useLanguage()

  const handleRenameFile = async (filename: string) => {
    const newName = prompt(t('newDocPrompt') || 'Nhập tên tài liệu mới:', filename)
    if (!newName || !newName.trim() || newName.trim() === filename) return
    const cleanNewName = newName.trim().endsWith('.md') ? newName.trim() : `${newName.trim()}.md`
    
    if (fileList.some(f => f.toLowerCase() === cleanNewName.toLowerCase() && f !== filename)) {
      showToast(t('docExists') || 'Tài liệu với tên đó đã tồn tại.', 'warning')
      return
    }

    try {
      await renameDocument(projectId, filename, cleanNewName)
      
      const newList = fileList.map(f => f === filename ? cleanNewName : f)
      setFileList(newList)
      
      if (activeFile === filename) {
        onFileSelect(cleanNewName)
        if (typeof window !== 'undefined') {
          const newPath = window.location.pathname.replace(encodeURIComponent(filename), encodeURIComponent(cleanNewName))
          window.history.replaceState(null, '', newPath)
        }
      }
      
      showToast('Đổi tên tài liệu thành công!', 'success')
      
      const titles = { ...chapterTitles }
      if (titles[filename]) {
        titles[cleanNewName] = titles[filename]
        delete titles[filename]
        setChapterTitles(titles)
      }
    } catch (err: any) {
      showToast(`Lỗi khi đổi tên tài liệu: ${err.message}`, 'error')
    }
  }

  const formatDoc = (ch: string) => {
    if (!ch) return ''
    let titleText = ch
    if (chapterTitles[ch]) {
      titleText = chapterTitles[ch]
    }
    const clean = titleText.replace(/\.md$/, '').replace(/_draft$/, '').replace(/_review$/, '').replace(/_final$/, '')
    const match = clean.match(/^ch(\d+)$/i);
    if (match) {
      return language === 'en' ? `Document ${parseInt(match[1], 10)}` : `Tài liệu ${parseInt(match[1], 10)}`;
    }
    return clean.charAt(0).toUpperCase() + clean.slice(1);
  };

  useEffect(() => {
    let active = true
    async function loadData() {
      try {
        const chapters = await listChapters(projectId)
        if (active) {
          const list = chapters?.length ? chapters : defaultFiles
          setFileList(list)
          
          // Concurrently fetch titles
          const titles: Record<string, string> = {}
          await Promise.all(
            list.map(async (slug) => {
              try {
                const detail = await getChapter(projectId, slug)
                if (detail && detail.draft) {
                  const firstLine = detail.draft.split('\n').find(l => l.startsWith('# '))
                  if (firstLine) {
                    titles[slug] = firstLine.replace('# ', '').trim()
                  }
                }
              } catch (e) {
                console.error('Failed to get chapter details for sidebar:', e)
              }
            })
          )
          if (active) {
            setChapterTitles(titles)
          }
        }
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
    const confirmMsg = t('deleteDocConfirm').replace('this document', `"${filename}"`).replace('tài liệu này', `"${filename}"`);
    if (!confirm(confirmMsg)) {
      return
    }
    const newList = fileList.filter(f => f !== filename)
    setFileList(newList)
    if (activeFile === filename) {
      if (newList.length > 0) {
        onFileSelect(newList[0])
      } else {
        onFileSelect('')
      }
    }
    try {
      await deleteChapter(projectId, filename)
      const successMsg = t('deleteDocSuccess').replace('Document', `"${filename}"`).replace('tài liệu', `"${filename}"`);
      showToast(successMsg, 'success')
    } catch (err: any) {
      const errMsg = `${t('deleteDocError')} ${err.message}`
      showToast(errMsg, 'error')
      const chapters = await listChapters(projectId)
      setFileList(chapters?.length ? chapters : defaultFiles)
    }
  }

  const handleAddFile = async () => {
    const filename = prompt(t('newDocPrompt'))
    if (!filename?.trim()) return
    const cleanName = filename.endsWith('.md') ? filename : `${filename}.md`
    if (fileList.some(f => f.toLowerCase() === cleanName.toLowerCase())) {
      showToast(t('docExists'), 'warning')
      return
    }
    
    // Optimistic update
    setFileList([...fileList, cleanName])
    onFileSelect(cleanName)
    
    try {
      await saveChapter(projectId, cleanName, { draft: '' })
      showToast(t('createDocSuccess'), 'success')
    } catch (err: any) {
      showToast(`${t('createDocError')} ${err.message}`, 'error')
      const chapters = await listChapters(projectId)
      setFileList(chapters?.length ? chapters : defaultFiles)
    }
  }

  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleUploadTxt = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    
    let cleanName = file.name.replace('.txt', '.md')
    if (!cleanName.endsWith('.md')) cleanName += '.md'
    
    if (fileList.some(f => f.toLowerCase() === cleanName.toLowerCase())) {
      showToast(t('docExists'), 'warning')
      if (fileInputRef.current) fileInputRef.current.value = ''
      return
    }
    
    // Optimistic update
    setFileList([...fileList, cleanName])
    onFileSelect(cleanName)
    
    try {
      await saveChapter(projectId, cleanName, { draft: '' })
      await uploadTextBulk(projectId, cleanName, 'ja', 'vi', file)
      showToast(t('uploadDocSuccess'), 'success', 6000)
    } catch (err: any) {
      const uploadErrMsg = `${t('uploadDocError')} ${err.message}`
      showToast(uploadErrMsg, 'error')
      const chapters = await listChapters(projectId)
      setFileList(chapters?.length ? chapters : defaultFiles)
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  return (
    <aside className="w-full h-full bg-themeSidebarWorkspace border-r border-themeBorder flex flex-col overflow-hidden">
      <div className="px-5 py-4 border-b border-themeBorder flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs text-themeMuted">{t('project')}</p>
          <h2 className="mt-1 text-sm font-semibold text-themeText truncate">{projectName}</h2>
        </div>
        {onClose && (
          <button onClick={onClose} className="p-1.5 rounded-md text-themeMuted hover:text-themeText hover:bg-themeCard" title={t('hideSidebar')}>
            <PanelLeft size={16} />
          </button>
        )}
      </div>

      <div className="px-4 py-4 border-b border-themeBorder">
        <p className="text-xs text-themeMuted">{t('activeDocument')}</p>
        <p className="mt-1 text-sm font-medium text-themeText truncate">{formatDoc(activeFile)}</p>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto scrollbar-none px-3 py-4">
        <div className="mb-2 flex items-center justify-between px-2">
          <h3 className="text-xs font-medium text-themeMuted">{t('sidebarDocuments')}</h3>
          <div className="flex items-center gap-1">
            <input 
              type="file" 
              ref={fileInputRef}
              accept=".txt" 
              onChange={handleUploadTxt} 
              className="hidden" 
              id="bulk-upload-input"
            />
            <label 
              htmlFor="bulk-upload-input" 
              className="p-1 rounded-md text-themeMuted hover:text-themeText hover:bg-themeCard cursor-pointer" 
              title={t('uploadTxtTooltip')}
            >
              <UploadCloud size={14} />
            </label>
            <button onClick={handleAddFile} className="p-1 rounded-md text-themeMuted hover:text-themeText hover:bg-themeCard" title={t('createDocBtn')}>
              <Plus size={14} />
            </button>
          </div>
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
                  <span className="truncate text-sm">{formatDoc(file)}</span>
                </button>
                <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-all shrink-0">
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      handleRenameFile(file)
                    }}
                    className="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-400 hover:text-indigo-500 transition-all"
                    title="Đổi tên tài liệu"
                  >
                    <Edit3 size={13} />
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      handleDeleteFile(file)
                    }}
                    className="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-400 hover:text-red-500 transition-all"
                    title={t('deleteDoc')}
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </aside>
  )
}
