'use client'

import React, { useState, useEffect } from 'react'
import { showToast } from './toast'
import { 
  getProjectMemory, 
  addGlossaryTerm, 
  deleteGlossaryTerm, 
  addEntity, 
  deleteEntity, 
  addStyleRule, 
  deleteStyleRule, 
  deleteCorrection, 
  promoteCorrection,
  listKbDocuments,
  deleteKbDocument,
  uploadKbDocument
} from '@/app/api-client'

interface MemoryManagerProps {
  projectId: string
  sourceLang: string
  targetLang: string
}

export default function MemoryManager({ projectId, sourceLang, targetLang }: MemoryManagerProps) {
  const [memoryData, setMemoryData] = useState<{
    glossary: any[]
    entities: any[]
    style_rules: any[]
    corrections: any[]
  }>({ glossary: [], entities: [], style_rules: [], corrections: [] })

  const [newTerm, setNewTerm] = useState({ source: '', target: '', note: '' })
  const [newEntity, setNewEntity] = useState({ id: '', source: '', target: '', type: 'character', pronouns: '', notes: '' })
  const [newRule, setNewRule] = useState({ id: '', category: 'tone', description: '', before: '', after: '' })
  const [activeMemorySubTab, setActiveMemorySubTab] = useState<'glossary' | 'entities' | 'rules' | 'corrections' | 'kb'>('glossary')
  const [kbDocs, setKbDocs] = useState<string[]>([])
  const [uploadingDoc, setUploadingDoc] = useState(false)

  const loadMemory = async () => {
    if (!projectId) return
    try {
      const data = await getProjectMemory(projectId)
      setMemoryData({
        glossary: data.glossary || [],
        entities: data.entities || [],
        style_rules: data.style_rules || [],
        corrections: data.corrections || []
      })
    } catch (err) {
      console.error('Failed to load project memory:', err)
    }
  }

  const loadKbDocs = async () => {
    try {
      const res = await listKbDocuments(projectId)
      setKbDocs(res.documents || [])
    } catch (err) {
      console.error('Failed to load KB docs:', err)
    }
  }

  useEffect(() => {
    loadMemory()
    if (activeMemorySubTab === 'kb') {
      loadKbDocs()
    }
  }, [projectId, activeMemorySubTab])

  const handleUploadKbFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploadingDoc(true)
    try {
      await uploadKbDocument(projectId, file)
      showToast('Đang tải lên và lập chỉ mục tài liệu...', 'success')
      setTimeout(loadKbDocs, 1500)
    } catch (err) {
      console.error(err)
      showToast('Không thể tải lên tài liệu tham khảo.', 'error')
    } finally {
      setUploadingDoc(false)
      e.target.value = ''
    }
  }

  const handleDeleteKbDoc = async (docId: string) => {
    if (!confirm(`Bạn có chắc muốn xóa tài liệu "${docId}" khỏi Knowledge Base?`)) return
    try {
      await deleteKbDocument(projectId, docId)
      showToast('Đã xóa tài liệu thành công!', 'success')
      loadKbDocs()
    } catch (err) {
      console.error(err)
      showToast('Không thể xóa tài liệu.', 'error')
    }
  }

  const handleAddTerm = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newTerm.source.trim() || !newTerm.target.trim()) return
    const termToAdd = {
      source_term: newTerm.source.trim(),
      target_term: newTerm.target.trim(),
      context_note: newTerm.note.trim()
    }
    
    // Optimistic state update
    setMemoryData(prev => ({
      ...prev,
      glossary: [...prev.glossary, termToAdd]
    }))
    setNewTerm({ source: '', target: '', note: '' })
    
    try {
      await addGlossaryTerm(projectId, {
        source_term: termToAdd.source_term,
        target_term: termToAdd.target_term,
        source_lang: sourceLang,
        target_lang: targetLang,
        context_note: termToAdd.context_note
      })
      showToast('Đã thêm thuật ngữ thành công!', 'success')
      loadMemory()
    } catch (err) {
      console.error(err)
      showToast('Không thể lưu thuật ngữ.', 'error')
      loadMemory()
    }
  }

  const handleDeleteTerm = async (sourceTerm: string) => {
    if (!confirm(`Bạn có chắc chắn muốn xóa thuật ngữ "${sourceTerm}"?`)) return
    
    // Optimistic state update
    setMemoryData(prev => ({
      ...prev,
      glossary: prev.glossary.filter(t => t.source_term !== sourceTerm)
    }))
    
    try {
      await deleteGlossaryTerm(projectId, sourceLang, targetLang, sourceTerm)
      showToast('Đã xóa thuật ngữ thành công!', 'success')
      loadMemory()
    } catch (err) {
      console.error(err)
      showToast('Không thể xóa thuật ngữ.', 'error')
      loadMemory()
    }
  }

  const handleAddEntity = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newEntity.id.trim() || !newEntity.target.trim() || !newEntity.source.trim()) return
    const entityToAdd = {
      entity_id: newEntity.id.trim(),
      canonical_name: newEntity.target.trim(),
      source_name: newEntity.source.trim(),
      entity_type: newEntity.type,
      pronouns: newEntity.pronouns.trim(),
      notes: newEntity.notes.trim()
    }
    
    // Optimistic state update
    setMemoryData(prev => ({
      ...prev,
      entities: [...prev.entities, entityToAdd]
    }))
    setNewEntity({ id: '', source: '', target: '', type: 'character', pronouns: '', notes: '' })
    
    try {
      await addEntity(projectId, {
        entity_id: entityToAdd.entity_id,
        canonical_name: entityToAdd.canonical_name,
        source_name: entityToAdd.source_name,
        entity_type: entityToAdd.entity_type,
        source_lang: sourceLang,
        target_lang: targetLang,
        pronouns: entityToAdd.pronouns,
        notes: entityToAdd.notes
      })
      showToast('Đã thêm thực thể thành công!', 'success')
      loadMemory()
    } catch (err) {
      console.error(err)
      showToast('Không thể lưu thực thể.', 'error')
      loadMemory()
    }
  }

  const handleDeleteEntity = async (entityId: string) => {
    if (!confirm(`Bạn có chắc chắn muốn xóa thực thể "${entityId}"?`)) return
    
    // Optimistic state update
    setMemoryData(prev => ({
      ...prev,
      entities: prev.entities.filter(e => e.entity_id !== entityId)
    }))
    
    try {
      await deleteEntity(projectId, entityId)
      showToast('Đã xóa thực thể thành công!', 'success')
      loadMemory()
    } catch (err) {
      console.error(err)
      showToast('Không thể xóa thực thể.', 'error')
      loadMemory()
    }
  }

  const handleAddRule = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newRule.id.trim() || !newRule.description.trim()) return
    const ruleToAdd = {
      rule_id: newRule.id.trim(),
      category: newRule.category,
      description: newRule.description.trim(),
      example_before: newRule.before.trim(),
      example_after: newRule.after.trim()
    }
    
    // Optimistic state update
    setMemoryData(prev => ({
      ...prev,
      style_rules: [...prev.style_rules, ruleToAdd]
    }))
    setNewRule({ id: '', category: 'tone', description: '', before: '', after: '' })
    
    try {
      await addStyleRule(projectId, {
        rule_id: ruleToAdd.rule_id,
        category: ruleToAdd.category,
        description: ruleToAdd.description,
        example_before: ruleToAdd.example_before,
        example_after: ruleToAdd.example_after,
        source_lang: sourceLang,
        target_lang: targetLang
      })
      showToast('Đã thêm quy tắc văn phong thành công!', 'success')
      loadMemory()
    } catch (err) {
      console.error(err)
      showToast('Không thể lưu quy tắc.', 'error')
      loadMemory()
    }
  }

  const handleDeleteRule = async (ruleId: string) => {
    if (!confirm('Bạn có chắc chắn muốn xóa quy tắc phong cách này?')) return
    
    // Optimistic state update
    setMemoryData(prev => ({
      ...prev,
      style_rules: prev.style_rules.filter(r => r.rule_id !== ruleId)
    }))
    
    try {
      await deleteStyleRule(projectId, ruleId)
      showToast('Đã xóa quy tắc thành công!', 'success')
      loadMemory()
    } catch (err) {
      console.error(err)
      showToast('Không thể xóa quy tắc.', 'error')
      loadMemory()
    }
  }

  const handleDeleteCorrection = async (correctionId: string) => {
    if (!confirm('Bạn có chắc chắn muốn từ chối phản hồi sửa lỗi này?')) return
    
    // Optimistic state update
    setMemoryData(prev => ({
      ...prev,
      corrections: prev.corrections.filter(c => c.correction_id !== correctionId)
    }))
    
    try {
      await deleteCorrection(projectId, correctionId)
      showToast('Đã từ chối phản hồi sửa lỗi.', 'success')
      loadMemory()
    } catch (err) {
      console.error(err)
      showToast('Không thể từ chối phản hồi.', 'error')
      loadMemory()
    }
  }

  const handlePromoteCorrection = async (correctionId: string) => {
    // Optimistic state update
    setMemoryData(prev => ({
      ...prev,
      corrections: prev.corrections.map(c => c.correction_id === correctionId ? { ...c, status: 'promoted' } : c)
    }))
    
    try {
      await promoteCorrection(projectId, correctionId, 'glossary')
      showToast('Đã phê duyệt và chuyển đổi thành thuật ngữ Glossary!', 'success')
      loadMemory()
    } catch (err) {
      console.error(err)
      showToast('Không thể chuyển đổi phản hồi.', 'error')
      loadMemory()
    }
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden p-6 max-w-4xl mx-auto w-full text-left">
      <div className="flex items-center justify-between border-b border-themeBorder pb-3 mb-6">
        <h1 className="text-lg font-serif font-semibold text-slate-800 dark:text-slate-100">Bộ nhớ dự án</h1>
        <div className="flex gap-4">
          {(['glossary', 'entities', 'rules', 'corrections', 'kb'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveMemorySubTab(tab)}
              className={`text-xs font-semibold pb-1 transition-all ${
                activeMemorySubTab === tab
                  ? 'text-accent-purple border-b-2 border-accent-purple'
                  : 'text-slate-400 dark:text-slate-500'
              }`}
            >
              {tab === 'glossary' && 'Glossary'}
              {tab === 'entities' && 'Thực thể & Nhân vật'}
              {tab === 'rules' && 'Quy tắc phong cách'}
              {tab === 'corrections' && 'Lịch sử sửa lỗi (Correction Log)'}
              {tab === 'kb' && 'Tài liệu tham khảo (Knowledge Base)'}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto pr-1">
        {activeMemorySubTab === 'glossary' && (
          <div className="space-y-6">
            <div className="bg-themeCard border border-themeBorder rounded-xl p-4">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">Thêm thuật ngữ mới</h3>
              <form onSubmit={handleAddTerm} className="grid grid-cols-3 gap-3">
                <input
                  type="text"
                  placeholder="Từ gốc (Source Term, vd: trap)"
                  value={newTerm.source}
                  onChange={e => setNewTerm({ ...newTerm, source: e.target.value })}
                  className="bg-transparent border border-themeBorder rounded p-2 text-xs text-themeText"
                />
                <input
                  type="text"
                  placeholder="Bản dịch tương ứng (Target Term, vd: bẫy)"
                  value={newTerm.target}
                  onChange={e => setNewTerm({ ...newTerm, target: e.target.value })}
                  className="bg-transparent border border-themeBorder rounded p-2 text-xs text-themeText"
                />
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Ghi chú ngữ cảnh"
                    value={newTerm.note}
                    onChange={e => setNewTerm({ ...newTerm, note: e.target.value })}
                    className="bg-transparent border border-themeBorder rounded p-2 text-xs text-themeText flex-1"
                  />
                  <button type="submit" className="bg-accent-purple text-white px-4 rounded text-xs font-semibold hover:bg-accent-violet">
                    Lưu
                  </button>
                </div>
              </form>
            </div>

            <div className="border border-themeBorder rounded-xl overflow-hidden bg-themeCard">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-500/5 text-slate-400 uppercase font-semibold">
                  <tr>
                    <th className="p-3">Từ gốc (Source)</th>
                    <th className="p-3">Bản dịch (Target)</th>
                    <th className="p-3">Ghi chú ngữ cảnh</th>
                    <th className="p-3 text-right">Thao tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-themeBorder">
                  {memoryData.glossary.map((g, idx) => (
                    <tr key={idx} className="hover:bg-slate-500/5">
                      <td className="p-3 font-semibold">{g.source_term}</td>
                      <td className="p-3">{g.target_term}</td>
                      <td className="p-3 text-slate-400">{g.context_note || '-'}</td>
                      <td className="p-3 text-right">
                        <button
                          type="button"
                          onClick={() => handleDeleteTerm(g.source_term)}
                          className="text-red-500 hover:text-red-750 font-semibold"
                        >
                          Xóa
                        </button>
                      </td>
                    </tr>
                  ))}
                  {memoryData.glossary.length === 0 && (
                    <tr>
                      <td colSpan={4} className="p-4 text-center text-slate-400">Không có dữ liệu thuật ngữ.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeMemorySubTab === 'entities' && (
          <div className="space-y-6">
            <div className="bg-themeCard border border-themeBorder rounded-xl p-4">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">Thêm thực thể / Nhân vật mới</h3>
              <form onSubmit={handleAddEntity} className="grid grid-cols-3 gap-3">
                <input
                  type="text"
                  placeholder="Mã định danh (Entity ID, vd: richa)"
                  value={newEntity.id}
                  onChange={e => setNewEntity({ ...newEntity, id: e.target.value })}
                  className="bg-transparent border border-themeBorder rounded p-2 text-xs text-themeText"
                />
                <input
                  type="text"
                  placeholder="Tên nguồn (Source Name)"
                  value={newEntity.source}
                  onChange={e => setNewEntity({ ...newEntity, source: e.target.value })}
                  className="bg-transparent border border-themeBorder rounded p-2 text-xs text-themeText"
                />
                <input
                  type="text"
                  placeholder="Tên dịch chuẩn (Canonical Name)"
                  value={newEntity.target}
                  onChange={e => setNewEntity({ ...newEntity, target: e.target.value })}
                  className="bg-transparent border border-themeBorder rounded p-2 text-xs text-themeText"
                />
                <select
                  value={newEntity.type}
                  onChange={e => setNewEntity({ ...newEntity, type: e.target.value })}
                  className="bg-themeCard border border-themeBorder rounded p-2 text-xs text-themeText"
                >
                  <option value="character">Nhân vật (Character)</option>
                  <option value="location">Địa danh (Location)</option>
                  <option value="organization">Tổ chức (Organization)</option>
                  <option value="other">Khác (Other)</option>
                </select>
                <input
                  type="text"
                  placeholder="Đại từ nhân xưng (Pronouns, vd: cô/nàng)"
                  value={newEntity.pronouns}
                  onChange={e => setNewEntity({ ...newEntity, pronouns: e.target.value })}
                  className="bg-transparent border border-themeBorder rounded p-2 text-xs text-themeText"
                />
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Mối quan hệ & Ghi chú"
                    value={newEntity.notes}
                    onChange={e => setNewEntity({ ...newEntity, notes: e.target.value })}
                    className="bg-transparent border border-themeBorder rounded p-2 text-xs text-themeText flex-1"
                  />
                  <button type="submit" className="bg-accent-purple text-white px-4 rounded text-xs font-semibold hover:bg-accent-violet">
                    Lưu
                  </button>
                </div>
              </form>
            </div>

            <div className="border border-themeBorder rounded-xl overflow-hidden bg-themeCard">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-500/5 text-slate-400 uppercase font-semibold">
                  <tr>
                    <th className="p-3">Tên nguồn (Source)</th>
                    <th className="p-3">Tên dịch chuẩn</th>
                    <th className="p-3">Loại</th>
                    <th className="p-3">Xưng hô</th>
                    <th className="p-3">Ghi chú</th>
                    <th className="p-3 text-right">Thao tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-themeBorder">
                  {memoryData.entities.map((ent, idx) => (
                    <tr key={idx} className="hover:bg-slate-500/5">
                      <td className="p-3 font-semibold">{ent.source_name}</td>
                      <td className="p-3">{ent.canonical_name}</td>
                      <td className="p-3 capitalize">{ent.entity_type === 'character' ? 'Nhân vật' : ent.entity_type}</td>
                      <td className="p-3">{ent.pronouns || '-'}</td>
                      <td className="p-3 text-slate-400">{ent.notes || '-'}</td>
                      <td className="p-3 text-right">
                        <button
                          type="button"
                          onClick={() => handleDeleteEntity(ent.entity_id)}
                          className="text-red-500 hover:text-red-750 font-semibold"
                        >
                          Xóa
                        </button>
                      </td>
                    </tr>
                  ))}
                  {memoryData.entities.length === 0 && (
                    <tr>
                      <td colSpan={6} className="p-4 text-center text-slate-400">Không có thực thể/nhân vật nào.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeMemorySubTab === 'rules' && (
          <div className="space-y-6">
            <div className="bg-themeCard border border-themeBorder rounded-xl p-4">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">Thêm quy tắc văn phong mới</h3>
              <form onSubmit={handleAddRule} className="grid grid-cols-3 gap-3">
                <input
                  type="text"
                  placeholder="Mã quy tắc (vd: register-formal)"
                  value={newRule.id}
                  onChange={e => setNewRule({ ...newRule, id: e.target.value })}
                  className="bg-transparent border border-themeBorder rounded p-2 text-xs text-themeText"
                />
                <select
                  value={newRule.category}
                  onChange={e => setNewRule({ ...newRule, category: e.target.value })}
                  className="bg-themeCard border border-themeBorder rounded p-2 text-xs text-themeText"
                >
                  <option value="tone">Giọng điệu (Tone)</option>
                  <option value="register">Văn phong (Register)</option>
                  <option value="honorific">Kính ngữ (Honorific)</option>
                  <option value="formatting">Định dạng (Formatting)</option>
                </select>
                <input
                  type="text"
                  placeholder="Mô tả quy tắc"
                  value={newRule.description}
                  onChange={e => setNewRule({ ...newRule, description: e.target.value })}
                  className="bg-transparent border border-themeBorder rounded p-2 text-xs text-themeText"
                />
                <input
                  type="text"
                  placeholder="Ví dụ chưa đúng (Example Before)"
                  value={newRule.before}
                  onChange={e => setNewRule({ ...newRule, before: e.target.value })}
                  className="bg-transparent border border-themeBorder rounded p-2 text-xs text-themeText"
                />
                <div className="flex gap-2 col-span-2">
                  <input
                    type="text"
                    placeholder="Ví dụ sửa đúng (Example After)"
                    value={newRule.after}
                    onChange={e => setNewRule({ ...newRule, after: e.target.value })}
                    className="bg-transparent border border-themeBorder rounded p-2 text-xs text-themeText flex-1"
                  />
                  <button type="submit" className="bg-accent-purple text-white px-4 rounded text-xs font-semibold hover:bg-accent-violet">
                    Lưu
                  </button>
                </div>
              </form>
            </div>

            <div className="border border-themeBorder rounded-xl overflow-hidden bg-themeCard">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-500/5 text-slate-400 uppercase font-semibold">
                  <tr>
                    <th className="p-3">Phân loại</th>
                    <th className="p-3">Mô tả</th>
                    <th className="p-3">Trước khi sửa</th>
                    <th className="p-3">Sau khi sửa</th>
                    <th className="p-3 text-right">Thao tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-themeBorder">
                  {memoryData.style_rules.map((rule, idx) => (
                    <tr key={idx} className="hover:bg-slate-500/5">
                      <td className="p-3 capitalize font-semibold">{rule.category}</td>
                      <td className="p-3">{rule.description}</td>
                      <td className="p-3 text-red-500 line-through">{rule.example_before || '-'}</td>
                      <td className="p-3 text-green-500">{rule.example_after || '-'}</td>
                      <td className="p-3 text-right">
                        <button
                          type="button"
                          onClick={() => handleDeleteRule(rule.rule_id)}
                          className="text-red-500 hover:text-red-750 font-semibold"
                        >
                          Xóa
                        </button>
                      </td>
                    </tr>
                  ))}
                  {memoryData.style_rules.length === 0 && (
                    <tr>
                      <td colSpan={5} className="p-4 text-center text-slate-400">Không có quy tắc phong cách nào.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeMemorySubTab === 'corrections' && (
          <div className="space-y-6">
            <div className="border border-themeBorder rounded-xl overflow-hidden bg-themeCard">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-500/5 text-slate-400 uppercase font-semibold">
                  <tr>
                    <th className="p-3">Bản dịch AI thô (Original)</th>
                    <th className="p-3">Bản dịch người sửa (Corrected)</th>
                    <th className="p-3">Loại sửa</th>
                    <th className="p-3">Trạng thái</th>
                    <th className="p-3 text-right">Hành động</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-themeBorder">
                  {memoryData.corrections.map((corr, idx) => (
                    <tr key={idx} className="hover:bg-slate-500/5">
                      <td className="p-3 text-red-500 line-through">{corr.original_text}</td>
                      <td className="p-3 text-green-500 font-semibold">{corr.corrected_text}</td>
                      <td className="p-3 capitalize text-slate-400">{corr.correction_type}</td>
                      <td className="p-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                          corr.status === 'promoted' 
                            ? 'bg-green-500/10 text-green-500' 
                            : corr.status === 'dismissed'
                            ? 'bg-red-500/10 text-red-500'
                            : 'bg-yellow-500/10 text-yellow-500'
                        }`}>
                          {corr.status}
                        </span>
                      </td>
                      <td className="p-3 text-right space-x-2">
                        {corr.status === 'pending' && (
                          <>
                            <button
                              type="button"
                              onClick={() => handlePromoteCorrection(corr.correction_id)}
                              className="text-accent-purple hover:text-accent-violet font-semibold"
                            >
                              Phê duyệt làm Glossary
                            </button>
                            <button
                              type="button"
                              onClick={() => handleDeleteCorrection(corr.correction_id)}
                              className="text-slate-400 hover:text-slate-600 font-semibold"
                            >
                              Từ chối
                            </button>
                          </>
                        )}
                      </td>
                    </tr>
                  ))}
                  {memoryData.corrections.length === 0 && (
                    <tr>
                      <td colSpan={5} className="p-4 text-center text-slate-400">Không có phản hồi sửa lỗi nào trong hệ thống.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeMemorySubTab === 'kb' && (
          <div className="space-y-6">
            <div className="bg-themeCard border border-themeBorder rounded-xl p-4">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">Tải lên tài liệu tham khảo (.txt)</h3>
              <div className="flex items-center gap-4">
                <input
                  type="file"
                  accept=".txt"
                  onChange={handleUploadKbFile}
                  disabled={uploadingDoc}
                  className="bg-transparent text-xs text-themeText"
                />
                {uploadingDoc && (
                  <span className="text-xs text-slate-400 animate-pulse">Đang tải lên...</span>
                )}
              </div>
              <p className="text-[10px] text-slate-400 mt-2">
                Hệ thống sẽ tự động phân tách tài liệu thành các đoạn văn nhỏ và tạo vector embedding (Layer 3) phục vụ cho tính năng Q&A và gợi ý dịch thuật.
              </p>
            </div>

            <div className="border border-themeBorder rounded-xl overflow-hidden bg-themeCard">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-500/5 text-slate-400 uppercase font-semibold">
                  <tr>
                    <th className="p-3">Tên tài liệu / Document ID</th>
                    <th className="p-3 text-right">Thao tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-themeBorder">
                  {kbDocs.map((doc, idx) => (
                    <tr key={idx} className="hover:bg-slate-500/5">
                      <td className="p-3 font-semibold">{doc}</td>
                      <td className="p-3 text-right">
                        <button
                          type="button"
                          onClick={() => handleDeleteKbDoc(doc)}
                          className="text-red-500 hover:text-red-750 font-semibold"
                        >
                          Xóa
                        </button>
                      </td>
                    </tr>
                  ))}
                  {kbDocs.length === 0 && (
                    <tr>
                      <td colSpan={2} className="p-4 text-center text-slate-400">Không có tài liệu tham khảo nào được lập chỉ mục.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
