<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { EditorContent, useEditor } from '@tiptap/vue-3';
import StarterKit from '@tiptap/starter-kit';
import { marked } from 'marked';
import TurndownService from 'turndown';
const activeMenu = ref('课程管理')
const isSidebarCollapsed = ref(false)
const menuItems = [
  { name: '课程管理', icon: '📘'},
  { name: '笔记管理', icon: '📄'},
  { name: 'AI总结', icon: '✨'},
  { name: '设置', icon: '⚙️',}
]
const settingsMenuName = menuItems[3].name

function changeMenu(menuName: string) {
  activeMenu.value = menuName
}

function toggleSidebar() {
  isSidebarCollapsed.value = !isSidebarCollapsed.value
}

type Course = {
  id: number
  title: string
  progress: number
  status: string
  cover: string
  theme: string
}

const COURSE_STORAGE_KEY = 'learnflow_courses'

function getCourseNoteKey(courseId: number, lessonId: number) {
  return `learnflow_note_course_${courseId}_lesson_${lessonId}`
}

function getCourseVideoKey(courseId: number, lessonId: number) {
  return `learnflow_video_course_${courseId}_lesson_${lessonId}`
}

function isCourse(value: unknown): value is Course {
  if (!value || typeof value !== 'object') return false

  const course = value as Partial<Course>

  return (
    typeof course.id === 'number' &&
    typeof course.title === 'string' &&
    typeof course.progress === 'number' &&
    typeof course.status === 'string' &&
    typeof course.cover === 'string' &&
    typeof course.theme === 'string'
  )
}

function loadSavedCourses() {
  try {
    const savedCourses = JSON.parse(localStorage.getItem(COURSE_STORAGE_KEY) ?? '[]')
    return Array.isArray(savedCourses) ? savedCourses.filter(isCourse) : []
  } catch {
    return []
  }
}

function saveCourses() {
  localStorage.setItem(COURSE_STORAGE_KEY, JSON.stringify(courses.value))
}

const courses = ref<Course[]>(loadSavedCourses())
const currentPage = ref<'courseList' | 'courseDetail'>('courseList')
const selectedCourse = ref<Course | null>(null)

const lessons = [
  {
    id: 1,
    title: '课程介绍',
    status: '已完成',
    time: ''
  },
  {
    id: 2,
    title: '环境搭建',
    status: '已完成',
    time: ''
  },
  {
    id: 3,
    title: '变量与数据类型',
    status: '正在学习',
    time: '18:24'
  },
  {
    id: 4,
    title: '条件判断',
    status: '未开始',
    time: ''
  },
  {
    id: 5,
    title: '循环',
    status: '未开始',
    time: ''
  },
  {
    id: 6,
    title: '函数',
    status: '未开始',
    time: ''
  }
]
const selectedLesson = ref(lessons[2])
const currentNote = ref('')
const currentVideoUrl = ref('')
const activeStudyTab = ref<'video' | 'notes' | 'ai'>('video')
type StudyTab = typeof activeStudyTab.value
type FullscreenMode = Exclude<StudyTab, 'ai'> | null
type ShortcutAction = 'videoFullscreen' | 'notesFullscreen' | 'exitFullscreen'
type ShortcutBinding = {
  key: string
  alt: boolean
  ctrl: boolean
  shift: boolean
  meta: boolean
}

const SHORTCUT_STORAGE_KEY = 'learnflow_shortcuts'
const fullscreenMode = ref<FullscreenMode>(null)
const recordingShortcutAction = ref<ShortcutAction | null>(null)
const shortcutMessage = ref('')
const defaultShortcuts: Record<ShortcutAction, ShortcutBinding> = {
  videoFullscreen: { key: 'F', alt: false, ctrl: false, shift: false, meta: false },
  notesFullscreen: { key: 'F', alt: true, ctrl: false, shift: false, meta: false },
  exitFullscreen: { key: 'Escape', alt: false, ctrl: false, shift: false, meta: false }
}
const shortcutActions: { action: ShortcutAction; label: string; description: string }[] = [
  { action: 'videoFullscreen', label: '视频区域全屏', description: '再次按下同一快捷键可退出全屏' },
  { action: 'notesFullscreen', label: '笔记区域全屏', description: '编辑笔记时也可以使用组合键' },
  { action: 'exitFullscreen', label: '退出全屏', description: '在任意全屏状态下生效' }
]
const shortcuts = ref<Record<ShortcutAction, ShortcutBinding>>(loadSavedShortcuts())
let autoSaveTimer: ReturnType<typeof setTimeout> | undefined
let shouldSkipNextAutoSave = false
let isApplyingEditorContent = false
const turndownService = new TurndownService({
  headingStyle: 'atx',
  codeBlockStyle: 'fenced',
  bulletListMarker: '-'
})

function markdownToHtml(markdown: string) {
  return marked.parse(markdown, { async: false }) as string
}

function isShortcutBinding(value: unknown): value is ShortcutBinding {
  if (!value || typeof value !== 'object') return false

  const binding = value as Partial<ShortcutBinding>

  return (
    typeof binding.key === 'string' &&
    typeof binding.alt === 'boolean' &&
    typeof binding.ctrl === 'boolean' &&
    typeof binding.shift === 'boolean' &&
    typeof binding.meta === 'boolean'
  )
}

function loadSavedShortcuts() {
  try {
    const savedShortcuts = JSON.parse(localStorage.getItem(SHORTCUT_STORAGE_KEY) ?? '{}') as Partial<Record<ShortcutAction, ShortcutBinding>>

    return {
      videoFullscreen: isShortcutBinding(savedShortcuts.videoFullscreen) ? savedShortcuts.videoFullscreen : defaultShortcuts.videoFullscreen,
      notesFullscreen: isShortcutBinding(savedShortcuts.notesFullscreen) ? savedShortcuts.notesFullscreen : defaultShortcuts.notesFullscreen,
      exitFullscreen: isShortcutBinding(savedShortcuts.exitFullscreen) ? savedShortcuts.exitFullscreen : defaultShortcuts.exitFullscreen
    }
  } catch {
    return { ...defaultShortcuts }
  }
}

function saveShortcuts() {
  localStorage.setItem(SHORTCUT_STORAGE_KEY, JSON.stringify(shortcuts.value))
}

function normalizeShortcutKey(key: string) {
  if (key === ' ') return 'Space'
  if (key === 'Esc') return 'Escape'
  if (key.length === 1) return key.toUpperCase()
  return key
}

function getShortcutFromEvent(event: KeyboardEvent): ShortcutBinding {
  return {
    key: normalizeShortcutKey(event.key),
    alt: event.altKey,
    ctrl: event.ctrlKey,
    shift: event.shiftKey,
    meta: event.metaKey
  }
}

function isModifierOnly(key: string) {
  return ['Alt', 'Control', 'Shift', 'Meta'].includes(key)
}

function isSameShortcut(first: ShortcutBinding, second: ShortcutBinding) {
  return (
    first.key === second.key &&
    first.alt === second.alt &&
    first.ctrl === second.ctrl &&
    first.shift === second.shift &&
    first.meta === second.meta
  )
}

function formatShortcut(binding: ShortcutBinding) {
  const parts = []

  if (binding.ctrl) parts.push('Ctrl')
  if (binding.alt) parts.push('Alt')
  if (binding.shift) parts.push('Shift')
  if (binding.meta) parts.push('Meta')

  parts.push(binding.key === 'Escape' ? 'Esc' : binding.key)

  return parts.join(' + ')
}

function startRecordingShortcut(action: ShortcutAction) {
  recordingShortcutAction.value = action
  shortcutMessage.value = '请按下新的快捷键组合'
}

function cancelRecordingShortcut() {
  recordingShortcutAction.value = null
  shortcutMessage.value = ''
}

function resetShortcuts() {
  shortcuts.value = { ...defaultShortcuts }
  saveShortcuts()
  cancelRecordingShortcut()
  shortcutMessage.value = '已恢复默认快捷键'
}

function setShortcut(action: ShortcutAction, binding: ShortcutBinding) {
  const conflict = shortcutActions.find((item) => item.action !== action && isSameShortcut(shortcuts.value[item.action], binding))

  if (conflict) {
    shortcutMessage.value = `和「${conflict.label}」冲突，请换一个快捷键`
    return
  }

  shortcuts.value = {
    ...shortcuts.value,
    [action]: binding
  }
  saveShortcuts()
  recordingShortcutAction.value = null
  shortcutMessage.value = `已设置为 ${formatShortcut(binding)}`
}

function isEditableTarget(target: EventTarget | null) {
  if (!(target instanceof HTMLElement)) return false

  return Boolean(target.closest('input, textarea, [contenteditable="true"], .tiptap'))
}

function toggleStudyFullscreen(mode: Exclude<FullscreenMode, null>) {
  if (!selectedCourse.value) return

  if (fullscreenMode.value === mode) {
    fullscreenMode.value = null
    return
  }

  activeStudyTab.value = mode
  fullscreenMode.value = mode
}

function exitStudyFullscreen() {
  fullscreenMode.value = null
}

function handleShortcutKeydown(event: KeyboardEvent) {
  if (event.repeat) return

  const binding = getShortcutFromEvent(event)

  if (recordingShortcutAction.value) {
    event.preventDefault()

    if (isModifierOnly(binding.key)) {
      shortcutMessage.value = '请至少再按一个字母、数字或功能键'
      return
    }

    setShortcut(recordingShortcutAction.value, binding)
    return
  }

  const matchedAction = shortcutActions.find((item) => isSameShortcut(shortcuts.value[item.action], binding))?.action

  if (!matchedAction) return

  const isStudyShortcut = matchedAction === 'videoFullscreen' || matchedAction === 'notesFullscreen'

  if (isStudyShortcut && (activeMenu.value === settingsMenuName || currentPage.value !== 'courseDetail')) {
    return
  }

  if (matchedAction === 'videoFullscreen' && !binding.alt && !binding.ctrl && !binding.shift && !binding.meta && isEditableTarget(event.target)) {
    return
  }

  event.preventDefault()

  if (matchedAction === 'videoFullscreen') {
    toggleStudyFullscreen('video')
    return
  }

  if (matchedAction === 'notesFullscreen') {
    toggleStudyFullscreen('notes')
    return
  }

  exitStudyFullscreen()
}

const noteEditor = useEditor({
  extensions: [
    StarterKit
  ],
  content: '',
  editorProps: {
    attributes: {
      class: 'tiptap-note-content'
    }
  },
  onUpdate: ({ editor }) => {
    if (isApplyingEditorContent) return
    currentNote.value = turndownService.turndown(editor.getHTML())
  }
})

const savedText = ref('未保存')

const currentVideoEmbedUrl = computed(() => getVideoEmbedUrl(currentVideoUrl.value))
const currentVideoPlatform = computed(() => getVideoPlatform(currentVideoUrl.value))

const defaultNotes: Record<number, string> = {
  1: `本节重点

• 了解这门课程主要学什么
• 明确学习目标
• 知道课程适合什么人`,

  2: `本节重点

• 安装开发环境
• 配置编辑器
• 运行第一个案例`,

  3: `本节重点

• 变量是用来存储数据的容器
• 变量名需要遵循命名规范
• 常见数据类型包括：
  - int
  - float
  - str
  - bool
  - list
  - dict`
}

function getNoteKey() {
  if (!selectedCourse.value) return ''
  return getCourseNoteKey(selectedCourse.value.id, selectedLesson.value.id)
}

function getVideoKey() {
  if (!selectedCourse.value) return ''
  return getCourseVideoKey(selectedCourse.value.id, selectedLesson.value.id)
}

function loadCurrentVideo() {
  const key = getVideoKey()
  currentVideoUrl.value = key ? localStorage.getItem(key) ?? '' : ''
}

function saveCurrentVideo(videoUrl: string) {
  const normalizedUrl = videoUrl.trim()
  const key = getVideoKey()

  if (!key) return

  if (!normalizedUrl) {
    removeCurrentVideo()
    return
  }

  currentVideoUrl.value = normalizedUrl
  localStorage.setItem(key, normalizedUrl)
}

function importVideo() {
  const videoUrl = window.prompt('粘贴 B站或 YouTube 视频链接', currentVideoUrl.value)

  if (videoUrl === null) return
  saveCurrentVideo(videoUrl)
}

function removeCurrentVideo() {
  const key = getVideoKey()

  currentVideoUrl.value = ''
  if (key) localStorage.removeItem(key)
}

function openCurrentVideo() {
  if (!currentVideoUrl.value) return
  window.open(currentVideoUrl.value, '_blank', 'noopener,noreferrer')
}

function setCourseVideo(course: Course, lessonId: number, videoUrl: string) {
  const normalizedUrl = videoUrl.trim()
  const key = getCourseVideoKey(course.id, lessonId)

  if (normalizedUrl) {
    localStorage.setItem(key, normalizedUrl)
  } else {
    localStorage.removeItem(key)
  }

  if (selectedCourse.value?.id === course.id && selectedLesson.value.id === lessonId) {
    currentVideoUrl.value = normalizedUrl
  }
}

function addCourse() {
  const title = window.prompt('请输入课程名称')

  if (!title?.trim()) return

  const videoUrl = window.prompt('粘贴 B站或 YouTube 视频链接（可选）')?.trim() ?? ''
  const newCourse: Course = {
    id: courses.value.length > 0 ? Math.max(...courses.value.map((course) => course.id)) + 1 : 1,
    title: title.trim(),
    progress: 0,
    status: '未开始',
    cover: '🎬',
    theme: 'cyan'
  }

  courses.value.push(newCourse)
  saveCourses()
  selectedCourse.value = newCourse
  selectedLesson.value = lessons[0]
  activeStudyTab.value = 'video'
  currentPage.value = 'courseDetail'

  setCourseVideo(newCourse, lessons[0].id, videoUrl)
}

function renameCourse(course: Course) {
  const nextTitle = window.prompt('请输入新的课程名称', course.title)

  if (!nextTitle?.trim()) return

  course.title = nextTitle.trim()
  saveCourses()
}

function changeCourseVideo(course: Course, lessonId = lessons[0].id) {
  const currentUrl = localStorage.getItem(getCourseVideoKey(course.id, lessonId)) ?? ''
  const nextVideoUrl = window.prompt('粘贴 B站或 YouTube 视频链接；留空将清除当前视频', currentUrl)

  if (nextVideoUrl === null) return

  setCourseVideo(course, lessonId, nextVideoUrl)
}

function deleteCourse(course: Course) {
  const shouldDelete = window.confirm(`确定删除「${course.title}」吗？这会同时删除该课程所有课节的笔记和视频链接。`)

  if (!shouldDelete) return

  courses.value = courses.value.filter((item) => item.id !== course.id)
  lessons.forEach((lesson) => {
    localStorage.removeItem(getCourseNoteKey(course.id, lesson.id))
    localStorage.removeItem(getCourseVideoKey(course.id, lesson.id))
  })
  saveCourses()

  if (selectedCourse.value?.id === course.id) {
    selectedCourse.value = null
    currentNote.value = ''
    currentVideoUrl.value = ''
    currentPage.value = 'courseList'
    applyNoteToEditor('')
  }
}

function manageCourse(course: Course, event?: MouseEvent) {
  event?.stopPropagation()

  const action = window.prompt(`管理「${course.title}」\n1. 重命名\n2. 修改视频\n3. 删除`, '1')

  if (action === null) return

  const normalizedAction = action.trim()

  if (normalizedAction === '1' || normalizedAction === '重命名') {
    renameCourse(course)
    return
  }

  if (normalizedAction === '2' || normalizedAction === '修改视频') {
    changeCourseVideo(course, selectedCourse.value?.id === course.id ? selectedLesson.value.id : lessons[0].id)
    return
  }

  if (normalizedAction === '3' || normalizedAction === '删除') {
    deleteCourse(course)
  }
}

function getBilibiliBvid(videoUrl: string) {
  const match = videoUrl.match(/(?:bilibili\.com\/video\/|\/)(BV[0-9A-Za-z]+)/i)
  return match?.[1]
}

function getYoutubeVideoId(videoUrl: string) {
  try {
    const url = new URL(videoUrl)

    if (url.hostname.includes('youtu.be')) {
      return url.pathname.split('/').filter(Boolean)[0]
    }

    if (url.hostname.includes('youtube.com')) {
      if (url.pathname.startsWith('/shorts/')) {
        return url.pathname.split('/').filter(Boolean)[1]
      }

      if (url.pathname.startsWith('/embed/')) {
        return url.pathname.split('/').filter(Boolean)[1]
      }

      return url.searchParams.get('v') ?? undefined
    }
  } catch {
    return undefined
  }
}

function getVideoEmbedUrl(videoUrl: string) {
  const bvid = getBilibiliBvid(videoUrl)

  if (bvid) {
    return `https://player.bilibili.com/player.html?bvid=${encodeURIComponent(bvid)}&page=1&high_quality=1&danmaku=0`
  }

  const youtubeId = getYoutubeVideoId(videoUrl)

  if (youtubeId) {
    return `https://www.youtube.com/embed/${encodeURIComponent(youtubeId)}`
  }

  return ''
}

function getVideoPlatform(videoUrl: string) {
  if (!videoUrl) return ''
  if (getBilibiliBvid(videoUrl) || videoUrl.includes('bilibili.com') || videoUrl.includes('b23.tv')) return 'B站'
  if (getYoutubeVideoId(videoUrl)) return 'YouTube'
  return '视频链接'
}

function loadCurrentNote() {
  const key = getNoteKey()
  const savedNote = key ? localStorage.getItem(key) : ''
  const nextNote = savedNote ?? defaultNotes[selectedLesson.value.id] ?? ''

  shouldSkipNextAutoSave = nextNote !== currentNote.value
  currentNote.value = nextNote
  applyNoteToEditor(nextNote)
  savedText.value = '已加载'
}

function applyNoteToEditor(markdown: string) {
  if (!noteEditor.value) return

  isApplyingEditorContent = true
  noteEditor.value.commands.setContent(markdownToHtml(markdown), {
    emitUpdate: false
  })
  queueMicrotask(() => {
    isApplyingEditorContent = false
  })
}

function syncCurrentNoteFromEditor() {
  if (!noteEditor.value) return

  currentNote.value = turndownService.turndown(noteEditor.value.getHTML())
}

function saveCurrentNote(source: 'manual' | 'auto' = 'manual') {
  const key = getNoteKey()

  if (!key) return

  syncCurrentNoteFromEditor()
  localStorage.setItem(key, currentNote.value)

  const savedAt = new Date().toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })

  savedText.value = source === 'auto' ? `自动保存 ${savedAt}` : `已保存 ${savedAt}`
}

function exportCurrentNote() {
  if (!selectedCourse.value) return

  saveCurrentNote()

  const markdownBlob = new Blob([currentNote.value], {
    type: 'text/markdown;charset=utf-8'
  })
  const downloadUrl = URL.createObjectURL(markdownBlob)
  const downloadLink = document.createElement('a')
  const safeCourseTitle = selectedCourse.value.title.replace(/[\\/:*?"<>|]/g, '-')
  const safeLessonTitle = selectedLesson.value.title.replace(/[\\/:*?"<>|]/g, '-')

  downloadLink.href = downloadUrl
  downloadLink.download = `${safeCourseTitle}-${safeLessonTitle}-笔记.md`
  downloadLink.click()
  URL.revokeObjectURL(downloadUrl)
}

function selectLesson(lesson: typeof lessons[number]) {
  selectedLesson.value = lesson
}

watch([selectedCourse, selectedLesson], () => {
  loadCurrentNote()
  loadCurrentVideo()
}, {
  immediate: true
})

watch(currentNote, () => {
  if (shouldSkipNextAutoSave) {
    shouldSkipNextAutoSave = false
    return
  }

  savedText.value = '正在自动保存...'
  clearTimeout(autoSaveTimer)
  autoSaveTimer = setTimeout(() => {
    saveCurrentNote('auto')
  }, 600)
})

onMounted(() => {
  window.addEventListener('keydown', handleShortcutKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleShortcutKeydown)
  clearTimeout(autoSaveTimer)
  syncCurrentNoteFromEditor()
  noteEditor.value?.destroy()
})

function openCourseDetail(course: Course) {
  selectedCourse.value = course
  currentPage.value = 'courseDetail'
}
function backToCourseList(){
  currentPage.value = 'courseList'
  selectedCourse.value = null
}
function getStatusClass(status: string) {
  if (status === '学习中') return 'status studying'
  if (status === '已完成') return 'status done'
  return 'status pending'
}
</script>

<template>
  <div
    class="app"
    :class="{
      'fullscreen-active': fullscreenMode,
      'fullscreen-video': fullscreenMode === 'video',
      'fullscreen-notes': fullscreenMode === 'notes',
      'sidebar-collapsed': isSidebarCollapsed
    }"
  >
    <header class="top-bar">
      <div class="brand">
        <div class="brand-icon">📘</div>
        <button class="brand-sidebar-toggle" type="button" :title="isSidebarCollapsed ? '展开侧边栏' : '收起侧边栏'" @click="toggleSidebar">
          <span class="dock-icon dock-sidebar-icon"></span>
        </button>
        <span>个人学习工作台</span>
      </div>

      <div v-if="isSidebarCollapsed" class="collapsed-dock" aria-label="主导航">
        <button
          v-for="item in menuItems"
          :key="item.name"
          type="button"
          :class="{ active: activeMenu === item.name }"
          :title="item.name"
          @click="changeMenu(item.name)"
        >
          <span class="dock-menu-icon">{{ item.icon }}</span>
        </button>
      </div>

      <div class="search-box">
        <span class="search-icon">🔍</span>
        <input placeholder="搜索课程、笔记、知识点..." />
        <span class="shortcut">⌘ K</span>
      </div>

      <div class="user-area">
        <button class="icon-button">🔔</button>
        <div class="avatar">👨‍💻</div>
        <span class="username">学习者</span>
        <span class="arrow">▾</span>
      </div>
    </header>

    <div class="layout">
      <aside class="sidebar">
        <nav class="menu">
    <button
      v-for="item in menuItems"
      :key="item.name"
      class="menu-item"
      :class="{ active: activeMenu === item.name }"
      @click="changeMenu(item.name)"
  >
    <span class="menu-icon">{{ item.icon }}</span>
    <span>{{ item.name }}</span>
  </button>
        </nav>

        <div class="tip-card">
          <div class="tip-title">
            <span>💡</span>
            <span>学习小贴士</span>
            <span>›</span>
          </div>
          <p>坚持每日学习，点滴进步！</p>
        </div>
      </aside>

      <main class="content">
        <section v-if="activeMenu === settingsMenuName" class="settings-panel">
          <div class="settings-header">
            <div>
              <h1>快捷键设置</h1>
              <p>设置学习时常用的区域全屏快捷键，配置会保存在本机浏览器中。</p>
            </div>
            <button class="reset-shortcuts-button" @click="resetShortcuts">恢复默认</button>
          </div>

          <div class="shortcut-settings-list">
            <article
              v-for="item in shortcutActions"
              :key="item.action"
              class="shortcut-setting-row"
            >
              <div>
                <h2>{{ item.label }}</h2>
                <p>{{ item.description }}</p>
              </div>

              <div class="shortcut-setting-actions">
                <kbd>{{ formatShortcut(shortcuts[item.action]) }}</kbd>
                <button
                  v-if="recordingShortcutAction !== item.action"
                  @click="startRecordingShortcut(item.action)"
                >
                  修改
                </button>
                <button
                  v-else
                  class="secondary"
                  @click="cancelRecordingShortcut"
                >
                  取消
                </button>
              </div>
            </article>
          </div>

          <p v-if="shortcutMessage" class="shortcut-message">
            {{ shortcutMessage }}
          </p>
        </section>

        <div v-else-if="currentPage === 'courseList'">
        <section class="page-header">
          <div>
            <h1>课程管理</h1>
            <p>你的学习打卡主页，掌握学习进度，保持持续成长！</p>
          </div>

          <button class="add-button" @click="addCourse">
            <span>＋</span>
            添加课程
          </button>
        </section>
      </div>
      <div v-else-if="selectedCourse" class="course-detail-page">
  <div class="breadcrumb">
    <button class="back-button" @click="backToCourseList">返回课程管理</button>
    <span>/</span>
    <span>{{ selectedCourse.title }}</span>
  </div>

  <section class="detail-header">
    <div>
      <div class="title-row">
        <h1>{{ selectedCourse.title }}</h1>
        <span :class="getStatusClass(selectedCourse.status)">
          {{ selectedCourse.status }}
        </span>
      </div>

      <div class="detail-progress-row">
        <span>课程进度：{{ selectedCourse.progress }}%</span>
        <div class="detail-progress-bar">
          <div
            class="detail-progress-inner"
            :style="{ width: selectedCourse.progress + '%' }"
          ></div>
        </div>
        <span>已学 15 / 24 课时</span>
      </div>
    </div>

    <button class="detail-button" @click="manageCourse(selectedCourse)">管理课程</button>
  </section>

  <section class="study-layout">
    <aside class="lesson-panel">
      <div class="lesson-header">
        <h2>课程目录</h2>
        <button>‹ 收起</button>
      </div>

      <div class="lesson-list">
        <button
          v-for="lesson in lessons"
          :key="lesson.id"
          class="lesson-item"
          :class="{ active: selectedLesson.id === lesson.id }"
          @click="selectLesson(lesson)"
        >
          <div>
            <strong>{{ lesson.id }}. {{ lesson.title }}</strong>
            <p v-if="lesson.status === '正在学习'">
              正在学习 · {{ lesson.time }}
            </p>
          </div>

          <span v-if="lesson.status === '已完成'" class="lesson-done">✓ 已完成</span>
          <span v-else-if="lesson.status === '正在学习'" class="lesson-playing">▶</span>
          <span v-else class="lesson-pending">○ 未开始</span>
        </button>
      </div>
    </aside>

    <section class="study-main-panel">
      <div class="study-tabs" role="tablist" aria-label="学习视图">
        <button
          type="button"
          :class="{ active: activeStudyTab === 'video' }"
          @click="activeStudyTab = 'video'"
        >
          看课
        </button>
        <button
          type="button"
          :class="{ active: activeStudyTab === 'notes' }"
          @click="activeStudyTab = 'notes'"
        >
          记笔记
        </button>
        <button
          type="button"
          :class="{ active: activeStudyTab === 'ai' }"
          @click="activeStudyTab = 'ai'"
        >
          AI助手
        </button>
      </div>

    <section v-if="activeStudyTab === 'video'" class="video-study-card">
      <div class="study-card-header">
        <h2>第{{ selectedLesson.id }}课 {{ selectedLesson.title }}</h2>
        <button class="fullscreen-button" @click="toggleStudyFullscreen('video')">
          {{ fullscreenMode === 'video' ? '退出全屏' : '全屏' }}
        </button>
      </div>

      <div v-if="currentVideoUrl" class="video-player-card">
        <iframe
          v-if="currentVideoEmbedUrl"
          class="video-iframe"
          :src="currentVideoEmbedUrl"
          title="课程视频播放器"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
          allowfullscreen
        ></iframe>

        <div v-else class="video-link-fallback">
          <div class="video-cover-icon">{{ selectedCourse.cover }}</div>
          <h3>已绑定{{ currentVideoPlatform }}</h3>
          <p>这个链接暂时不能直接嵌入播放，可以打开原链接学习。</p>
        </div>

        <div class="video-source-bar">
          <span>{{ currentVideoPlatform }}</span>
          <button @click="openCurrentVideo">打开原链接</button>
          <button @click="importVideo">更换</button>
          <button class="danger" @click="removeCurrentVideo">移除</button>
        </div>
      </div>

      <div v-else class="fake-video">
        <div class="video-cover-icon">{{ selectedCourse.cover }}</div>
        <h3>{{ selectedLesson.title }}</h3>
        <p>{{ selectedCourse.title }} 系列课程</p>

        <div class="fake-video-control">
          <span>▶</span>
          <span>🔊</span>
          <span>02:18 / 18:24</span>
          <span>1.0x</span>
          <span>超清</span>
          <span>⛶</span>
        </div>
      </div>

      <p class="lesson-desc">
        本节课我们将学习 {{ selectedLesson.title }} 的核心内容，并记录关键知识点。
      </p>

      <div class="lesson-actions">
        <button class="prev-button">← 上一节</button>

        <div class="mini-progress">
          <span>课程进度</span>
          <div class="mini-progress-bar">
            <div class="mini-progress-inner"></div>
          </div>
        </div>

        <button class="next-button">下一节 →</button>
      </div>
    </section>

      <section v-else-if="activeStudyTab === 'notes'" class="note-card">
        <div class="note-header">
          <h2>课堂笔记</h2>
          <span>{{savedText}}</span>
          <div class="note-actions">
            <button class="secondary" @click="toggleStudyFullscreen('notes')">
              {{ fullscreenMode === 'notes' ? '退出全屏' : '全屏' }}
            </button>
            <button @click="saveCurrentNote()">保存</button>
            <button class="secondary" @click="exportCurrentNote">导出</button>
          </div>
        </div>

        <div class="wysiwyg-note-editor">
          <EditorContent :editor="noteEditor" />
        </div>
      </section>

      <section v-else class="ai-card">
        <div class="ai-title">
          <div class="ai-icon">✦</div>
          <div>
            <h2>AI学习助手</h2>
            <p>基于本节内容，为你提供智能学习支持</p>
          </div>
        </div>

        <div class="ai-actions">
          <button>✨ AI总结本节</button>
          <button>☷ 提炼重点</button>
        </div>
      </section>
    </section>
  </section>
</div>
        <section v-if="activeMenu !== settingsMenuName && currentPage === 'courseList' && courses.length > 0" class="course-grid">
          <article
            v-for="course in courses"
            :key="course.id"
            class="course-card"
            @click="openCourseDetail(course)"
          >
            <div class="course-cover" :class="course.theme">
              {{ course.cover }}
            </div>

            <div class="course-info">
              <div class="course-top">
                <h3>{{ course.title }}</h3>
                <span :class="getStatusClass(course.status)">
                  {{ course.status }}
                </span>
              </div>

              <div class="progress-row">
                <span>进度</span>
                <strong>{{ course.progress }}%</strong>
              </div>

              <div class="progress-bar">
                <div
                  class="progress-inner"
                  :style="{ width: course.progress + '%' }"
                ></div>
              </div>
            </div>

            <button class="more-button" @click="manageCourse(course, $event)">•••</button>
          </article>
        </section>
      </main>
    </div>
  </div>
</template>

<style scoped>
.app {
  width: 100vw;
  height: 100vh;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #f6f8fc;
}

.top-bar {
  position: relative;
  height: 72px;
  flex: 0 0 72px;
  padding: 0 28px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  background: white;
  border-bottom: 1px solid #e5eaf3;
}

.collapsed-dock {
  height: 54px;
  padding: 6px 14px;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  border: 1px solid #e5e7eb;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 16px 34px rgba(15, 23, 42, 0.1);
  backdrop-filter: blur(14px);
  z-index: 2;
}

.collapsed-dock button {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  border: none;
  border-radius: 50%;
  background: transparent;
  color: #111827;
  transition:
    background 150ms ease,
    color 150ms ease,
    transform 150ms ease;
}

.collapsed-dock button:hover,
.collapsed-dock button.active,
.brand-sidebar-toggle:hover {
  background: #f3f7ff;
  color: #2563eb;
}

.collapsed-dock button:hover {
  transform: translateY(-1px);
}

.dock-menu-icon {
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  font-size: 21px;
  line-height: 1;
}

.dock-icon {
  position: relative;
  display: inline-block;
  width: 24px;
  height: 24px;
}

.dock-sidebar-icon {
  border: 2px solid currentColor;
  border-radius: 7px;
}

.dock-sidebar-icon::before {
  content: '';
  position: absolute;
  left: 7px;
  top: 2px;
  bottom: 2px;
  width: 2px;
  background: currentColor;
  border-radius: 999px;
}

.dock-search-icon::before {
  content: '';
  position: absolute;
  left: 2px;
  top: 2px;
  width: 14px;
  height: 14px;
  border: 3px solid currentColor;
  border-radius: 50%;
}

.dock-search-icon::after {
  content: '';
  position: absolute;
  right: 2px;
  bottom: 3px;
  width: 10px;
  height: 3px;
  border-radius: 999px;
  background: currentColor;
  transform: rotate(45deg);
  transform-origin: center;
}

.dock-add-icon::before {
  content: '';
  position: absolute;
  inset: 3px;
  border: 2px solid currentColor;
  border-radius: 50%;
}

.dock-add-icon::after {
  content: '+';
  position: absolute;
  left: 50%;
  top: 40%;
  color: currentColor;
  font-size: 24px;
  font-weight: 800;
  line-height: 1;
  transform: translate(-50%, -50%);
}

.brand {
  min-width: 0;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 22px;
  font-weight: 700;
}

.brand-sidebar-toggle {
  width: 38px;
  height: 38px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  border: 1px solid #e5eaf3;
  border-radius: 999px;
  background: white;
  color: #111827;
  transition:
    background 150ms ease,
    color 150ms ease,
    border-color 150ms ease;
}

.brand-sidebar-toggle .dock-icon {
  width: 20px;
  height: 20px;
}

.brand span {
  white-space: nowrap;
}

.brand-icon {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  background: #eaf1ff;
}

.search-box {
  width: 460px;
  height: 44px;
  padding: 0 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  background: #f9fafb;
  border: 1px solid #dfe5ee;
  border-radius: 10px;
}

.search-box input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 14px;
}

.search-icon {
  opacity: 0.6;
}

.shortcut {
  padding: 3px 8px;
  border-radius: 6px;
  background: white;
  color: #8a94a6;
  font-size: 12px;
  border: 1px solid #e5e7eb;
}

.user-area {
  min-width: 0;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 14px;
  font-weight: 600;
}

.icon-button {
  width: 36px;
  height: 36px;
  border: none;
  background: transparent;
  font-size: 20px;
}

.avatar {
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: #e8f0ff;
}

.layout {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-columns: 280px 1fr;
  overflow: hidden;
  transition: grid-template-columns 180ms ease;
}

.sidebar {
  position: relative;
  padding: 28px;
  background: white;
  border-right: 1px solid #e5eaf3;
  overflow: hidden;
  transition:
    opacity 160ms ease,
    padding 180ms ease,
    transform 180ms ease;
}

.sidebar-collapsed .layout {
  grid-template-columns: 0 1fr;
}

.sidebar-collapsed .sidebar {
  padding-left: 0;
  padding-right: 0;
  opacity: 0;
  pointer-events: none;
  transform: translateX(-18px);
}

.sidebar-collapsed .content {
  padding-left: 56px;
  padding-right: 56px;
}

.sidebar-collapsed .brand > span {
  display: none;
}

.sidebar-collapsed .search-box {
  display: none;
}

.menu {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.menu-item {
  height: 64px;
  padding: 0 20px;
  display: flex;
  align-items: center;
  gap: 14px;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: #4b5563;
  font-size: 18px;
  font-weight: 600;
  text-align: left;
}

.menu-item.active {
  color: #2563eb;
  background: #f3f7ff;
  border: 1px solid #2563eb;
}

.menu-icon {
  font-size: 24px;
}

.tip-card {
  position: absolute;
  left: 28px;
  right: 28px;
  bottom: 28px;
  padding: 18px;
  border: 1px solid #e0e7f0;
  border-radius: 10px;
  background: white;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
}

.tip-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #64748b;
  font-weight: 600;
}

.tip-card p {
  margin: 14px 0 0;
  color: #64748b;
}

.content {
  min-width: 0;
  min-height: 0;
  padding: 34px 48px;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  overflow: hidden;
}

.settings-panel {
  width: min(820px, 100%);
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.settings-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}

.settings-header h1 {
  margin: 0;
  color: #111827;
  font-size: 32px;
}

.settings-header p,
.shortcut-setting-row p,
.shortcut-message {
  margin: 8px 0 0;
  color: #64748b;
}

.reset-shortcuts-button,
.shortcut-setting-actions button,
.fullscreen-button {
  height: 36px;
  padding: 0 14px;
  border: 1px solid #dbe3ee;
  border-radius: 8px;
  background: white;
  color: #334155;
  font-weight: 700;
}

.shortcut-settings-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.shortcut-setting-row {
  min-height: 92px;
  padding: 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  background: white;
  border: 1px solid #e1e7ef;
  border-radius: 10px;
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.05);
}

.shortcut-setting-row h2 {
  margin: 0;
  color: #111827;
  font-size: 18px;
}

.shortcut-setting-actions {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.shortcut-setting-actions kbd {
  min-width: 96px;
  height: 36px;
  padding: 0 12px;
  display: inline-grid;
  place-items: center;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #f8fafc;
  color: #0f172a;
  font: 700 14px/1 var(--sans);
}

.shortcut-setting-actions button {
  border: none;
  background: #2563eb;
  color: white;
}

.shortcut-setting-actions button.secondary {
  border: 1px solid #dbe3ee;
  background: white;
  color: #334155;
}

.shortcut-message {
  min-height: 22px;
  font-weight: 600;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 24px;
}

.page-header h1 {
  margin: 0;
  font-size: 36px;
  letter-spacing: -1px;
}

.page-header p {
  margin: 8px 0 0;
  color: #6b7280;
  font-size: 16px;
}

.add-button {
  flex-shrink: 0;
  height: 52px;
  padding: 0 24px;
  border: none;
  border-radius: 8px;
  background: #2563eb;
  color: white;
  font-size: 16px;
  font-weight: 600;
  box-shadow: 0 8px 18px rgba(37, 99, 235, 0.24);
}

.course-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
  min-width: 0;
}

.course-card {
  position: relative;
  width: 100%;
  min-height: 154px;
  padding: 14px;
  display: flex;
  gap: 18px;
  min-width: 0;
  overflow: hidden;
  background: white;
  border: 1px solid #e1e7ef;
  border-radius: 10px;
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.05);
}

.course-cover {
  width: 124px;
  height: 124px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  border-radius: 8px;
  font-size: 42px;
}

.course-cover.blue {
  background: linear-gradient(135deg, #1d4ed8, #60a5fa);
}

.course-cover.green {
  background: linear-gradient(135deg, #34d399, #a7f3d0);
}

.course-cover.purple {
  background: linear-gradient(135deg, #818cf8, #c4b5fd);
}

.course-cover.yellow {
  background: linear-gradient(135deg, #fde68a, #fff7ed);
}

.course-cover.pink {
  background: linear-gradient(135deg, #fbcfe8, #f5f3ff);
}

.course-cover.gray {
  background: linear-gradient(135deg, #cbd5e1, #f8fafc);
}

.course-cover.green-light {
  background: linear-gradient(135deg, #bbf7d0, #f0fdf4);
}

.course-cover.cyan {
  background: linear-gradient(135deg, #a5f3fc, #ecfeff);
}

.course-cover.orange {
  background: linear-gradient(135deg, #fed7aa, #fff7ed);
}

.course-info {
  flex: 1;
  min-width: 0;
}

.course-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.course-top h3 {
  margin: 8px 0 24px;
  font-size: 17px;
  line-height: 1.4;
}

.status {
  padding: 5px 9px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
}

.status.studying {
  color: #2563eb;
  background: #eff6ff;
}

.status.pending {
  color: #64748b;
  background: #f1f5f9;
}

.status.done {
  color: #16a34a;
  background: #dcfce7;
}

.progress-row {
  display: flex;
  gap: 8px;
  font-size: 14px;
  color: #374151;
}

.progress-row strong {
  font-weight: 700;
}

.progress-bar {
  height: 7px;
  margin-top: 12px;
  border-radius: 99px;
  overflow: hidden;
  background: #e5eaf3;
}

.progress-inner {
  height: 100%;
  border-radius: 99px;
  background: #3b82f6;
}

.more-button {
  position: absolute;
  right: 14px;
  bottom: 14px;
  border: none;
  background: transparent;
  color: #334155;
  font-size: 18px;
  letter-spacing: 2px;
}

@media (max-width: 1100px) {
  .search-box {
    width: 340px;
  }

  .course-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 820px) {
  .top-bar {
    padding: 0 18px;
    gap: 12px;
  }

  .brand {
    gap: 10px;
    font-size: 20px;
  }

  .user-area {
    gap: 10px;
  }

  .search-box {
    display: none;
  }

  .layout {
    grid-template-columns: 1fr;
  }

  .sidebar {
    display: none;
  }

  .collapsed-dock {
    margin-left: auto;
    padding: 5px 8px;
    gap: 4px;
  }

  .content {
    padding: 24px;
    justify-content: flex-start;
  }

  .course-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 520px) {
  .top-bar {
    padding: 0 16px;
  }

  .brand {
    font-size: 18px;
  }

  .username,
  .arrow,
  .user-area .icon-button {
    display: none;
  }

  .page-header {
    display: grid;
    grid-template-columns: 1fr;
    align-items: start;
  }

  .add-button {
    height: 44px;
    justify-self: start;
    padding: 0 18px;
  }

  .course-card {
    min-height: 126px;
    gap: 12px;
  }

  .course-cover {
    width: 96px;
    height: 96px;
    font-size: 34px;
  }

  .course-top {
    display: block;
  }

  .course-top h3 {
    margin: 4px 0 12px;
  }

  .status {
    display: inline-block;
    margin-bottom: 10px;
  }
}

@media (max-height: 800px) {
  .content {
    justify-content: flex-start;
    padding-top: 24px;
    padding-bottom: 24px;
  }
}
.course-detail-page {
  height: 100%;
  min-width: 0;
  overflow: auto;
  padding-right: 4px;
}

.course-detail-page ~ .course-grid {
  display: none;
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 18px;
  color: #64748b;
  font-size: 15px;
}

.back-button {
  border: none;
  background: transparent;
  color: #64748b;
  font-size: 15px;
  cursor: pointer;
}

.back-button:hover {
  color: #2563eb;
}

.detail-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 24px;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 22px;
}

.title-row h1 {
  margin: 0;
  font-size: 32px;
}

.detail-progress-row {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 18px;
  color: #475569;
}

.detail-progress-bar {
  width: min(640px, 100%);
  height: 7px;
  border-radius: 99px;
  background: #e5eaf3;
  overflow: hidden;
}

.detail-progress-inner {
  height: 100%;
  border-radius: 99px;
  background: #2563eb;
}

.detail-button {
  height: 46px;
  padding: 0 22px;
  border: 1px solid #dbe3ee;
  border-radius: 8px;
  background: white;
  color: #334155;
  font-weight: 600;
}

.study-layout {
  display: grid;
  grid-template-columns: minmax(220px, 260px) minmax(0, 1fr);
  gap: 18px;
  min-width: 0;
  overflow: visible;
}

.lesson-panel,
.study-main-panel,
.video-study-card,
.note-card,
.ai-card {
  background: white;
  border: 1px solid #e1e7ef;
  border-radius: 10px;
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.05);
}

.lesson-panel {
  padding: 18px;
}

.study-main-panel {
  min-width: 0;
  min-height: 0;
  padding: 18px;
}

.study-tabs {
  height: 44px;
  padding: 4px;
  margin-bottom: 18px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: 1px solid #dbe3ee;
  border-radius: 8px;
  background: #f8fafc;
}

.study-tabs button {
  height: 34px;
  padding: 0 18px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #475569;
  font-weight: 700;
}

.study-tabs button.active {
  background: #2563eb;
  color: white;
  box-shadow: 0 6px 14px rgba(37, 99, 235, 0.18);
}

.lesson-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 14px;
  border-bottom: 1px solid #e5eaf3;
}

.lesson-header h2 {
  margin: 0;
  font-size: 20px;
}

.lesson-header button {
  border: none;
  background: transparent;
  color: #64748b;
}

.lesson-list {
  margin-top: 14px;
}

.lesson-item {
  width: 100%;
  min-height: 76px;
  padding: 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border: none;
  border-bottom: 1px solid #e5eaf3;
  background: white;
  text-align: left;
  color: #111827;
}

.lesson-item strong {
  font-size: 16px;
}

.lesson-item p {
  margin: 8px 0 0;
  color: #2563eb;
  font-size: 14px;
  font-weight: 600;
}

.lesson-item.active {
  border: 1px solid #2563eb;
  border-radius: 8px;
  background: #eff6ff;
}

.lesson-done {
  color: #22c55e;
  font-size: 14px;
}

.lesson-playing {
  color: #2563eb;
}

.lesson-pending {
  color: #94a3b8;
  font-size: 14px;
}

.video-study-card {
  padding: 0;
  border: none;
  box-shadow: none;
}

.study-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 18px;
}

.study-card-header h2 {
  margin: 0;
  font-size: 22px;
}

.fullscreen-button {
  flex-shrink: 0;
}

.fake-video {
  position: relative;
  height: min(56vh, 520px);
  min-height: 360px;
  overflow: hidden;
  border-radius: 10px;
  background: linear-gradient(135deg, #0f172a, #1d4ed8);
  color: white;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.video-player-card {
  overflow: hidden;
  border: 1px solid #dbe3ee;
  border-radius: 10px;
  background: #0f172a;
}

.video-iframe {
  display: block;
  width: 100%;
  height: min(56vh, 520px);
  min-height: 360px;
  border: none;
  background: #0f172a;
}

.video-link-fallback {
  height: min(56vh, 520px);
  min-height: 360px;
  padding: 28px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: white;
  text-align: center;
  background: linear-gradient(135deg, #0f172a, #334155);
}

.video-link-fallback h3 {
  margin: 0;
  font-size: 28px;
}

.video-link-fallback p {
  max-width: 420px;
  margin: 12px 0 0;
  color: #cbd5e1;
  line-height: 1.7;
}

.video-source-bar {
  min-height: 46px;
  padding: 8px 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  background: white;
  border-top: 1px solid #dbe3ee;
}

.video-source-bar span {
  flex: 1;
  min-width: 0;
  color: #475569;
  font-size: 14px;
  font-weight: 700;
}

.video-source-bar button {
  height: 32px;
  padding: 0 12px;
  border: 1px solid #dbe3ee;
  border-radius: 6px;
  background: white;
  color: #334155;
  font-size: 14px;
  font-weight: 700;
}

.video-source-bar button.danger {
  color: #dc2626;
}

.video-cover-icon {
  font-size: 88px;
  margin-bottom: 12px;
}

.fake-video h3 {
  margin: 0;
  font-size: 32px;
}

.fake-video p {
  margin: 12px 0 0;
  color: #cbd5e1;
}

.fake-video-control {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 48px;
  padding: 0 18px;
  display: flex;
  align-items: center;
  gap: 18px;
  background: rgba(15, 23, 42, 0.7);
}

.lesson-desc {
  margin: 18px 0 42px;
  color: #475569;
  line-height: 1.8;
}

.lesson-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.prev-button,
.next-button {
  height: 42px;
  padding: 0 22px;
  border-radius: 8px;
  font-weight: 600;
}

.prev-button {
  border: 1px solid #dbe3ee;
  background: white;
  color: #334155;
}

.next-button {
  border: none;
  background: #2563eb;
  color: white;
}

.mini-progress {
  display: flex;
  align-items: center;
  gap: 12px;
  color: #475569;
  font-size: 14px;
}

.mini-progress-bar {
  width: 190px;
  height: 7px;
  border-radius: 99px;
  background: #e5eaf3;
  overflow: hidden;
}

.mini-progress-inner {
  width: 60%;
  height: 100%;
  background: #2563eb;
}

.right-panel {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.note-card {
  padding: 0;
  min-height: 620px;
  border: none;
  box-shadow: none;
}

.note-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.note-header h2 {
  flex: 1;
  margin: 0;
  font-size: 20px;
}

.note-header span {
  color: #64748b;
  font-size: 14px;
}

.note-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.note-actions button {
  height: 32px;
  padding: 0 12px;
  border: none;
  border-radius: 6px;
  background: #2563eb;
  color: white;
  font-weight: 600;
}

.note-actions button.secondary {
  border: 1px solid #dbe3ee;
  background: white;
  color: #334155;
}

.wysiwyg-note-editor {
  height: min(64vh, 620px);
  min-height: 460px;
  border: 1px solid #e1e7ef;
  border-radius: 8px;
  overflow: hidden;
  background: white;
}

.wysiwyg-note-editor :deep(.tiptap) {
  height: 100%;
  min-height: 458px;
  padding: 20px;
  overflow: hidden;
  outline: none;
  color: #111827;
  font-size: 15px;
  line-height: 1.75;
}

.wysiwyg-note-editor :deep(.tiptap p) {
  margin: 0 0 12px;
}

.wysiwyg-note-editor :deep(.tiptap h1),
.wysiwyg-note-editor :deep(.tiptap h2),
.wysiwyg-note-editor :deep(.tiptap h3) {
  margin: 18px 0 10px;
  color: #0f172a;
  line-height: 1.25;
}

.wysiwyg-note-editor :deep(.tiptap h1) {
  font-size: 28px;
}

.wysiwyg-note-editor :deep(.tiptap h2) {
  font-size: 23px;
}

.wysiwyg-note-editor :deep(.tiptap h3) {
  font-size: 19px;
}

.wysiwyg-note-editor :deep(.tiptap pre) {
  padding: 12px 14px;
  overflow: auto;
  border-radius: 8px;
  background: #0f172a;
  color: #e2e8f0;
}

.wysiwyg-note-editor :deep(.tiptap code) {
  padding: 2px 5px;
  border-radius: 5px;
  background: #f1f5f9;
  color: #be123c;
}

.wysiwyg-note-editor :deep(.tiptap pre code) {
  padding: 0;
  background: transparent;
  color: inherit;
}

.wysiwyg-note-editor :deep(.tiptap blockquote) {
  margin: 14px 0;
  padding-left: 14px;
  border-left: 3px solid #93c5fd;
  color: #475569;
}

.note-toolbar {
  height: 38px;
  padding: 0 12px;
  display: flex;
  align-items: center;
  gap: 20px;
  border: 1px solid #e1e7ef;
  border-radius: 8px 8px 0 0;
  color: #475569;
}

.detail-note-input {
  width: 100%;
  height: 340px;
  padding: 16px;
  border: 1px solid #e1e7ef;
  border-top: none;
  border-radius: 0 0 8px 8px;
  resize: none;
  outline: none;
  font-size: 15px;
  line-height: 1.8;
}

.ai-card {
  padding: 22px;
  min-height: 420px;
  border: none;
  box-shadow: none;
}

.ai-title {
  display: flex;
  gap: 14px;
  margin-bottom: 18px;
}

.ai-icon {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: #eaf1ff;
  color: #2563eb;
  font-size: 22px;
}

.ai-title h2 {
  margin: 0 0 6px;
  font-size: 18px;
}

.ai-title p {
  margin: 0;
  color: #64748b;
  font-size: 14px;
}

.ai-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.ai-actions button {
  height: 46px;
  border: 1px solid #2563eb;
  border-radius: 8px;
  background: white;
  color: #2563eb;
  font-weight: 700;
}

.fullscreen-active .top-bar,
.fullscreen-active .sidebar,
.fullscreen-active .collapsed-dock,
.fullscreen-active .breadcrumb,
.fullscreen-active .detail-header,
.fullscreen-active .lesson-panel,
.fullscreen-active .study-tabs,
.fullscreen-active .lesson-desc,
.fullscreen-active .lesson-actions {
  display: none;
}

.fullscreen-active .layout {
  grid-template-columns: 1fr;
}

.fullscreen-active .content {
  padding: 0;
}

.fullscreen-active .course-detail-page,
.fullscreen-active .study-layout,
.fullscreen-active .study-main-panel {
  width: 100%;
  height: 100vh;
  min-height: 0;
}

.fullscreen-active .study-layout {
  display: block;
}

.fullscreen-active .study-main-panel {
  padding: 0;
  border: none;
  border-radius: 0;
  box-shadow: none;
}

.fullscreen-active .video-study-card,
.fullscreen-active .note-card {
  height: 100vh;
  padding: 18px;
  border: none;
  border-radius: 0;
  box-shadow: none;
}

.fullscreen-active .study-card-header,
.fullscreen-active .note-header {
  height: 44px;
  margin-bottom: 12px;
}

.fullscreen-active .video-player-card,
.fullscreen-active .fake-video {
  height: calc(100vh - 74px);
  min-height: 0;
}

.fullscreen-active .video-iframe {
  height: calc(100vh - 124px);
}

.fullscreen-notes .wysiwyg-note-editor {
  height: calc(100vh - 74px);
  min-height: 0;
}

.fullscreen-notes .wysiwyg-note-editor :deep(.tiptap) {
  min-height: 0;
  overflow: auto;
}
</style>
