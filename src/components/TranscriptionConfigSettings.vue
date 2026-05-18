<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  fetchTranscriptionConfig,
  updateTranscriptionConfig,
  type TranscriptionConfig
} from '../services/transcriptionConfig'

const config = ref<TranscriptionConfig>({
  provider: 'local_whisper',
  baseUrl: '',
  apiKey: '',
  modelName: '',
  localModelSize: 'base',
  localDevice: 'cpu'
})
const isLoading = ref(false)
const isSaving = ref(false)
const message = ref('')
const isError = ref(false)
const usesCloudProvider = computed(() => config.value.provider !== 'local_whisper')

onMounted(async () => {
  isLoading.value = true
  try {
    config.value = await fetchTranscriptionConfig()
  } catch {
    isError.value = true
    message.value = '读取转写配置失败'
  } finally {
    isLoading.value = false
  }
})

async function saveConfig() {
  isSaving.value = true
  isError.value = false
  message.value = ''

  try {
    config.value = await updateTranscriptionConfig(config.value)
    message.value = '转写配置已保存'
  } catch {
    isError.value = true
    message.value = '保存失败，请确认后端已启动'
  } finally {
    isSaving.value = false
  }
}
</script>

<template>
  <section class="settings-card">
    <div class="settings-header-row">
      <div>
        <h2>转写配置</h2>
        <p>默认使用本地 Whisper；也可以切换到 OpenAI 兼容接口或 Groq。</p>
      </div>
      <button type="button" :disabled="isSaving || isLoading" @click="saveConfig">
        {{ isSaving ? '保存中…' : '保存配置' }}
      </button>
    </div>

    <div class="settings-fields">
      <label>
        <span>Provider</span>
        <select v-model="config.provider">
          <option value="local_whisper">Local Whisper</option>
          <option value="openai_compatible">OpenAI compatible</option>
          <option value="groq">Groq</option>
        </select>
      </label>

      <template v-if="config.provider === 'local_whisper'">
        <label>
          <span>本地模型</span>
          <input v-model="config.localModelSize" type="text" placeholder="base" />
        </label>
        <label>
          <span>设备</span>
          <input v-model="config.localDevice" type="text" placeholder="cpu / cuda" />
        </label>
      </template>

      <template v-if="usesCloudProvider">
        <label>
          <span>Base URL</span>
          <input v-model="config.baseUrl" type="url" placeholder="https://api.openai.com/v1" />
        </label>
        <label>
          <span>API Key</span>
          <input v-model="config.apiKey" type="password" placeholder="sk-..." />
        </label>
        <label>
          <span>模型名</span>
          <input v-model="config.modelName" type="text" placeholder="gpt-4o-mini-transcribe" />
        </label>
      </template>
    </div>

    <p v-if="message" class="settings-message" :class="{ error: isError }">{{ message }}</p>
  </section>
</template>

<style scoped>
.settings-card {
  padding: 20px;
  border: 1px solid #e1e7ef;
  border-radius: 12px;
  background: white;
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.05);
}

.settings-header-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.settings-header-row h2 {
  margin: 0;
  color: #111827;
  font-size: 22px;
}

.settings-header-row p {
  margin: 8px 0 0;
  color: #64748b;
}

.settings-header-row button {
  height: 38px;
  padding: 0 14px;
  border: none;
  border-radius: 8px;
  background: #2563eb;
  color: white;
  font-weight: 700;
}

.settings-fields {
  display: grid;
  gap: 14px;
}

.settings-fields label {
  display: grid;
  gap: 8px;
  color: #334155;
  font-size: 14px;
  font-weight: 700;
}

.settings-fields input,
.settings-fields select {
  width: 100%;
  height: 44px;
  padding: 0 12px;
  border: 1px solid #dbe3ee;
  border-radius: 8px;
  outline: none;
  background: #f8fafc;
  color: #111827;
}

.settings-fields input:focus,
.settings-fields select:focus {
  border-color: #2563eb;
  background: white;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.settings-message {
  margin: 14px 0 0;
  color: #16a34a;
  font-weight: 700;
}

.settings-message.error {
  color: #dc2626;
}

@media (max-width: 520px) {
  .settings-header-row {
    flex-direction: column;
  }
}
</style>
