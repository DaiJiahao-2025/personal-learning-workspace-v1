import { ref, watch } from 'vue'
import { fetchAiConfig, updateAiConfig, type AiConfig } from '../services/aiConfig'

function createEmptyConfig(): AiConfig {
  return {
    baseUrl: '',
    apiKey: '',
    modelName: ''
  }
}

function isSameConfig(first: AiConfig, second: AiConfig) {
  return (
    first.baseUrl === second.baseUrl &&
    first.apiKey === second.apiKey &&
    first.modelName === second.modelName
  )
}

const config = ref<AiConfig>(createEmptyConfig())
const lastSavedConfig = ref<AiConfig>(createEmptyConfig())
const isHydrated = ref(false)
const isLoading = ref(false)
const isSaving = ref(false)
const isDirty = ref(false)

watch(
  config,
  (nextConfig) => {
    if (!isHydrated.value && !isLoading.value) return
    isDirty.value = !isSameConfig(nextConfig, lastSavedConfig.value)
  },
  { deep: true }
)

export function useAiConfigDraft() {
  async function hydrate() {
    if (isHydrated.value || isLoading.value) return

    isLoading.value = true

    try {
      const savedConfig = await fetchAiConfig()
      lastSavedConfig.value = savedConfig

      if (!isDirty.value) {
        config.value = { ...savedConfig }
      }
    } finally {
      isHydrated.value = true
      isLoading.value = false
    }
  }

  async function save() {
    isSaving.value = true

    try {
      const savedConfig = await updateAiConfig(config.value)
      lastSavedConfig.value = savedConfig
      config.value = { ...savedConfig }
      isDirty.value = false
      return savedConfig
    } finally {
      isSaving.value = false
    }
  }

  return {
    config,
    isHydrated,
    isLoading,
    isSaving,
    isDirty,
    hydrate,
    save
  }
}

