'use client'

import React, { useEffect, useMemo, useRef, useState } from 'react'
import { showToast } from './toast'
import { useLanguage } from '@/app/i18n'
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
  Sparkles,
  Edit3,
  Paperclip,
  Type,
  Upload,
  ChevronDown,
  Search,
  Globe
} from 'lucide-react'
import {
  approveTranslation,
  exportChapter,
  getChapter,
  runTranslate,
  saveChapter,
  refineTranslation,
  saveSessionDraft,
  uploadFont,
  listFonts,
  runImageTranslate,
  renderDocumentImage,
  getImagePipelineStatus,
  getFontDownloadUrl,
  getDocumentSegments,
  updateSegmentText,
  uploadAssets,
  sendGeneralChat,
  upsertChatMessage,
  getChatHistory,
  deleteChatMessage,
  getChapterSummary,
  saveChapterSummary
} from '@/app/api-client'

import PipelineTracker from './PipelineTracker'
import MangaBubbleEditor from './MangaBubbleEditor'
import ReactMarkdown from 'react-markdown'

type WorkflowStep = 'read' | 'edit' | 'review' | 'approve'

const splitSentences = (txt: string) => {
  if (!txt) return []
  const sentences: string[] = []
  let current = ''
  let inQuotes = false
  let quoteChar = ''
  const punctTerminators = new Set(['.', '!', '?', '。', '！', '？'])
  const newlines = new Set(['\n', '\r'])
  
  for (let i = 0; i < txt.length; i++) {
    const char = txt[i]
    current += char
    
    if (char === '"' || char === '“' || char === '”' || char === '「' || char === '」' || char === '『' || char === '』') {
      if (!inQuotes && (char === '"' || char === '“' || char === '「' || char === '『')) {
        inQuotes = true
        quoteChar = char
      } else if (inQuotes) {
        if ((quoteChar === '「' && char === '」') || (quoteChar === '『' && char === '』') || (quoteChar === '“' && char === '”') || (quoteChar === '"' && char === '"')) {
          inQuotes = false
          quoteChar = ''
          
          let hasTerminatorBefore = current.length > 1 && (punctTerminators.has(current[current.length - 2]) || newlines.has(current[current.length - 2]))
          
          let nextCharIdx = i + 1
          while (nextCharIdx < txt.length && txt[nextCharIdx] === ' ') nextCharIdx++
          let nextChar = nextCharIdx < txt.length ? txt[nextCharIdx] : ''
          
          let nextIsUppercase = nextChar.length === 1 && nextChar.toUpperCase() === nextChar && nextChar.toLowerCase() !== nextChar
          let nextIsNewline = newlines.has(nextChar)
          let nextIsBracket = ['「','『','”','"','“'].includes(nextChar)
          
          if (hasTerminatorBefore || nextIsUppercase || nextIsNewline || nextIsBracket) {
            if (!(i + 1 < txt.length && (punctTerminators.has(txt[i+1]) || newlines.has(txt[i+1])))) {
              let peek = i + 1
              while (peek < txt.length && (txt[peek] === ' ' || txt[peek] === '\n' || txt[peek] === '\r')) {
                 current += txt[peek]
                 peek++
              }
              if (current.trim()) sentences.push(current)
              current = ''
              i = peek - 1
            }
          }
        }
      }
    } else if (!inQuotes) {
      if (punctTerminators.has(char)) {
        if (i + 1 < txt.length && punctTerminators.has(txt[i+1])) continue
        if (i + 1 < txt.length && ['」', '』', '”', '"'].includes(txt[i+1])) continue
        
        let peek = i + 1
        while (peek < txt.length && (txt[peek] === ' ' || txt[peek] === '\n' || txt[peek] === '\r')) {
           current += txt[peek]
           peek++
        }
        if (current.trim()) sentences.push(current)
        current = ''
        i = peek - 1
      } else if (newlines.has(char)) {
        if (i + 1 < txt.length && newlines.has(txt[i+1])) continue
        
        let peek = i + 1
        while (peek < txt.length && (txt[peek] === ' ' || txt[peek] === '\n' || txt[peek] === '\r')) {
           current += txt[peek]
           peek++
        }
        if (current.trim()) sentences.push(current)
        current = ''
        i = peek - 1
      }
    }
  }
  if (current.trim()) sentences.push(current)
  return sentences.filter(Boolean)
}

const parseUserMessage = (msg: string) => {
  const jpCharRegex = /[\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\uff00-\uff9f\u4e00-\u9faf\u4e00-\u9fff]/;
  
  let firstIdx = -1;
  let lastIdx = -1;
  for (let i = 0; i < msg.length; i++) {
    if (jpCharRegex.test(msg[i])) {
      if (firstIdx === -1) firstIdx = i;
      lastIdx = i;
    }
  }
  
  if (firstIdx !== -1) {
    while (firstIdx > 0 && /[\s\n"'「『\[（(]/.test(msg[firstIdx - 1])) {
      firstIdx--;
    }
    while (lastIdx < msg.length - 1 && /[\s\n"'」』\]）).!?。！？]/.test(msg[lastIdx + 1])) {
      lastIdx++;
    }
    
    const originalText = msg.substring(firstIdx, lastIdx + 1).trim();
    const instruction = (msg.substring(0, firstIdx) + " " + msg.substring(lastIdx + 1)).trim();
    
    return { originalText, instruction };
  }
  
  return { originalText: '', instruction: msg };
}

const renderFormattedText = (text: string) => {
  if (!text) return null
  const cleanText = text.replace(/\[s-\d+\]\s*/g, '')
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
      {cleanText}
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
  isGeneralChat?: boolean
  model?: string
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
  pipelineStep: 'idle' | 'ready' | 'translating' | 'polishing' | 'qa_check';
  setPipelineStep: (step: 'idle' | 'ready' | 'translating' | 'polishing' | 'qa_check') => void;
  pipelineLogs: string[];
  setPipelineLogs: (logs: string[] | ((prev: string[]) => string[])) => void;
}

const languages = [
  ['ja', '日本語 (Japanese)'],
  ['vi', 'Tiếng Việt (Vietnamese)'],
  ['en', 'English (English)'],
  ['zh', '中文 (Chinese)'],
  ['ko', '한국어 (Korean)'],
  ['lo', 'ພາສາລາວ (Lao)'],
  ['es', 'Español (Spanish)'],
  ['fr', 'Français (French)'],
  ['de', 'Deutsch (German)'],
  ['it', 'Italiano (Italian)'],
  ['ru', 'Русский (Russian)'],
  ['pt', 'Português (Portuguese)'],
  ['th', 'ไทย (Thai)'],
  ['id', 'Bahasa Indonesia (Indonesian)'],
  ['ms', 'Bahasa Melayu (Malay)'],
  ['ar', 'العربية (Arabic)'],
  ['hi', 'हिन्दी (Hindi)'],
  ['tl', 'Tagalog (Filipino)']
] as const

export default function CenterPanel({
  projectId,
  activeFile,
  showLeftSidebar = true,
  onToggleLeft,
  onStepChange,
  setPipelineStep
}: CenterPanelProps) {
  const { language, t } = useLanguage()
  const [original, setOriginal] = useState('')
  const [translation, setTranslation] = useState('')
  const [sourceLang] = useState('ja')
  const [targetLang, setTargetLang] = useState('vi')
  const [isTranslating, setIsTranslating] = useState(false)
  const [saveState, setSaveState] = useState<'saved' | 'saving' | 'failed'>('saved')
  const [isEditingOriginal, setIsEditingOriginal] = useState(false)
  const [loadedTitle, setLoadedTitle] = useState<string | null>(null)

  useEffect(() => {
    setLoadedTitle(null)
  }, [activeFile])

  const docTitle = useMemo(() => {
    if (loadedTitle) return loadedTitle
    if (!activeFile) return ''
    const clean = activeFile.replace(/\.md$/, '').replace(/_draft$/, '').replace(/_review$/, '').replace(/_final$/, '')
    const match = clean.match(/^ch(\d+)$/i)
    if (match) {
      return language === 'en' ? `Document ${parseInt(match[1], 10)}` : `Tài liệu ${parseInt(match[1], 10)}`
    }
    return clean.charAt(0).toUpperCase() + clean.slice(1)
  }, [activeFile, language, loadedTitle])

  // Custom searchable language dropdown state
  const [isLangOpen, setIsLangOpen] = useState(false)
  const [langQuery, setLangQuery] = useState('')
  const dropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsLangOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [])

  // Chat Timeline States
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
  const [chatInput, setChatInput] = useState('')

  const [editingMessageId, setEditingMessageId] = useState<string | null>(null)
  const [editTranslationText, setEditTranslationText] = useState('')
  const [refineFeedbackText, setRefineFeedbackText] = useState('')
  const [showSourcePanel, setShowSourcePanel] = useState(false)
  const chatEndRef = useRef<HTMLDivElement>(null)
  const persistedMessagesRef = useRef<Map<string, string>>(new Map())

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
  const [approvingMsgId, setApprovingMsgId] = useState<string | null>(null)
  const [chatLanguage, setChatLanguage] = useState<string>(language || 'vi')

  const [summaryModal, setSummaryModal] = useState<{
    isOpen: boolean
    docId: string
    summary: string
    loading: boolean
  }>({
    isOpen: false,
    docId: '',
    summary: '',
    loading: false
  })

  const triggerSummaryModal = async () => {
    if (!activeFile) return
    setSummaryModal({
      isOpen: true,
      docId: activeFile,
      summary: '',
      loading: true
    })
    try {
      const res = await getChapterSummary(projectId, activeFile)
      setSummaryModal(prev => ({ ...prev, summary: res.summary, loading: false }))
    } catch (err) {
      console.error(err)
      setSummaryModal(prev => ({ ...prev, loading: false }))
    }
  }

  useEffect(() => {
    if (language) {
      setChatLanguage(language)
    }
  }, [language])

  // Font manager states
  const [availableFonts, setAvailableFonts] = useState<string[]>([])
  const [selectedFont, setSelectedFont] = useState<string>('Noto Sans')
  const [fontSize, setFontSize] = useState<number>(18)

  // Active view for manga editor side-by-side (original or rendered)
  const [mangaViewModes, setMangaViewModes] = useState<Record<string, 'original' | 'rendered'>>({})

  // Tab and segment states for slide-out view
  const [activeTab, setActiveTab] = useState<'approved' | 'source'>('approved')
  const [segments, setSegments] = useState<any[]>([])
  const [expandedSegments, setExpandedSegments] = useState<Set<string>>(new Set())

  const toggleSegment = (segId: string) => {
    const next = new Set(expandedSegments)
    if (next.has(segId)) next.delete(segId)
    else next.add(segId)
    setExpandedSegments(next)
  }

  useEffect(() => {
    async function loadSegments() {
      if (showSourcePanel && projectId && activeFile) {
        try {
          const segs = await getDocumentSegments(projectId, activeFile)
          setSegments(segs || [])
        } catch (e) {
          console.error('Failed to load segments:', e)
        }
      }
    }
    loadSegments()
  }, [showSourcePanel, projectId, activeFile, chatMessages])

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

  // Load chapter data & chat history
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
        setPipelineStep('idle')
        onStepChange('read')

        let titleVal = ''
        if (data.draft) {
          const firstLine = data.draft.split('\n').find((l: string) => l.startsWith('# '))
          if (firstLine) {
            titleVal = firstLine.replace('# ', '').trim()
          }
        }
        if (!titleVal) {
          const clean = activeFile.replace(/\.md$/, '').replace(/_draft$/, '').replace(/_review$/, '').replace(/_final$/, '')
          const match = clean.match(/^ch(\d+)$/i)
          if (match) {
            titleVal = language === 'en' ? `Document ${parseInt(match[1], 10)}` : `Tài liệu ${parseInt(match[1], 10)}`
          } else {
            titleVal = clean.charAt(0).toUpperCase() + clean.slice(1)
          }
        }
        setLoadedTitle(titleVal || null)
        
        // Detect if active file is an image file (manga, comic, scan)
        const isImg = activeFile.toLowerCase().endsWith('.png') ||
                      activeFile.toLowerCase().endsWith('.jpg') ||
                      activeFile.toLowerCase().endsWith('.jpeg') ||
                      activeFile.toLowerCase().endsWith('.webp')
        setIsImageDoc(isImg)

        // Clear refs map on doc reload
        persistedMessagesRef.current.clear()

        // Fetch persisted chat history
        const history = await getChatHistory(projectId, activeFile)
        if (!active) return

        if (history && history.length > 0) {
          history.forEach(m => {
            const cacheKey = `${m.id}_${m.status}_${m.text?.length || 0}_${m.sessionId || ''}`
            persistedMessagesRef.current.set(m.id, cacheKey)
          })
          setChatMessages(history)
          
          // Resume polling if any message is processing
          const runningMsg = history.find(m => m.status === 'processing' && m.sessionId)
          if (runningMsg && runningMsg.sessionId) {
            setActiveSessionId(runningMsg.sessionId)
            if (runningMsg.isImageWorkflow && runningMsg.assetId) {
              setCurrentAssetId(runningMsg.assetId)
              setPipelineStep('translating')
              setIsTranslating(true)
            }
          }
        } else {
          // Populate timeline with initial greeting
          setChatMessages([
            {
              id: 'welcome',
              sender: 'ai',
              text: language === 'en'
                ? `Welcome to the **Localization Workspace** for document **${titleVal || activeFile}**. You can submit translation requests or attach manga/comic images to translate directly in this chat thread.`
                : `Chào mừng bạn đến với **Localization Workspace** cho tài liệu **${titleVal || activeFile}**. Bạn có thể gửi yêu cầu dịch văn bản hoặc đính kèm ảnh manga/comic để dịch trực tiếp trong luồng chat này.`,
              status: 'done',
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            }
          ])
        }
      } catch (err) {
        console.error('Failed to load chapter content or chat history:', err)
      }
    }
    load()
    return () => {
      active = false
    }
  }, [projectId, activeFile])

  // Auto-persist chat history messages when they change
  useEffect(() => {
    if (!projectId || !activeFile || chatMessages.length === 0) return
    
    // Skip welcome message
    const msgsToPersist = chatMessages.filter(m => m.id !== 'welcome')
    
    msgsToPersist.forEach(async (msg) => {
      const segmentsHash = msg.segments ? JSON.stringify(msg.segments) : ''
      const cacheKey = `${msg.id}_${msg.status}_${msg.text?.length || 0}_${msg.sessionId || ''}_${msg.isApproved ? '1' : '0'}_${segmentsHash}`
      if (persistedMessagesRef.current.get(msg.id) === cacheKey) {
        return
      }
      // Update ref cache immediately to prevent duplicate triggers
      persistedMessagesRef.current.set(msg.id, cacheKey)
      
      try {
        await upsertChatMessage(projectId, activeFile, msg)
      } catch (err) {
        console.error(`Failed to persist message ${msg.id}:`, err)
        // Evict key from ref map on failure so it can retry later
        persistedMessagesRef.current.delete(msg.id)
      }
    })
  }, [chatMessages, projectId, activeFile])

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
        const res = await getImagePipelineStatus(activeSessionId as string)
        if (!active) return
        
        if (res && res.pipeline_status) {
          setPipelineStatus(res.pipeline_status)
          
          // Update message text dynamically based on running pipeline stage
          const runningStageEntry = Object.entries(res.pipeline_status).find(([_, val]) => val === 'running')
          if (runningStageEntry) {
            const stage = runningStageEntry[0]
            let stageText = `Đang xử lý hình ảnh...`
            if (stage === 'ocr') stageText = 'Đang trích xuất văn bản từ hình ảnh (OCR)...'
            if (stage === 'context_retrieval') stageText = 'Đang nạp bối cảnh và bộ nhớ dự án...'
            if (stage === 'draft_translation') stageText = 'Đang tiến hành dịch thô các bong bóng thoại...'
            if (stage === 'review') stageText = 'Đang rà soát và tinh chỉnh bản dịch...'
            
            setChatMessages(prev => prev.map(m => m.sessionId === activeSessionId ? {
              ...m,
              text: stageText
            } : m))
          }
          
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
          const isReviewing = res.pipeline_status.review === 'success'

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
                segments: segs,
                model: res.model_name || ''
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

  const handleDeleteMessage = async (msgId: string) => {
    if (!msgId || msgId === 'welcome') return
    try {
      await deleteChatMessage(projectId, msgId)
      setChatMessages(prev => prev.filter(m => m.id !== msgId))
      
      // If we are deleting a paired prompt/response, delete the user request as well
      if (msgId.startsWith('ai_')) {
        const correspondingUserId = msgId.replace('ai_', 'user_')
        try {
          await deleteChatMessage(projectId, correspondingUserId)
        } catch (e) {}
        setChatMessages(prev => prev.filter(m => m.id !== msgId && m.id !== correspondingUserId))
      } else if (msgId.startsWith('user_')) {
        const correspondingAiId = msgId.replace('user_', 'ai_')
        try {
          await deleteChatMessage(projectId, correspondingAiId)
        } catch (e) {}
        setChatMessages(prev => prev.filter(m => m.id !== msgId && m.id !== correspondingAiId))
      }
      
      if (activeSessionId === msgId) {
        setActiveSessionId(null)
      }
    } catch (e) {
      console.error('Failed to delete chat message:', e)
    }
  }

  // Start text translation pipeline
  const startTranslationPipeline = async (rawPrompt: string, sourceText: string, instruction?: string) => {
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
        proposals: finalSession.memory_proposals || [],
        model: finalSession.model_name || ''
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

  // Start general chat assistant pipeline
  const startGeneralChatPipeline = async (promptText: string) => {
    const messageId = `msg_${Date.now()}`
    
    const userMsg: ChatMessage = {
      id: `user_${messageId}`,
      sender: 'user',
      text: promptText,
      status: 'done',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      isGeneralChat: true
    }
    
    const aiMsg: ChatMessage = {
      id: `ai_${messageId}`,
      sender: 'ai',
      text: '',
      status: 'processing',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      isGeneralChat: true
    }
    
    setChatMessages(prev => [...prev, userMsg, aiMsg])
    setIsTranslating(true)
    
    try {
      // Build history payload from previous general chat messages
      const history = chatMessages
        .filter(m => m.isGeneralChat && m.status === 'done')
        .slice(-10) // last 10 messages
        .map(m => ({
          role: m.sender === 'user' ? 'user' : 'assistant',
          content: m.text
        }))
        
      const res = await sendGeneralChat(projectId, activeFile, promptText, aiMsg.id, history, chatLanguage)
      
      setChatMessages(prev => prev.map(m => m.id === aiMsg.id ? {
        ...m,
        status: 'done',
        text: res.reply,
        model: res.model_name || ''
      } : m))
    } catch (err: any) {
      console.error(err)
      setChatMessages(prev => prev.map(m => m.id === aiMsg.id ? {
        ...m,
        status: 'failed',
        text: `${t('chatConnectionError')}: ${err.message || 'Error'}`
      } : m))
    } finally {
      setIsTranslating(false)
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
      // Standard text translation or general chat
      const { originalText, instruction } = parseUserMessage(chatInput)
      
      const isJp = /[\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\uff00-\uff9f\u4e00-\u9faf\u4e00-\u9fff]+/g.test(chatInput)
      const isTranslateKeyword = /\b(dịch|translate|translation|dich)\b/i.test(chatInput)
      
      const isTranslation = isJp || isTranslateKeyword
      
      if (isTranslation) {
        if (originalText) {
          startTranslationPipeline(chatInput, originalText, instruction)
        } else {
          // Treat user input text as the source text directly
          startTranslationPipeline(chatInput, chatInput)
        }
      } else {
        // Run general chatbot conversation assistant
        startGeneralChatPipeline(chatInput)
      }
      setChatInput('')
    }
  }

  // Save segment inline editing
  const handleSegmentChange = async (msgId: string, _assetId: string, segmentId: string, newText: string) => {
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
    setApprovingMsgId(msgId)
    try {
      // 1. Approve session (adds translations to memory)
      await approveTranslation(projectId, sessionId)
      
      setChatMessages(prev => prev.map(m => m.id === msgId ? { ...m, isApproved: true } : m))
      setPipelineStatus(prev => ({
        ...prev,
        review: 'success',
        approve: 'success',
        render: 'running'
      }))

      // 2. Call Pillow rendering
      await renderDocumentImage(projectId, activeFile, assetId, selectedFont, fontSize, sessionId)
      
      setPipelineStatus(prev => ({ ...prev, render: 'success' }))
      
      // Update preview to rendered image
      setMangaViewModes(prev => ({ ...prev, [assetId]: 'rendered' }))
      showToast('Đã phê duyệt và vẽ dịch thành công!', 'success')
    } catch (err: any) {
      showToast(`Lỗi phê duyệt và vẽ dịch: ${err.message}`, 'error')
      setPipelineStatus(prev => ({ ...prev, render: 'failed' }))
    } finally {
      setApprovingMsgId(null)
    }
  }

  const handleApproveChatMessage = async (msgId: string, sessionId: string) => {
    setApprovingMsgId(msgId)
    try {
      await approveTranslation(projectId, sessionId)
      setChatMessages(prev => prev.map(m => m.id === msgId ? { ...m, isApproved: true } : m))
      setPipelineStatus(prev => ({ 
        ...prev, 
        review: 'success',
        approve: 'success' 
      }))
      showToast('Đã duyệt bản dịch thành công!', 'success')
    } catch (err: any) {
      showToast(`Lỗi khi duyệt bản dịch: ${err.message}`, 'error')
    } finally {
      setApprovingMsgId(null)
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
      originalText: originalMsg.originalText,
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
      showToast(`Đã tải lên font custom ${res.font_name} thành công!`, 'success')
      const listRes = await listFonts(projectId)
      setAvailableFonts([...listRes.default_fonts, ...listRes.custom_fonts])
    } catch (err: any) {
      showToast(`Lỗi tải lên font: ${err.message}`, 'error')
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
            <h1 className="text-sm font-semibold text-slate-850 dark:text-slate-200 truncate">{docTitle}</h1>
            <p className="text-xs text-slate-400 truncate">
              {pipelineStatus.review === 'running' ? t('workspaceReviewText') : t('workspaceIntroText')}
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
              title={t('uploadFontTooltip')}
            >
              <Upload size={12} />
            </label>
          </div>

          {/* Chapter Summary Trigger */}
          <button 
            onClick={triggerSummaryModal}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-900 transition-colors"
            title={t('chapterSummaryTitle')}
          >
            <Sparkles size={13} className="text-amber-500 fill-amber-500/20" />
            <span>{t('chapterSummaryTitle')}</span>
          </button>

          {/* View Source & Approved Translation panel trigger */}
          <button 
            onClick={() => setShowSourcePanel(!showSourcePanel)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold border transition-colors ${
              showSourcePanel 
                ? 'border-indigo-500 bg-indigo-500/5 text-indigo-600 dark:text-indigo-400' 
                : 'border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-900'
            }`}
            title={t('viewBilingualTooltip')}
          >
            <BookOpen size={13} />
            <span>{t('bilingualView')}</span>
          </button>

          {/* Export/Download Button */}
          <button 
            onClick={handleExport}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold border border-slate-200 dark:border-slate-850 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-900 transition-colors"
            title={t('downloadTranslation')}
          >
            <Download size={13} />
            <span>{t('download')}</span>
          </button>
        </div>
      </div>

      {/* Visual tracker sub-component */}
      <PipelineTracker pipelineStatus={pipelineStatus} isImageDoc={isImageDoc} />

      {/* Main Full-Bleed Chat Container */}
      <section className="flex-1 min-h-0 overflow-hidden flex flex-col relative bg-white dark:bg-slate-950">
        
        {/* Chat Header */}
        <div className="h-10 px-5 border-b border-themeBorder flex items-center justify-between bg-slate-55/30 dark:bg-slate-900/10 shrink-0 select-none">
          <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">{t('localizationWorkspace')}</span>
          <div className="flex items-center gap-2">
            {/* AI Assistant Chat Language Selector */}
            <span className="text-[10px] text-themeMuted uppercase font-bold tracking-wider flex items-center gap-1">
              <Globe size={11} className="text-slate-400 shrink-0" />
              <span>{t('aiChatLabel')}</span>
            </span>
            <select
              value={chatLanguage}
              onChange={(e) => setChatLanguage(e.target.value)}
              className="bg-transparent border-none text-[11px] font-semibold text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-all select-none focus:ring-0 focus:outline-none p-0 cursor-pointer mr-2 pr-1"
            >
              <option value="vi" className="bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-200">Tiếng Việt</option>
              <option value="en" className="bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-200">English</option>
              <option value="ja" className="bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-200">日本語</option>
              <option value="zh" className="bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-200">中文</option>
              <option value="ko" className="bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-200">한국어</option>
              <option value="lo" className="bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-200">ພາສາລາວ</option>
              <option value="es" className="bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-200">Español</option>
              <option value="fr" className="bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-200">Français</option>
              <option value="de" className="bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-200">Deutsch</option>
              <option value="it" className="bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-200">Italiano</option>
              <option value="ru" className="bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-200">Русский</option>
              <option value="pt" className="bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-200">Português</option>
              <option value="th" className="bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-200">ไทย</option>
              <option value="id" className="bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-200">Bahasa Indonesia</option>
              <option value="ms" className="bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-200">Bahasa Melayu</option>
              <option value="ar" className="bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-200">العربية</option>
              <option value="hi" className="bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-200">हिन्दी</option>
              <option value="tl" className="bg-white dark:bg-slate-950 text-slate-800 dark:text-slate-200">Tagalog</option>
            </select>

            <span className="text-[10px] text-themeMuted uppercase font-bold tracking-wider border-l pl-2 border-themeBorder">{t('targetLangLabel')}:</span>
            
            {/* Custom Searchable Dropdown */}
            <div className="relative inline-block text-left" ref={dropdownRef}>
              <button
                type="button"
                onClick={() => {
                  setIsLangOpen(!isLangOpen)
                  setLangQuery('')
                }}
                className="flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-semibold text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-all select-none"
              >
                <span>{languages.find(([v]) => v === targetLang)?.[1] || targetLang}</span>
                <ChevronDown size={12} className={`text-slate-400 dark:text-slate-500 transition-transform ${isLangOpen ? 'rotate-180' : ''}`} />
              </button>

              {isLangOpen && (
                <div className="absolute right-0 top-full mt-2 w-64 rounded-xl border border-slate-200/80 dark:border-slate-850 bg-white/90 dark:bg-slate-900/90 backdrop-blur-md shadow-2xl overflow-hidden z-[9999]">
                  <div className="p-2 border-b border-slate-150 dark:border-slate-850 flex items-center gap-2 bg-slate-50/50 dark:bg-slate-950/30">
                    <Search size={14} className="text-slate-400 dark:text-slate-500 shrink-0" />
                    <input
                      type="text"
                      value={langQuery}
                      onChange={(e) => setLangQuery(e.target.value)}
                      placeholder={t('searchLanguagePlaceholder')}
                      className="w-full bg-transparent border-0 text-xs text-slate-700 dark:text-slate-200 focus:ring-0 focus:outline-none p-0"
                      autoFocus
                    />
                  </div>
                  <div className="max-h-60 overflow-y-auto py-1 scrollbar-none">
                    {(() => {
                      const filtered = languages.filter(([_, label]) =>
                        label.toLowerCase().includes(langQuery.toLowerCase())
                      )
                      if (filtered.length === 0) {
                        return (
                          <div className="px-4 py-3 text-xs text-center text-slate-400 dark:text-slate-500 font-medium">
                            No languages found
                          </div>
                        )
                      }
                      return filtered.map(([value, label]) => {
                        const isSelected = value === targetLang
                        return (
                          <button
                            key={value}
                            type="button"
                            onClick={() => {
                              setTargetLang(value)
                              setIsLangOpen(false)
                            }}
                            className={`w-full px-3 py-2 text-left text-xs flex items-center justify-between hover:bg-indigo-55 dark:hover:bg-indigo-950/40 transition-colors ${
                              isSelected
                                ? 'text-indigo-600 dark:text-indigo-400 font-semibold bg-indigo-50/40 dark:bg-indigo-950/20'
                                : 'text-slate-600 dark:text-slate-400'
                            }`}
                          >
                            <span>{label}</span>
                            {isSelected && <Check size={12} className="text-indigo-500 shrink-0" />}
                          </button>
                        )
                      })
                    })()}
                  </div>
                </div>
              )}
            </div>

            <span className="text-[11px] text-themeMuted select-none border-l pl-2 border-themeBorder">{saveState === 'saving' ? t('saving') : t('saved')} · {wordCount} {t('words')}</span>
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
                {t('workspaceIntro')}
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
                            {isUser ? t('you') : t('system')}
                          </span>
                          <div className="flex items-center gap-2 select-none">
                            {!isUser && msg.model && (
                              <span className="text-[10px] text-indigo-500/80 bg-indigo-500/5 px-1.5 py-0.5 rounded font-mono border border-indigo-500/10">
                                {msg.model}
                              </span>
                            )}
                            <span className="text-[10px] text-slate-400">
                              {msg.timestamp}
                            </span>
                            {msg.id !== 'welcome' && (
                              <button
                                onClick={() => handleDeleteMessage(msg.id)}
                                className="text-slate-300 hover:text-red-500 transition-colors p-0.5 rounded hover:bg-slate-100 dark:hover:bg-slate-900"
                                title={t('deleteMsgConfirm')}
                              >
                                <X size={12} />
                              </button>
                            )}
                          </div>
                        </div>

                        {/* Processing indicators */}
                        {msg.status === 'processing' && (
                          <div className="flex items-center gap-2 text-slate-400">
                            <Loader2 size={12} className="animate-spin text-indigo-500" />
                            <span>
                              {msg.isImageWorkflow 
                                ? (msg.text || t('processingImage'))
                                : (msg.isGeneralChat 
                                    ? t('draftingAnswer') 
                                    : t('translatingAndAuditing'))}
                            </span>
                          </div>
                        )}

                        {msg.status === 'failed' && (
                          <div className="text-red-500 flex items-center gap-2 p-2 rounded bg-red-500/5 border border-red-500/10">
                            <AlertTriangle size={14} />
                            <span>{msg.text}</span>
                          </div>
                        )}

                        {/* Text translation result */}
                        {msg.status === 'done' && (!msg.isImageWorkflow || isUser) && (
                          <div className="space-y-2">
                            {isUser || !msg.originalText ? (
                              <div 
                                className="text-slate-850 dark:text-slate-200 text-[13.5px] leading-relaxed font-serif whitespace-pre-wrap select-text"
                              >
                                {msg.id === 'welcome' 
                                  ? renderFormattedText(t('welcomeMsg').replace('{activeFile}', docTitle))
                                  : renderFormattedText(msg.text)}
                              </div>
                            ) : (
                              <div className="text-slate-850 dark:text-slate-200 text-[13.5px] leading-relaxed font-serif whitespace-pre-wrap select-text block">
                                {(() => {
                                  const ts = splitSentences(msg.text)
                                  const ss = splitSentences(msg.originalText)
                                  return ts.map((sentence, index) => {
                                    const key = `${msg.id}-${index}`
                                    const isExpanded = inspectedMsgId === key
                                    
                                    let sIdx = index
                                    let cleanSentence = sentence
                                    const match = sentence.match(/^\[s-(\d+)\]\s*(.*)/s)
                                    if (match) {
                                      sIdx = parseInt(match[1], 10)
                                      cleanSentence = match[2]
                                    } else {
                                      if (ts.length > 0 && ss.length > 0 && ts.length !== ss.length) {
                                        sIdx = Math.min(Math.floor(index * (ss.length / ts.length)), ss.length - 1)
                                      }
                                    }
                                    
                                    const sourceSentence = ss[sIdx] || ss[ss.length - 1] || msg.originalText
                                    
                                    return (
                                      <span key={key} className="inline group cursor-pointer" onClick={() => setInspectedMsgId(isExpanded ? null : key)}>
                                        {isExpanded && sourceSentence && (
                                          <span className="block my-2 p-2.5 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg border-l-2 border-indigo-400 text-indigo-900 dark:text-indigo-200 font-sans text-[12px] leading-relaxed whitespace-pre-wrap font-medium shadow-sm w-full">
                                            {sourceSentence}
                                          </span>
                                        )}
                                        <span className="hover:bg-indigo-500/10 dark:hover:bg-indigo-400/20 hover:text-indigo-600 dark:hover:text-indigo-300 transition-colors rounded" title="Click để xem bản gốc">
                                          {cleanSentence}
                                        </span>
                                      </span>
                                    )
                                  })
                                })()}
                              </div>
                            )}
                          </div>
                        )}

                        {/* Image workflow with side-by-side MangaBubbleEditor */}
                        {msg.isImageWorkflow && !isUser && msg.status === 'done' && (
                          <MangaBubbleEditor
                            projectId={projectId}
                            activeFile={activeFile}
                            msg={msg}
                            mangaViewMode={mangaViewModes[msg.assetId || ''] || 'original'}
                            setViewMode={(mode) => setMangaViewModes(prev => ({ ...prev, [msg.assetId || '']: mode }))}
                            handleSegmentChange={handleSegmentChange}
                            handleApproveAndRender={handleApproveAndRender}
                            selectedFont={selectedFont}
                            setSelectedFont={setSelectedFont}
                            fontSize={fontSize}
                            setFontSize={setFontSize}
                            availableFonts={availableFonts}
                            isApproving={approvingMsgId === msg.id}
                          />
                        )}

                        {/* QA validation feedback - Temporarily hidden
                        msg.status === 'done' && msg.validationIssues && msg.validationIssues.length > 0 && (
                          <div className="p-2.5 bg-amber-500/5 rounded-lg border border-amber-500/10 space-y-1.5">
                            <div className="text-[10px] font-bold text-amber-600 uppercase tracking-wider flex items-center gap-1 select-none">
                              <AlertTriangle size={11} />
                              <span>Cảnh báo QA:</span>
                            </div>
                            <div className="space-y-1">
                              {msg.validationIssues.map((issue, i) => {
                                const messageText = issue.detail || issue.message || 'Phát hiện vấn đề chưa xác định';
                                const typeText = issue.violation_type || issue.severity || 'Cảnh báo';
                                const suggestionText = issue.suggestion ? ` (Gợi ý: ${issue.suggestion})` : '';
                                return (
                                  <p key={i} className="text-[10.5px] text-slate-600 dark:text-slate-400 leading-normal">
                                    • {messageText}{suggestionText} <span className="text-[9.5px] text-slate-400">[{typeText}]</span>
                                  </p>
                                );
                              })}
                            </div>
                          </div>
                        )
                        */}

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
                                  disabled={approvingMsgId === msg.id}
                                  onClick={() => handleApproveChatMessage(msg.id, msg.sessionId || '')}
                                  className={`px-2.5 py-1 rounded-md text-[11px] font-medium border border-slate-200 transition-colors bg-white dark:bg-slate-900 flex items-center gap-1 ${
                                    approvingMsgId === msg.id
                                      ? 'text-slate-400 border-slate-100 dark:border-slate-800 cursor-not-allowed'
                                      : 'hover:border-emerald-500 hover:text-emerald-600 dark:border-slate-800 dark:hover:border-emerald-700'
                                  }`}
                                >
                                  {approvingMsgId === msg.id ? (
                                    <Loader2 size={12} className="animate-spin text-slate-400" />
                                  ) : (
                                    <CheckCircle2 size={12} />
                                  )}
                                  <span>{approvingMsgId === msg.id ? 'Đang duyệt...' : 'OK (Chốt)'}</span>
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
                <h2 className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider">{t('bilingualView')}</h2>
              </div>
              <div className="flex items-center gap-1.5">
                {activeTab === 'source' && (
                  <button
                    onClick={async () => {
                      if (isEditingOriginal) {
                        setSaveState('saving')
                        try {
                          await saveChapter(projectId, activeFile, { source_text: original })
                          setSaveState('saved')
                        } catch (err) {
                          console.error('Failed to save original text:', err)
                          setSaveState('failed')
                        }
                      }
                      setIsEditingOriginal(!isEditingOriginal)
                    }}
                    className="p-1.5 rounded-md hover:bg-slate-50 dark:hover:bg-slate-900 text-slate-500 hover:text-slate-700 transition-colors"
                    title={isEditingOriginal ? t('doneEditing') : t('editOriginal')}
                  >
                    {isEditingOriginal ? <Check size={14} /> : <Edit3 size={14} />}
                  </button>
                )}
                <button 
                  onClick={() => setShowSourcePanel(false)}
                  className="p-1.5 rounded-md hover:bg-slate-50 dark:hover:bg-slate-900 text-slate-500 hover:text-slate-700 transition-colors"
                >
                  <X size={14} />
                </button>
              </div>
            </div>

            {/* Tab selector */}
            <div className="flex border-b border-slate-100 dark:border-slate-800 mb-4 select-none shrink-0">
              <button
                onClick={() => {
                  setActiveTab('approved')
                  setIsEditingOriginal(false)
                }}
                className={`flex-1 pb-2 text-[10px] font-bold uppercase tracking-wider text-center border-b-2 transition-all ${
                  activeTab === 'approved'
                    ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                    : 'border-transparent text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'
                }`}
              >
                {t('approvedTranslationTitle')}
              </button>
              <button
                onClick={() => setActiveTab('source')}
                className={`flex-1 pb-2 text-[10px] font-bold uppercase tracking-wider text-center border-b-2 transition-all ${
                  activeTab === 'source'
                    ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                    : 'border-transparent text-slate-400 hover:text-slate-655 dark:hover:text-slate-300'
                }`}
              >
                {t('sourceTextTitle')}
              </button>
            </div>

            {activeTab === 'approved' ? (
              <div className="flex-1 overflow-y-auto space-y-3.5 pr-1.5 scrollbar-thin">
                {segments.length === 0 ? (
                  <p className="text-xs text-slate-400 text-center py-6">Chưa có phân đoạn nào được dịch hoặc duyệt.</p>
                ) : (
                  segments.map((seg, idx) => {
                    const segKey = seg.segment_id || idx.toString()
                    const targetSentences = splitSentences(seg.target_text)
                    const sourceSentences = splitSentences(seg.source_text)
                    
                    return (
                    <div
                      key={segKey}
                      className="p-3 rounded-lg border border-slate-100 dark:border-slate-900 bg-slate-50/20 dark:bg-slate-900/10 space-y-1.5"
                    >
                      <div className="flex items-center justify-between text-[10px] text-slate-455 dark:text-slate-400 font-bold uppercase tracking-wide mb-1">
                        <span>Đoạn {idx + 1}</span>
                        {seg.approved_at ? (
                          <span className="text-emerald-500 bg-emerald-500/5 px-1.5 py-0.2 rounded font-medium normal-case">Đã duyệt</span>
                        ) : (
                          <span className="text-amber-500 bg-amber-500/5 px-1.5 py-0.2 rounded font-medium normal-case font-semibold">Bản nháp</span>
                        )}
                      </div>
                      <div className="space-y-1 block">
                        {!seg.target_text ? (
                          <span className="italic text-slate-450 text-xs font-serif">[Chưa có bản dịch đã duyệt]</span>
                        ) : (
                          targetSentences.map((sentence: string, index: number) => {
                            const sentenceKey = `${segKey}-${index}`
                            const isExpanded = expandedSegments.has(sentenceKey)
                            
                            let sIdx = index
                            let cleanSentence = sentence
                            const match = sentence.match(/^\[s-(\d+)\]\s*(.*)/s)
                            if (match) {
                              sIdx = parseInt(match[1], 10)
                              cleanSentence = match[2]
                            } else {
                              if (targetSentences.length > 0 && sourceSentences.length > 0 && targetSentences.length !== sourceSentences.length) {
                                sIdx = Math.min(Math.floor(index * (sourceSentences.length / targetSentences.length)), sourceSentences.length - 1)
                              }
                            }
                            const sourceText = sourceSentences[sIdx] || sourceSentences[sourceSentences.length - 1]
                            
                            return (
                              <span key={sentenceKey} className="inline group cursor-pointer" onClick={() => toggleSegment(sentenceKey)}>
                                {isExpanded && sourceText && (
                                  <span className="block my-1 p-2 bg-indigo-50 dark:bg-indigo-900/20 rounded border-l-2 border-indigo-400 text-indigo-900 dark:text-indigo-200 font-sans text-[12px] leading-relaxed whitespace-pre-wrap font-medium shadow-sm">
                                    {sourceText}
                                  </span>
                                )}
                                <span className="text-[13px] font-serif leading-relaxed text-slate-800 dark:text-slate-200 whitespace-pre-wrap hover:bg-indigo-500/10 dark:hover:bg-indigo-400/20 hover:text-indigo-600 dark:hover:text-indigo-300 transition-colors rounded">
                                  {cleanSentence}
                                </span>
                              </span>
                            )
                          })
                        )}
                      </div>
                    </div>
                  )})
                )}
              </div>
            ) : isEditingOriginal ? (
              <textarea
                value={original}
                onChange={(e) => setOriginal(e.target.value)}
                className="flex-1 w-full bg-slate-50/50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 rounded-xl p-4 text-xs font-serif leading-relaxed text-slate-800 dark:text-slate-200 resize-none focus:outline-none focus:ring-1 focus:ring-indigo-400 focus:ring-indigo-400/50"
                placeholder={t('enterOriginalPlaceholder')}
              />
            ) : (
              <div className="flex-1 overflow-y-auto space-y-2.5 pr-1.5 scrollbar-thin">
                {originalSentences.map((sent, idx) => (
                  <div
                    key={idx}
                    className="p-2.5 rounded-lg border border-slate-100 dark:border-slate-900 bg-slate-50/30 dark:bg-slate-900/10 font-serif leading-relaxed text-slate-700 dark:text-slate-350"
                  >
                    <span className="text-[10px] font-bold text-indigo-500 block mb-0.5">
                      {t('sentenceLabel')} {idx + 1}
                    </span>
                    <span className="text-xs">{sent}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {summaryModal.isOpen && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center z-[9999] animate-in fade-in select-none">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-2xl p-6 max-w-md w-full mx-4 text-left">
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-2">Tóm tắt chương (Layer 2 CS)</h2>
            <p className="text-xs text-slate-500 mb-4">
              Xem lại và chỉnh sửa bản tóm tắt chương 2-3 câu để duy trì tính nhất quán mạch truyện.
            </p>
            {summaryModal.loading ? (
              <div className="flex flex-col items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-accent-purple" />
                <span className="text-xs text-slate-400 mt-2">Đang tạo tóm tắt nháp bằng LLM...</span>
              </div>
            ) : (
              <textarea
                value={summaryModal.summary}
                onChange={e => setSummaryModal(prev => ({ ...prev, summary: e.target.value }))}
                className="w-full h-32 bg-transparent border border-slate-200 dark:border-slate-800 rounded p-2 text-xs text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-accent-purple resize-none"
                placeholder="Nhập 2-3 câu tóm tắt chương truyện..."
              />
            )}
            <div className="flex justify-end gap-2 mt-4">
              <button
                type="button"
                onClick={() => setSummaryModal(prev => ({ ...prev, isOpen: false }))}
                className="px-3 py-1.5 rounded text-xs font-semibold text-slate-500 hover:bg-slate-500/10"
              >
                Bỏ qua
              </button>
              <button
                type="button"
                disabled={summaryModal.loading || !summaryModal.summary.trim()}
                onClick={async () => {
                  try {
                    await saveChapterSummary(projectId, summaryModal.docId, summaryModal.summary)
                    showToast('Đã lưu tóm tắt chương truyện thành công!', 'success')
                    setSummaryModal(prev => ({ ...prev, isOpen: false }))
                  } catch (err) {
                    showToast('Không thể lưu tóm tắt chương truyện.', 'error')
                  }
                }}
                className="bg-indigo-600 text-white px-4 py-1.5 rounded text-xs font-semibold hover:bg-indigo-750 disabled:opacity-50"
              >
                Lưu tóm tắt
              </button>
            </div>
          </div>
        </div>
      )}

    </main>
  )
}
