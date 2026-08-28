# Frontend scaffold and manual import screen

The frontend is a Vite/React/TypeScript shell. The Imports page calls the
manual backend endpoint with synthetic/already-read rows and renders import
counters and row errors. The Clients page lists persisted profiles, supports
name/email search, and opens a detail view with submission metadata, raw
answers, downloaded visual references, and a user-authored Signature Style
Report editor. The editor stores drafts through the manual report API; it does
not generate report text.

## Commands

    corepack enable
    pnpm install
    pnpm dev
    pnpm lint
    pnpm test
    pnpm build
