# Agents.md

## Project Overview

This project is a Vue 3 + TypeScript + Vite single-page app for a personal learning workspace. The current UI is a course-management dashboard with:

- a top navigation bar, search box, and user area
- a left sidebar menu for course management, notes, AI summary, and settings
- a course list with progress cards
- a course-detail view with lessons, a mock video area, notes, and AI assistant actions
- note persistence through `localStorage`

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

## Development Notes

- Treat `src/App.vue` as the current source of truth for product behavior.
- The project currently uses hard-coded course and lesson data inside `App.vue`.
- Notes are saved per course and lesson using keys like:

```ts
learnflow_note_course_${courseId}_lesson_${lessonId}
```

- The app uses scoped CSS inside `App.vue` for most dashboard styling.
- `src/style.css` still contains a lot of Vite starter-page styling. Some of it affects the app globally, especially `#app`, `body`, heading styles, and CSS variables.
- Avoid editing `node_modules/`.
- Keep changes focused. There is not yet an established component architecture, so introduce new components only when they clearly reduce complexity.

## Known Current Issues

`npm run build` currently fails. Verified on 2026-05-12 with these TypeScript errors:

```text
src/App.vue(182,10): error TS6133: 'selectLesson' is declared but its value is never read.
src/App.vue(191,27): error TS2502: 'course' is referenced directly or indirectly in its own type annotation.
src/App.vue(310,19): error TS2349: This expression is not callable.
  Type '{ id: number; title: string; status: string; time: string; }' has no call signatures.
```

Likely fixes:

- Use `@click="selectLesson(lesson)"` instead of calling `selectedLesson(lesson)` in the template.
- Type `openCourseDetail` from the course array, for example `typeof courses[number]`, not `typeof course[number]`.
- After the template calls `selectLesson`, the unused-local error should go away.

The source text displayed in the terminal appears mojibake/garbled for Chinese and emoji strings. Before making large text edits, inspect the file carefully in an editor that preserves the intended encoding and avoid broad search-and-replace over user-facing copy.

## Suggested Workflow For Future Agents

1. Start by reading `package.json`, `src/App.vue`, `src/main.ts`, and `src/style.css`.
2. Run `npm run build` before and after code changes when possible.
3. If working on UI, run `npm run dev` and inspect the app in a browser.
4. Prefer extracting stable pieces from `App.vue` only when the feature work benefits from it.
5. Preserve the current product direction: a quiet, productivity-focused personal learning dashboard rather than a marketing page.

## Git State

This directory is currently not a git repository. `git status` reports:

```text
fatal: not a git repository (or any of the parent directories): .git
```

Do not assume branch, commit, or diff tooling is available unless git is initialized later.
