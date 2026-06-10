const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface ProjectInfo {
  project_id: string;
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

async function getAuthToken(): Promise<string> {
  if (typeof window === 'undefined') return ''
  const token = localStorage.getItem('drs_token')
  if (token && !isTokenExpired(token)) return token
  
  // Token missing or expired — clear token and redirect to login page
  localStorage.removeItem('drs_token')
  window.location.href = '/'
  return ''
}

export async function apiFetch(endpoint: string, options: RequestInit = {}): Promise<any> {
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
    localStorage.removeItem('drs_token')
    if (typeof window !== 'undefined') {
      window.location.href = '/'
    }
    throw new Error('Session expired. Redirecting to login...')
  }

  if (!res.ok) {
    const errorText = await res.text()
    throw new Error(errorText || `API Error: ${res.status}`)
  }

  return res.json()
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

export async function saveChapter(projectId: string, docId: string, data: { draft?: string; approved?: string }): Promise<any> {
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

export async function addGlossaryTerm(projectId: string, data: { source_term: string; target_term: string; source_lang: string; target_lang: string; context_note?: string }): Promise<any> {
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

export async function addEntity(projectId: string, data: { entity_id: string; canonical_name: string; source_name: string; entity_type: string; source_lang: string; target_lang: string; pronouns?: string; notes?: string }): Promise<any> {
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

export async function addStyleRule(projectId: string, data: { rule_id: string; category: string; description: string; example_before?: string; example_after?: string; source_lang?: string; target_lang?: string }): Promise<any> {
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

export async function createProject(data: { project_id: string; source_lang: string; target_lang: string; content_type: string; tone_note: string }): Promise<ProjectInfo> {
  return await apiFetch('/api/projects', {
    method: 'POST',
    body: JSON.stringify(data)
  });
}

export async function uploadAssets(projectId: string, docId: string, files: File[]): Promise<any> {
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

