<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { EditorContent, useEditor } from '@tiptap/vue-3';
import StarterKit from '@tiptap/starter-kit';
import { marked } from 'marked';
import TurndownService from 'turndown';

type YoutubePlayer = {
  getCurrentTime: () => number
  pauseVideo: () => void
  seekTo: (seconds: number, allowSeekAhead: boolean) => void
  destroy: () => void
}

declare global {
  interface Window {
    YT?: {
      Player: new (element: HTMLIFrameElement, options?: Record<string, unknown>) => YoutubePlayer
    }
    onYouTubeIframeAPIReady?: () => void
  }
}

const activeMenu = ref('课程管理')
const isSidebarCollapsed = ref(false)
const menuItems = [
  { name: '课程管理', icon: '📘'},
  { name: '笔记管理', icon: '📄'},
  { name: 'AI总结', icon: '✨'},
  { name: '设置', icon: '⚙️',}
]
const courseMenuName = menuItems[0].name
const noteMenuName = menuItems[1].name
const settingsMenuName = menuItems[3].name

function changeMenu(menuName: string) {
  saveCurrentNote()

  rememberCurrentPlaybackTime()
  pauseCurrentPlayer()

  activeMenu.value = menuName
  fullscreenMode.value = null

  if (menuName === courseMenuName) {
    backToCourseList()
  }

  if (menuName === noteMenuName) {
    initializeNoteWorkspace()
    loadCurrentNote()
  }
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
  lessons: Lesson[]
}

type Lesson = {
  id: number
  title: string
  status: string
  time: string
}

const COURSE_STORAGE_KEY = 'learnflow_courses'

function getCourseNoteKey(courseId: number, lessonId: number) {
  return `learnflow_note_course_${courseId}_lesson_${lessonId}`
}

function getCourseVideoKey(courseId: number, lessonId: number) {
  return `learnflow_video_course_${courseId}_lesson_${lessonId}`
}

const defaultLessons: Lesson[] = [
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

function cloneDefaultLessons() {
  return defaultLessons.map((lesson) => ({ ...lesson }))
}

function isLesson(value: unknown): value is Lesson {
  if (!value || typeof value !== 'object') return false

  const lesson = value as Partial<Lesson>

  return (
    typeof lesson.id === 'number' &&
    typeof lesson.title === 'string' &&
    typeof lesson.status === 'string' &&
    typeof lesson.time === 'string'
  )
}

function normalizeCourse(value: unknown): Course | null {
  if (!value || typeof value !== 'object') return null

  const course = value as Partial<Course>

  if (
    typeof course.id !== 'number' ||
    typeof course.title !== 'string' ||
    typeof course.progress !== 'number' ||
    typeof course.status !== 'string' ||
    typeof course.cover !== 'string' ||
    typeof course.theme !== 'string'
  ) {
    return null
  }

  const lessons = Array.isArray(course.lessons) ? course.lessons.filter(isLesson) : cloneDefaultLessons()

  return {
    id: course.id,
    title: course.title,
    progress: course.progress,
    status: course.status,
    cover: course.cover,
    theme: course.theme,
    lessons: lessons.length > 0 ? lessons : cloneDefaultLessons()
  }
}

function loadSavedCourses() {
  try {
    const savedCourses = JSON.parse(localStorage.getItem(COURSE_STORAGE_KEY) ?? '[]')
    return Array.isArray(savedCourses) ? savedCourses.map(normalizeCourse).filter((course): course is Course => Boolean(course)) : []
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
const isAddCourseDialogOpen = ref(false)
const newCourseName = ref('')
const newCourseLink = ref('')
const newCourseCoverUrl = ref('')
const addCourseError = ref('')
const isManageCourseDialogOpen = ref(false)
const managedCourse = ref<Course | null>(null)
const managedCourseName = ref('')
const managedCourseLink = ref('')
const manageCourseError = ref('')
const isDeleteCourseConfirming = ref(false)
const isAddLessonDialogOpen = ref(false)
const newLessonTitle = ref('')
const newLessonVideoLink = ref('')
const addLessonError = ref('')
const selectedLesson = ref<Lesson>(cloneDefaultLessons()[2])
const noteWorkspaceCourse = ref<Course | null>(null)
const noteWorkspaceLesson = ref<Lesson | null>(null)
const expandedNoteCourseIds = ref<number[]>([])
const autoRevealCurrentNote = ref(true)
const notesFolderListRef = ref<HTMLElement | null>(null)
const isCreateWorkspaceNoteDialogOpen = ref(false)
const newWorkspaceNoteTitle = ref('')
const createWorkspaceNoteError = ref('')
const isCreateWorkspaceFolderDialogOpen = ref(false)
const newWorkspaceFolderTitle = ref('')
const createWorkspaceFolderError = ref('')
const currentNote = ref('')
const currentVideoUrl = ref('')
type FullscreenMode = 'video' | 'notes' | null
type StudyNotePosition = 'bottom' | 'right'
type ShortcutAction = 'videoFullscreen' | 'notesFullscreen' | 'exitFullscreen'
type ShortcutBinding = {
  key: string
  alt: boolean
  ctrl: boolean
  shift: boolean
  meta: boolean
}

const SHORTCUT_STORAGE_KEY = 'learnflow_shortcuts'
const STUDY_SPLIT_STORAGE_KEY = 'learnflow_study_split_ratio'
const STUDY_NOTE_POSITION_STORAGE_KEY = 'learnflow_study_note_position'
const DEFAULT_STUDY_SPLIT_RATIO = 0.6
const DEFAULT_STUDY_NOTE_POSITION: StudyNotePosition = 'bottom'
const STUDY_VIDEO_MIN_HEIGHT = 280
const STUDY_NOTES_MIN_HEIGHT = 220
const STUDY_SPLIT_HANDLE_HEIGHT = 8
const fullscreenMode = ref<FullscreenMode>(null)
const videoIframeRef = ref<HTMLIFrameElement | null>(null)
const studyWorkspaceRef = ref<HTMLElement | null>(null)
const studySplitRatio = ref(loadSavedStudySplitRatio())
const studyNotePosition = ref<StudyNotePosition>(loadSavedStudyNotePosition())
const isResizingStudySplit = ref(false)
const activeStudySplitPointerId = ref<number | null>(null)
const isLessonPanelCollapsed = ref(false)
const savedPlaybackSeconds = ref<Record<string, number>>({})
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
let youtubePlayer: YoutubePlayer | null = null
let youtubePlayerVideoId = ''
let youtubeApiReadyPromise: Promise<void> | null = null
const turndownService = new TurndownService({
  headingStyle: 'atx',
  codeBlockStyle: 'fenced',
  bulletListMarker: '-'
})

function markdownToHtml(markdown: string) {
  return marked.parse(markdown, { async: false }) as string
}

const markdownPastePatterns = [
  /(^|\n)\s{0,3}#{1,6}\s+\S/,
  /(^|\n)\s{0,3}([-*+]\s+\S|\d+\.\s+\S)/,
  /(^|\n)\s{0,3}>\s+\S/,
  /(^|\n)```/,
  /(^|\n)\s{0,3}(-{3,}|\*{3,}|_{3,})\s*($|\n)/,
  /\*\*[^*\n]+?\*\*|__[^_\n]+?__|`[^`\n]+?`|\[[^\]\n]+?\]\([^)]+?\)/,
  /(^|\n)\|.+\|/
]

function shouldParseMarkdownPaste(text: string) {
  const trimmedText = text.trim()

  return trimmedText.length > 0 && markdownPastePatterns.some((pattern) => pattern.test(trimmedText))
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

function clampStudySplitRatio(ratio: number) {
  if (!Number.isFinite(ratio)) return DEFAULT_STUDY_SPLIT_RATIO
  return Math.min(0.78, Math.max(0.32, ratio))
}

function loadSavedStudySplitRatio() {
  const savedRatio = Number(localStorage.getItem(STUDY_SPLIT_STORAGE_KEY))
  return clampStudySplitRatio(savedRatio || DEFAULT_STUDY_SPLIT_RATIO)
}

function saveStudySplitRatio() {
  localStorage.setItem(STUDY_SPLIT_STORAGE_KEY, String(studySplitRatio.value))
}

function isStudyNotePosition(value: string | null): value is StudyNotePosition {
  return value === 'bottom' || value === 'right'
}

function loadSavedStudyNotePosition() {
  const savedPosition = localStorage.getItem(STUDY_NOTE_POSITION_STORAGE_KEY)
  return isStudyNotePosition(savedPosition) ? savedPosition : DEFAULT_STUDY_NOTE_POSITION
}

function saveStudyNotePosition() {
  localStorage.setItem(STUDY_NOTE_POSITION_STORAGE_KEY, studyNotePosition.value)
}

function toggleStudyNotePosition() {
  if (studyNotePosition.value === 'bottom') {
    stopStudySplitResize()
  }

  studyNotePosition.value = studyNotePosition.value === 'bottom' ? 'right' : 'bottom'
  saveStudyNotePosition()
}

const studyWorkspaceStyle = computed(() => (
  studyNotePosition.value === 'bottom'
    ? {
        gridTemplateRows: `${studySplitRatio.value * 100}% ${STUDY_SPLIT_HANDLE_HEIGHT}px minmax(${STUDY_NOTES_MIN_HEIGHT}px, 1fr)`
      }
    : {
        gridTemplateRows: 'minmax(0, 1fr)'
      }
))

function toggleLessonPanel() {
  isLessonPanelCollapsed.value = !isLessonPanelCollapsed.value
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

  if (mode === 'notes') {
    rememberCurrentPlaybackTime()
    pauseCurrentPlayer()
  }

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
    handlePaste: (_view, event) => {
      const pastedText = event.clipboardData?.getData('text/plain') ?? ''

      if (!shouldParseMarkdownPaste(pastedText) || !noteEditor.value) return false

      event.preventDefault()
      noteEditor.value.commands.insertContent(markdownToHtml(pastedText))
      return true
    },
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

const currentLessons = computed(() => selectedCourse.value?.lessons ?? cloneDefaultLessons())
const activeNoteCourse = computed(() => activeMenu.value === noteMenuName ? noteWorkspaceCourse.value : selectedCourse.value)
const activeNoteLesson = computed(() => activeMenu.value === noteMenuName ? noteWorkspaceLesson.value : selectedLesson.value)
const areAllNoteCoursesExpanded = computed(() => (
  courses.value.length > 0 &&
  courses.value.every((course) => expandedNoteCourseIds.value.includes(course.id))
))
const currentVideoEmbedUrl = computed(() => getVideoEmbedUrl(currentVideoUrl.value))
const currentVideoPlatform = computed(() => getVideoPlatform(currentVideoUrl.value))
const currentYoutubeVideoId = computed(() => getYoutubeVideoId(currentVideoUrl.value) ?? '')

function getPlaybackKey() {
  if (!selectedCourse.value) return ''
  return `${selectedCourse.value.id}_${selectedLesson.value.id}`
}

function savePlaybackTime(seconds: number) {
  const key = getPlaybackKey()

  if (!key || !Number.isFinite(seconds) || seconds < 0) return

  savedPlaybackSeconds.value = {
    ...savedPlaybackSeconds.value,
    [key]: seconds
  }
}

function clearCurrentPlaybackTime() {
  const key = getPlaybackKey()

  if (!key) return

  const remainingTimes = { ...savedPlaybackSeconds.value }
  delete remainingTimes[key]
  savedPlaybackSeconds.value = remainingTimes
}

function loadYoutubeApi() {
  if (window.YT?.Player) return Promise.resolve()
  if (youtubeApiReadyPromise) return youtubeApiReadyPromise

  youtubeApiReadyPromise = new Promise((resolve) => {
    const previousReadyHandler = window.onYouTubeIframeAPIReady

    window.onYouTubeIframeAPIReady = () => {
      previousReadyHandler?.()
      resolve()
    }

    if (!document.querySelector('script[src="https://www.youtube.com/iframe_api"]')) {
      const script = document.createElement('script')
      script.src = 'https://www.youtube.com/iframe_api'
      document.head.appendChild(script)
    }
  })

  return youtubeApiReadyPromise
}

function destroyYoutubePlayer() {
  try {
    youtubePlayer?.destroy()
  } catch {
    // The iframe may already have been removed by Vue during a video switch.
  }

  youtubePlayer = null
  youtubePlayerVideoId = ''
}

async function initializeYoutubePlayer() {
  if (!videoIframeRef.value || !currentYoutubeVideoId.value) {
    destroyYoutubePlayer()
    return
  }

  if (youtubePlayer && youtubePlayerVideoId === currentYoutubeVideoId.value) return

  destroyYoutubePlayer()
  await loadYoutubeApi()

  if (!videoIframeRef.value || !currentYoutubeVideoId.value) return

  youtubePlayer = new window.YT!.Player(videoIframeRef.value, {
    events: {
      onReady: () => {
        restoreCurrentPlaybackTime()
      }
    }
  })
  youtubePlayerVideoId = currentYoutubeVideoId.value
}

function rememberCurrentPlaybackTime() {
  if (currentVideoPlatform.value !== 'YouTube' || !youtubePlayer) return

  savePlaybackTime(youtubePlayer.getCurrentTime())
}

function pauseBilibiliPlayer() {
  try {
    videoIframeRef.value?.contentWindow?.postMessage({ command: 'pause' }, '*')
    videoIframeRef.value?.contentWindow?.postMessage('pause', '*')
  } catch {
    // Bilibili does not expose a stable public control API for embeds.
  }
}

function pauseCurrentPlayer() {
  if (currentVideoPlatform.value === 'YouTube' && youtubePlayer) {
    youtubePlayer.pauseVideo()
    return
  }

  if (currentVideoPlatform.value === 'B站') {
    pauseBilibiliPlayer()
  }
}

function restoreCurrentPlaybackTime() {
  if (currentVideoPlatform.value !== 'YouTube' || !youtubePlayer) return

  const seconds = savedPlaybackSeconds.value[getPlaybackKey()]

  if (typeof seconds === 'number' && Number.isFinite(seconds) && seconds > 0) {
    youtubePlayer.seekTo(seconds, true)
    youtubePlayer.pauseVideo()
  }
}

function handleVideoIframeLoad() {
  if (currentVideoPlatform.value === 'YouTube') {
    void initializeYoutubePlayer()
  }
}

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
  if (!activeNoteCourse.value || !activeNoteLesson.value) return ''
  return getCourseNoteKey(activeNoteCourse.value.id, activeNoteLesson.value.id)
}

function getNoteKeyFor(course: Course, lesson: Lesson) {
  return getCourseNoteKey(course.id, lesson.id)
}

function loadNote(course: Course, lesson: Lesson) {
  return localStorage.getItem(getNoteKeyFor(course, lesson)) ?? defaultNotes[lesson.id] ?? ''
}

function hasSavedNote(course: Course, lesson: Lesson) {
  return Boolean(localStorage.getItem(getNoteKeyFor(course, lesson))?.trim())
}

function getVideoKey() {
  if (!selectedCourse.value) return ''
  return getCourseVideoKey(selectedCourse.value.id, selectedLesson.value.id)
}

function loadCurrentVideo() {
  const key = getVideoKey()
  currentVideoUrl.value = key ? localStorage.getItem(key) ?? '' : ''
}

function setCourseVideo(course: Course, lessonId: number, videoUrl: string) {
  const normalizedUrl = normalizeVideoUrl(videoUrl)
  const key = getCourseVideoKey(course.id, lessonId)
  const isCurrentLessonVideo = selectedCourse.value?.id === course.id && selectedLesson.value.id === lessonId

  if (normalizedUrl) {
    localStorage.setItem(key, normalizedUrl)
  } else {
    localStorage.removeItem(key)
  }

  if (isCurrentLessonVideo) {
    clearCurrentPlaybackTime()
    destroyYoutubePlayer()
    currentVideoUrl.value = normalizedUrl
  }
}

function addCourse() {
  isAddCourseDialogOpen.value = true
  addCourseError.value = ''
}

function goToAddCourse() {
  activeMenu.value = courseMenuName
  currentPage.value = 'courseList'
  addCourse()
}

function closeAddCourseDialog() {
  isAddCourseDialogOpen.value = false
  addCourseError.value = ''
  newCourseName.value = ''
  newCourseLink.value = ''
  newCourseCoverUrl.value = ''
}

function isValidUrl(url: string) {
  try {
    const parsedUrl = new URL(url)
    return parsedUrl.protocol === 'http:' || parsedUrl.protocol === 'https:'
  } catch {
    return false
  }
}

function isImageCover(cover: string) {
  return isValidUrl(cover)
}

function createCourse() {
  const title = newCourseName.value.trim()
  const videoUrl = newCourseLink.value.trim()
  const coverUrl = newCourseCoverUrl.value.trim()
  const courseLessons = cloneDefaultLessons()
  const firstLesson = courseLessons[0]

  if (!title) {
    addCourseError.value = '请输入课程名称'
    return
  }

  if (!videoUrl) {
    addCourseError.value = '请输入课程链接'
    return
  }

  if (coverUrl && !isValidUrl(coverUrl)) {
    addCourseError.value = '课程封面需要填写 http 或 https 开头的 URL'
    return
  }

  const newCourse: Course = {
    id: courses.value.length > 0 ? Math.max(...courses.value.map((course) => course.id)) + 1 : 1,
    title,
    progress: 0,
    status: '未开始',
    cover: coverUrl || '🎬',
    theme: coverUrl ? 'image' : 'cyan',
    lessons: courseLessons
  }

  courses.value.push(newCourse)
  saveCourses()
  selectedCourse.value = newCourse
  selectedLesson.value = firstLesson
  currentPage.value = 'courseDetail'

  setCourseVideo(newCourse, firstLesson.id, videoUrl)
  closeAddCourseDialog()
}

function deleteCourse(course: Course) {
  courses.value = courses.value.filter((item) => item.id !== course.id)
  expandedNoteCourseIds.value = expandedNoteCourseIds.value.filter((courseId) => courseId !== course.id)
  course.lessons.forEach((lesson) => {
    localStorage.removeItem(getCourseNoteKey(course.id, lesson.id))
    localStorage.removeItem(getCourseVideoKey(course.id, lesson.id))
  })
  saveCourses()

  if (noteWorkspaceCourse.value?.id === course.id) {
    noteWorkspaceCourse.value = courses.value[0] ?? null
    noteWorkspaceLesson.value = noteWorkspaceCourse.value?.lessons[0] ?? null
  }

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

  const firstLesson = course.lessons[0] ?? cloneDefaultLessons()[0]
  const lessonId = selectedCourse.value?.id === course.id ? selectedLesson.value.id : firstLesson.id

  managedCourse.value = course
  managedCourseName.value = course.title
  managedCourseLink.value = localStorage.getItem(getCourseVideoKey(course.id, lessonId)) ?? ''
  manageCourseError.value = ''
  isDeleteCourseConfirming.value = false
  isManageCourseDialogOpen.value = true
}

function closeManageCourseDialog() {
  isManageCourseDialogOpen.value = false
  managedCourse.value = null
  managedCourseName.value = ''
  managedCourseLink.value = ''
  manageCourseError.value = ''
  isDeleteCourseConfirming.value = false
}

function saveManagedCourse() {
  if (!managedCourse.value) return

  const title = managedCourseName.value.trim()

  if (!title) {
    manageCourseError.value = '请输入课程名称'
    return
  }

  managedCourse.value.title = title
  setCourseVideo(
    managedCourse.value,
    selectedCourse.value?.id === managedCourse.value.id ? selectedLesson.value.id : (managedCourse.value.lessons[0] ?? cloneDefaultLessons()[0]).id,
    managedCourseLink.value
  )
  saveCourses()
  closeManageCourseDialog()
}

function addLesson() {
  if (!selectedCourse.value) return

  isAddLessonDialogOpen.value = true
  addLessonError.value = ''
}

function closeAddLessonDialog() {
  isAddLessonDialogOpen.value = false
  newLessonTitle.value = ''
  newLessonVideoLink.value = ''
  addLessonError.value = ''
}

function createLesson() {
  if (!selectedCourse.value) return

  const title = newLessonTitle.value.trim()
  const videoUrl = newLessonVideoLink.value.trim()

  if (!title) {
    addLessonError.value = '请输入课节标题'
    return
  }

  if (!videoUrl) {
    addLessonError.value = '请输入课节视频链接'
    return
  }

  const nextLesson: Lesson = {
    id: selectedCourse.value.lessons.length > 0 ? Math.max(...selectedCourse.value.lessons.map((lesson) => lesson.id)) + 1 : 1,
    title,
    status: '未开始',
    time: ''
  }

  selectedCourse.value.lessons.push(nextLesson)
  saveCourses()
  setCourseVideo(selectedCourse.value, nextLesson.id, videoUrl)
  selectLesson(nextLesson)
  closeAddLessonDialog()
}

function confirmDeleteManagedCourse() {
  if (!managedCourse.value) return

  if (!isDeleteCourseConfirming.value) {
    isDeleteCourseConfirming.value = true
    manageCourseError.value = '再次点击删除课程，将同时删除该课程所有课节的笔记和视频链接。'
    return
  }

  deleteCourse(managedCourse.value)
  closeManageCourseDialog()
}

function normalizeVideoUrl(videoUrl: string) {
  const normalizedUrl = videoUrl.trim().replace(/\s+/g, '')

  if (/^(?:www\.)?(?:youtube\.com|youtu\.be|bilibili\.com|b23\.tv)\//i.test(normalizedUrl)) {
    return `https://${normalizedUrl}`
  }

  return normalizedUrl
}

function getBilibiliBvid(videoUrl: string) {
  const normalizedUrl = normalizeVideoUrl(videoUrl)
  const match = normalizedUrl.match(/(?:bilibili\.com\/video\/|\/)(BV[0-9A-Za-z]+)/i)
  return match?.[1]
}

function getYoutubeVideoId(videoUrl: string) {
  try {
    const url = new URL(normalizeVideoUrl(videoUrl))

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
    return `https://player.bilibili.com/player.html?bvid=${encodeURIComponent(bvid)}&page=1&high_quality=1&danmaku=0&autoplay=0`
  }

  const youtubeId = getYoutubeVideoId(videoUrl)

  if (youtubeId) {
    const origin = encodeURIComponent(window.location.origin)
    return `https://www.youtube.com/embed/${encodeURIComponent(youtubeId)}?enablejsapi=1&origin=${origin}`
  }

  return ''
}

function getVideoPlatform(videoUrl: string) {
  if (!videoUrl) return ''
  const normalizedUrl = normalizeVideoUrl(videoUrl)

  if (getBilibiliBvid(normalizedUrl) || normalizedUrl.includes('bilibili.com') || normalizedUrl.includes('b23.tv')) return 'B站'
  if (getYoutubeVideoId(videoUrl)) return 'YouTube'
  return '视频链接'
}

function loadCurrentNote() {
  const nextNote = activeNoteCourse.value && activeNoteLesson.value ? loadNote(activeNoteCourse.value, activeNoteLesson.value) : ''

  shouldSkipNextAutoSave = nextNote !== currentNote.value
  currentNote.value = nextNote
  applyNoteToEditor(nextNote)
  savedText.value = activeNoteCourse.value && activeNoteLesson.value ? '已加载' : '未选择笔记'
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
  if (!activeNoteCourse.value || !activeNoteLesson.value) return

  saveCurrentNote()

  const markdownBlob = new Blob([currentNote.value], {
    type: 'text/markdown;charset=utf-8'
  })
  const downloadUrl = URL.createObjectURL(markdownBlob)
  const downloadLink = document.createElement('a')
  const safeCourseTitle = activeNoteCourse.value.title.replace(/[\\/:*?"<>|]/g, '-')
  const safeLessonTitle = activeNoteLesson.value.title.replace(/[\\/:*?"<>|]/g, '-')

  downloadLink.href = downloadUrl
  downloadLink.download = `${safeCourseTitle}-${safeLessonTitle}-笔记.md`
  downloadLink.click()
  URL.revokeObjectURL(downloadUrl)
}

function initializeNoteWorkspace() {
  if (courses.value.length === 0) {
    noteWorkspaceCourse.value = null
    noteWorkspaceLesson.value = null
    return
  }

  const preferredCourse = selectedCourse.value && courses.value.some((course) => course.id === selectedCourse.value?.id)
    ? selectedCourse.value
    : noteWorkspaceCourse.value && courses.value.some((course) => course.id === noteWorkspaceCourse.value?.id)
      ? noteWorkspaceCourse.value
      : courses.value[0]
  const preferredLesson = preferredCourse.lessons.find((lesson) => lesson.id === selectedLesson.value.id)
    ?? preferredCourse.lessons.find((lesson) => lesson.id === noteWorkspaceLesson.value?.id)
    ?? preferredCourse.lessons[0]
    ?? null

  noteWorkspaceCourse.value = preferredCourse
  noteWorkspaceLesson.value = preferredLesson
  ensureNoteCourseExpanded(preferredCourse.id)
}

function selectNoteWorkspaceCourse(course: Course) {
  toggleNoteCourseExpansion(course.id)

  if (noteWorkspaceCourse.value?.id === course.id) return

  saveCurrentNote()
  noteWorkspaceCourse.value = course
  noteWorkspaceLesson.value = course.lessons[0] ?? null
  loadCurrentNote()
}

function selectNoteWorkspaceLesson(course: Course, lesson: Lesson) {
  if (noteWorkspaceCourse.value?.id === course.id && noteWorkspaceLesson.value?.id === lesson.id) return

  saveCurrentNote()
  ensureNoteCourseExpanded(course.id)
  noteWorkspaceCourse.value = course
  noteWorkspaceLesson.value = lesson
  loadCurrentNote()
}

function isNoteCourseExpanded(courseId: number) {
  return expandedNoteCourseIds.value.includes(courseId)
}

function ensureNoteCourseExpanded(courseId: number) {
  if (isNoteCourseExpanded(courseId)) return

  expandedNoteCourseIds.value = [...expandedNoteCourseIds.value, courseId]
}

function toggleNoteCourseExpansion(courseId: number) {
  expandedNoteCourseIds.value = isNoteCourseExpanded(courseId)
    ? expandedNoteCourseIds.value.filter((id) => id !== courseId)
    : [...expandedNoteCourseIds.value, courseId]
}

function toggleAllNoteFolders() {
  expandedNoteCourseIds.value = areAllNoteCoursesExpanded.value
    ? []
    : courses.value.map((course) => course.id)
}

async function revealCurrentNoteInTree() {
  if (!noteWorkspaceCourse.value || !noteWorkspaceLesson.value) return

  ensureNoteCourseExpanded(noteWorkspaceCourse.value.id)
  await nextTick()

  const currentNoteButton = notesFolderListRef.value?.querySelector<HTMLElement>(
    `[data-note-tree-item="${noteWorkspaceCourse.value.id}-${noteWorkspaceLesson.value.id}"]`
  )

  currentNoteButton?.scrollIntoView({
    block: 'nearest'
  })
}

function toggleAutoRevealCurrentNote() {
  autoRevealCurrentNote.value = !autoRevealCurrentNote.value

  if (autoRevealCurrentNote.value) {
    void revealCurrentNoteInTree()
  }
}

function openCreateWorkspaceNoteDialog() {
  if (!noteWorkspaceCourse.value) return

  createWorkspaceNoteError.value = ''
  newWorkspaceNoteTitle.value = ''
  isCreateWorkspaceNoteDialogOpen.value = true
}

function closeCreateWorkspaceNoteDialog() {
  isCreateWorkspaceNoteDialogOpen.value = false
  newWorkspaceNoteTitle.value = ''
  createWorkspaceNoteError.value = ''
}

function createWorkspaceNote() {
  const course = noteWorkspaceCourse.value
  const title = newWorkspaceNoteTitle.value.trim()

  if (!course) return

  if (!title) {
    createWorkspaceNoteError.value = '请输入笔记名称'
    return
  }

  const nextLesson: Lesson = {
    id: course.lessons.length > 0 ? Math.max(...course.lessons.map((lesson) => lesson.id)) + 1 : 1,
    title,
    status: '未开始',
    time: ''
  }

  course.lessons.push(nextLesson)
  localStorage.setItem(getNoteKeyFor(course, nextLesson), '')
  saveCourses()
  ensureNoteCourseExpanded(course.id)
  noteWorkspaceCourse.value = course
  noteWorkspaceLesson.value = nextLesson
  loadCurrentNote()
  closeCreateWorkspaceNoteDialog()
}

function openCreateWorkspaceFolderDialog() {
  createWorkspaceFolderError.value = ''
  newWorkspaceFolderTitle.value = ''
  isCreateWorkspaceFolderDialogOpen.value = true
}

function closeCreateWorkspaceFolderDialog() {
  isCreateWorkspaceFolderDialogOpen.value = false
  newWorkspaceFolderTitle.value = ''
  createWorkspaceFolderError.value = ''
}

function createWorkspaceFolder() {
  const title = newWorkspaceFolderTitle.value.trim()

  if (!title) {
    createWorkspaceFolderError.value = '请输入文件夹名称'
    return
  }

  const firstNote: Lesson = {
    id: 1,
    title: '未命名笔记',
    status: '未开始',
    time: ''
  }
  const newFolder: Course = {
    id: courses.value.length > 0 ? Math.max(...courses.value.map((course) => course.id)) + 1 : 1,
    title,
    progress: 0,
    status: '未开始',
    cover: '📁',
    theme: 'gray',
    lessons: [firstNote]
  }

  courses.value.push(newFolder)
  localStorage.setItem(getNoteKeyFor(newFolder, firstNote), '')
  saveCourses()
  ensureNoteCourseExpanded(newFolder.id)
  noteWorkspaceCourse.value = newFolder
  noteWorkspaceLesson.value = firstNote
  loadCurrentNote()
  closeCreateWorkspaceFolderDialog()
}

function selectLesson(lesson: Lesson) {
  if (selectedLesson.value.id === lesson.id) return

  saveCurrentNote()
  rememberCurrentPlaybackTime()
  pauseCurrentPlayer()

  destroyYoutubePlayer()
  selectedLesson.value = lesson
}

function getStudySplitBounds() {
  const workspace = studyWorkspaceRef.value

  if (!workspace) {
    return {
      minRatio: 0.32,
      maxRatio: 0.78,
      availableHeight: 1
    }
  }

  const availableHeight = Math.max(workspace.clientHeight - STUDY_SPLIT_HANDLE_HEIGHT, 1)
  const minRatio = Math.max(0.32, STUDY_VIDEO_MIN_HEIGHT / availableHeight)
  const maxRatio = Math.min(0.78, 1 - STUDY_NOTES_MIN_HEIGHT / availableHeight)

  return {
    minRatio,
    maxRatio: Math.max(minRatio, maxRatio),
    availableHeight
  }
}

function updateStudySplitFromClientY(clientY: number) {
  const workspace = studyWorkspaceRef.value

  if (!workspace) return

  const rect = workspace.getBoundingClientRect()
  const { minRatio, maxRatio, availableHeight } = getStudySplitBounds()
  const rawRatio = (clientY - rect.top) / availableHeight
  studySplitRatio.value = Math.min(maxRatio, Math.max(minRatio, rawRatio))
}

function handleStudySplitPointerMove(event: PointerEvent) {
  if (!isResizingStudySplit.value) return
  if (activeStudySplitPointerId.value !== null && event.pointerId !== activeStudySplitPointerId.value) return

  if (event.pointerType === 'mouse' && (event.buttons & 1) === 0) {
    stopStudySplitResize()
    return
  }

  event.preventDefault()
  updateStudySplitFromClientY(event.clientY)
}

function stopStudySplitResize() {
  if (!isResizingStudySplit.value) return

  isResizingStudySplit.value = false
  activeStudySplitPointerId.value = null
  saveStudySplitRatio()
  window.removeEventListener('pointermove', handleStudySplitPointerMove)
  window.removeEventListener('pointerup', stopStudySplitResize)
  window.removeEventListener('pointercancel', stopStudySplitResize)
  window.removeEventListener('blur', stopStudySplitResize)
}

function startStudySplitResize(event: PointerEvent) {
  if (window.matchMedia('(max-width: 820px)').matches) return
  if (event.pointerType === 'mouse' && event.button !== 0) return

  event.preventDefault()
  isResizingStudySplit.value = true
  activeStudySplitPointerId.value = event.pointerId
  updateStudySplitFromClientY(event.clientY)
  window.addEventListener('pointermove', handleStudySplitPointerMove)
  window.addEventListener('pointerup', stopStudySplitResize)
  window.addEventListener('pointercancel', stopStudySplitResize)
  window.addEventListener('blur', stopStudySplitResize)
}

function resizeStudySplitByKeyboard(event: KeyboardEvent) {
  if (!['ArrowUp', 'ArrowDown', 'Home', 'End'].includes(event.key)) return

  event.preventDefault()
  const { minRatio, maxRatio } = getStudySplitBounds()

  if (event.key === 'Home') {
    studySplitRatio.value = minRatio
  } else if (event.key === 'End') {
    studySplitRatio.value = maxRatio
  } else {
    const delta = event.key === 'ArrowUp' ? -0.02 : 0.02
    studySplitRatio.value = Math.min(maxRatio, Math.max(minRatio, studySplitRatio.value + delta))
  }

  saveStudySplitRatio()
}

watch([selectedCourse, selectedLesson], () => {
  if (activeMenu.value !== noteMenuName) {
    loadCurrentNote()
  }
  loadCurrentVideo()
}, {
  immediate: true
})

watch([noteWorkspaceCourse, noteWorkspaceLesson], () => {
  if (activeMenu.value === noteMenuName) {
    loadCurrentNote()

    if (autoRevealCurrentNote.value) {
      void revealCurrentNoteInTree()
    }
  }
})

watch(currentVideoEmbedUrl, () => {
  destroyYoutubePlayer()
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
  window.removeEventListener('pointermove', handleStudySplitPointerMove)
  window.removeEventListener('pointerup', stopStudySplitResize)
  window.removeEventListener('pointercancel', stopStudySplitResize)
  window.removeEventListener('blur', stopStudySplitResize)
  clearTimeout(autoSaveTimer)
  destroyYoutubePlayer()
  syncCurrentNoteFromEditor()
  noteEditor.value?.destroy()
})

function openCourseDetail(course: Course) {
  selectedCourse.value = course
  selectedLesson.value = noteWorkspaceCourse.value?.id === course.id && noteWorkspaceLesson.value
    ? noteWorkspaceLesson.value
    : course.lessons[0] ?? cloneDefaultLessons()[0]
  currentPage.value = 'courseDetail'
}
function backToCourseList(){
  rememberCurrentPlaybackTime()
  pauseCurrentPlayer()

  destroyYoutubePlayer()
  fullscreenMode.value = null
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
      'sidebar-collapsed': isSidebarCollapsed,
      'course-study-active': currentPage === 'courseDetail' && activeMenu === courseMenuName
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

        <section v-else-if="activeMenu === noteMenuName" class="notes-workspace">
          <div v-if="courses.length === 0" class="notes-empty-state">
            <h1>笔记管理</h1>
            <p>先添加课程后开始整理每个小节的笔记。</p>
            <button class="add-button" @click="goToAddCourse">
              <span>＋</span>
              添加课程
            </button>
          </div>

          <template v-else>
            <aside class="notes-folder-panel">
              <div class="notes-folder-toolbar">
                <h1>笔记管理</h1>
                <span>{{ courses.length }} 门课程</span>
              </div>

              <div class="notes-tree-actions" role="toolbar" aria-label="笔记管理工具栏">
                <button
                  type="button"
                  class="notes-tree-action-button"
                  title="新建笔记"
                  aria-label="新建笔记"
                  @click="openCreateWorkspaceNoteDialog"
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M4 20h4l10.5-10.5a2.8 2.8 0 0 0-4-4L4 16v4Z"></path>
                    <path d="m13.5 6.5 4 4"></path>
                  </svg>
                </button>
                <button
                  type="button"
                  class="notes-tree-action-button"
                  title="新建文件夹"
                  aria-label="新建文件夹"
                  @click="openCreateWorkspaceFolderDialog"
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M3.5 18.5V7.8A1.8 1.8 0 0 1 5.3 6h4.2l2 2h7.2a1.8 1.8 0 0 1 1.8 1.8v8.7a1.8 1.8 0 0 1-1.8 1.8H5.3a1.8 1.8 0 0 1-1.8-1.8Z"></path>
                    <path d="M12 11v6"></path>
                    <path d="M9 14h6"></path>
                  </svg>
                </button>
                <button
                  type="button"
                  class="notes-tree-action-button"
                  :class="{ active: autoRevealCurrentNote }"
                  :title="autoRevealCurrentNote ? '自动显示当前文件：已开启' : '自动显示当前文件：已关闭'"
                  :aria-label="autoRevealCurrentNote ? '关闭自动显示当前文件' : '开启自动显示当前文件'"
                  :aria-pressed="autoRevealCurrentNote"
                  @click="toggleAutoRevealCurrentNote"
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M4 6h7"></path>
                    <path d="M4 12h11"></path>
                    <path d="M4 18h7"></path>
                    <path d="m14 7 4 5-4 5"></path>
                  </svg>
                </button>
                <button
                  type="button"
                  class="notes-tree-action-button"
                  :title="areAllNoteCoursesExpanded ? '全部折叠' : '全部展开'"
                  :aria-label="areAllNoteCoursesExpanded ? '全部折叠' : '全部展开'"
                  @click="toggleAllNoteFolders"
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="m7 9 5-5 5 5"></path>
                    <path d="m7 15 5 5 5-5"></path>
                  </svg>
                </button>
              </div>

              <div ref="notesFolderListRef" class="notes-folder-list">
                <section
                  v-for="course in courses"
                  :key="course.id"
                  class="notes-folder"
                >
                  <button
                    type="button"
                    class="notes-folder-button"
                    :class="{ active: noteWorkspaceCourse?.id === course.id }"
                    @click="selectNoteWorkspaceCourse(course)"
                  >
                    <span>📁</span>
                    <strong>{{ course.title }}</strong>
                    <small>{{ course.lessons.length }} 节</small>
                  </button>

                  <Transition name="notes-lesson-expand">
                    <div v-if="isNoteCourseExpanded(course.id)" class="notes-lesson-list-shell">
                      <div class="notes-lesson-list">
                        <p v-if="course.lessons.length === 0" class="notes-empty-folder">该课程暂无课节</p>
                        <button
                          v-for="lesson in course.lessons"
                          :key="lesson.id"
                          type="button"
                          class="notes-lesson-button"
                          :data-note-tree-item="`${course.id}-${lesson.id}`"
                          :class="{ active: noteWorkspaceCourse?.id === course.id && noteWorkspaceLesson?.id === lesson.id }"
                          @click="selectNoteWorkspaceLesson(course, lesson)"
                        >
                          <span>📄</span>
                          <span>{{ lesson.id }}. {{ lesson.title }}</span>
                          <small>{{ hasSavedNote(course, lesson) ? '有笔记' : '空白' }}</small>
                        </button>
                      </div>
                    </div>
                  </Transition>
                </section>
              </div>
            </aside>

            <section class="notes-editor-panel">
              <div v-if="noteWorkspaceCourse && noteWorkspaceLesson" class="notes-editor-shell">
                <div class="notes-editor-topbar">
                  <div>
                    <p>{{ noteWorkspaceCourse.title }} / {{ noteWorkspaceLesson.title }}</p>
                    <h1>{{ noteWorkspaceLesson.title }}</h1>
                  </div>

                  <div class="note-actions">
                    <span>{{ savedText }}</span>
                    <button @click="saveCurrentNote()">保存</button>
                    <button class="secondary" @click="exportCurrentNote">导出</button>
                  </div>
                </div>

                <div class="wysiwyg-note-editor notes-manager-editor">
                  <EditorContent class="note-editor-content" :editor="noteEditor" />
                </div>
              </div>

              <div v-else class="notes-empty-state inline">
                <h1>选择一节课</h1>
                <p>从左侧课程文件夹中选择小节后开始编辑笔记。</p>
              </div>
            </section>
          </template>
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
        <section
          ref="studyWorkspaceRef"
          class="course-study-workspace"
          :class="{
            resizing: isResizingStudySplit,
            'lesson-panel-collapsed': isLessonPanelCollapsed,
            'note-position-right': studyNotePosition === 'right'
          }"
          :style="studyWorkspaceStyle"
        >
          <aside v-if="!isLessonPanelCollapsed" class="lesson-panel">
            <div class="lesson-header">
              <h2>课程目录</h2>
              <div class="lesson-header-actions">
                <button type="button" @click="addLesson">+ 添加课节</button>
                <button type="button" @click="toggleLessonPanel">收起</button>
              </div>
            </div>

            <div class="lesson-list">
              <button
                v-for="lesson in currentLessons"
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
              </button>
            </div>
          </aside>

          <button
            v-else
            class="lesson-expand-button"
            type="button"
            @click="toggleLessonPanel"
          >
            展开目录
          </button>

          <section class="video-study-card">
            <div v-if="currentVideoUrl" class="video-player-card">
              <iframe
                v-if="currentVideoEmbedUrl"
                ref="videoIframeRef"
                class="video-iframe"
                :src="currentVideoEmbedUrl"
                title="课程视频播放器"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                allowfullscreen
                @load="handleVideoIframeLoad"
              ></iframe>

              <div v-else class="video-link-fallback">
                <img
                  v-if="isImageCover(selectedCourse.cover)"
                  class="video-cover-image"
                  :src="selectedCourse.cover"
                  :alt="selectedCourse.title"
                />
                <div v-else class="video-cover-icon">{{ selectedCourse.cover }}</div>
                <h3>已绑定{{ currentVideoPlatform }}</h3>
                <p>这个链接暂时不能直接嵌入播放，可以打开原链接学习。</p>
              </div>

            </div>

            <div v-else class="fake-video">
              <img
                v-if="isImageCover(selectedCourse.cover)"
                class="video-cover-image"
                :src="selectedCourse.cover"
                :alt="selectedCourse.title"
              />
              <div v-else class="video-cover-icon">{{ selectedCourse.cover }}</div>
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
          </section>

          <button
            class="study-resize-handle"
            type="button"
            aria-label="调整视频区和笔记区高度"
            aria-orientation="horizontal"
            @pointerdown="startStudySplitResize"
            @keydown="resizeStudySplitByKeyboard"
          >
            <span></span>
          </button>

          <section class="note-card">
            <div class="note-header">
              <span class="note-save-status">{{savedText}}</span>
              <div class="note-actions">
                <button
                  type="button"
                  class="secondary"
                  :title="studyNotePosition === 'bottom' ? '移到右侧' : '移到下方'"
                  :aria-label="studyNotePosition === 'bottom' ? '将笔记移到右侧' : '将笔记移到下方'"
                  @click="toggleStudyNotePosition"
                >
                  <svg v-if="studyNotePosition === 'bottom'" viewBox="0 0 20 20" aria-hidden="true">
                    <rect x="3" y="3" width="14" height="14" rx="2"></rect>
                    <path d="M12 3v14"></path>
                  </svg>
                  <svg v-else viewBox="0 0 20 20" aria-hidden="true">
                    <rect x="3" y="3" width="14" height="14" rx="2"></rect>
                    <path d="M3 12h14"></path>
                  </svg>
                </button>
                <button
                  type="button"
                  class="secondary"
                  :title="fullscreenMode === 'notes' ? '退出全屏' : '全屏'"
                  :aria-label="fullscreenMode === 'notes' ? '退出笔记全屏' : '笔记全屏'"
                  @click="toggleStudyFullscreen('notes')"
                >
                  <svg v-if="fullscreenMode !== 'notes'" viewBox="0 0 20 20" aria-hidden="true">
                    <path d="M7 3H3v4"></path>
                    <path d="M13 3h4v4"></path>
                    <path d="M17 13v4h-4"></path>
                    <path d="M7 17H3v-4"></path>
                  </svg>
                  <svg v-else viewBox="0 0 20 20" aria-hidden="true">
                    <path d="M8 3v5H3"></path>
                    <path d="M12 3v5h5"></path>
                    <path d="M17 12h-5v5"></path>
                    <path d="M8 17v-5H3"></path>
                  </svg>
                </button>
                <button
                  type="button"
                  class="save-action"
                  title="保存"
                  aria-label="保存笔记"
                  @click="saveCurrentNote()"
                >
                  <svg viewBox="0 0 20 20" aria-hidden="true">
                    <path d="M4 4.5A1.5 1.5 0 0 1 5.5 3h8.2L16 5.3v10.2a1.5 1.5 0 0 1-1.5 1.5h-9A1.5 1.5 0 0 1 4 15.5v-11Z"></path>
                    <path d="M7 3v5h6V3"></path>
                    <path d="M7 17v-5h6v5"></path>
                  </svg>
                </button>
                <button
                  type="button"
                  class="secondary"
                  title="导出"
                  aria-label="导出笔记"
                  @click="exportCurrentNote"
                >
                  <svg viewBox="0 0 20 20" aria-hidden="true">
                    <path d="M10 3v9"></path>
                    <path d="m6.5 8.5 3.5 3.5 3.5-3.5"></path>
                    <path d="M4 16h12"></path>
                  </svg>
                </button>
              </div>
            </div>

            <div class="wysiwyg-note-editor">
              <EditorContent class="note-editor-content" :editor="noteEditor" />
            </div>
          </section>
        </section>
      </div>
        <section v-if="activeMenu !== settingsMenuName && activeMenu !== noteMenuName && currentPage === 'courseList' && courses.length > 0" class="course-grid">
          <article
            v-for="course in courses"
            :key="course.id"
            class="course-card"
            @click="openCourseDetail(course)"
          >
            <div class="course-cover" :class="course.theme">
              <img v-if="isImageCover(course.cover)" :src="course.cover" :alt="course.title" />
              <span v-else>{{ course.cover }}</span>
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

    <div
      v-if="isAddCourseDialogOpen"
      class="dialog-backdrop"
      role="presentation"
      @click.self="closeAddCourseDialog"
    >
      <form class="add-course-dialog" @submit.prevent="createCourse">
        <div class="dialog-header">
          <div>
            <h2>添加课程</h2>
            <p>填写课程信息后，会自动进入第一节课。</p>
          </div>
          <button
            class="dialog-close-button"
            type="button"
            aria-label="关闭"
            @click="closeAddCourseDialog"
          >
            ×
          </button>
        </div>

        <label class="field-group">
          <span>课程名称</span>
          <input v-model="newCourseName" type="text" autocomplete="off" placeholder="例如：Python 入门" />
        </label>

        <label class="field-group">
          <span>课程链接（B 站或 YouTube）</span>
          <input v-model="newCourseLink" type="text" inputmode="url" autocomplete="off" placeholder="粘贴 YouTube 或 B 站视频链接" />
        </label>

        <label class="field-group">
          <span>课程封面（url 格式，可选）</span>
          <input v-model="newCourseCoverUrl" type="url" autocomplete="off" placeholder="https://..." />
        </label>

        <div v-if="newCourseCoverUrl.trim()" class="cover-preview">
          <img
            v-if="isImageCover(newCourseCoverUrl.trim())"
            :src="newCourseCoverUrl.trim()"
            alt="课程封面预览"
          />
          <span v-else>封面 URL 格式不正确</span>
        </div>

        <p v-if="addCourseError" class="dialog-error">{{ addCourseError }}</p>

        <div class="dialog-actions">
          <button class="dialog-secondary-button" type="button" @click="closeAddCourseDialog">取消</button>
          <button class="dialog-primary-button" type="submit">添加课程</button>
        </div>
      </form>
    </div>

    <div
      v-if="isCreateWorkspaceNoteDialogOpen"
      class="dialog-backdrop"
      role="presentation"
      @click.self="closeCreateWorkspaceNoteDialog"
    >
      <form class="add-course-dialog" @submit.prevent="createWorkspaceNote">
        <div class="dialog-header">
          <div>
            <h2>新建笔记</h2>
            <p>将在当前文件夹下创建一条新的笔记。</p>
          </div>
          <button
            class="dialog-close-button"
            type="button"
            aria-label="关闭"
            @click="closeCreateWorkspaceNoteDialog"
          >
            ×
          </button>
        </div>

        <label class="field-group">
          笔记名称
          <input
            v-model="newWorkspaceNoteTitle"
            type="text"
            placeholder="例如：Vue 生命周期"
            autofocus
          />
        </label>

        <p class="dialog-error">{{ createWorkspaceNoteError }}</p>

        <div class="dialog-actions">
          <button class="dialog-secondary-button" type="button" @click="closeCreateWorkspaceNoteDialog">
            取消
          </button>
          <button class="dialog-primary-button" type="submit">
            创建笔记
          </button>
        </div>
      </form>
    </div>

    <div
      v-if="isCreateWorkspaceFolderDialogOpen"
      class="dialog-backdrop"
      role="presentation"
      @click.self="closeCreateWorkspaceFolderDialog"
    >
      <form class="add-course-dialog" @submit.prevent="createWorkspaceFolder">
        <div class="dialog-header">
          <div>
            <h2>新建文件夹</h2>
            <p>会先附带一条空白笔记，方便你马上开始整理。</p>
          </div>
          <button
            class="dialog-close-button"
            type="button"
            aria-label="关闭"
            @click="closeCreateWorkspaceFolderDialog"
          >
            ×
          </button>
        </div>

        <label class="field-group">
          文件夹名称
          <input
            v-model="newWorkspaceFolderTitle"
            type="text"
            placeholder="例如：面试"
            autofocus
          />
        </label>

        <p class="dialog-error">{{ createWorkspaceFolderError }}</p>

        <div class="dialog-actions">
          <button class="dialog-secondary-button" type="button" @click="closeCreateWorkspaceFolderDialog">
            取消
          </button>
          <button class="dialog-primary-button" type="submit">
            创建文件夹
          </button>
        </div>
      </form>
    </div>

    <div
      v-if="isManageCourseDialogOpen && managedCourse"
      class="dialog-backdrop"
      role="presentation"
      @click.self="closeManageCourseDialog"
    >
      <form class="add-course-dialog manage-course-dialog" @submit.prevent="saveManagedCourse">
        <div class="dialog-header">
          <div>
            <h2>管理课程</h2>
            <p>{{ managedCourse.title }}</p>
          </div>
          <button
            class="dialog-close-button"
            type="button"
            aria-label="关闭"
            @click="closeManageCourseDialog"
          >
            ×
          </button>
        </div>

        <label class="field-group">
          <span>课程名称</span>
          <input v-model="managedCourseName" type="text" autocomplete="off" />
        </label>

        <label class="field-group">
          <span>课程链接（B 站或 YouTube）</span>
          <input v-model="managedCourseLink" type="text" inputmode="url" autocomplete="off" placeholder="粘贴 YouTube 或 B 站视频链接" />
        </label>

        <p v-if="manageCourseError" class="dialog-error">{{ manageCourseError }}</p>

        <div class="manage-danger-zone">
          <button
            class="dialog-danger-button"
            type="button"
            @click="confirmDeleteManagedCourse"
          >
            {{ isDeleteCourseConfirming ? '确认删除课程' : '删除课程' }}
          </button>
        </div>

        <div class="dialog-actions">
          <button class="dialog-secondary-button" type="button" @click="closeManageCourseDialog">取消</button>
          <button class="dialog-primary-button" type="submit">保存修改</button>
        </div>
      </form>
    </div>

    <div
      v-if="isAddLessonDialogOpen && selectedCourse"
      class="dialog-backdrop"
      role="presentation"
      @click.self="closeAddLessonDialog"
    >
      <form class="add-course-dialog" @submit.prevent="createLesson">
        <div class="dialog-header">
          <div>
            <h2>添加课节</h2>
            <p>{{ selectedCourse.title }}</p>
          </div>
          <button
            class="dialog-close-button"
            type="button"
            aria-label="关闭"
            @click="closeAddLessonDialog"
          >
            ×
          </button>
        </div>

        <label class="field-group">
          <span>课节标题</span>
          <input v-model="newLessonTitle" type="text" autocomplete="off" placeholder="例如：数组与对象" />
        </label>

        <label class="field-group">
          <span>视频链接（B 站或 YouTube）</span>
          <input v-model="newLessonVideoLink" type="text" inputmode="url" autocomplete="off" placeholder="粘贴 YouTube 或 B 站视频链接" />
        </label>

        <p v-if="addLessonError" class="dialog-error">{{ addLessonError }}</p>

        <div class="dialog-actions">
          <button class="dialog-secondary-button" type="button" @click="closeAddLessonDialog">取消</button>
          <button class="dialog-primary-button" type="submit">添加课节</button>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
.app {
  width: 100vw;
  height: 100vh;
  min-width: 0;
  --shell-padding: 16px;
  --panel-gap: 10px;
  --panel-padding: 14px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #f6f8fc;
}

.top-bar {
  position: relative;
  height: 72px;
  flex: 0 0 72px;
  padding: 0 var(--shell-padding);
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

.layout {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-columns: 208px 1fr;
  overflow: hidden;
  transition: grid-template-columns 180ms ease;
}

.sidebar {
  position: relative;
  padding: 20px 14px;
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
  padding-left: 20px;
  padding-right: 20px;
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
  gap: 10px;
}

.menu-item {
  height: 58px;
  padding: 0 12px;
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

.content {
  min-width: 0;
  min-height: 0;
  padding: var(--shell-padding);
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  overflow: hidden;
}

.settings-panel {
  width: min(820px, 100%);
  display: flex;
  flex-direction: column;
  gap: 14px;
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
  min-height: 84px;
  padding: 16px;
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
  margin-bottom: 18px;
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
  gap: 14px;
  min-width: 0;
}

.course-card {
  position: relative;
  width: 100%;
  min-height: 154px;
  padding: 14px;
  display: flex;
  gap: 14px;
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
  overflow: hidden;
}

.course-cover img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
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

.course-cover.image {
  background: #e2e8f0;
}

.dialog-backdrop {
  position: fixed;
  inset: 0;
  z-index: 30;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(15, 23, 42, 0.32);
  backdrop-filter: blur(6px);
}

.add-course-dialog {
  width: min(440px, 100%);
  padding: 24px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 24px 70px rgba(15, 23, 42, 0.22);
}

.dialog-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 22px;
}

.dialog-header h2 {
  margin: 0;
  color: #111827;
  font-size: 24px;
  line-height: 1.2;
}

.dialog-header p {
  margin: 8px 0 0;
  color: #64748b;
  font-size: 14px;
}

.dialog-close-button {
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
  color: #475569;
  font-size: 22px;
  line-height: 1;
}

.field-group {
  display: grid;
  gap: 8px;
  margin-bottom: 16px;
  color: #334155;
  font-size: 14px;
  font-weight: 700;
}

.field-group input {
  width: 100%;
  height: 44px;
  padding: 0 12px;
  border: 1px solid #dbe3ee;
  border-radius: 8px;
  outline: none;
  background: #f8fafc;
  color: #111827;
  font-size: 15px;
  transition:
    background 150ms ease,
    border-color 150ms ease,
    box-shadow 150ms ease;
}

.field-group input:focus {
  background: white;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.cover-preview {
  height: 116px;
  margin: 4px 0 16px;
  display: grid;
  place-items: center;
  overflow: hidden;
  border: 1px dashed #cbd5e1;
  border-radius: 10px;
  background: #f8fafc;
  color: #dc2626;
  font-size: 14px;
  font-weight: 700;
}

.cover-preview img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
}

.dialog-error {
  min-height: 20px;
  margin: 0 0 14px;
  color: #dc2626;
  font-size: 14px;
  font-weight: 700;
}

.manage-danger-zone {
  padding: 14px 0 4px;
  margin-top: 2px;
  border-top: 1px solid #eef2f7;
}

.dialog-danger-button {
  height: 38px;
  padding: 0 14px;
  border: 1px solid #fecaca;
  border-radius: 8px;
  background: #fff7f7;
  color: #dc2626;
  font-weight: 700;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 6px;
}

.dialog-secondary-button,
.dialog-primary-button {
  height: 42px;
  padding: 0 18px;
  border-radius: 8px;
  font-weight: 700;
}

.dialog-secondary-button {
  border: 1px solid #dbe3ee;
  background: white;
  color: #334155;
}

.dialog-primary-button {
  border: none;
  background: #2563eb;
  color: white;
  box-shadow: 0 8px 18px rgba(37, 99, 235, 0.24);
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

.notes-workspace {
  height: 100%;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(240px, 300px) minmax(0, 1fr);
  gap: var(--panel-gap);
}

.notes-folder-panel,
.notes-editor-panel,
.notes-empty-state {
  min-height: 0;
  background: white;
  border: 1px solid #e1e7ef;
  border-radius: 10px;
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.05);
}

.notes-folder-panel {
  padding: var(--panel-padding);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.notes-folder-toolbar {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 14px;
  border-bottom: 1px solid #e5eaf3;
}

.notes-folder-toolbar h1 {
  margin: 0;
  color: #111827;
  font-size: 24px;
}

.notes-folder-toolbar span,
.notes-folder-button small,
.notes-lesson-button small,
.notes-editor-topbar p {
  color: #64748b;
  font-size: 13px;
  font-weight: 700;
}

.notes-tree-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 12px 0 2px;
}

.notes-tree-action-button {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border: 1px solid transparent;
  border-radius: 8px;
  background: transparent;
  color: #64748b;
  transition:
    color 150ms ease,
    border-color 150ms ease,
    background 150ms ease;
}

.notes-tree-action-button:hover,
.notes-tree-action-button:focus-visible {
  border-color: #dbe3ee;
  background: #f8fafc;
  color: #334155;
  outline: none;
}

.notes-tree-action-button.active {
  border-color: #bfdbfe;
  background: #eff6ff;
  color: #2563eb;
}

.notes-tree-action-button svg {
  width: 21px;
  height: 21px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.notes-folder-list {
  min-height: 0;
  margin-top: 10px;
  overflow: auto;
}

.notes-folder {
  display: grid;
  gap: 8px;
  margin-bottom: 10px;
}

.notes-folder-button,
.notes-lesson-button {
  width: 100%;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: #334155;
  text-align: left;
}

.notes-folder-button {
  min-height: 48px;
  padding: 10px 12px;
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 10px;
  border: 1px solid #e5eaf3;
}

.notes-folder-button.active {
  border-color: #2563eb;
  background: #eff6ff;
  color: #1d4ed8;
}

.notes-lesson-list-shell {
  display: grid;
  grid-template-rows: 1fr;
  overflow: hidden;
}

.notes-lesson-expand-enter-active,
.notes-lesson-expand-leave-active {
  transition:
    grid-template-rows 180ms ease,
    opacity 160ms ease,
    transform 180ms ease;
}

.notes-lesson-expand-enter-from,
.notes-lesson-expand-leave-to {
  grid-template-rows: 0fr;
  opacity: 0;
  transform: translateY(-4px);
}

.notes-lesson-expand-enter-to,
.notes-lesson-expand-leave-from {
  grid-template-rows: 1fr;
  opacity: 1;
  transform: translateY(0);
}

.notes-lesson-list {
  min-height: 0;
  display: grid;
  gap: 6px;
  padding-left: 20px;
}

.notes-lesson-button {
  min-height: 40px;
  padding: 8px 10px;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
}

.notes-lesson-button span:nth-child(2) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.notes-lesson-button.active {
  background: #f8fafc;
  color: #111827;
  font-weight: 700;
}

.notes-empty-folder {
  margin: 8px 0;
  color: #94a3b8;
  font-size: 14px;
}

.notes-editor-panel {
  padding: var(--panel-padding);
  overflow: hidden;
}

.notes-editor-shell {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.notes-editor-topbar {
  min-height: 60px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  padding-bottom: 10px;
}

.notes-editor-topbar h1 {
  margin: 6px 0 0;
  color: #111827;
  font-size: 28px;
}

.notes-editor-topbar p {
  margin: 0;
}

.notes-manager-editor {
  flex: 1;
  height: auto;
  min-height: 0;
}

.notes-manager-editor :deep(.tiptap) {
  min-height: 0;
  overflow: auto;
}

.notes-empty-state {
  padding: 20px;
  display: grid;
  align-content: center;
  justify-items: start;
}

.notes-empty-state.inline {
  height: 100%;
  box-shadow: none;
}

.notes-empty-state h1 {
  margin: 0;
  color: #111827;
  font-size: 30px;
}

.notes-empty-state p {
  margin: 10px 0 22px;
  color: #64748b;
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
    padding: 18px;
    justify-content: flex-start;
  }

  .course-grid {
    grid-template-columns: 1fr;
  }

  .notes-workspace {
    grid-template-columns: 1fr;
    overflow: auto;
  }

  .notes-folder-panel {
    max-height: 340px;
  }
}

@media (max-width: 520px) {
  .top-bar {
    padding: 0 16px;
  }

  .brand {
    font-size: 18px;
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
    padding-top: 18px;
    padding-bottom: 18px;
  }
}

.course-study-active .content {
  padding: 12px;
}

.course-detail-page {
  height: 100%;
  min-width: 0;
  min-height: 0;
  display: block;
  overflow: hidden;
}

.course-detail-page ~ .course-grid {
  display: none;
}

.course-study-workspace {
  position: relative;
  height: 100%;
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(220px, 240px) minmax(0, 1fr);
  column-gap: var(--panel-gap);
  overflow: hidden;
}

.course-study-workspace.lesson-panel-collapsed {
  grid-template-columns: minmax(0, 1fr);
  column-gap: 0;
}

.course-study-workspace.note-position-right {
  grid-template-columns: minmax(220px, 240px) minmax(0, 1fr) minmax(320px, 380px);
  column-gap: var(--panel-gap);
}

.course-study-workspace.note-position-right.lesson-panel-collapsed {
  grid-template-columns: minmax(0, 1fr) minmax(320px, 380px);
}

.course-study-workspace.resizing {
  user-select: none;
  cursor: row-resize;
}

.lesson-panel,
.video-study-card,
.note-card {
  background: white;
  border: 1px solid #e1e7ef;
  border-radius: 10px;
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.05);
}

.lesson-panel {
  min-height: 0;
  grid-column: 1;
  grid-row: 1;
  padding: var(--panel-padding);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.lesson-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding-bottom: 14px;
  border-bottom: 1px solid #e5eaf3;
}

.lesson-header h2 {
  margin: 0;
  font-size: 18px;
}

.lesson-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.lesson-header button {
  border: none;
  background: transparent;
  color: #64748b;
  font-size: 14px;
}

.lesson-expand-button {
  position: absolute;
  top: 16px;
  left: 16px;
  z-index: 2;
  height: 34px;
  padding: 0 12px;
  border: 1px solid #dbe3ee;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.94);
  color: #475569;
  font-weight: 700;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(10px);
}

.lesson-list {
  min-height: 0;
  margin-top: 10px;
  overflow: auto;
}

.lesson-item {
  width: 100%;
  min-height: 76px;
  padding: 14px 12px;
  display: flex;
  align-items: center;
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

.video-study-card {
  min-width: 0;
  min-height: 0;
  grid-column: 2;
  grid-row: 1;
  padding: var(--panel-padding);
  display: flex;
  flex-direction: column;
}

.course-study-workspace.lesson-panel-collapsed .video-study-card {
  grid-column: 1;
}

.course-study-workspace.note-position-right .video-study-card {
  grid-column: 2;
  grid-row: 1;
}

.course-study-workspace.note-position-right.lesson-panel-collapsed .video-study-card {
  grid-column: 1;
}

.fake-video {
  position: relative;
  flex: 1;
  min-height: 280px;
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
  flex: 1;
  min-height: 0;
  overflow: hidden;
  border: 1px solid #dbe3ee;
  border-radius: 10px;
  background: #0f172a;
  display: flex;
  flex-direction: column;
}

.video-iframe {
  display: block;
  width: 100%;
  flex: 1;
  min-height: 0;
  border: none;
  background: #0f172a;
}

.video-link-fallback {
  flex: 1;
  min-height: 280px;
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

.video-cover-icon {
  font-size: 88px;
  margin-bottom: 12px;
}

.video-cover-image {
  width: 132px;
  height: 88px;
  margin-bottom: 16px;
  display: block;
  border-radius: 10px;
  object-fit: cover;
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.26);
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

.note-card {
  min-height: 0;
  grid-column: 1 / -1;
  grid-row: 3;
  padding: var(--panel-padding);
  display: flex;
  flex-direction: column;
}

.course-study-workspace.note-position-right .note-card {
  grid-column: 3;
  grid-row: 1;
}

.course-study-workspace.note-position-right.lesson-panel-collapsed .note-card {
  grid-column: 2;
}

.note-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-height: 28px;
  margin-bottom: 10px;
}

.note-save-status {
  color: #64748b;
  font-size: 12px;
  white-space: nowrap;
}

.note-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.note-actions button {
  width: 28px;
  height: 28px;
  padding: 0;
  display: grid;
  place-items: center;
  border: none;
  border-radius: 7px;
  background: #2563eb;
  color: white;
}

.note-actions button.secondary {
  border: 1px solid #dbe3ee;
  background: white;
  color: #334155;
}

.note-actions button:hover,
.note-actions button:focus-visible {
  transform: translateY(-1px);
  outline: none;
}

.note-actions button.secondary:hover,
.note-actions button.secondary:focus-visible {
  border-color: #bfdbfe;
  background: #f8fbff;
  color: #2563eb;
}

.note-actions button.save-action:hover,
.note-actions button.save-action:focus-visible {
  background: #1d4ed8;
}

.note-actions svg {
  width: 15px;
  height: 15px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.7;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.wysiwyg-note-editor {
  flex: 1;
  min-height: 0;
  border: 1px solid #e1e7ef;
  border-radius: 8px;
  overflow: hidden;
  background: white;
}

.note-editor-content {
  height: 100%;
  min-height: 0;
}

.wysiwyg-note-editor :deep(.tiptap) {
  height: 100%;
  min-height: 0;
  padding: 20px;
  overflow: auto;
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

.study-resize-handle {
  grid-column: 1 / -1;
  grid-row: 2;
  width: 100%;
  height: 8px;
  border: none;
  background: transparent;
  display: grid;
  place-items: center;
  cursor: row-resize;
}

.study-resize-handle span {
  width: 72px;
  height: 4px;
  border-radius: 999px;
  background: #cbd5e1;
  transition:
    width 150ms ease,
    background 150ms ease;
}

.study-resize-handle:hover span,
.study-resize-handle:focus-visible span,
.course-study-workspace.resizing .study-resize-handle span {
  width: 96px;
  background: #2563eb;
}

.course-study-workspace.note-position-right .study-resize-handle {
  display: none;
}

.fullscreen-active .top-bar,
.fullscreen-active .sidebar,
.fullscreen-active .collapsed-dock,
.fullscreen-active .lesson-panel,
.fullscreen-active .lesson-expand-button,
.fullscreen-active .study-resize-handle {
  display: none;
}

.fullscreen-active .layout {
  grid-template-columns: 1fr;
}

.fullscreen-active .content {
  padding: 0;
}

.fullscreen-active .course-detail-page,
.fullscreen-active .course-study-workspace {
  width: 100%;
  height: 100vh;
  min-height: 0;
}

.fullscreen-active .course-detail-page {
  display: block;
}

.fullscreen-active .course-study-workspace {
  display: block;
}

.fullscreen-active .video-study-card,
.fullscreen-active .note-card {
  height: 100vh;
  padding: 18px;
  border: none;
  border-radius: 0;
  box-shadow: none;
}

.fullscreen-active .note-header {
  height: 44px;
  margin-bottom: 12px;
}

.fullscreen-active .video-player-card,
.fullscreen-active .fake-video {
  height: 100%;
  min-height: 0;
}

.fullscreen-video .note-card,
.fullscreen-notes .video-study-card {
  display: none;
}

.fullscreen-notes .wysiwyg-note-editor {
  height: calc(100vh - 74px);
  min-height: 0;
}

.fullscreen-notes .wysiwyg-note-editor :deep(.tiptap) {
  min-height: 0;
  overflow: auto;
}

@media (max-width: 820px) {
  .course-study-active .content,
  .course-study-active.sidebar-collapsed .content {
    padding: 18px;
  }

  .course-detail-page {
    display: block;
    overflow: auto;
  }

  .course-study-workspace {
    height: auto;
    display: flex;
    flex-direction: column;
    gap: 14px;
    overflow: visible;
  }

  .lesson-panel {
    max-height: 320px;
  }

  .video-study-card {
    min-height: 360px;
  }

  .note-card {
    min-height: 420px;
  }

  .study-resize-handle {
    display: none;
  }

  .lesson-expand-button {
    position: static;
    align-self: flex-start;
  }

  .fake-video,
  .video-link-fallback {
    min-height: 280px;
  }
}
</style>
