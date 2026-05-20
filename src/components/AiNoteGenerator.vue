<script setup lang="ts">
import { computed, ref } from 'vue'
import { useVideoNoteGeneration } from '../composables/useVideoNoteGeneration'
import type {
  LearningNote,
  SttProvider,
  TranscriptSource,
  VideoNotePlatform,
  VideoNoteStyle
} from '../services/videoNotes'

const props = defineProps<{
  videoUrl: string
  platform: VideoNotePlatform | ''
}>()

const emit = defineEmits<{
  append: [markdown: string]
}>()

const isDialogOpen = ref(false)
const selectedStyle = ref<VideoNoteStyle>('minimal')
const selectedProvider = ref<SttProvider>('local_whisper')
const generatedMarkdown = ref('')
const generatedNote = ref<LearningNote | null>(null)
const generatedTranscriptSource = ref<TranscriptSource | null>(null)
const { isGenerating, statusText, errorMessage, generate } = useVideoNoteGeneration()

const isDisabled = computed(() => !props.videoUrl || !props.platform || isGenerating.value)
const buttonTitle = computed(() => {
  if (!props.videoUrl) return '当前课节未绑定视频'
  if (!props.platform) return '仅支持 B 站或 YouTube 视频'
  return '从当前视频生成摘要'
})

function openDialog() {
  if (isDisabled.value) return
  errorMessage.value = ''
  generatedMarkdown.value = ''
  generatedNote.value = null
  generatedTranscriptSource.value = null
  isDialogOpen.value = true
}

function closeDialog() {
  if (isGenerating.value) return
  isDialogOpen.value = false
}

async function handleGenerate() {
  if (!props.videoUrl || !props.platform) return

  try {
    const result = await generate(
      props.videoUrl,
      props.platform,
      selectedStyle.value,
      selectedProvider.value
    )
    generatedMarkdown.value = result.markdown ?? ''
    generatedNote.value = result.note ?? null
    generatedTranscriptSource.value = result.transcriptSource ?? null
  } catch {
    // Error state is rendered inside the dialog.
  }
}

function appendResult() {
  if (!generatedMarkdown.value) return
  emit('append', generatedMarkdown.value)
  isDialogOpen.value = false
}
</script>

<template>
  <button
    type="button"
    class="ai-note-trigger"
    :disabled="isDisabled"
    :title="buttonTitle"
    :aria-label="buttonTitle"
    @click="openDialog"
  >
    <span v-if="isGenerating" class="spinner" aria-hidden="true"></span>
    <svg v-else class="trigger-icon" viewBox="0 0 20 20" aria-hidden="true">
      <path d="M10 3.5l1.2 3.2 3.3 1.1-3.3 1.2L10 12.2 8.8 9 5.5 7.8l3.3-1.1L10 3.5Z"></path>
      <path d="M15 12.5l.6 1.6 1.6.6-1.6.6-.6 1.6-.6-1.6-1.6-.6 1.6-.6.6-1.6Z"></path>
    </svg>
    {{ isGenerating ? '生成中' : 'AI生成' }}
  </button>

  <Teleport to="body">
    <div v-if="isDialogOpen" class="ai-dialog-backdrop" @click.self="closeDialog">
      <section class="ai-dialog" role="dialog" aria-modal="true" aria-labelledby="ai-note-title">
        <header>
          <div>
            <h2 id="ai-note-title">生成视频笔记</h2>
            <p>先生成结构化结果，再追加到当前课节笔记。</p>
          </div>
          <button type="button" :disabled="isGenerating" aria-label="关闭" @click="closeDialog">
            <svg class="close-icon" viewBox="0 0 20 20" aria-hidden="true">
              <path d="M5.5 5.5 14.5 14.5"></path>
              <path d="M14.5 5.5 5.5 14.5"></path>
            </svg>
          </button>
        </header>

        <div class="controls">
          <fieldset>
            <legend>摘要风格</legend>
            <label>
              <input v-model="selectedStyle" type="radio" value="minimal" />
              <span>精简</span>
            </label>
            <label>
              <input v-model="selectedStyle" type="radio" value="detailed" />
              <span>详细</span>
            </label>
          </fieldset>

          <label class="provider-field">
            <span>无字幕时使用的转写服务</span>
            <select v-model="selectedProvider">
              <option value="local_whisper">Local Whisper</option>
              <option value="openai_compatible">OpenAI compatible</option>
              <option value="groq">Groq</option>
            </select>
          </label>
        </div>

        <p v-if="errorMessage" class="dialog-error">{{ errorMessage }}</p>
        <p v-else-if="statusText" class="dialog-status">{{ statusText }}</p>

        <article v-if="generatedNote" class="result-preview">
          <p v-if="generatedTranscriptSource" class="source-badge">
            {{ generatedTranscriptSource === 'native_subtitle' ? '来自原生字幕' : '来自语音转写' }}
          </p>
          <h3>{{ generatedNote.title }}</h3>
          <p>{{ generatedNote.summary }}</p>

          <div v-if="generatedNote.chapters.length">
            <h4>章节</h4>
            <ul>
              <li v-for="chapter in generatedNote.chapters" :key="chapter.title">
                <strong>{{ chapter.title }}</strong>
                <span>{{ chapter.summary }}</span>
              </li>
            </ul>
          </div>

          <div v-if="generatedNote.keyPoints.length">
            <h4>关键要点</h4>
            <ul>
              <li v-for="point in generatedNote.keyPoints" :key="point">{{ point }}</li>
            </ul>
          </div>

          <div v-if="generatedNote.actionItems.length">
            <h4>行动项</h4>
            <ul>
              <li v-for="item in generatedNote.actionItems" :key="item">{{ item }}</li>
            </ul>
          </div>
        </article>

        <footer>
          <button type="button" class="secondary" :disabled="isGenerating" @click="closeDialog">取消</button>
          <button
            v-if="!generatedMarkdown"
            type="button"
            class="primary"
            :disabled="isGenerating"
            @click="handleGenerate"
          >
            {{ isGenerating ? '生成中…' : '开始生成' }}
          </button>
          <button
            v-else
            type="button"
            class="primary"
            :disabled="isGenerating"
            @click="appendResult"
          >
            追加到笔记
          </button>
        </footer>
      </section>
    </div>
  </Teleport>
</template>

<style scoped>
.ai-note-trigger {
  min-width: 78px;
  height: 28px;
  padding: 0 9px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  background: #eff6ff;
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
}

.trigger-icon,
.close-icon {
  display: block;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.75;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.trigger-icon {
  width: 14px;
  height: 14px;
}

.ai-note-trigger:disabled {
  border-color: #e2e8f0;
  background: #f8fafc;
  color: #94a3b8;
  cursor: not-allowed;
}

.spinner {
  width: 12px;
  height: 12px;
  border: 2px solid rgba(37, 99, 235, 0.22);
  border-top-color: currentColor;
  border-radius: 999px;
  animation: spin 700ms linear infinite;
}

.ai-dialog-backdrop {
  position: fixed;
  inset: 0;
  z-index: 20;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(15, 23, 42, 0.34);
  backdrop-filter: blur(6px);
}

.ai-dialog {
  width: min(560px, 100%);
  max-height: min(760px, calc(100vh - 40px));
  overflow: auto;
  padding: 22px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 24px 70px rgba(15, 23, 42, 0.22);
}

.ai-dialog header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}

.ai-dialog h2 {
  margin: 0;
  color: #111827;
  font-size: 22px;
}

.ai-dialog p {
  margin: 7px 0 0;
  color: #64748b;
  font-size: 14px;
}

.ai-dialog header button {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
  color: #475569;
}

.close-icon {
  width: 18px;
  height: 18px;
}

.controls {
  display: grid;
  gap: 16px;
}

.ai-dialog fieldset {
  margin: 0;
  padding: 0;
  display: grid;
  gap: 10px;
  border: none;
}

.ai-dialog legend,
.provider-field span {
  margin-bottom: 10px;
  color: #334155;
  font-size: 14px;
  font-weight: 700;
}

.ai-dialog label {
  min-height: 42px;
  padding: 0 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid #dbe3ee;
  border-radius: 8px;
  background: #f8fafc;
  color: #334155;
}

.provider-field {
  display: grid !important;
  align-items: stretch !important;
  gap: 8px !important;
  padding: 12px !important;
}

.provider-field select {
  height: 40px;
  border: 1px solid #dbe3ee;
  border-radius: 8px;
  background: white;
  padding: 0 10px;
}

.dialog-error,
.dialog-status {
  min-height: 20px;
  margin-top: 16px;
  font-weight: 700;
}

.dialog-error {
  color: #dc2626;
}

.dialog-status {
  color: #2563eb;
}

.result-preview {
  margin-top: 18px;
  padding: 16px;
  border: 1px solid #dbeafe;
  border-radius: 8px;
  background: #f8fbff;
}

.source-badge {
  display: inline-flex;
  width: fit-content;
  margin: 0 0 12px !important;
  padding: 5px 10px;
  border-radius: 999px;
  background: #dbeafe;
  color: #1d4ed8 !important;
  font-size: 12px !important;
  font-weight: 700;
}

.result-preview h3,
.result-preview h4 {
  margin: 0 0 8px;
  color: #111827;
}

.result-preview h4 {
  margin-top: 16px;
  font-size: 14px;
}

.result-preview p {
  color: #334155;
}

.result-preview ul {
  margin: 0;
  padding-left: 20px;
}

.result-preview li {
  margin-top: 6px;
  color: #334155;
}

.result-preview li span {
  display: block;
  color: #64748b;
}

.ai-dialog footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}

.ai-dialog footer button {
  height: 40px;
  padding: 0 16px;
  border-radius: 8px;
  font-weight: 700;
}

.ai-dialog footer .secondary {
  border: 1px solid #dbe3ee;
  background: white;
  color: #334155;
}

.ai-dialog footer .primary {
  border: none;
  background: #2563eb;
  color: white;
}

.ai-dialog button:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
