export type VideoNoteStyle = 'minimal' | 'detailed'
export type VideoNotePlatform = 'bilibili' | 'youtube'
export type VideoNoteStatus =
  | 'PENDING'
  | 'FETCHING_SUBTITLE'
  | 'EXTRACTING_AUDIO'
  | 'TRANSCRIBING'
  | 'CHUNKING'
  | 'SUMMARIZING'
  | 'SUCCESS'
  | 'FAILED'
export type SttProvider = 'local_whisper' | 'openai_compatible' | 'groq'
export type TranscriptSource = 'native_subtitle' | 'speech_to_text'

export type NoteChapter = {
  title: string
  summary: string
  start?: number | null
  end?: number | null
}

export type NoteReference = {
  timestamp: number
  label: string
}

export type LearningNote = {
  title: string
  summary: string
  chapters: NoteChapter[]
  keyPoints: string[]
  actionItems: string[]
  references: NoteReference[]
}

export type VideoNoteTask = {
  taskId: string
  status: VideoNoteStatus
  platform?: VideoNotePlatform | null
  style?: VideoNoteStyle | null
  sttProvider?: SttProvider | null
  transcriptSource?: TranscriptSource | null
  markdown?: string | null
  note?: LearningNote | null
  message?: string | null
}

type StartVideoNotePayload = {
  videoUrl: string
  platform: VideoNotePlatform
  style: VideoNoteStyle
  sttProvider?: SttProvider
}

async function parseJsonResponse<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => null)

  if (!response.ok) {
    throw new Error(payload?.detail ?? payload?.message ?? '请求失败，请稍后重试')
  }

  return payload as T
}

export async function startVideoNote(payload: StartVideoNotePayload) {
  const response = await fetch('/api/video-notes', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload)
  })

  return parseJsonResponse<{ taskId: string }>(response)
}

export async function fetchVideoNoteTask(taskId: string) {
  const response = await fetch(`/api/video-notes/${encodeURIComponent(taskId)}`)
  return parseJsonResponse<VideoNoteTask>(response)
}
