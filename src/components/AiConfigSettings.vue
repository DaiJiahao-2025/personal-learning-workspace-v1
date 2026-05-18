<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useAiConfigDraft } from '../composables/useAiConfigDraft'

const { config, isLoading, isSaving, isDirty, hydrate, save } = useAiConfigDraft()
const message = ref('')
const isError = ref(false)

onMounted(async () => {
  try {
    await hydrate()
  } catch {
    isError.value = true
    message.value = '读取 AI 配置失败'
  }
})

async function saveConfig() {
  isSaving.value = true
  isError.value = false
  message.value = ''

  try {
    await save()
    message.value = 'AI 生成配置已保存'
  } catch {
    isError.value = true
    message.value = '保存失败，请确认后端已启动'
  } finally {
    isSaving.value = false
  }
}
</script>

<template>
  <section class="ai-config-card">
    <div class="ai-config-header">
      <div>
        <h2>AI 生成配置</h2>
        <p>用于把视频字幕整理成结构化摘要，配置保存在本地后端。</p>
      </div>
      <button type="button" :disabled="isSaving || isLoading" @click="saveConfig">
        {{ isSaving ? '保存中…' : '保存配置' }}
      </button>
    </div>

    <div class="ai-config-fields">
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
        <input v-model="config.modelName" type="text" placeholder="gpt-4.1-mini" />
      </label>
    </div>

    <p v-if="message" class="ai-config-message" :class="{ error: isError }">{{ message }}</p>
    <p v-else-if="isDirty" class="ai-config-message pending">有未保存的修改</p>
  </section>
</template>

<style scoped>
.ai-config-card {
  padding: 20px;
  border: 1px solid #e1e7ef;
  border-radius: 12px;
  background: white;
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.05);
}

.ai-config-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.ai-config-header h2 {
  margin: 0;
  color: #111827;
  font-size: 22px;
}

.ai-config-header p {
  margin: 8px 0 0;
  color: #64748b;
}

.ai-config-header button {
  height: 38px;
  padding: 0 14px;
  border: none;
  border-radius: 8px;
  background: #2563eb;
  color: white;
  font-weight: 700;
}

.ai-config-fields {
  display: grid;
  gap: 14px;
}

.ai-config-fields label {
  display: grid;
  gap: 8px;
  color: #334155;
  font-size: 14px;
  font-weight: 700;
}

.ai-config-fields input {
  width: 100%;
  height: 44px;
  padding: 0 12px;
  border: 1px solid #dbe3ee;
  border-radius: 8px;
  outline: none;
  background: #f8fafc;
  color: #111827;
}

.ai-config-fields input:focus {
  border-color: #2563eb;
  background: white;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.ai-config-message {
  margin: 14px 0 0;
  color: #16a34a;
  font-weight: 700;
}

.ai-config-message.error {
  color: #dc2626;
}

.ai-config-message.pending {
  color: #d97706;
}

@media (max-width: 520px) {
  .ai-config-header {
    flex-direction: column;
  }
}
</style>
