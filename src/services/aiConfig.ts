export type AiConfig = {
  baseUrl: string
  apiKey: string
  modelName: string
}

async function parseJsonResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error('请求失败，请稍后重试')
  }

  return response.json() as Promise<T>
}

export async function fetchAiConfig() {
  const response = await fetch('/api/ai-config')
  return parseJsonResponse<AiConfig>(response)
}

export async function updateAiConfig(config: AiConfig) {
  const response = await fetch('/api/ai-config', {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(config)
  })

  return parseJsonResponse<AiConfig>(response)
}

