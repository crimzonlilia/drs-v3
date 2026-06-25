export const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

export interface ProjectInfo {
  project_id: string;
  description?: string;
  source_lang: string;
  target_lang: string;
  content_type: string;
  tone_note: string;
}

export interface GlossaryEntry {
  source_term: string;
  target_term: string;
  source_lang: string;
  target_lang: string;
  context_note?: string;
}

export interface EntityEntry {
  entity_id: string;
  canonical_name: string;
  source_name: string;
  entity_type: string;
  pronouns?: string;
  aliases?: string[];
  notes?: string;
}

export interface StyleRuleEntry {
  rule_id: string;
  category: string;
  description: string;
  example_before?: string;
  example_after?: string;
}

export interface CorrectionEntry {
  correction_id?: string;
  id?: string;
  source_text?: string;
  original?: string;
  corrected_text?: string;
  corrected?: string;
  status?: string;
  [key: string]: unknown;
}

export interface MemoryData {
  glossary: GlossaryEntry[];
  entities: EntityEntry[];
  style_rules: StyleRuleEntry[];
  corrections?: CorrectionEntry[];
}

export interface ChapterData {
  project_id: string;
  chapter_id: string;
  doc_id?: string;
  source_text?: string;
  draft: string;
  approved: string;
}

function isTokenExpired(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')))
    // Expire 60s early to avoid edge cases
    return payload.exp && Date.now() / 1000 > payload.exp - 60
  } catch {
    return true
  }
}

async function performSilentLogin(): Promise<string> {
  try {
    const params = new URLSearchParams()
    params.append('username', 'admin')
    params.append('password', 'admin123')
    
    const response = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: params
    })
    
    if (response.ok) {
      const data = await response.json()
      if (data.access_token) {
        localStorage.setItem('drs_token', data.access_token)
        return data.access_token
      }
    }
  } catch (err) {
    console.error('Silent auto-login request failed:', err)
  }
  return ''
}

async function getAuthToken(): Promise<string> {
  if (typeof window === 'undefined') return ''
  const token = localStorage.getItem('drs_token')
  if (token && !isTokenExpired(token)) return token
  
  // Token missing or expired — attempt silent auto-login
  const newToken = await performSilentLogin()
  if (newToken) return newToken

  // If silent login fails, clear token and redirect to login
  localStorage.removeItem('drs_token')
  window.location.href = '/login'
  return ''
}

interface CacheEntry {
  data: any
  timestamp: number
}

const apiCache = new Map<string, CacheEntry>()
const CACHE_TTL_MS = 15000 // 15 seconds

export function clearApiCache() {
  apiCache.clear()
}

export async function apiFetch(endpoint: string, options: RequestInit = {}): Promise<any> {
  const method = (options.method || 'GET').toUpperCase()
  const isGet = method === 'GET'
  
  // Cache invalidation: Clear cache on write operations
  if (!isGet) {
    apiCache.clear()
  }

  // Blacklist endpoints that should bypass cache (status check or real-time polling)
  const bypassCache = endpoint.includes('/status') || endpoint.includes('/history') || endpoint.includes('/chat')

  if (isGet && !bypassCache) {
    const cached = apiCache.get(endpoint)
    if (cached && Date.now() - cached.timestamp < CACHE_TTL_MS) {
      return Promise.resolve(JSON.parse(JSON.stringify(cached.data)))
    }
  }

  const makeRequest = async (token: string) => {
    const headers = {
      ...options.headers,
      'Authorization': `Bearer ${token}`
    } as any
    if (options.body && !(options.body instanceof URLSearchParams) && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json'
    }
    return fetch(`${API_BASE}${endpoint}`, { ...options, headers })
  }

  let token = await getAuthToken()
  if (!token) {
    throw new Error('Not authenticated')
  }

  let res = await makeRequest(token)

  if (res.status === 401) {
    // Retry once with a freshly obtained token
    const newToken = await performSilentLogin()
    if (newToken) {
      res = await makeRequest(newToken)
      if (res.ok) {
        const data = await res.json()
        if (isGet && !bypassCache) {
          apiCache.set(endpoint, { data, timestamp: Date.now() })
        }
        return JSON.parse(JSON.stringify(data))
      }
    }
    
    // If retry also fails or login fails, redirect to login
    localStorage.removeItem('drs_token')
    if (typeof window !== 'undefined') {
      window.location.href = '/login'
    }
    throw new Error('Session expired. Redirecting to login...')
  }

  if (!res.ok) {
    const errorText = await res.text()
    throw new Error(errorText || `API Error: ${res.status}`)
  }

  const data = await res.json()
  if (isGet && !bypassCache) {
    apiCache.set(endpoint, { data, timestamp: Date.now() })
  }
  return JSON.parse(JSON.stringify(data))
}

export async function listProjects(): Promise<string[]> {
  try {
    return await apiFetch('/api/projects');
  } catch (err) {
    console.error('Error fetching projects:', err);
    return ['demo_project', 'sample_project']; // Fallback
  }
}

export async function getProject(projectId: string): Promise<ProjectInfo> {
  return await apiFetch(`/api/projects/${projectId}`);
}

export async function getProjectMemory(projectId: string): Promise<MemoryData> {
  return await apiFetch(`/api/memory/${projectId}`);
}

export async function listChapters(projectId: string): Promise<string[]> {
  try {
    return await apiFetch(`/api/projects/${projectId}/chapters`);
  } catch (err) {
    console.error('Error listing chapters:', err);
    return ['ch001', 'ch002', 'ch003']; // Fallback
  }
}

export async function getChapter(projectId: string, docId: string): Promise<ChapterData> {
  return await apiFetch(`/api/projects/${projectId}/chapters/${docId}`);
}

export async function deleteChapter(projectId: string, docId: string): Promise<any> {
  return await apiFetch(`/api/projects/${projectId}/chapters/${docId}`, {
    method: 'DELETE'
  });
}

export async function saveChapter(projectId: string, docId: string, data: { draft?: string; approved?: string; source_text?: string }): Promise<any> {
  return await apiFetch(`/api/projects/${projectId}/chapters/${docId}`, {
    method: 'POST',
    body: JSON.stringify(data)
  });
}

export async function exportChapter(projectId: string, docId: string): Promise<void> {
  const token = await getAuthToken();
  const res = await fetch(`${API_BASE}/api/projects/${projectId}/chapters/${docId}/export`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  if (!res.ok) throw new Error(`Export failed: ${res.status}`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${docId}.md`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export async function runTranslate(projectId: string, docId: string, sourceText: string, sourceLang: string, targetLang: string, segmentId = ""): Promise<any> {
  return await apiFetch('/api/translation/translate', {
    method: 'POST',
    body: JSON.stringify({
      project_id: projectId,
      doc_id: docId,
      segment_id: segmentId,
      source_text: sourceText,
      source_lang: sourceLang,
      target_lang: targetLang,
      content_type: 'novel'
    })
  });
}

export async function approveTranslation(projectId: string, sessionId: string): Promise<any> {
  void projectId;
  return await apiFetch(`/api/translation/approve/${sessionId}`, {
    method: 'POST'
  });
}

export async function getSession(sessionId: string): Promise<any> {
  return await apiFetch(`/api/translation/session/${sessionId}`);
}

export async function saveSessionDraft(sessionId: string, currentDraft: string): Promise<any> {
  return await apiFetch(`/api/translation/session/${sessionId}/draft`, {
    method: 'PUT',
    body: JSON.stringify({ current_draft: currentDraft })
  });
}

export async function submitSessionProposals(sessionId: string, proposals: any[]): Promise<any> {
  return await apiFetch(`/api/translation/session/${sessionId}/proposals`, {
    method: 'PUT',
    body: JSON.stringify({ memory_proposals: proposals })
  });
}

export async function resumeSession(sessionId: string): Promise<any> {
  return await apiFetch(`/api/translation/session/${sessionId}/resume`, {
    method: 'POST'
  });
}

export async function refineTranslation(sessionId: string, instruction: string): Promise<any> {
  return await apiFetch(`/api/translation/session/${sessionId}/refine`, {
    method: 'POST',
    body: JSON.stringify({ instruction })
  });
}

export async function addGlossaryTerm(projectId: string, data: { source_term: string; target_term: string; source_lang: string; target_lang: string; context_note?: string; old_source_term?: string }): Promise<any> {
  return await apiFetch(`/api/memory/${projectId}/glossary`, {
    method: 'POST',
    body: JSON.stringify(data)
  });
}

export async function deleteGlossaryTerm(projectId: string, sourceLang: string, targetLang: string, sourceTerm: string): Promise<any> {
  return await apiFetch(`/api/memory/${projectId}/glossary/${sourceLang}/${targetLang}/${encodeURIComponent(sourceTerm)}`, {
    method: 'DELETE'
  });
}

export async function addEntity(projectId: string, data: { entity_id: string; canonical_name: string; source_name: string; entity_type: string; source_lang: string; target_lang: string; pronouns?: string; notes?: string; old_entity_id?: string }): Promise<any> {
  return await apiFetch(`/api/memory/${projectId}/entities`, {
    method: 'POST',
    body: JSON.stringify(data)
  });
}

export async function deleteEntity(projectId: string, entityId: string): Promise<any> {
  return await apiFetch(`/api/memory/${projectId}/entities/${entityId}`, {
    method: 'DELETE'
  });
}

export async function addStyleRule(projectId: string, data: { rule_id: string; category: string; description: string; example_before?: string; example_after?: string; source_lang?: string; target_lang?: string; old_rule_id?: string }): Promise<any> {
  return await apiFetch(`/api/memory/${projectId}/style-rules`, {
    method: 'POST',
    body: JSON.stringify(data)
  });
}

export async function deleteStyleRule(projectId: string, ruleId: string): Promise<any> {
  return await apiFetch(`/api/memory/${projectId}/style-rules/${ruleId}`, {
    method: 'DELETE'
  });
}

export async function patchProject(projectId: string, data: { display_name: string; description?: string }): Promise<any> {
  return await apiFetch(`/api/projects/${projectId}`, {
    method: 'PATCH',
    body: JSON.stringify(data)
  });
}

export async function renameDocument(projectId: string, docId: string, newDocId: string): Promise<any> {
  return await apiFetch(`/api/projects/${projectId}/docs/${docId}/rename`, {
    method: 'POST',
    body: JSON.stringify({ new_doc_id: newDocId })
  });
}

export async function deleteCorrection(projectId: string, correctionId: string): Promise<any> {
  return await apiFetch(`/api/memory/${projectId}/corrections/${correctionId}`, {
    method: 'DELETE'
  });
}

export async function promoteCorrection(projectId: string, correctionId: string, targetType: string): Promise<any> {
  return await apiFetch(`/api/memory/${projectId}/corrections/${correctionId}/promote?target_type=${targetType}`, {
    method: 'POST'
  });
}

export async function createProject(data: { project_id: string; description?: string; source_lang: string; target_lang: string; content_type: string; tone_note: string }): Promise<ProjectInfo> {
  return await apiFetch('/api/projects', {
    method: 'POST',
    body: JSON.stringify(data)
  });
}

export async function uploadAssets(projectId: string, docId: string, files: File[]): Promise<any> {
  clearApiCache();
  const formData = new FormData();
  files.forEach(file => formData.append('files', file));
  
  const token = await getAuthToken();
  const res = await fetch(`${API_BASE}/api/docs/${docId}/assets/upload?project_id=${projectId}`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    },
    body: formData
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(errorText || `Upload failed: ${res.status}`);
  }
  return res.json();
}

export async function runOcr(projectId: string, docId: string, force = false): Promise<any> {
  return await apiFetch(`/api/docs/${docId}/ocr/run?project_id=${projectId}&force=${force}`, {
    method: 'POST'
  });
}

export async function exportDoc(projectId: string, docId: string, format: string, options: { font?: string; heading?: string; spacing?: number } = {}): Promise<void> {
  const token = await getAuthToken();
  const res = await fetch(`${API_BASE}/api/docs/${docId}/export`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      project_id: projectId,
      format,
      ...options
    })
  });
  if (!res.ok) throw new Error(`Export failed: ${res.status}`);
  
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  
  let ext = 'txt';
  if (format === 'docx') ext = 'docx';
  else if (format === 'zip') ext = 'zip';
  
  a.download = `${docId}_export.${ext}`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export async function login(username: string, password: string): Promise<any> {
  const params = new URLSearchParams();
  params.append('username', username);
  params.append('password', password);
  
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded'
    },
    body: params
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(errorText || `Login failed: ${res.status}`);
  }
  const data = await res.json();
  if (data.access_token) {
    localStorage.setItem('drs_token', data.access_token);
  }
  return data;
}

export async function register(username: string, password: string, email?: string): Promise<any> {
  const res = await fetch(`${API_BASE}/api/auth/register`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ username, password, email })
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(errorText || `Registration failed: ${res.status}`);
  }
  return res.json();
}

export async function logout(): Promise<void> {
  const token = localStorage.getItem('drs_token');
  if (token) {
    try {
      await fetch(`${API_BASE}/api/auth/logout-token`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
    } catch (e) {
      console.error('Logout request failed:', e);
    }
  }
  localStorage.removeItem('drs_token');
  if (typeof window !== 'undefined') {
    window.location.href = '/';
  }
}

export async function uploadFont(projectId: string, file: File): Promise<any> {
  clearApiCache();
  const formData = new FormData();
  formData.append('file', file);
  
  const token = await getAuthToken();
  const res = await fetch(`${API_BASE}/api/projects/${projectId}/fonts/upload`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    },
    body: formData
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(errorText || `Font upload failed: ${res.status}`);
  }
  return res.json();
}

export async function listFonts(projectId: string): Promise<{ default_fonts: string[]; custom_fonts: string[] }> {
  return await apiFetch(`/api/projects/${projectId}/fonts`);
}

export async function runImageTranslate(projectId: string, docId: string, assetId: string, sourceLang: string, targetLang: string): Promise<any> {
  return await apiFetch(`/api/docs/${docId}/translate-image`, {
    method: 'POST',
    body: JSON.stringify({
      project_id: projectId,
      asset_id: assetId,
      source_lang: sourceLang,
      target_lang: targetLang
    })
  });
}

export async function renderDocumentImage(
  projectId: string,
  docId: string,
  assetId: string,
  fontName: string,
  fontSize: number,
  sessionId?: string
): Promise<any> {
  return await apiFetch(`/api/docs/${docId}/render`, {
    method: 'POST',
    body: JSON.stringify({
      project_id: projectId,
      asset_id: assetId,
      font_name: fontName,
      font_size: fontSize,
      session_id: sessionId
    })
  });
}

export async function getImagePipelineStatus(sessionId: string): Promise<any> {
  return await apiFetch(`/api/translation/session/${sessionId}/status`);
}

export function getAssetViewUrl(projectId: string, docId: string, assetId: string): string {
  return `${API_BASE}/api/docs/assets/view/${projectId}/${docId}/${assetId}`;
}

export function getRenderedViewUrl(projectId: string, docId: string, assetId: string): string {
  return `${API_BASE}/api/docs/rendered/view/${projectId}/${docId}/${assetId}`;
}

export function getFontDownloadUrl(projectId: string, fontName: string): string {
  return `${API_BASE}/api/projects/${projectId}/fonts/download/${fontName}`;
}

export async function getDocumentSegments(projectId: string, docId: string, assetId?: string): Promise<any[]> {
  return await apiFetch(`/api/docs/${docId}/segments?project_id=${projectId}${assetId ? `&asset_id=${encodeURIComponent(assetId)}` : ''}`);
}

export async function uploadTextBulk(
  projectId: string,
  docId: string,
  sourceLang: string,
  targetLang: string,
  file: File
): Promise<any> {
  clearApiCache();
  const formData = new FormData();
  formData.append('file', file);

  const token = localStorage.getItem('token');
  const headers: HeadersInit = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}/api/docs/${docId}/upload-text-bulk?project_id=${projectId}&source_lang=${sourceLang}&target_lang=${targetLang}`, {
    method: 'POST',
    headers,
    body: formData,
  });
  if (!res.ok) {
    let msg = 'Failed to upload text file';
    try {
      const data = await res.json();
      msg = data.detail || msg;
    } catch (e) {}
    throw new Error(msg);
  }
  return await res.json();
}

export async function updateSegmentText(projectId: string, docId: string, segmentId: string, targetText: string): Promise<any> {
  return await apiFetch(`/api/docs/${docId}/segments/${segmentId}`, {
    method: 'PUT',
    body: JSON.stringify({
      project_id: projectId,
      target_text: targetText
    })
  });
}

export async function sendGeneralChat(
  projectId: string,
  docId: string,
  message: string,
  messageId?: string,
  history?: { role: string; content: string }[],
  userLang?: string
): Promise<{ reply: string; model_name?: string }> {
  return await apiFetch(`/api/translation/chat`, {
    method: 'POST',
    body: JSON.stringify({
      project_id: projectId,
      doc_id: docId,
      message,
      message_id: messageId,
      history,
      user_lang: userLang
    })
  });
}

export async function upsertChatMessage(projectId: string, docId: string, msg: any): Promise<any> {
  return await apiFetch(`/api/translation/history/upsert`, {
    method: 'POST',
    body: JSON.stringify({
      project_id: projectId,
      doc_id: docId,
      ...msg
    })
  });
}

export async function getChatHistory(projectId: string, docId: string): Promise<any[]> {
  return await apiFetch(`/api/translation/history?project_id=${projectId}&doc_id=${docId}`);
}

export async function deleteChatMessage(projectId: string, messageId: string): Promise<any> {
  return await apiFetch(`/api/translation/history/${messageId}?project_id=${projectId}`, {
    method: 'DELETE'
  });
}

export async function getChapterSummary(projectId: string, docId: string, text?: string): Promise<{ summary: string }> {
  return await apiFetch(`/api/projects/${projectId}/docs/${docId}/summarize`, {
    method: 'POST',
    body: JSON.stringify({ text })
  });
}

export async function saveChapterSummary(projectId: string, docId: string, summary: string): Promise<any> {
  return await apiFetch(`/api/projects/${projectId}/docs/${docId}/save-summary`, {
    method: 'POST',
    body: JSON.stringify({ summary })
  });
}

export async function listKbDocuments(projectId: string): Promise<{ documents: string[] }> {
  return await apiFetch(`/api/projects/${projectId}/kb/list`);
}

export async function deleteKbDocument(projectId: string, docId: string): Promise<any> {
  return await apiFetch(`/api/projects/${projectId}/kb/delete/${docId}`, {
    method: 'DELETE'
  });
}

export async function uploadKbDocument(projectId: string, file: File): Promise<any> {
  const token = await getAuthToken();
  const formData = new FormData();
  formData.append('file', file);
  
  const res = await fetch(`${API_BASE}/api/projects/${projectId}/kb/upload`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    },
    body: formData
  });
  if (!res.ok) {
    throw new Error(`Upload failed: ${res.statusText}`);
  }
  return await res.json();
}

export async function listProjectFonts(projectId: string): Promise<{ default_fonts: string[], custom_fonts: string[] }> {
  return await apiFetch(`/api/projects/${projectId}/fonts`);
}

export async function uploadProjectFont(projectId: string, file: File): Promise<any> {
  const token = await getAuthToken();
  const formData = new FormData();
  formData.append('file', file);
  
  const res = await fetch(`${API_BASE}/api/projects/${projectId}/fonts/upload`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    },
    body: formData
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || `Font upload failed: ${res.statusText}`);
  }
  return await res.json();
}

export async function login(username: string, password: string): Promise<void> {
  const params = new URLSearchParams()
  params.append('username', username)
  params.append('password', password)

  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: params
  })

  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error(detail.detail || `Đăng nhập thất bại (${res.status})`)
  }

  const data = await res.json()
  if (!data.access_token) {
    throw new Error('Server không trả về token hợp lệ.')
  }
  localStorage.setItem('drs_token', data.access_token)
}

export async function register(username: string, password: string, email?: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password, email: email || null })
  })

  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error(detail.detail || `Đăng ký thất bại (${res.status})`)
  }
}

