const API_BASE = 'http://localhost:8000';

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

async function doLogin(): Promise<string> {
  const formData = new URLSearchParams()
  formData.append('username', 'admin')
  formData.append('password', 'admin123')
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: 'POST',
    body: formData,
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
  })
  if (res.ok) {
    const data = await res.json()
    if (data.access_token) {
      localStorage.setItem('drs_token', data.access_token)
      return data.access_token
    }
  }
  return ''
}

async function getAuthToken(): Promise<string> {
  if (typeof window === 'undefined') return ''
  const token = localStorage.getItem('drs_token')
  if (token && !isTokenExpired(token)) return token
  // Token missing or expired — silent re-login
  localStorage.removeItem('drs_token')
  try {
    return await doLogin()
  } catch (err) {
    console.error('Failed to log in automatically:', err)
    return ''
  }
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
  let res = await makeRequest(token)

  // Retry once on 401: token may have just expired between check and request
  if (res.status === 401) {
    localStorage.removeItem('drs_token')
    token = await doLogin()
    res = await makeRequest(token)
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

export async function getChapter(projectId: string, chapterId: string): Promise<ChapterData> {
  return await apiFetch(`/api/projects/${projectId}/chapters/${chapterId}`);
}

export async function saveChapter(projectId: string, chapterId: string, data: { draft?: string; approved?: string }): Promise<any> {
  return await apiFetch(`/api/projects/${projectId}/chapters/${chapterId}`, {
    method: 'POST',
    body: JSON.stringify(data)
  });
}

export async function exportChapter(projectId: string, chapterId: string): Promise<void> {
  const token = await getAuthToken();
  const res = await fetch(`${API_BASE}/api/projects/${projectId}/chapters/${chapterId}/export`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  if (!res.ok) throw new Error(`Export failed: ${res.status}`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${chapterId}.md`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export async function runTranslate(projectId: string, chapterId: string, sourceText: string, sourceLang: string, targetLang: string): Promise<any> {
  return await apiFetch('/api/translation/translate', {
    method: 'POST',
    body: JSON.stringify({
      project_id: projectId,
      source_text: sourceText,
      chapter_or_doc: chapterId,
      source_lang: sourceLang,
      target_lang: targetLang,
      content_type: 'novel'
    })
  });
}

export async function approveTranslation(projectId: string, sessionId: string, finalText: string, corrections: any[] = []): Promise<any> {
  return await apiFetch(`/api/translation/approve/${projectId}/${sessionId}`, {
    method: 'POST',
    body: JSON.stringify({
      final_text: finalText,
      corrections
    })
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

