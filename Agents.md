# Agents.md

## Project Overview

This project is a Vue 3 + TypeScript + Vite single-page app for a personal learning workspace. The current UI is a quiet course-management and study dashboard with:

- a top navigation bar, search box, and user area
- a collapsible left sidebar for course management, notes, AI summary, and settings
- a course list with progress cards and course management actions
- add/edit/delete course dialogs with persisted course data
- a course-detail study view with lessons, video, notes, and AI assistant panels
- imported Bilibili/YouTube video links embedded per course and lesson when possible
- rich-text note editing through Tiptap, with Markdown import/export conversion
- per-course and per-lesson note/video persistence through `localStorage`
- configurable keyboard shortcuts for video/notes fullscreen study modes

Most application logic and UI currently live in one large Vue single-file component:

- `src/App.vue`

The app entry point is:

- `src/main.ts`

Global styles are in:

- `src/style.css`

Static assets are in:

- `public/`
- `src/assets/`

## Tech Stack

- Vue 3
- TypeScript
- Vite
- `vue-tsc` for type checking
- Tiptap (`@tiptap/vue-3`, `@tiptap/starter-kit`) for the note editor
- `marked` for Markdown-to-HTML conversion
- `turndown` for HTML-to-Markdown conversion
- No router, store, backend API, or test framework is configured yet

Package scripts:

```bash
npm run dev
npm run build
npm run preview
```

## Current Structure

```text
.
|-- index.html
|-- package.json
|-- package-lock.json
|-- vite.config.ts
|-- tsconfig.json
|-- tsconfig.app.json
|-- tsconfig.node.json
|-- public/
|   |-- favicon.svg
|   `-- icons.svg
`-- src/
    |-- main.ts
    |-- App.vue
    |-- style.css
    |-- components/
    |   `-- HelloWorld.vue
    `-- assets/
        |-- hero.png
        |-- vite.svg
        `-- vue.svg
```

`src/components/HelloWorld.vue` and several default Vite assets appear to be template leftovers unless they are reintroduced later.

## Application State And Persistence

- Courses are stored under `learnflow_courses`.
- Notes are saved per course and lesson using keys like:

```ts
learnflow_note_course_${courseId}_lesson_${lessonId}
```

- Video links are saved per course and lesson using keys like:

```ts
learnflow_video_course_${courseId}_lesson_${lessonId}
```

- Keyboard shortcuts are stored under `learnflow_shortcuts`.
- The app currently uses a fixed lesson list in `src/App.vue`; courses are user-created and persisted locally.
- Default note content exists for the first few lessons when there is no saved local note.

## Development Notes

- Treat `src/App.vue` as the current source of truth for product behavior.
- The app uses scoped CSS inside `App.vue` for most dashboard styling.
- `src/style.css` now contains the lean global reset and shared CSS variables for the full-screen app shell.
- Avoid editing `node_modules/`.
- Keep changes focused. There is not yet an established component architecture, so introduce new components only when they clearly reduce complexity.
- Preserve Chinese user-facing copy and emoji carefully. The app intentionally uses Chinese labels throughout the UI.
- For large text edits, inspect files with UTF-8 handling and avoid broad search-and-replace over user-facing copy.
- Course/video/note data is browser-local only; there is no backend synchronization.

## Current Verification

`npm run build` passes as of 2026-05-14:

```text
vue-tsc -b && vite build
```

The build produces assets in `dist/`. Treat `dist/` as generated output unless the project later documents a deployment workflow that requires committing it.

## Suggested Workflow For Future Agents

1. Start by reading `package.json`, `src/App.vue`, `src/main.ts`, and `src/style.css`.
2. Run `npm run build` before and after code changes when possible.
3. If working on UI, run `npm run dev` and inspect the app in a browser.
4. Prefer extracting stable pieces from `App.vue` only when feature work benefits from it.
5. Preserve the current product direction: a quiet, productivity-focused personal learning dashboard rather than a marketing page.
6. Be careful with `localStorage` key changes because they affect existing user data.

## Git State

This directory is now a git repository. Check the working tree before editing:

```bash
git status --short
```

At the time this document was updated, `src/App.vue` already had uncommitted changes. Do not revert or overwrite unrelated user changes.
