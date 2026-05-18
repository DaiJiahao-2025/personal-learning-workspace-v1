import type { SttProvider } from './videoNotes'

export type TranscriptionConfig = {
  provider: SttProvider
  baseUrl: string
  apiKey: string
  modelName: string
  localModelSize: string
  localDevice: string
}

async function parseJsonResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error('请求失败，请稍后重试')
  }

  return response.json() as Promise<T>
}

export async function fetchTranscriptionConfig() {
  const response = await fetch('/api/transcription-config')
  return parseJsonResponse<TranscriptionConfig>(response)
}

export async function updateTranscriptionConfig(config: TranscriptionConfig) {
  const response = await fetch('/api/transcription-config', {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(config)
  })

  return parseJsonResponse<TranscriptionConfig>(response)
}
