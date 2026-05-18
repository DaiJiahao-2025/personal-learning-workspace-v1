<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { fetchDownloaderConfig, updateDownloaderConfig, type DownloaderConfig } from '../services/downloaderConfig'

const config = ref<DownloaderConfig>({
  bilibiliCookie: '',
  proxyUrl: ''
})
const isLoading = ref(false)
const isSaving = ref(false)
const message = ref('')
const isError = ref(false)

onMounted(async () => {
  isLoading.value = true
  try {
    config.value = await fetchDownloaderConfig()
  } catch {
    isError.value = true
    message.value = '读取下载配置失败'
  } finally {
    isLoading.value = false
  }
})

async function saveConfig() {
  isSaving.value = true
  isError.value = false
  message.value = ''

  try {
    config.value = await updateDownloaderConfig(config.value)
    message.value = '下载配置已保存'
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
        <h2>下载配置</h2>
        <p>B 站登录态与网络代理会用于字幕读取、音频下载和 YouTube 字幕请求。</p>
      </div>
      <button type="button" :disabled="isSaving || isLoading" @click="saveConfig">
        {{ isSaving ? '保存中…' : '保存配置' }}
      </button>
    </div>

    <div class="settings-fields">
      <label>
        <span>B 站 Cookie</span>
        <textarea
          v-model="config.bilibiliCookie"
          rows="3"
          placeholder="SESSDATA=...; bili_jct=..."
        ></textarea>
      </label>
      <label>
        <span>代理 URL</span>
        <input v-model="config.proxyUrl" type="url" placeholder="http://127.0.0.1:7890" />
      </label>
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
.settings-fields textarea {
  width: 100%;
  padding: 0 12px;
  border: 1px solid #dbe3ee;
  border-radius: 8px;
  outline: none;
  background: #f8fafc;
  color: #111827;
}

.settings-fields input {
  height: 44px;
}

.settings-fields textarea {
  min-height: 84px;
  padding-top: 12px;
  padding-bottom: 12px;
  resize: vertical;
}

.settings-fields input:focus,
.settings-fields textarea:focus {
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
