import { useState, useRef, useEffect } from 'react'
import { TOKEN_STORAGE_KEY } from '../../api'

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
const MAX_FILE_MB = 10
const ALLOWED_TYPES = /\.(mp3|wav|m4a|webm|ogg)$/i

function VoiceUploadTab() {
  const [mode, setMode] = useState('idle') // idle | recording | previewing | uploading | done | error
  const [audioBlob, setAudioBlob] = useState(null)
  const [audioUrl, setAudioUrl] = useState(null)
  const [fileName, setFileName] = useState('')
  const [uploadedVoice, setUploadedVoice] = useState(null)
  const [errorMsg, setErrorMsg] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const [recordSec, setRecordSec] = useState(0)

  const fileInputRef = useRef(null)
  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])
  const streamRef = useRef(null)
  const timerRef = useRef(null)

  useEffect(() => {
    fetchUploadedVoice()
    return () => {
      if (audioUrl) URL.revokeObjectURL(audioUrl)
      stopStream()
      clearInterval(timerRef.current)
    }
  }, [])

  function stopStream() {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop())
      streamRef.current = null
    }
  }

  async function fetchUploadedVoice() {
    try {
      const token = localStorage.getItem(TOKEN_STORAGE_KEY)
      const res = await fetch(`${API_BASE}/api/voice`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (res.ok) {
        const data = await res.json()
        setUploadedVoice(data.voice || null)
      }
    } catch {}
  }

  function validateFile(file) {
    if (!file) return '파일을 선택해주세요'
    if (!ALLOWED_TYPES.test(file.name) && !file.type.startsWith('audio/')) {
      return 'mp3, wav, m4a, webm 파일만 업로드할 수 있습니다'
    }
    if (file.size > MAX_FILE_MB * 1024 * 1024) {
      return `파일 크기는 ${MAX_FILE_MB}MB 이하여야 합니다`
    }
    return null
  }

  function applyFile(file, name) {
    if (audioUrl) URL.revokeObjectURL(audioUrl)
    const url = URL.createObjectURL(file)
    setAudioBlob(file)
    setAudioUrl(url)
    setFileName(name)
    setMode('previewing')
    setErrorMsg('')
  }

  function handleFileSelect(file) {
    const err = validateFile(file)
    if (err) { setErrorMsg(err); return }
    applyFile(file, file.name)
  }

  function handleDrop(e) {
    e.preventDefault()
    setIsDragging(false)
    handleFileSelect(e.dataTransfer.files[0])
  }

  async function handleStartRecord() {
    setErrorMsg('')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      chunksRef.current = []
      setRecordSec(0)

      timerRef.current = setInterval(() => setRecordSec((s) => s + 1), 1000)

      const mr = new MediaRecorder(stream, { mimeType: 'audio/webm' })
      mr.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data) }
      mr.onstop = () => {
        clearInterval(timerRef.current)
        stopStream()
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        const time = new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
        applyFile(blob, `녹음_${time}.webm`)
      }
      mediaRecorderRef.current = mr
      mr.start()
      setMode('recording')
    } catch {
      setErrorMsg('마이크 접근 권한이 필요합니다. 브라우저 설정에서 허용해주세요.')
    }
  }

  function handleStopRecord() {
    if (mediaRecorderRef.current?.state !== 'inactive') {
      mediaRecorderRef.current.stop()
    }
  }

  async function handleUpload() {
    if (!audioBlob) return
    setMode('uploading')
    setErrorMsg('')
    try {
      const token = localStorage.getItem(TOKEN_STORAGE_KEY)
      const formData = new FormData()
      formData.append('voice', audioBlob, fileName || 'voice.webm')

      const res = await fetch(`${API_BASE}/api/voice/upload`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      })
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.message || '업로드에 실패했습니다')
      }
      const data = await res.json()
      setUploadedVoice(data.voice || { file_name: fileName, uploaded_at: new Date().toISOString() })
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

  function fmtSec(s) {
    const m = Math.floor(s / 60)
    const sec = s % 60
    return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
  }

  return (
    <div className="voice-tab">
      {/* 현재 등록된 목소리 */}
      {uploadedVoice && mode !== 'done' && (
        <div className="voice-current">
          <div className="voice-current__icon">🎙️</div>
          <div className="voice-current__info">
            <p className="voice-current__label">현재 등록된 목소리</p>
            <p className="voice-current__name">{uploadedVoice.file_name || '목소리 파일'}</p>
            {uploadedVoice.uploaded_at && (
              <p className="voice-current__date">
                등록일: {new Date(uploadedVoice.uploaded_at).toLocaleDateString('ko-KR')}
              </p>
            )}
          </div>
          <span className="voice-current__badge">적용 중</span>
        </div>
      )}

      {/* 업로드 완료 */}
      {mode === 'done' && (
        <div className="voice-done">
          <div className="voice-done__check">✓</div>
          <div className="voice-done__text">
            <p className="voice-done__title">목소리 등록 완료</p>
            <p className="voice-done__desc">AI가 목소리를 학습 후 복약 알림에 적용합니다</p>
          </div>
          <button className="voice-done__retry" onClick={() => { setMode('idle'); setUploadedVoice(null) }}>
            다시 업로드
          </button>
        </div>
      )}

      {/* 업로드 / 녹음 선택 영역 */}
      {(mode === 'idle' || mode === 'recording') && (
        <>
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
              accept=".mp3,.wav,.m4a,.webm,.ogg,audio/*"
              style={{ display: 'none' }}
              onChange={(e) => handleFileSelect(e.target.files[0])}
            />
            <span className="voice-dropzone__icon">🎵</span>
            <p className="voice-dropzone__title">파일을 드래그하거나 클릭하여 선택</p>
            <p className="voice-dropzone__sub">mp3 · wav · m4a · webm &nbsp;|&nbsp; 최대 {MAX_FILE_MB}MB</p>
          </div>

          <div className="voice-or">
            <span className="voice-or__line" />
            <span className="voice-or__text">또는</span>
            <span className="voice-or__line" />
          </div>

          {mode === 'idle' ? (
            <button className="voice-record-btn" onClick={handleStartRecord}>
              <span className="voice-record-btn__dot" />
              마이크로 직접 녹음
            </button>
          ) : (
            <div className="voice-recording">
              <span className="voice-recording__pulse" />
              <span className="voice-recording__timer">{fmtSec(recordSec)}</span>
              <span className="voice-recording__label">녹음 중</span>
              <button className="voice-recording__stop" onClick={handleStopRecord}>
                ⏹ 중지
              </button>
            </div>
          )}
        </>
      )}

      {/* 미리듣기 */}
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

      {/* 업로드 중 */}
      {mode === 'uploading' && (
        <div className="voice-uploading">
          <span className="voice-uploading__spinner" />
          <p className="voice-uploading__text">업로드 중...</p>
        </div>
      )}

      {/* 에러 */}
      {errorMsg && <p className="voice-error">{errorMsg}</p>}

      {/* 가이드 */}
      <div className="voice-guide">
        <p className="voice-guide__title">녹음 가이드</p>
        <ul className="voice-guide__list">
          <li>조용한 환경에서 <strong>10~30초</strong> 분량의 목소리를 녹음해 주세요</li>
          <li>녹음된 목소리는 AI 처리 후 복약 알림 음성으로 사용됩니다</li>
          <li>자연스럽고 명확하게 말씀해 주시면 더 좋은 품질이 나옵니다</li>
          <li>이미 등록된 목소리가 있으면 새로 업로드 시 덮어씁니다</li>
        </ul>
      </div>
    </div>
  )
}

export default VoiceUploadTab
