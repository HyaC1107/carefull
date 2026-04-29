import { useEffect, useRef, useState } from 'react'
import { TOKEN_STORAGE_KEY } from '../../api'

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
const MAX_FILE_MB = 20

function AlarmSoundTab() {
  const [mode, setMode] = useState('idle') // idle | previewing | uploading | done
  const [audioBlob, setAudioBlob] = useState(null)
  const [audioUrl, setAudioUrl] = useState(null)
  const [fileName, setFileName] = useState('')
  const [currentSound, setCurrentSound] = useState(null)
  const [errorMsg, setErrorMsg] = useState('')
  const [isDragging, setIsDragging] = useState(false)

  const fileInputRef = useRef(null)

  useEffect(() => {
    fetchCurrentSound()
    return () => { if (audioUrl) URL.revokeObjectURL(audioUrl) }
  }, [])

  async function fetchCurrentSound() {
    try {
      const token = localStorage.getItem(TOKEN_STORAGE_KEY)
      const res = await fetch(`${API_BASE}/api/device/sound`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (res.ok) {
        const data = await res.json()
        setCurrentSound(data.sound || null)
      }
    } catch {}
  }

  function validate(file) {
    if (!file) return '파일을 선택해주세요'
    if (!file.type.startsWith('audio/') && !/\.(mp3|wav|m4a|ogg)$/i.test(file.name)) {
      return 'MP3, WAV, M4A, OGG 파일만 업로드할 수 있습니다'
    }
    if (file.size > MAX_FILE_MB * 1024 * 1024) {
      return `파일 크기는 ${MAX_FILE_MB}MB 이하여야 합니다`
    }
    return null
  }

  function applyFile(file) {
    const err = validate(file)
    if (err) { setErrorMsg(err); return }
    if (audioUrl) URL.revokeObjectURL(audioUrl)
    setAudioBlob(file)
    setAudioUrl(URL.createObjectURL(file))
    setFileName(file.name)
    setMode('previewing')
    setErrorMsg('')
  }

  function handleDrop(e) {
    e.preventDefault()
    setIsDragging(false)
    applyFile(e.dataTransfer.files[0])
  }

  async function handleUpload() {
    if (!audioBlob) return
    setMode('uploading')
    setErrorMsg('')
    try {
      const token = localStorage.getItem(TOKEN_STORAGE_KEY)
      const formData = new FormData()
      formData.append('sound', audioBlob, fileName)

      const res = await fetch(`${API_BASE}/api/device/sound`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.message || '업로드에 실패했습니다')
      }
      const data = await res.json()
      setCurrentSound(data.sound || { file_name: fileName, updated_at: new Date().toISOString() })
      setMode('done')
      setAudioBlob(null)
      if (audioUrl) URL.revokeObjectURL(audioUrl)
      setAudioUrl(null)
    } catch (err) {
      setErrorMsg(err.message || '업로드 중 오류가 발생했습니다')
      setMode('previewing')
    }
  }

  function handleReset() {
    if (audioUrl) URL.revokeObjectURL(audioUrl)
    setAudioBlob(null)
    setAudioUrl(null)
    setFileName('')
    setMode('idle')
    setErrorMsg('')
  }

  return (
    <div className="voice-tab">
      {currentSound && mode !== 'done' && (
        <div className="voice-current">
          <div className="voice-current__icon">🔔</div>
          <div className="voice-current__info">
            <p className="voice-current__label">현재 등록된 알림음</p>
            <p className="voice-current__name">{currentSound.file_name || '알림음 파일'}</p>
            {currentSound.updated_at && (
              <p className="voice-current__date">
                등록일: {new Date(currentSound.updated_at).toLocaleDateString('ko-KR')}
              </p>
            )}
          </div>
          <span className="voice-current__badge">적용 중</span>
        </div>
      )}

      {mode === 'done' && (
        <div className="voice-done">
          <div className="voice-done__check">✓</div>
          <div className="voice-done__text">
            <p className="voice-done__title">알림음 등록 완료</p>
            <p className="voice-done__desc">30초 이내에 기기에 자동으로 적용됩니다</p>
          </div>
          <button className="voice-done__retry" onClick={() => setMode('idle')}>
            다시 업로드
          </button>
        </div>
      )}

      {mode === 'idle' && (
        <div
          className={`voice-dropzone${isDragging ? ' voice-dropzone--over' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".mp3,.wav,.m4a,.ogg,audio/*"
            style={{ display: 'none' }}
            onChange={(e) => applyFile(e.target.files[0])}
          />
          <span className="voice-dropzone__icon">🎵</span>
          <p className="voice-dropzone__title">파일을 드래그하거나 클릭하여 선택</p>
          <p className="voice-dropzone__sub">mp3 · wav · m4a · ogg &nbsp;|&nbsp; 최대 {MAX_FILE_MB}MB</p>
        </div>
      )}

      {mode === 'previewing' && (
        <div className="voice-preview">
          <div className="voice-preview__header">
            <span className="voice-preview__icon">🎵</span>
            <span className="voice-preview__name">{fileName}</span>
            <button className="voice-preview__remove" onClick={handleReset} title="제거">✕</button>
          </div>
          <audio src={audioUrl} controls className="voice-preview__player" />
          <div className="voice-preview__actions">
            <button className="voice-preview__btn voice-preview__btn--cancel" onClick={handleReset}>
              다시 선택
            </button>
            <button className="voice-preview__btn voice-preview__btn--upload" onClick={handleUpload}>
              업로드
            </button>
          </div>
        </div>
      )}

      {mode === 'uploading' && (
        <div className="voice-uploading">
          <span className="voice-uploading__spinner" />
          <p className="voice-uploading__text">업로드 중...</p>
        </div>
      )}

      {errorMsg && <p className="voice-error">{errorMsg}</p>}

      <div className="voice-guide">
        <p className="voice-guide__title">알림음 안내</p>
        <ul className="voice-guide__list">
          <li>복약 시간이 되면 기기에서 이 파일이 재생됩니다</li>
          <li>업로드 후 <strong>30초 이내</strong>에 기기에 자동으로 적용됩니다</li>
          <li>기존 알림음이 있으면 새로 업로드 시 자동으로 대체됩니다</li>
          <li>등록된 알림음이 없으면 기기 기본음이 사용됩니다</li>
        </ul>
      </div>
    </div>
  )
}

export default AlarmSoundTab
