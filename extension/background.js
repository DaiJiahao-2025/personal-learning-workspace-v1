const BACKEND_ORIGIN = 'http://127.0.0.1:8483'

function extractBvid(url) {
  return url.match(/BV[0-9A-Za-z]+/)?.[0] ?? ''
}

function extractPage(url) {
  try {
    const parsed = new URL(url)
    const page = Number(parsed.searchParams.get('p') || '1')
    return Number.isFinite(page) && page > 0 ? page : 1
  } catch {
    return 1
  }
}

function buildCookieHeader(cookies) {
  return cookies.map(cookie => `${cookie.name}=${cookie.value}`).join('; ')
}

async function fetchJson(url, init = {}) {
  const response = await fetch(url, init)
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }
  return response.json()
}

async function ensureBackendReady() {
  try {
    const response = await fetch(`${BACKEND_ORIGIN}/api/health`)
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }
  } catch {
    throw new Error('请先启动本地后端')
  }
}

function pickSubtitle(subtitles) {
  if (!subtitles.length) return null
  const isZh = subtitle => {
    const language = String(subtitle.lan || '').toLowerCase()
    return language.startsWith('zh') || language === 'ai-zh'
  }
  return subtitles.find(subtitle => isZh(subtitle) && !subtitle.ai_type)
    || subtitles.find(isZh)
    || subtitles[0]
}

async function prefetchCurrentBilibiliVideo(tab) {
  if (!tab.url || !tab.url.includes('bilibili.com/video/')) {
    throw new Error('当前页面不是 B 站视频页')
  }

  const bvid = extractBvid(tab.url)
  const page = extractPage(tab.url)
  if (!bvid) {
    throw new Error('无法识别 BV 号')
  }

  await ensureBackendReady()

  const cookies = await chrome.cookies.getAll({ url: 'https://www.bilibili.com/' })
  const cookie = buildCookieHeader(cookies)
  const bilibiliRequest = {
    credentials: 'include'
  }

  const viewPayload = await fetchJson(`https://api.bilibili.com/x/web-interface/view?bvid=${bvid}`, bilibiliRequest)
  const pages = viewPayload.data?.pages ?? []
  const targetPage = pages[page - 1]
  const cid = targetPage?.cid ?? viewPayload.data?.cid
  if (!cid) {
    throw new Error('无法读取当前分 P 的 cid')
  }

  const playerPayload = await fetchJson(
    `https://api.bilibili.com/x/player/wbi/v2?bvid=${bvid}&cid=${cid}`,
    bilibiliRequest
  )
  const track = pickSubtitle(playerPayload.data?.subtitle?.subtitles ?? [])
  let transcript = null

  if (track?.subtitle_url) {
    const subtitleUrl = track.subtitle_url.startsWith('//') ? `https:${track.subtitle_url}` : track.subtitle_url
    const subtitlePayload = await fetchJson(subtitleUrl, bilibiliRequest)
    const segments = (subtitlePayload.body ?? [])
      .map(item => ({
        start: Number(item.from ?? 0),
        end: Number(item.to ?? 0),
        text: String(item.content ?? '').trim()
      }))
      .filter(item => item.text)

    if (segments.length) {
      transcript = {
        language: String(track.lan || 'zh'),
        full_text: segments.map(segment => segment.text).join(' '),
        segments
      }
    }
  }

  await fetchJson(`${BACKEND_ORIGIN}/api/bilibili-prefetch`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      videoUrl: tab.url,
      bvid,
      page,
      cookie,
      transcript
    })
  })

  return transcript ? 'OK' : 'COOKIE'
}

chrome.action.onClicked.addListener(async tab => {
  try {
    const result = await prefetchCurrentBilibiliVideo(tab)
    await chrome.action.setBadgeBackgroundColor({ color: result === 'OK' ? '#16a34a' : '#d97706', tabId: tab.id })
    await chrome.action.setBadgeText({ text: result === 'OK' ? 'OK' : 'CK', tabId: tab.id })
    await chrome.action.setTitle({
      title: result === 'OK' ? '字幕已同步到 LearnFlow' : '已同步登录态，但当前视频未抓到字幕',
      tabId: tab.id
    })
  } catch (error) {
    console.warn('LearnFlow 字幕助手失败:', error)
    const message = error instanceof Error ? error.message : '同步失败'
    const badge = message === '请先启动本地后端' ? 'OFF' : 'ERR'
    await chrome.action.setBadgeBackgroundColor({ color: '#dc2626', tabId: tab.id })
    await chrome.action.setBadgeText({ text: badge, tabId: tab.id })
    await chrome.action.setTitle({ title: message, tabId: tab.id })
  }
})
