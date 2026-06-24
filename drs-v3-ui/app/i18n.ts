'use client'

import React, { createContext, useContext, useState, useEffect } from 'react'

export type Language = 'en' | 'vi'

const translations = {
  en: {
    dashboardTitle: 'DRS v3 - Project Hub',
    selectProject: 'Select Project',
    searchProjects: 'Search projects...',
    createProjectBtn: 'Create Project',
    createNewProjectTitle: 'Create New Project',
    projectNameLabel: 'Project Name',
    cancel: 'Cancel',
    create: 'Create',
    creating: 'Creating...',
    enterProjNameWarning: 'Please enter a project name.',
    createProjSuccess: 'Project created successfully.',
    createProjError: 'Failed to create project:',
    pages: 'pages',
    updatedAt: 'Updated',
    justNow: 'Just now',
    
    // Project page
    documents: 'Documents',
    searchDocs: 'Search documents...',
    createDocBtn: 'Create Document',
    createNewDocTitle: 'Create New Document',
    docTitleLabel: 'Document Title',
    docPlaceholder: 'e.g. Chapter 1: The Gathering',
    enterDocTitleWarning: 'Please enter a document title.',
    createDocSuccess: 'Document created successfully.',
    createDocError: 'Failed to create document:',
    loadingDocs: 'Loading documents...',
    translateCTA: 'Translate',
    
    // Left Sidebar & workspace tabs
    sidebarDocuments: 'Documents',
    sidebarGlossary: 'Glossary',
    sidebarStyleGuide: 'Style Guide',
    sidebarAssets: 'Visual Assets',
    sidebarSettings: 'Settings',
    
    // Workspace
    sourcePlaceholder: 'Japanese source text here...',
    translateBtn: 'Translate',
    translatingBtn: 'Translating...',
    saveBtn: 'Save',
    savingBtn: 'Saving...',
    approveBtn: 'Approve',
    approvedBtn: 'Approved',
    sourceLang: 'Source',
    targetLang: 'Target',
    chatPlaceholder: 'Ask AI or type instructions (e.g. "make it more formal")...',
    send: 'Send',
    thinking: 'Thinking...',
    validationIssues: 'Validation Issues',
    noValidationIssues: 'No issues found. Translation looks good!',
    ref: 'Reference:',
    auditorSuggestions: 'Auditor Suggestions',
    score: 'Quality Score',
    
    // Settings / Glossary / Style Guide
    glossaryTitle: 'Project Glossary',
    styleTitle: 'Style Guide Rules',
    assetsTitle: 'Visual Assets Reference',
    addEntry: 'Add Entry',
    termJa: 'Source Term',
    termVi: 'Target Term',
    category: 'Category',
    description: 'Description',
    exampleBefore: 'Before Example',
    exampleAfter: 'After Example',
    uploadAssets: 'Upload Assets',
    noAssets: 'No assets uploaded yet.',
    noGlossary: 'Glossary is empty.',
    noStyle: 'No style rules defined.',
    
    // Global Header
    logout: 'Log out',
    themeLight: 'Light Mode',
    themeDark: 'Dark Mode',

    // New translation keys
    deleteDocConfirm: 'Are you sure you want to delete this document? This action is permanent.',
    deleteDocSuccess: 'Document deleted successfully.',
    deleteDocError: 'Failed to delete document:',
    uploadDocSuccess: 'File uploaded successfully! The system is translating automatically in the background.',
    uploadDocError: 'Failed to upload file:',
    activeDocument: 'Active Document',
    targetLangLabel: 'Target',
    saved: 'Saved',
    saving: 'Saving...',
    words: 'words',
    deleteMsgConfirm: 'Delete this message',
    processingImage: 'Processing image...',
    draftingAnswer: 'Drafting answer...',
    translatingAndAuditing: 'Translating draft and auditing rules...',
    sentenceLabel: 'Sentence',
    bilingualView: 'Bilingual View',
    downloadTranslation: 'Download translation',
    backToChapters: 'Back to chapters',
    searchLanguagePlaceholder: 'Search language...',
    project: 'Project',
    uploadTxtTooltip: 'Upload TXT file for background translation',
    deleteDoc: 'Delete document',
    docExists: 'A document with that name already exists.',
    newDocPrompt: 'New document name:',
    hideSidebar: 'Hide sidebar',
    projectMemory: 'Project Memory',
    projectMemoryTooltip: 'Project Memory Cache',
    switchLanguage: 'Switch Language',
    download: 'Download',
    workspaceIntro: 'Submit your source text, ask instructions, or upload an image to start the workflow.',
    viewBilingualTooltip: 'View Translation and Source',
    you: 'You',
    system: 'System',
    doneEditing: 'Done editing',
    editOriginal: 'Edit original text',
    approvedTranslationTitle: 'Approved Translation',
    sourceTextTitle: 'Source Text',
    enterOriginalPlaceholder: 'Enter original text content here...',
    chatConnectionError: 'Failed to connect to assistant',
    uploadFontTooltip: 'Upload custom font (.ttf/.otf)',
    welcomeMsg: 'Welcome to the **Localization Workspace** for document **{activeFile}**. You can submit translation requests or attach manga/comic images to translate directly in this chat thread.',
    pipelineProgress: 'Pipeline Progress:',
    localizationWorkspace: 'Localization Workspace',
    workspaceIntroText: 'Submit a text translation prompt or upload a manga/comic image.',
    workspaceReviewText: 'Review & approve the localization drafts below.',
    aiChatLabel: 'AI Chat:',
    stepUpload: 'Upload',
    stepOcr: 'OCR',
    stepContext: 'Context',
    stepDraft: 'Draft',
    stepReview: 'Review',
    stepApprove: 'Approve',
    stepRender: 'Render'
  },
  vi: {
    dashboardTitle: 'DRS v3 - Quản lý Dự án',
    selectProject: 'Chọn Dự án',
    searchProjects: 'Tìm kiếm dự án...',
    createProjectBtn: 'Tạo Dự án',
    createNewProjectTitle: 'Tạo Dự án Mới',
    projectNameLabel: 'Tên dự án',
    cancel: 'Hủy',
    create: 'Tạo',
    creating: 'Đang tạo...',
    enterProjNameWarning: 'Vui lòng nhập tên dự án.',
    createProjSuccess: 'Đã tạo dự án mới thành công.',
    createProjError: 'Không thể tạo dự án mới:',
    pages: 'tài liệu',
    updatedAt: 'Cập nhật',
    justNow: 'Vừa xong',
    
    // Project page
    documents: 'Danh sách Tài liệu',
    searchDocs: 'Tìm kiếm tài liệu...',
    createDocBtn: 'Tạo Tài liệu',
    createNewDocTitle: 'Tạo Tài liệu Mới',
    docTitleLabel: 'Tiêu đề Tài liệu',
    docPlaceholder: 'Ví dụ: Chương 1: Khởi đầu cuộc hành trình',
    enterDocTitleWarning: 'Vui lòng nhập tiêu đề tài liệu.',
    createDocSuccess: 'Tạo tài liệu mới thành công.',
    createDocError: 'Không thể tạo tài liệu mới:',
    loadingDocs: 'Đang tải tài liệu...',
    translateCTA: 'Dịch',
    
    // Left Sidebar & workspace tabs
    sidebarDocuments: 'Tài liệu',
    sidebarGlossary: 'Thuật ngữ',
    sidebarStyleGuide: 'Phong cách',
    sidebarAssets: 'Hình ảnh',
    sidebarSettings: 'Cài đặt',
    
    // Workspace
    sourcePlaceholder: 'Nhập văn bản tiếng Nhật nguồn tại đây...',
    translateBtn: 'Dịch thuật',
    translatingBtn: 'Đang dịch...',
    saveBtn: 'Lưu nháp',
    savingBtn: 'Đang lưu...',
    approveBtn: 'Phê duyệt',
    approvedBtn: 'Đã duyệt',
    sourceLang: 'Nguồn',
    targetLang: 'Mục tiêu',
    chatPlaceholder: 'Hỏi AI hoặc nhập yêu cầu (ví dụ: "chuyển sang giọng trang trọng")...',
    send: 'Gửi',
    thinking: 'Đang suy nghĩ...',
    validationIssues: 'Lỗi phát hiện bởi AI',
    noValidationIssues: 'Không phát hiện lỗi. Bản dịch rất tốt!',
    ref: 'Tham chiếu:',
    auditorSuggestions: 'Đề xuất hiệu đính',
    score: 'Điểm chất lượng',
    
    // Settings / Glossary / Style Guide
    glossaryTitle: 'Thuật ngữ Dự án',
    styleTitle: 'Quy tắc Phong cách',
    assetsTitle: 'Hình ảnh Tham chiếu',
    addEntry: 'Thêm mục mới',
    termJa: 'Từ gốc',
    termVi: 'Từ dịch',
    category: 'Danh mục',
    description: 'Mô tả quy tắc',
    exampleBefore: 'Ví dụ trước',
    exampleAfter: 'Ví dụ sau',
    uploadAssets: 'Tải ảnh lên',
    noAssets: 'Chưa có hình ảnh tham chiếu.',
    noGlossary: 'Danh sách thuật ngữ trống.',
    noStyle: 'Chưa có quy tắc phong cách nào.',
    
    // Global Header
    logout: 'Đăng xuất',
    themeLight: 'Giao diện sáng',
    themeDark: 'Giao diện tối',

    // New translation keys
    deleteDocConfirm: 'Bạn có chắc chắn muốn xóa tài liệu này không? Thao tác này sẽ xóa vĩnh viễn dữ liệu trên hệ thống.',
    deleteDocSuccess: 'Đã xóa tài liệu thành công.',
    deleteDocError: 'Lỗi khi xóa tài liệu:',
    uploadDocSuccess: 'Đã nạp file thành công! Hệ thống đang dịch ngầm tự động. Các đoạn dịch xong sẽ dần xuất hiện ở tab "Bản dịch đã duyệt".',
    uploadDocError: 'Lỗi khi tải file:',
    activeDocument: 'Tài liệu đang mở',
    targetLangLabel: 'Mục tiêu',
    saved: 'Đã lưu',
    saving: 'Đang lưu...',
    words: 'từ',
    deleteMsgConfirm: 'Hủy/Xóa tin nhắn này',
    processingImage: 'Đang xử lý hình ảnh...',
    draftingAnswer: 'Đang soạn câu trả lời...',
    translatingAndAuditing: 'Đang dịch thô và đối chiếu rules...',
    sentenceLabel: 'Câu',
    bilingualView: 'Bản dịch & Gốc',
    downloadTranslation: 'Tải bản dịch',
    backToChapters: 'Quay lại danh sách tài liệu',
    searchLanguagePlaceholder: 'Tìm kiếm ngôn ngữ...',
    project: 'Dự án',
    uploadTxtTooltip: 'Tải file TXT lên để dịch ngầm',
    deleteDoc: 'Xóa tài liệu',
    docExists: 'Tài liệu với tên đó đã tồn tại.',
    newDocPrompt: 'Nhập tên tài liệu mới:',
    hideSidebar: 'Ẩn thanh bên',
    projectMemory: 'Bộ nhớ Dự án',
    projectMemoryTooltip: 'Bộ nhớ đệm dự án',
    switchLanguage: 'Chuyển đổi ngôn ngữ',
    download: 'Tải xuống',
    workspaceIntro: 'Vui lòng nhập văn bản gốc, yêu cầu chỉnh sửa, hoặc tải ảnh lên để bắt đầu.',
    viewBilingualTooltip: 'Xem tổng hợp bản dịch và bản gốc',
    you: 'Bạn',
    system: 'Hệ thống',
    doneEditing: 'Hoàn thành chỉnh sửa',
    editOriginal: 'Sửa văn bản gốc',
    approvedTranslationTitle: 'Bản dịch đã duyệt',
    sourceTextTitle: 'Văn bản gốc',
    enterOriginalPlaceholder: 'Nhập nội dung văn bản gốc tại đây...',
    chatConnectionError: 'Không thể kết nối với trợ lý',
    uploadFontTooltip: 'Tải font custom lên (.ttf/.otf)',
    welcomeMsg: 'Chào mừng bạn đến với **Localization Workspace** cho tài liệu **{activeFile}**. Bạn có thể gửi yêu cầu dịch văn bản hoặc đính kèm ảnh manga/comic để dịch trực tiếp trong luồng chat này.',
    pipelineProgress: 'Tiến trình Pipeline:',
    localizationWorkspace: 'Không gian Dịch thuật',
    workspaceIntroText: 'Gửi yêu cầu dịch văn bản hoặc tải ảnh manga/comic để dịch.',
    workspaceReviewText: 'Xem và duyệt bản dịch nháp bên dưới.',
    aiChatLabel: 'Trợ lý AI:',
    stepUpload: 'Tải lên',
    stepOcr: 'Nhận diện OCR',
    stepContext: 'Ngữ cảnh',
    stepDraft: 'Dịch nháp',
    stepReview: 'Chỉnh sửa',
    stepApprove: 'Phê duyệt',
    stepRender: 'Xuất ảnh'
  }
}

interface LanguageContextType {
  language: Language
  setLanguage: (lang: Language) => void
  t: (key: keyof typeof translations['en']) => string
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined)

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguageState] = useState<Language>('vi')

  useEffect(() => {
    const saved = localStorage.getItem('drs-lang') as Language
    if (saved === 'en' || saved === 'vi') {
      setLanguageState(saved)
    }
  }, [])

  const setLanguage = (lang: Language) => {
    setLanguageState(lang)
    localStorage.setItem('drs-lang', lang)
  }

  const t = (key: keyof typeof translations['en']): string => {
    return translations[language][key] || translations['en'][key] || String(key)
  }

  return React.createElement(LanguageContext.Provider, { value: { language, setLanguage, t } }, children)
}

export function useLanguage() {
  const context = useContext(LanguageContext)
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider')
  }
  return context
}
