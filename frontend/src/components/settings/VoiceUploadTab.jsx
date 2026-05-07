import { useState, useEffect, useRef } from 'react'
import { TOKEN_STORAGE_KEY } from '../../api'

const API_BASE     = import.meta.env.VITE_API_BASE_URL || ''
const DEFAULT_TEXT = '약 먹을 시간이에요. 보호자님이 알려드려요. 물과 함께 천천히 약을 복용해주세요.'
const MAX_TEXT_LEN = 200

function VoiceUploadTab() {
  const [voices,        setVoices]        = useState([])
  const [voicesLoading, setVoicesLoading] = useState(true)
  const [selectedVoice, setSelectedVoice] = useState(null)
  const [text,          setText]          = useState(DEFAULT_TEXT)
  const [savedVoice,    setSavedVoice]    = useState(null)
  const [mode,          setMode]          = useState('idle') // idle | previewing | saving | done
  const [previewUrl,    setPreviewUrl]    = useState(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [errorMsg,      setErrorMsg]      = useState('')

  const audioRef = useRef(null)

  useEffect(() => {
    fetchVoices()
    fetchSavedVoice()
  }, [])

  function authHeaders() {
    const token = localStorage.getItem(TOKEN_STORAGE_KEY)
    const base  = { 'Content-Type': 'application/json' }
    return token ? { ...base, Authorization: `Bearer ${token}` } : base
  }

  async function fetchVoices() {
    setVoicesLoading(true)
    try {
      const res  = await fetch(`${API_BASE}/api/voice/voices`, { headers: authHeaders() })
      const data = await res.json()
      setVoices(data.voices || [])
    } catch {
      setVoices([])
    } finally {
      setVoicesLoading(false)
    }
  }

  async function fetchSavedVoice() {
    try {
      const res  = await fetch(`${API_BASE}/api/voice`, { headers: authHeaders() })
      const data = await res.json()
      setSavedVoice(data.voice || null)
    } catch {}
  }

  async function handlePreview() {
    if (!selectedVoice) { setErrorMsg('목소리를 먼저 선택해주세요'); return }
    if (!text.trim())   { setErrorMsg('알림 문구를 입력해주세요');    return }
    setPreviewLoading(true)
    setErrorMsg('')
    setPreviewUrl(null)
    try {
      const res = await fetch(`${API_BASE}/api/voice/preview`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ voice_id: selectedVoice.voice_id, text: text.trim() }),
      })
      if (!res.ok) {
        const e = await res.json().catch(() => ({}))
        throw new Error(e.message || '미리듣기 생성에 실패했습니다')
      }
      const data = await res.json()
      setPreviewUrl(data.url)
      setTimeout(() => audioRef.current?.play(), 150)
    } catch (err) {
      setErrorMsg(err.message)
    } finally {
      setPreviewLoading(false)
    }
  }

  async function handleSave() {
    if (!selectedVoice) { setErrorMsg('목소리를 먼저 선택해주세요'); return }
    if (!text.trim())   { setErrorMsg('알림 문구를 입력해주세요');    return }
    setMode('saving')
    setErrorMsg('')
    try {
      const res = await fetch(`${API_BASE}/api/voice/generate`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({
          voice_id:   selectedVoice.voice_id,
          voice_name: selectedVoice.name,
          text:       text.trim(),
        }),
      })
      if (!res.ok) {
        const e = await res.json().catch(() => ({}))
        throw new Error(e.message || '저장에 실패했습니다')
      }
      const data = await res.json()
      setSavedVoice(data.voice)
      setMode('done')
    } catch (err) {
      setErrorMsg(err.message)
      setMode('idle')
    }
  }

  const genderLabel = (labels) => {
    if (!labels) return ''
    if (labels.gender === 'female') return '여성'
    if (labels.gender === 'male')   return '남성'
    return ''
  }

  return (
    <div className="voice-tab">
      {/* 현재 등록된 음성 */}
      {savedVoice && mode !== 'done' && (
        <div className="voice-current">
          <div className="voice-current__icon">🔊</div>
          <div className="voice-current__info">
            <p className="voice-current__label">현재 적용된 알림 음성</p>
            <p className="voice-current__name">
              {savedVoice.tts_voice_name || '알림 음성'}
            </p>
            {savedVoice.updated_at && (
              <p className="voice-current__date">
                등록일: {new Date(savedVoice.updated_at).toLocaleDateString('ko-KR')}
              </p>
            )}
          </div>
          <span className="voice-current__badge">적용 완료</span>
        </div>
      )}

      {/* 저장 완료 */}
      {mode === 'done' && (
        <div className="voice-done">
          <div className="voice-done__check">✓</div>
          <div className="voice-done__text">
            <p className="voice-done__title">알림 음성 저장 완료</p>
            <p className="voice-done__desc">30초 이내 기기에 자동 반영됩니다</p>
          </div>
          <button className="voice-done__retry" onClick={() => setMode('idle')}>
            다시 설정
          </button>
        </div>
      )}

      {/* 저장 중 */}
      {mode === 'saving' && (
        <div className="voice-uploading">
          <span className="voice-uploading__spinner" />
          <p className="voice-uploading__text">음성을 생성하고 있습니다...</p>
        </div>
      )}

      {/* 설정 폼 */}
      {(mode === 'idle' || mode === 'previewing') && (
        <>
          {/* 알림 문구 입력 */}
          <div className="voice-section">
            <label className="voice-section__label">알림 문구</label>
            <textarea
              className="voice-text-input"
              value={text}
              onChange={(e) => setText(e.target.value.slice(0, MAX_TEXT_LEN))}
              rows={3}
              placeholder="복약 알림 시 읽어드릴 문구를 입력하세요"
            />
            <p className="voice-text-count">{text.length} / {MAX_TEXT_LEN}</p>
          </div>

          {/* 목소리 선택 */}
          <div className="voice-section">
            <label className="voice-section__label">목소리 선택</label>
            {voicesLoading ? (
              <p className="voice-loading">목소리 목록을 불러오는 중...</p>
            ) : voices.length === 0 ? (
              <p className="voice-loading">목소리 목록을 가져올 수 없습니다</p>
            ) : (
              <div className="voice-list">
                {voices.map((v) => (
                  <button
                    key={v.voice_id}
                    className={`voice-item${selectedVoice?.voice_id === v.voice_id ? ' voice-item--selected' : ''}`}
                    onClick={() => {
                      setSelectedVoice(v)
                      setPreviewUrl(null)
                      setErrorMsg('')
                    }}
                  >
                    <span className="voice-item__name">{v.name}</span>
                    {genderLabel(v.labels) && (
                      <span className="voice-item__tag">{genderLabel(v.labels)}</span>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* 미리듣기 플레이어 */}
          {previewUrl && (
            <audio
              ref={audioRef}
              src={`${API_BASE}${previewUrl}`}
              controls
              className="voice-preview-player"
            />
          )}

          {/* 액션 버튼 */}
          <div className="voice-actions">
            <button
              className="voice-btn voice-btn--preview"
              onClick={handlePreview}
              disabled={previewLoading || !selectedVoice}
            >
              {previewLoading ? '생성 중...' : '▶ 미리듣기'}
            </button>
            <button
              className="voice-btn voice-btn--save"
              onClick={handleSave}
              disabled={!selectedVoice || !text.trim()}
            >
              저장
            </button>
          </div>
        </>
      )}

      {/* 에러 */}
      {errorMsg && <p className="voice-error">{errorMsg}</p>}

      {/* 가이드 */}
      {(mode === 'idle' || mode === 'previewing') && (
        <div className="voice-guide">
          <p className="voice-guide__title">안내</p>
          <ul className="voice-guide__list">
            <li>알림 문구를 원하는 내용으로 수정할 수 있습니다</li>
            <li>목소리를 선택한 뒤 <strong>미리듣기</strong>로 확인 후 저장해주세요</li>
            <li>저장된 음성은 30초 이내 기기에 자동 반영됩니다</li>
            <li>이미 등록된 음성이 있으면 새로 저장 시 덮어씁니다</li>
          </ul>
        </div>
      )}
    </div>
  )
}

export default VoiceUploadTab
