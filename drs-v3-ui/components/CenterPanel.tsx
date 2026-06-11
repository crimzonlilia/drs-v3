'use client'

import React, { useEffect, useMemo, useRef, useState } from 'react'
import {
  Download,
  PanelLeft,
  Send,
  Check,
  CheckCircle2,
  MessageSquare,
  Loader2,
  X,
  AlertTriangle,
  BookOpen,
  Edit3,
  Paperclip,
  Type,
  Upload
} from 'lucide-react'
import {
  approveTranslation,
  exportChapter,
  getChapter,
  runTranslate,
  saveChapter,
  refineTranslation,
  uploadFont,
  listFonts,
  runImageTranslate,
  renderDocumentImage,
  getImagePipelineStatus,
  getFontDownloadUrl,
  getDocumentSegments,
  updateSegmentText,
  uploadAssets
} from '@/app/api-client'

import PipelineTracker from './PipelineTracker'
import MangaBubbleEditor from './MangaBubbleEditor'
import ReactMarkdown from 'react-markdown'

type WorkflowStep = 'read' | 'edit' | 'review' | 'approve'

const splitSentences = (text: string) => {
  if (!text) return []
  const matches = text.match(/([^.?!。！？\n\r]+[.?!。！？\n\r]*)/g)
  return matches ? matches.map(s => s.trim()).filter(Boolean) : [text]
}

const parseUserMessage = (msg: string) => {
  const jpRegex = /[\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\uff00-\uff9f\u4e00-\u9faf\u4e00-\u9fff]+/g
  const matches = msg.match(jpRegex)
  if (matches && matches.length > 0) {
    const originalText = matches.join(' ')
    const instruction = msg.replace(originalText, '').replace(/[\s,.:;!"'""“”:：、。]+/g, ' ').trim()
    return { originalText, instruction }
  }
  return { originalText: '', instruction: msg }
}

const renderFormattedText = (text: string) => {
  if (!text) return null
  return (
    <ReactMarkdown
      components={{
        strong: ({ node, ...props }) => <strong className="font-bold text-indigo-650 dark:text-indigo-400" {...props} />,
        code: ({ node, ...props }) => <code className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-[11px] font-mono text-pink-600 dark:text-pink-400" {...props} />,
        p: ({ node, ...props }) => <p className="mb-1 last:mb-0" {...props} />,
        ul: ({ node, ...props }) => <ul className="list-disc pl-4 mb-2" {...props} />,
        ol: ({ node, ...props }) => <ol className="list-decimal pl-4 mb-2" {...props} />,
        li: ({ node, ...props }) => <li className="mb-0.5" {...props} />
      }}
    >
      {text}
    </ReactMarkdown>
  )
}

interface ChatMessage {
  id: string
  sender: 'user' | 'ai'
  text: string
  originalText?: string
  instruction?: string
  status: 'processing' | 'done' | 'failed'
  processingStep?: 'literal' | 'ai' | 'qa' | 'done'
  sessionId?: string
  qaScore?: number
  editorialScore?: Record<string, number>
  validationIssues?: any[]
  editorialFeedback?: string[]
  proposals?: any[]
  isApproved?: boolean
  timestamp: string
  // Image properties
  isImageWorkflow?: boolean
  assetId?: string
  segments?: any[]
}

interface CenterPanelProps {
  projectId: string;
  activeFile: string;
  sourceMode?: 'text' | 'visual';
  onSourceModeChange?: (mode: 'text' | 'visual') => void;
  selectedBlock?: number;
  onBlockSelect?: (idx: number) => void;
  showLeftSidebar?: boolean;
  onToggleLeft?: () => void;
  currentStep: WorkflowStep;
  onStepChange: (step: WorkflowStep) => void;
  pipelineStep: string;
  setPipelineStep: (step: string) => void;
  pipelineLogs: string[];
  setPipelineLogs: (logs: string[] | ((prev: string[]) => string[])) => void;
}

const languages = [
  ['ja', 'Japanese'],
  ['vi', 'Vietnamese'],
  ['en', 'English'],
  ['zh', 'Chinese'],
  ['ko', 'Korean']
] as const

export default function CenterPanel({
  projectId,
  activeFile,
  showLeftSidebar = true,
  onToggleLeft,
  onStepChange,
  pipelineStep,
  setPipelineStep,
  setPipelineLogs
}: CenterPanelProps) {
  const [original, setOriginal] = useState('')
  const [translation, setTranslation] = useState('')
  const [sourceLang, setSourceLang] = useState('ja')
  const [targetLang, setTargetLang] = useState('vi')
  const [isTranslating, setIsTranslating] = useState(false)
  const [saveState, setSaveState] = useState<'saved' | 'saving'>('saved')
  const [isEditingOriginal, setIsEditingOriginal] = useState(false)
  const [isApproved, setIsApproved] = useState(false)

  // Chat Timeline States
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
  const [chatInput, setChatInput] = useState('')

  const [editingMessageId, setEditingMessageId] = useState<string | null>(null)
  const [editTranslationText, setEditTranslationText] = useState('')
  const [refineFeedbackText, setRefineFeedbackText] = useState('')
  const [showSourcePanel, setShowSourcePanel] = useState(false)
  const chatEndRef = useRef<HTMLDivElement>(null)

  // File upload state for unified input area
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null)

  // Session status / tracking
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [currentAssetId, setCurrentAssetId] = useState<string | null>(null)
  const [pipelineStatus, setPipelineStatus] = useState<Record<string, string>>({
    upload: 'idle',
    ocr: 'idle',
    context_retrieval: 'idle',
    draft_translation: 'idle',
    review: 'idle',
    approve: 'idle',
    render: 'idle'
  })
  const [isImageDoc, setIsImageDoc] = useState(false)
  const [inspectedMsgId, setInspectedMsgId] = useState<string | null>(null)

  // Font manager states
  const [availableFonts, setAvailableFonts] = useState<string[]>([])
  const [selectedFont, setSelectedFont] = useState<string>('Noto Sans')
  const [fontSize, setFontSize] = useState<number>(18)

  // Active view for manga editor side-by-side (original or rendered)
  const [mangaViewModes, setMangaViewModes] = useState<Record<string, 'original' | 'rendered'>>({})

  const originalSentences = useMemo(() => splitSentences(original), [original])

  const wordCount = useMemo(() => {
    return translation.replace(/<[^>]*>/g, '').trim().split(/\s+/).filter(Boolean).length
  }, [translation])

  // Scroll to bottom on new messages
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages])

  // Initial load of fonts and document
  useEffect(() => {
    async function loadFonts() {
      if (!projectId) return
      try {
        const res = await listFonts(projectId)
        const allFonts = [...res.default_fonts, ...res.custom_fonts]
        setAvailableFonts(allFonts)

        // Inject font face dynamically
        res.custom_fonts.forEach(font => {
          const fontUrl = getFontDownloadUrl(projectId, font)
          const fontNameClean = font.replace(/\.[^/.]+$/, "")
          const fontFace = new FontFace(fontNameClean, `url(${fontUrl})`)
          fontFace.load().then(loadedFace => {
            document.fonts.add(loadedFace)
          }).catch(err => {
            console.error(`Error loading font ${font}:`, err)
          })
        })
      } catch (err) {
        console.error('Failed to load project fonts:', err)
      }
    }
    loadFonts()
  }, [projectId])

  // Load chapter data
  useEffect(() => {
    let active = true
    async function load() {
      if (!projectId || !activeFile) return
      
      try {
        const data = await getChapter(projectId, activeFile)
        if (!active) return
        const sourceText = data.source_text || ''
        const targetText = data.approved || ''
        setOriginal(sourceText)
        setTranslation(targetText)
        setIsApproved(!!data.approved)
        setPipelineStep('idle')
        onStepChange('read')
        
        // Detect if active file is an image file (manga, comic, scan)
        const isImg = activeFile.toLowerCase().endsWith('.png') ||
                      activeFile.toLowerCase().endsWith('.jpg') ||
                      activeFile.toLowerCase().endsWith('.jpeg') ||
                      activeFile.toLowerCase().endsWith('.webp')
        setIsImageDoc(isImg)

        // Populate timeline with initial greeting
        setChatMessages([
          {
            id: 'welcome',
            sender: 'ai',
            text: `Chào mừng bạn đến với **Localization Workspace** cho tài liệu **${activeFile}**. Bạn có thể gửi yêu cầu dịch văn bản hoặc đính kèm ảnh manga/comic để dịch trực tiếp trong luồng chat này.`,
            status: 'done',
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          }
        ])
      } catch (err) {
        console.error('Failed to load chapter content:', err)
      }
    }
    load()
    return () => {
      active = false
    }
  }, [projectId, activeFile])

  // Auto-save full doc text occasionally
  useEffect(() => {
    if (!original.trim() || isImageDoc) return
    const timer = setTimeout(async () => {
      setSaveState('saving')
      try {
        await saveChapter(projectId, activeFile, { approved: translation })
        setSaveState('saved')
      } catch (err) {
        console.error('Auto-save failed:', err)
        setSaveState('saved')
      }
    }, 2000)
    return () => clearTimeout(timer)
  }, [translation, original, projectId, activeFile, isImageDoc])

  // Polling pipeline status
  useEffect(() => {
    if (!activeSessionId) return
    let active = true
    let timer: NodeJS.Timeout

    async function poll() {
      try {
        const res = await getImagePipelineStatus(activeSessionId)
        if (!active) return
        
        if (res && res.pipeline_status) {
          setPipelineStatus(res.pipeline_status)
          
          const errorMsg = res.pipeline_error || ""
          if (errorMsg) {
            setPipelineStep('idle')
            setIsTranslating(false)
            setChatMessages(prev => prev.map(m => m.sessionId === activeSessionId ? {
              ...m,
              status: 'failed',
              text: `Dịch hình ảnh thất bại: ${errorMsg}`
            } : m))
            setActiveSessionId(null)
            return
          }

          const hasFailed = Object.values(res.pipeline_status).some(val => val === 'failed')
          const isReviewing = res.pipeline_status.review === 'running' || res.pipeline_status.review === 'success'

          if (hasFailed) {
            setPipelineStep('idle')
            setIsTranslating(false)
            setActiveSessionId(null)
            return
          }

          if (isReviewing) {
            setPipelineStep('ready')
            setIsTranslating(false)
            
            // Load segments from D1
            if (currentAssetId) {
              const segs = await getDocumentSegments(projectId, activeFile, currentAssetId)
              setChatMessages(prev => prev.map(m => m.sessionId === activeSessionId ? {
                ...m,
                status: 'done',
                segments: segs
              } : m))
            }
            
            setActiveSessionId(null) // Stop polling
            return;
          }
        }
      } catch (err) {
        console.error("Error polling image translation status:", err)
      }
      timer = setTimeout(poll, 1500)
    }

    poll()
    return () => {
      active = false
      clearTimeout(timer)
    }
  }, [activeSessionId, currentAssetId, projectId, activeFile])

  // Start text translation pipeline
  const startTranslationPipeline = async (rawPrompt: string, sourceText: string, sentenceIdx: number, instruction?: string) => {
    const messageId = `msg_${Date.now()}`
      
    const userMsg: ChatMessage = {
      id: `user_${messageId}`,
      sender: 'user',
      text: rawPrompt,
      originalText: sourceText,
      instruction: instruction || '',
      status: 'done',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
    
    const aiMsg: ChatMessage = {
      id: `ai_${messageId}`,
      sender: 'ai',
      text: '',
      status: 'processing',
      processingStep: 'literal',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
    
    setChatMessages(prev => [...prev, userMsg, aiMsg])
    setIsTranslating(true)
    setPipelineStep('translating')

    // Reset status tracker
    setPipelineStatus({
      upload: 'success',
      ocr: 'success', // skipped
      context_retrieval: 'running',
      draft_translation: 'idle',
      review: 'idle',
      approve: 'idle',
      render: 'idle'
    })
    
    try {
      // Call translate API
      const res = await runTranslate(projectId, activeFile, sourceText, sourceLang, targetLang)
      if (!res || !res.session_id) {
        throw new Error("Failed to initialize translation session")
      }
      
      const sId = res.session_id
      let finalSession = res
      
      setPipelineStatus({
        upload: 'success',
        ocr: 'success',
        context_retrieval: 'success',
        draft_translation: 'running',
        review: 'idle',
        approve: 'idle',
        render: 'idle'
      })

      if (instruction) {
        const refineRes = await refineTranslation(sId, instruction)
        if (refineRes && refineRes.session) {
          finalSession = refineRes.session
        }
      }
      
      setPipelineStep('ready')
      setIsTranslating(false)
      
      const draftText = finalSession.current_draft || finalSession.draft || ''
      
      setPipelineStatus({
        upload: 'success',
        ocr: 'success',
        context_retrieval: 'success',
        draft_translation: 'success',
        review: 'running',
        approve: 'idle',
        render: 'idle'
      })

      setChatMessages(prev => prev.map(m => m.id === aiMsg.id ? {
        ...m,
        text: draftText,
        originalText: sourceText,
        status: 'done',
        processingStep: 'done',
        sessionId: sId,
        qaScore: finalSession.editorial_score ? Math.round(
          Object.values(finalSession.editorial_score).reduce((sum: number, val: any) => sum + Number(val), 0) /
          Math.max(1, Object.keys(finalSession.editorial_score).length)
        ) : 95,
        editorialScore: finalSession.editorial_score || {},
        validationIssues: finalSession.validation_issues || [],
        editorialFeedback: finalSession.editorial_feedback || [],
        proposals: finalSession.memory_proposals || []
      } : m))
      
      setTranslation(prev => prev ? `${prev}\n${draftText}` : draftText)
      onStepChange('approve')
    } catch (err: any) {
      console.error(err)
      setIsTranslating(false)
      setPipelineStep('idle')
      setPipelineStatus(prev => ({ ...prev, draft_translation: 'failed' }))
      setChatMessages(prev => prev.map(m => m.id === aiMsg.id ? {
        ...m,
        status: 'failed',
        text: `Dịch thất bại: ${err.message || 'Lỗi kết nối server'}`
      } : m))
    }
  }

  // Handle selected image file and prompt
  const handleImageFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setSelectedFile(file)
    const url = URL.createObjectURL(file)
    setImagePreviewUrl(url)
  }

  const handleSendInput = async () => {
    if (!selectedFile && !chatInput.trim()) return

    if (selectedFile) {
      // Image translation flow
      const filename = selectedFile.name
      const msgId = `img_msg_${Date.now()}`
      
      const userMsg: ChatMessage = {
        id: `user_${msgId}`,
        sender: 'user',
        text: chatInput ? `Dịch ảnh [${filename}]\nYêu cầu: ${chatInput}` : `Dịch ảnh [${filename}]`,
        status: 'done',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        isImageWorkflow: true,
        assetId: filename
      }

      const aiMsg: ChatMessage = {
        id: `ai_${msgId}`,
        sender: 'ai',
        text: `Đang xử lý hình ảnh ${filename}...`,
        status: 'processing',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        isImageWorkflow: true,
        assetId: filename
      }

      setChatMessages(prev => [...prev, userMsg, aiMsg])
      setSelectedFile(null)
      setImagePreviewUrl(null)
      setIsTranslating(true)
      setPipelineStep('translating')

      // Set tracker status to running upload
      setPipelineStatus({
        upload: 'running',
        ocr: 'idle',
        context_retrieval: 'idle',
        draft_translation: 'idle',
        review: 'idle',
        approve: 'idle',
        render: 'idle'
      })

      try {
        // Step 1: Upload asset image to R2
        await uploadAssets(projectId, activeFile, [selectedFile])
        
        setPipelineStatus({
          upload: 'success',
          ocr: 'running',
          context_retrieval: 'idle',
          draft_translation: 'idle',
          review: 'idle',
          approve: 'idle',
          render: 'idle'
        })

        // Step 2: Trigger unified image translation pipeline
        const transRes = await runImageTranslate(projectId, activeFile, filename, sourceLang, targetLang)
        if (!transRes || !transRes.session_id) {
          throw new Error("Không thể khởi động tiến trình dịch ảnh")
        }

        const sId = transRes.session_id
        setChatMessages(prev => prev.map(m => m.id === aiMsg.id ? { ...m, sessionId: sId } : m))
        setActiveSessionId(sId)
        setCurrentAssetId(filename)
        setMangaViewModes(prev => ({ ...prev, [filename]: 'original' }))
      } catch (err: any) {
        console.error(err)
        setIsTranslating(false)
        setPipelineStep('idle')
        setPipelineStatus(prev => ({ ...prev, upload: 'failed' }))
        setChatMessages(prev => prev.map(m => m.id === aiMsg.id ? {
          ...m,
          status: 'failed',
          text: `Tiến trình dịch ảnh thất bại: ${err.message || 'Lỗi hệ thống'}`
        } : m))
      }
      setChatInput('')
    } else {
      // Standard text translation
      const { originalText, instruction } = parseUserMessage(chatInput)
      if (originalText) {
        startTranslationPipeline(chatInput, originalText, chatMessages.length / 2, instruction)
      } else {
        // Treat user input text as the source text directly
        startTranslationPipeline(chatInput, chatInput, chatMessages.length / 2)
      }
      setChatInput('')
    }
  }

  // Save segment inline editing
  const handleSegmentChange = async (msgId: string, assetId: string, segmentId: string, newText: string) => {
    setChatMessages(prev => prev.map(m => {
      if (m.id === msgId && m.segments) {
        return {
          ...m,
          segments: m.segments.map(s => s.segment_id === segmentId ? { ...s, target_text: newText } : s)
        }
      }
      return m
    }))

    try {
      await updateSegmentText(projectId, activeFile, segmentId, newText)
    } catch (err) {
      console.error(`Failed to auto-save segment ${segmentId}:`, err)
    }
  }

  // Approve a segment group / image page translation and render it
  const handleApproveAndRender = async (msgId: string, sessionId: string, assetId: string) => {
    try {
      // 1. Approve session (adds translations to memory)
      await approveTranslation(projectId, sessionId)
      
      setChatMessages(prev => prev.map(m => m.id === msgId ? { ...m, isApproved: true } : m))
      setPipelineStatus(prev => ({
        ...prev,
        approve: 'success',
        render: 'running'
      }))

      // 2. Call Pillow rendering
      await renderDocumentImage(projectId, activeFile, assetId, selectedFont, fontSize, sessionId)
      
      setPipelineStatus(prev => ({ ...prev, render: 'success' }))
      
      // Update preview to rendered image
      setMangaViewModes(prev => ({ ...prev, [assetId]: 'rendered' }))
      
      alert("Đã vẽ dịch và chốt dịch manga thành công!")
    } catch (err: any) {
      alert(`Lỗi phê duyệt và vẽ dịch: ${err.message}`)
      setPipelineStatus(prev => ({ ...prev, render: 'failed' }))
    }
  }

  const handleApproveChatMessage = async (msgId: string, sessionId: string) => {
    try {
      await approveTranslation(projectId, sessionId)
      setChatMessages(prev => prev.map(m => m.id === msgId ? { ...m, isApproved: true } : m))
      setIsApproved(true)
      setPipelineStatus(prev => ({ ...prev, approve: 'success' }))
      alert("Đã chốt bản dịch thành công!")
    } catch (err: any) {
      alert(`Lỗi khi duyệt bản dịch: ${err.message}`)
    }
  }

  const handleSendRefinement = async (msgId: string, sessionId: string) => {
    const originalMsg = chatMessages.find(m => m.id === msgId)
    if (!originalMsg) return
    
    const userMsgId = `user_${Date.now()}`
    const promptText = `Sửa bản dịch câu này: "${editTranslationText}"` + 
      (refineFeedbackText ? `\nYêu cầu thêm: "${refineFeedbackText}"` : '')
      
    const userMsg: ChatMessage = {
      id: userMsgId,
      sender: 'user',
      text: promptText,
      status: 'done',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
    
    const newAiMsgId = `ai_${Date.now()}`
    const newAiMsg: ChatMessage = {
      id: newAiMsgId,
      sender: 'ai',
      text: '',
      status: 'processing',
      processingStep: 'literal',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
    
    setChatMessages(prev => [...prev, userMsg, newAiMsg])
    setEditingMessageId(null)
    setIsTranslating(true)
    setPipelineStep('translating')
    
    try {
      if (editTranslationText !== originalMsg.text) {
        await saveSessionDraft(sessionId, editTranslationText)
      }
      
      let finalDraftText = editTranslationText
      let finalIssues = originalMsg.validationIssues || []
      let finalScore = originalMsg.editorialScore || {}
      let finalProposals = originalMsg.proposals || []
      
      if (refineFeedbackText) {
        const res = await refineTranslation(sessionId, refineFeedbackText)
        if (res && res.session) {
          finalDraftText = res.session.current_draft || res.current_draft || ''
          finalIssues = res.session.validation_issues || []
          finalScore = res.session.editorial_score || {}
          finalProposals = res.session.memory_proposals || []
        }
      }
      
      setPipelineStep('ready')
      setIsTranslating(false)
      
      setChatMessages(prev => prev.map(m => m.id === newAiMsgId ? {
        ...m,
        text: finalDraftText,
        status: 'done',
        processingStep: 'done',
        sessionId: sessionId,
        qaScore: finalScore ? Math.round(
          Object.values(finalScore).reduce((sum: number, val: any) => sum + Number(val), 0) /
          Math.max(1, Object.keys(finalScore).length)
        ) : 95,
        editorialScore: finalScore,
        validationIssues: finalIssues,
        proposals: finalProposals
      } : m))
      
      setEditTranslationText('')
      setRefineFeedbackText('')
    } catch (err: any) {
      console.error(err)
      setIsTranslating(false)
      setPipelineStep('idle')
      setChatMessages(prev => prev.map(m => m.id === newAiMsgId ? {
        ...m,
        status: 'failed',
        text: `Lỗi chỉnh sửa: ${err.message || 'Lỗi server'}`
      } : m))
    }
  }

  const handleFontUploadChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !projectId) return
    try {
      const res = await uploadFont(projectId, file)
      alert(`Đã tải lên font custom ${res.font_name} thành công!`)
      const listRes = await listFonts(projectId)
      setAvailableFonts([...listRes.default_fonts, ...listRes.custom_fonts])
    } catch (err: any) {
      alert(`Lỗi tải lên font: ${err.message}`)
    }
  }

  const handleExport = async () => {
    try {
      await exportChapter(projectId, activeFile)
    } catch (err) {
      console.error('Export failed:', err)
    }
  }

  return (
    <main className="flex-1 flex flex-col h-full bg-slate-50 dark:bg-slate-900 overflow-hidden relative font-sans">
      
      {/* Top Header */}
      <div className="h-14 px-5 border-b border-themeBorder bg-white dark:bg-slate-950 flex items-center justify-between z-10 shrink-0 select-none">
        <div className="flex items-center gap-3 min-w-0">
          {!showLeftSidebar && onToggleLeft && (
            <button onClick={onToggleLeft} className="p-1.5 rounded-md text-themeMuted hover:text-themeText hover:bg-themeCard" title="Show documents">
              <PanelLeft size={16} />
            </button>
          )}
          <div className="min-w-0">
            <h1 className="text-sm font-semibold text-slate-850 dark:text-slate-200 truncate">{activeFile}</h1>
            <p className="text-xs text-slate-400 truncate">
              {pipelineStatus.review === 'running' ? 'Review & approve the localization drafts below.' : 'Submit a text translation prompt or upload a manga/comic image.'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Custom Font selector */}
          <div className="flex items-center gap-1.5 border border-slate-200 dark:border-slate-800 rounded-lg p-1 bg-slate-50 dark:bg-slate-900">
            <Type size={12} className="text-slate-400 ml-1.5" />
            <select
              value={selectedFont}
              onChange={(e) => setSelectedFont(e.target.value)}
              className="bg-transparent border-0 text-[11px] font-semibold text-slate-600 dark:text-slate-350 focus:ring-0 py-0.5"
            >
              {availableFonts.map(f => (
                <option key={f} value={f.replace(/\.[^/.]+$/, "")}>{f.replace(/\.[^/.]+$/, "")}</option>
              ))}
            </select>
            
            <input
              type="text"
              value={fontSize}
              onChange={(e) => setFontSize(Number(e.target.value) || 16)}
              className="w-10 bg-transparent border-l border-slate-200 dark:border-slate-800 text-[11px] font-semibold text-slate-600 dark:text-slate-350 focus:ring-0 text-center py-0.5"
            />
            
            <input
              type="file"
              id="font-upload-input"
              accept=".ttf,.otf"
              className="hidden"
              onChange={handleFontUploadChange}
            />
            <label
              htmlFor="font-upload-input"
              className="p-1 rounded-md hover:bg-slate-200 dark:hover:bg-slate-800 cursor-pointer text-slate-400 hover:text-slate-600 transition-colors"
              title="Tải font custom lên (.ttf/.otf)"
            >
              <Upload size={12} />
            </label>
          </div>

          {/* View Source panel trigger */}
          <button 
            onClick={() => setShowSourcePanel(!showSourcePanel)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-900 transition-colors"
          >
            <BookOpen size={13} />
            <span>Văn bản gốc</span>
          </button>

          {/* Export/Download Button */}
          <button 
            onClick={handleExport}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold border border-slate-200 dark:border-slate-850 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-900 transition-colors"
            title="Tải bản dịch xuống"
          >
            <Download size={13} />
            <span>Tải xuống</span>
          </button>
        </div>
      </div>

      {/* Visual tracker sub-component */}
      <PipelineTracker pipelineStatus={pipelineStatus} isImageDoc={isImageDoc} />

      {/* Main Full-Bleed Chat Container */}
      <section className="flex-1 min-h-0 overflow-hidden flex flex-col relative bg-white dark:bg-slate-950">
        
        {/* Chat Header */}
        <div className="h-10 px-5 border-b border-themeBorder flex items-center justify-between bg-slate-55/30 dark:bg-slate-900/10 shrink-0 select-none">
          <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Localization Workspace</span>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-themeMuted uppercase font-bold tracking-wider">Mục tiêu:</span>
            <select value={targetLang} onChange={(e) => setTargetLang(e.target.value)} className="bg-transparent border-0 text-xs font-semibold text-slate-600 dark:text-slate-400 focus:ring-0 py-0 pr-6">
              {languages.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
            <span className="text-[11px] text-themeMuted select-none border-l pl-2 border-themeBorder">{saveState === 'saving' ? 'Đang lưu' : 'Đã lưu'} · {wordCount} từ</span>
          </div>
        </div>

        {/* Chat Messages Timeline (Alternating flat ChatGPT rows) */}
        <div className="flex-1 min-h-0 overflow-y-auto scrollbar-thin">
          {chatMessages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center p-6 select-none max-w-2xl mx-auto">
              <div className="w-12 h-12 rounded-full bg-slate-50 dark:bg-slate-900 border border-slate-100 dark:border-slate-800 flex items-center justify-center mb-3 text-slate-400">
                <MessageSquare size={20} />
              </div>
              <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-1">Localization Workspace</h3>
              <p className="text-xs text-slate-400 text-center leading-relaxed">
                Vui lòng gửi câu gốc của bạn, nhập yêu cầu, hoặc đính kèm ảnh để bắt đầu quy trình làm việc.
              </p>
            </div>
          ) : (
            <div className="w-full flex flex-col">
              {chatMessages.map((msg, mIdx) => {
                const isUser = msg.sender === 'user'
                const rowBg = isUser 
                  ? 'bg-slate-50 dark:bg-slate-900/30' 
                  : 'bg-white dark:bg-slate-950 border-y border-slate-100/50 dark:border-slate-900/30'

                return (
                  <div key={msg.id || mIdx} className={`w-full py-6 px-5 flex justify-center ${rowBg}`}>
                    <div className="max-w-4xl w-full flex gap-4 text-xs leading-relaxed">
                      
                      {/* Avatar Column */}
                      <div className="w-8 shrink-0 flex flex-col items-center select-none">
                        <div className={`w-7 h-7 rounded-md flex items-center justify-center text-[10px] font-bold uppercase ${
                          isUser ? 'bg-slate-200 text-slate-650 dark:bg-slate-850 dark:text-slate-300' : 'bg-indigo-500/10 text-indigo-500'
                        }`}>
                          {isUser ? 'ME' : 'SYS'}
                        </div>
                      </div>

                      {/* Content Column */}
                      <div className="flex-1 space-y-3 min-w-0">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-slate-850 dark:text-slate-200 select-none">
                            {isUser ? 'Bạn' : 'Hệ thống'}
                          </span>
                          <span className="text-[10px] text-slate-400 select-none">
                            {msg.timestamp}
                          </span>
                        </div>

                        {/* Processing indicators */}
                        {msg.status === 'processing' && !msg.isImageWorkflow && (
                          <div className="flex items-center gap-2 text-slate-400">
                            <Loader2 size={12} className="animate-spin text-indigo-500" />
                            <span>Đang dịch thô và đối chiếu rules...</span>
                          </div>
                        )}

                        {msg.status === 'failed' && (
                          <div className="text-red-500 flex items-center gap-2 p-2 rounded bg-red-500/5 border border-red-500/10">
                            <AlertTriangle size={14} />
                            <span>{msg.text}</span>
                          </div>
                        )}

                        {/* Text translation result */}
                        {msg.status === 'done' && !msg.isImageWorkflow && (
                          <div className="space-y-2">
                            <div 
                              onClick={() => setInspectedMsgId(inspectedMsgId === msg.id ? null : msg.id)}
                              className="text-slate-805 dark:text-slate-200 text-[13.5px] leading-relaxed cursor-pointer hover:bg-slate-100/50 dark:hover:bg-slate-900/50 p-1.5 rounded-lg transition-colors font-serif whitespace-pre-wrap select-text"
                              title="Click để hiển thị câu gốc"
                            >
                              {renderFormattedText(msg.text)}
                            </div>
                            
                            {inspectedMsgId === msg.id && msg.originalText && (
                              <div className="px-2.5 py-1.5 bg-slate-50 dark:bg-slate-900/40 rounded-lg border-l-2 border-indigo-400 text-slate-400 dark:text-slate-450 text-[11px] font-sans italic">
                                {msg.originalText}
                              </div>
                            )}
                          </div>
                        )}

                        {/* Image workflow with side-by-side MangaBubbleEditor */}
                        {msg.isImageWorkflow && (
                          <MangaBubbleEditor
                            projectId={projectId}
                            activeFile={activeFile}
                            msg={msg}
                            mangaViewMode={mangaViewModes[msg.assetId || ''] || 'original'}
                            setViewMode={(mode) => setMangaViewModes(prev => ({ ...prev, [msg.assetId || '']: mode }))}
                            handleSegmentChange={handleSegmentChange}
                            handleApproveAndRender={handleApproveAndRender}
                            selectedFont={selectedFont}
                            fontSize={fontSize}
                          />
                        )}

                        {/* QA validation feedback */}
                        {msg.status === 'done' && msg.validationIssues && msg.validationIssues.length > 0 && (
                          <div className="p-2.5 bg-amber-500/5 rounded-lg border border-amber-500/10 space-y-1.5">
                            <div className="text-[10px] font-bold text-amber-600 uppercase tracking-wider flex items-center gap-1 select-none">
                              <AlertTriangle size={11} />
                              <span>Cảnh báo QA:</span>
                            </div>
                            <div className="space-y-1">
                              {msg.validationIssues.map((issue, i) => (
                                <p key={i} className="text-[10.5px] text-slate-600 dark:text-slate-400 leading-normal">
                                  • {issue.message} ({issue.severity || 'Cảnh báo'})
                                </p>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Direct editorial action buttons for text */}
                        {msg.status === 'done' && !msg.isImageWorkflow && msg.sessionId && (
                          <div className="flex items-center gap-2 pt-2 border-t border-slate-100 dark:border-slate-900 select-none">
                            {msg.isApproved ? (
                              <span className="px-2.5 py-1 rounded-md text-[11px] font-semibold bg-emerald-500/10 text-emerald-600 dark:bg-emerald-950/20 dark:text-emerald-400 flex items-center gap-1.5">
                                <Check size={12} />
                                <span>Đã chốt bản dịch</span>
                              </span>
                            ) : (
                              <>
                                <button
                                  onClick={() => handleApproveChatMessage(msg.id, msg.sessionId || '')}
                                  className="px-2.5 py-1 rounded-md text-[11px] font-medium border border-slate-200 hover:border-emerald-500 hover:text-emerald-600 dark:border-slate-800 dark:hover:border-emerald-700 transition-colors bg-white dark:bg-slate-900 flex items-center gap-1"
                                >
                                  <CheckCircle2 size={12} />
                                  <span>OK (Chốt)</span>
                                </button>
                                <button
                                  onClick={() => {
                                      setEditingMessageId(editingMessageId === msg.id ? null : msg.id)
                                      setEditTranslationText(msg.text)
                                      setRefineFeedbackText('')
                                  }}
                                  className="px-2.5 py-1 rounded-md text-[11px] font-medium border border-slate-200 hover:border-indigo-500 hover:text-indigo-600 hover:bg-indigo-500/5 dark:border-slate-800 dark:hover:border-indigo-700 transition-colors bg-white dark:bg-slate-900 flex items-center gap-1"
                                >
                                  <MessageSquare size={12} />
                                  <span>Sửa & Góp ý</span>
                                </button>
                              </>
                            )}
                          </div>
                        )}

                        {/* Inline refinement dialog */}
                        {msg.status === 'done' && editingMessageId === msg.id && (
                          <div className="mt-3 p-3 border border-slate-100 dark:border-slate-850 bg-slate-50/50 dark:bg-slate-900/30 rounded-xl space-y-3 animate-in fade-in slide-in-from-top-1">
                            <div>
                              <label className="text-[10px] uppercase font-bold text-slate-400 tracking-wider block mb-1">Sửa trực tiếp bản dịch:</label>
                              <textarea
                                value={editTranslationText}
                                onChange={(e) => setEditTranslationText(e.target.value)}
                                className="w-full bg-white dark:bg-slate-950 border border-slate-250 dark:border-slate-800 rounded-lg p-2.5 text-xs text-slate-800 dark:text-slate-200 font-serif leading-relaxed focus:outline-none focus:ring-1 focus:ring-indigo-400 resize-none h-16"
                              />
                            </div>
                            <div>
                              <label className="text-[10px] uppercase font-bold text-slate-400 tracking-wider block mb-1">Yêu cầu sửa đổi thêm (Feedback):</label>
                              <input
                                type="text"
                                value={refineFeedbackText}
                                onChange={(e) => setRefineFeedbackText(e.target.value)}
                                placeholder="e.g. Dịch lãng mạn hơn, đổi xưng hô..."
                                className="w-full bg-white dark:bg-slate-950 border border-slate-250 dark:border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-400"
                              />
                            </div>
                            <div className="flex justify-end gap-1.5 select-none">
                              <button
                                onClick={() => setEditingMessageId(null)}
                                className="px-2.5 py-1 text-[11px] font-semibold text-slate-500 hover:text-slate-755 bg-transparent rounded"
                              >
                                Hủy
                              </button>
                              <button
                                onClick={() => handleSendRefinement(msg.id, msg.sessionId || '')}
                                className="px-3 py-1 text-[11px] font-semibold bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-955 rounded hover:opacity-90 transition-opacity"
                              >
                                Gửi
                              </button>
                            </div>
                          </div>
                        )}

                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Bottom Chat Input Box */}
        <div className="shrink-0 p-5 border-t border-themeBorder bg-white dark:bg-slate-950 select-none">
          <div className="max-w-4xl mx-auto w-full space-y-2.5">
            {/* Uploaded file preview */}
            {imagePreviewUrl && selectedFile && (
              <div className="flex items-center justify-between p-2 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="w-10 h-10 rounded border overflow-hidden bg-white dark:bg-slate-950 flex items-center justify-center shrink-0">
                    <img src={imagePreviewUrl} alt="Upload preview" className="max-w-full max-h-full object-contain" />
                  </div>
                  <div className="min-w-0">
                    <div className="text-xs font-semibold text-slate-800 dark:text-slate-250 truncate">{selectedFile.name}</div>
                    <div className="text-[10px] text-slate-400">{(selectedFile.size / 1024).toFixed(1)} KB</div>
                  </div>
                </div>
                <button 
                  onClick={() => {
                    setSelectedFile(null)
                    setImagePreviewUrl(null)
                  }}
                  className="p-1 rounded-full hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-600 transition-colors"
                >
                  <X size={14} />
                </button>
              </div>
            )}

            {/* Text input area */}
            <div className="relative flex items-center">
              <textarea
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    handleSendInput()
                  }
                }}
                disabled={isTranslating}
                placeholder="Nhập văn bản hoặc kéo thả/đính kèm ảnh vào đây..."
                className="w-full bg-slate-50/50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-xl pl-4 pr-24 py-3.5 text-xs text-slate-800 dark:text-slate-200 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-indigo-400/50 resize-none max-h-24 scrollbar-none disabled:opacity-50"
                rows={1}
              />
              <div className="absolute right-3 top-1/2 transform -translate-y-1/2 flex items-center gap-1.5">
                <input
                  type="file"
                  id="image-attach-input"
                  accept="image/*"
                  className="hidden"
                  onChange={handleImageFileSelect}
                />
                <label
                  htmlFor="image-attach-input"
                  className="p-2 rounded-lg cursor-pointer text-slate-400 hover:text-indigo-500 hover:bg-indigo-500/5 transition-all"
                  title="Đính kèm ảnh manga/comic"
                >
                  <Paperclip size={14} />
                </label>
                
                <button
                  onClick={handleSendInput}
                  disabled={isTranslating || (!chatInput.trim() && !selectedFile)}
                  className="p-2 rounded-lg text-slate-400 hover:text-indigo-500 hover:bg-indigo-500/5 disabled:opacity-30 disabled:hover:bg-transparent disabled:hover:text-slate-400 transition-all"
                >
                  <Send size={14} />
                </button>
              </div>
            </div>
          </div>
        </div>

      </section>

      {/* Slide-out Panel to view original sentences or edit them */}
      {showSourcePanel && (
        <div className="absolute inset-0 bg-slate-900/20 backdrop-blur-xs flex justify-end z-45 animate-in fade-in select-none">
          <div className="w-80 h-full bg-white dark:bg-slate-950 border-l border-themeBorder flex flex-col p-5 shadow-2xl animate-in slide-in-from-right">
            <div className="flex items-center justify-between border-b pb-3 mb-4">
              <div className="flex items-center gap-2">
                <BookOpen size={16} className="text-indigo-500" />
                <h2 className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider">Văn bản gốc</h2>
              </div>
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => setIsEditingOriginal(!isEditingOriginal)}
                  className="p-1.5 rounded-md hover:bg-slate-50 dark:hover:bg-slate-900 text-slate-500 hover:text-slate-700 transition-colors"
                  title={isEditingOriginal ? "Hoàn thành chỉnh sửa" : "Sửa văn bản gốc"}
                >
                  {isEditingOriginal ? <Check size={14} /> : <Edit3 size={14} />}
                </button>
                <button 
                  onClick={() => setShowSourcePanel(false)}
                  className="p-1.5 rounded-md hover:bg-slate-50 dark:hover:bg-slate-900 text-slate-500 hover:text-slate-700 transition-colors"
                >
                  <X size={14} />
                </button>
              </div>
            </div>

            {isEditingOriginal ? (
              <textarea
                value={original}
                onChange={(e) => setOriginal(e.target.value)}
                className="flex-1 w-full bg-slate-50/50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-xl p-4 text-xs font-serif leading-relaxed text-slate-800 dark:text-slate-200 resize-none focus:outline-none focus:ring-1 focus:ring-indigo-400 focus:ring-indigo-400/50"
                placeholder="Nhập nội dung văn bản gốc tại đây..."
              />
            ) : (
              <div className="flex-1 overflow-y-auto space-y-2.5 pr-1.5 scrollbar-thin">
                {originalSentences.map((sent, idx) => (
                  <div
                    key={idx}
                    className="p-2.5 rounded-lg border border-slate-100 dark:border-slate-900 bg-slate-50/30 dark:bg-slate-900/10 font-serif leading-relaxed text-slate-700 dark:text-slate-300"
                  >
                    <span className="text-[10px] font-bold text-indigo-500 block mb-0.5">Câu {idx + 1}</span>
                    <span className="text-xs">{sent}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

    </main>
  )
}
