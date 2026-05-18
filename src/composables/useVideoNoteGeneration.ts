import { onBeforeUnmount, ref } from 'vue'
import {
  fetchVideoNoteTask,
  startVideoNote,
  type SttProvider,
  type VideoNotePlatform,
  type VideoNoteStyle,
  type VideoNoteTask
} from '../services/videoNotes'

const POLL_INTERVAL_MS = 1200

const STATUS_TEXT: Record<VideoNoteTask['status'], string> = {
  PENDING: '任务排队中',
  FETCHING_SUBTITLE: '正在读取原生字幕',
  EXTRACTING_AUDIO: '正在提取音频',
  TRANSCRIBING: '正在语音转写',
  CHUNKING: '正在切分长文本',
  SUMMARIZING: '正在生成结构化笔记',
  SUCCESS: '生成完成',
  FAILED: '生成失败'
}

export function useVideoNoteGeneration() {
  const isGenerating = ref(false)
  const statusText = ref('')
  const errorMessage = ref('')
  let pollTimer: ReturnType<typeof setTimeout> | undefined

  function clearPollTimer() {
    if (!pollTimer) return
    clearTimeout(pollTimer)
    pollTimer = undefined
  }

  async function waitForResult(taskId: string): Promise<VideoNoteTask> {
    const task = await fetchVideoNoteTask(taskId)

    if (task.status === 'SUCCESS' && task.markdown && task.note) {
      return task
    }

    if (task.status === 'FAILED') {
      throw new Error(task.message ?? '生成失败，请稍后重试')
    }

    statusText.value = STATUS_TEXT[task.status]

    return new Promise((resolve, reject) => {
      pollTimer = setTimeout(() => {
        waitForResult(taskId).then(resolve).catch(reject)
      }, POLL_INTERVAL_MS)
    })
  }

  async function generate(
    videoUrl: string,
    platform: VideoNotePlatform,
    style: VideoNoteStyle,
    sttProvider?: SttProvider
  ) {
    isGenerating.value = true
    errorMessage.value = ''
    statusText.value = STATUS_TEXT.PENDING
    clearPollTimer()

    try {
      const { taskId } = await startVideoNote({ videoUrl, platform, style, sttProvider })
      return await waitForResult(taskId)
    } catch (error) {
      errorMessage.value = error instanceof Error ? error.message : '生成失败，请稍后重试'
      throw error
    } finally {
      isGenerating.value = false
      clearPollTimer()
    }
  }

  onBeforeUnmount(() => {
    clearPollTimer()
  })

  return {
    isGenerating,
    statusText,
    errorMessage,
    generate
  }
}
