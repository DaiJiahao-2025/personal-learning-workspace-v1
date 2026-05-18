export type DownloaderConfig = {
  bilibiliCookie: string
  proxyUrl: string
}

async function parseJsonResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error('请求失败，请稍后重试')
  }

  return response.json() as Promise<T>
}

export async function fetchDownloaderConfig() {
  const response = await fetch('/api/downloader-config')
  return parseJsonResponse<DownloaderConfig>(response)
}

export async function updateDownloaderConfig(config: DownloaderConfig) {
  const response = await fetch('/api/downloader-config', {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(config)
  })

  return parseJsonResponse<DownloaderConfig>(response)
}
