'use client'

import React, { useState, useEffect } from 'react'
import { 
  getProjectMemory, 
  addGlossaryTerm, 
  deleteGlossaryTerm, 
  addEntity, 
  deleteEntity, 
  addStyleRule, 
  deleteStyleRule, 
  deleteCorrection, 
  promoteCorrection 
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
  const [activeMemorySubTab, setActiveMemorySubTab] = useState<'glossary' | 'entities' | 'rules' | 'corrections'>('glossary')

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

  useEffect(() => {
    loadMemory()
  }, [projectId])

  const handleAddTerm = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newTerm.source.trim() || !newTerm.target.trim()) return
    try {
      await addGlossaryTerm(projectId, {
        source_term: newTerm.source.trim(),
        target_term: newTerm.target.trim(),
        source_lang: sourceLang,
        target_lang: targetLang,
        context_note: newTerm.note.trim()
      })
      setNewTerm({ source: '', target: '', note: '' })
      loadMemory()
    } catch (err) {
      console.error(err)
      alert('Không thể lưu thuật ngữ.')
    }
  }

  const handleDeleteTerm = async (sourceTerm: string) => {
    if (!confirm(`Bạn có chắc chắn muốn xóa thuật ngữ "${sourceTerm}"?`)) return
    try {
      await deleteGlossaryTerm(projectId, sourceLang, targetLang, sourceTerm)
      loadMemory()
    } catch (err) {
      console.error(err)
      alert('Không thể xóa thuật ngữ.')
    }
  }

  const handleAddEntity = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newEntity.id.trim() || !newEntity.target.trim() || !newEntity.source.trim()) return
    try {
      await addEntity(projectId, {
        entity_id: newEntity.id.trim(),
        canonical_name: newEntity.target.trim(),
        source_name: newEntity.source.trim(),
        entity_type: newEntity.type,
        source_lang: sourceLang,
        target_lang: targetLang,
        pronouns: newEntity.pronouns.trim(),
        notes: newEntity.notes.trim()
      })
      setNewEntity({ id: '', source: '', target: '', type: 'character', pronouns: '', notes: '' })
      loadMemory()
    } catch (err) {
      console.error(err)
      alert('Không thể lưu thực thể.')
    }
  }

  const handleDeleteEntity = async (entityId: string) => {
    if (!confirm(`Bạn có chắc chắn muốn xóa thực thể "${entityId}"?`)) return
    try {
      await deleteEntity(projectId, entityId)
      loadMemory()
    } catch (err) {
      console.error(err)
      alert('Không thể xóa thực thể.')
    }
  }

  const handleAddRule = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newRule.id.trim() || !newRule.description.trim()) return
    try {
      await addStyleRule(projectId, {
        rule_id: newRule.id.trim(),
        category: newRule.category,
        description: newRule.description.trim(),
        example_before: newRule.before.trim(),
        example_after: newRule.after.trim(),
        source_lang: sourceLang,
        target_lang: targetLang
      })
      setNewRule({ id: '', category: 'tone', description: '', before: '', after: '' })
      loadMemory()
    } catch (err) {
      console.error(err)
      alert('Không thể lưu quy tắc.')
    }
  }

  const handleDeleteRule = async (ruleId: string) => {
    if (!confirm('Bạn có chắc chắn muốn xóa quy tắc phong cách này?')) return
    try {
      await deleteStyleRule(projectId, ruleId)
      loadMemory()
    } catch (err) {
      console.error(err)
      alert('Không thể xóa quy tắc.')
    }
  }

  const handleDeleteCorrection = async (correctionId: string) => {
    if (!confirm('Bạn có chắc chắn muốn từ chối phản hồi sửa lỗi này?')) return
    try {
      await deleteCorrection(projectId, correctionId)
      loadMemory()
    } catch (err) {
      console.error(err)
      alert('Không thể từ chối phản hồi.')
    }
  }

  const handlePromoteCorrection = async (correctionId: string) => {
    try {
      await promoteCorrection(projectId, correctionId, 'glossary')
      alert('Đã phê duyệt và chuyển đổi thành thuật ngữ Glossary thành công!')
      loadMemory()
    } catch (err) {
      console.error(err)
      alert('Không thể chuyển đổi phản hồi.')
    }
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden p-6 max-w-4xl mx-auto w-full text-left">
      <div className="flex items-center justify-between border-b border-themeBorder pb-3 mb-6">
        <h1 className="text-lg font-serif font-semibold text-slate-800 dark:text-slate-100">Bộ nhớ dự án</h1>
        <div className="flex gap-4">
          {(['glossary', 'entities', 'rules', 'corrections'] as const).map(tab => (
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
      </div>
    </div>
  )
}
