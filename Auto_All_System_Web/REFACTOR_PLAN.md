# 🚀 UI Refactoring Plan: Vue 3 + Tailwind + shadcn-vue

**Objective:** Modernize the entire application UI using Tailwind CSS and shadcn-vue components without altering business logic.

## 🔎 Project Reality Check (Align Plan With Repo)

- [x] **Frontend Root:** This repo's frontend lives under `frontend/`.
- [x] **Current UI Stack:** Element Plus has been fully removed (dependency + plugin wiring). A local compatibility layer now provides the legacy `el-*` tags using shadcn-vue primitives.
- [x] **Tailwind:** Already present/configured via `frontend/tailwind.config.js` and `frontend/postcss.config.cjs`.
- [x] **Global Styles Entry:** Currently imported from `frontend/src/styles/index.scss` (see `frontend/src/main.ts`).

## 🛠 Phase 1: Environment & Dependencies (Pre-requisites)
> *Action: User/AI must ensure these are installed before proceeding.*

- [x] **Install Core (run inside `frontend/`):** `npx shadcn-vue@latest init`
- [x] **Install Icons (run inside `frontend/`):** `npm install lucide-vue-next`
- [x] **Add Essential Components (run inside `frontend/`):**
    ```bash
    npx shadcn-vue@latest add button card input label form select table dropdown-menu dialog sheet avatar badge separator alert toast
    ```

## 🎨 Phase 2: Global Styles & Theming

- [x] **Typography:** Prefer keeping the existing system font stack initially (moved into `frontend/src/styles/index.scss`), then switch to Inter later if desired.
- [x] **Colors:** Align Tailwind + shadcn CSS variables (also bridged Element Plus CSS vars to these tokens) while preserving existing Element Plus pages during the transition.
- [x] **Reset:** Do NOT delete existing resets/Element deep overrides early. Move to cleanup only after the corresponding pages have been migrated.
- [x] **Where to edit:** Use `frontend/src/styles/index.scss` (imported by `frontend/src/main.ts`) for global styles.

## 🤝 Coexistence Rules (Element Plus + shadcn-vue)

- [x] **Element removed:** `frontend/src/main.ts` no longer uses ElementPlus; `element-plus` and `@element-plus/icons-vue` have been uninstalled.
- [x] **Legacy tag strategy:** Existing `el-*` tags remain, backed by local components under `frontend/src/components/element/` (built on shadcn-vue primitives). This keeps behavior stable while eliminating the external dependency.
- [x] **Icons strategy:** All Element icon imports replaced by `frontend/src/icons/index.ts` (lucide-vue-next).

## 🧩 Phase 3: Component Mapping Strategy

| Legacy/HTML/Element Plus | Target shadcn-vue | Note |
| :--- | :--- | :--- |
| `<div class="card">` / `el-card` | `<Card>`, `<CardHeader>`, `<CardContent>` | Wrap content properly; keep existing data/slots. |
| `<button>` / `el-button` | `<Button>` | Map variants: `primary` -> `default`, `danger` -> `destructive`. |
| `<input>` / `el-input` | `<Input>` | Preserve `v-model` + validation wiring. |
| `<select>` / `el-select` | `<Select>` | Preserve `v-model` and option lists. |
| `<table>` / `el-table` | `<Table>`... | For complex tables, keep logic; apply Tailwind layout first. |
| `el-dialog` | `<Dialog>` | Prefer `v-model:open` (verify actual shadcn-vue API). |
| `el-drawer` | `<Sheet>` | Mobile-first drawer behavior. |
| `el-dropdown` | `<DropdownMenu>` | Keep menu item actions unchanged. |
| `el-avatar` | `<Avatar>` | Map user initials/image. |
| Element icons | `lucide-vue-next` | Replace with closest semantic icon. |

## 📋 Phase 4: Refactoring Execution Queue

**Strict Rule:** Do NOT change `<script>` logic. Only refactor `<template>` and `<style>`.

### 4.1 Layouts (High Priority)

- [x] `frontend/src/App.vue` (Root layout structure + minimal global styles)
- [x] `frontend/src/layouts/MainLayout.vue` (Sidebar, Header, Main Content Area)
- [x] `frontend/src/layouts/AdminLayout.vue` (Admin layout)

### 4.2 Common UI Components (Medium Priority)

*Refactor these first so Views can reuse them.*

- [x] `frontend/src/components/*` (shared components)

### 4.3 Views / Pages (Low Priority - Batch Processing)

*Focus on visual structure: Grid layouts, Cards, Typography.*

- [x] `frontend/src/views/*` (batch by route priority)

## ✅ Definition of Done

1. No console errors regarding missing components.
2. Legacy Element Plus styles are only removed AFTER each affected screen has been migrated.
3. The UI is responsive (mobile-friendly).
4. All interactive elements (buttons, inputs) work as before.
5. No dependency on `element-plus` / `@element-plus/icons-vue`.

## 🧾 Progress Log

### 2026-01-31

- Build verification: `frontend/` runs `npm run build` successfully.
- Removed remaining `element-plus` import in request layer (now uses `@/lib/element`).
- API cleanup: removed `frontend/src/api/*.js` duplicates; keep `.ts` as single source of truth.
- Docs cleanup: removed `@element-plus/icons-vue` references; docs now import icons from `@/icons`.
- Global styles cleanup: removed App-scoped reset; consolidated app height + font stack into `frontend/src/styles/index.scss`.
- Layouts: `MainLayout` and `AdminLayout` now auto-collapse sidebar on small screens (Element Plus menu collapse + Tailwind layout wrappers).
- User password: backend now supports `POST /users/change_password/` (checks old password, sets new password).
  - Frontend: Profile page re-enabled self-service password change and forces re-login on success.
- Dev tooling: installed `@vue/language-server` (vue-language-server) so `lsp_diagnostics` works for `.vue`.
- Shared components: `frontend/src/components/BrowserSelector.vue` removed scoped SCSS and switched to Tailwind utility classes (kept Element Plus controls; no logic change).
  - Views (Phase 4.3 in progress):
    - `frontend/src/views/admin/AdminDashboard.vue` migrated to shadcn `Card` + Tailwind grid (replaced Element `el-row/el-col/el-card/el-timeline`).
    - Admin pages (layout layer migrated; Element table/form/dialog kept where needed):
      - `frontend/src/views/admin/UserManagement.vue` switched main container to shadcn `Card`.
      - `frontend/src/views/admin/TaskManagement.vue` replaced `el-card/el-row/el-col` layout with Tailwind grid + shadcn `Card`.
      - `frontend/src/views/admin/SystemSettings.vue` replaced `el-row/el-col/el-card` layout with Tailwind grid + shadcn `Card`.
      - `frontend/src/views/admin/DataAnalytics.vue` replaced `el-row/el-col/el-card` layout with Tailwind grid + shadcn `Card`.
      - `frontend/src/views/admin/ProxyManagement.vue` replaced container `el-card` with shadcn `Card` and removed color inline style.
      - `frontend/src/views/admin/PaymentConfigManagement.vue` replaced container `el-card` with shadcn `Card` and removed inline styles + scoped SCSS.
    - `frontend/src/views/zones/ZoneListView.vue` replaced Element `el-tag` + `el-empty` with shadcn `Badge` + Tailwind empty state.
    - User-side pages:
      - `frontend/src/views/dashboard/DashboardView.vue` swapped ad-hoc `bg-card` blocks for shadcn `Card` sections; removed empty scoped style.
      - `frontend/src/views/zones/ZoneDetailView.vue` replaced Element `el-card` wrappers with shadcn `Card` and replaced category `el-tag` with shadcn `Badge` (kept Element descriptions/page header).
  - Auth pages:
    - `frontend/src/views/auth/LoginView.vue` replaced `el-card` wrapper with shadcn `Card` + Tailwind layout; kept Element `el-form/el-input` validation.
    - `frontend/src/views/auth/RegisterView.vue` replaced `el-card` wrapper with shadcn `Card` + Tailwind layout; kept Element `el-form/el-input` validation.
  - `frontend/src/views/google/GoogleDashboard.vue` removed scoped SCSS + most inline styles; replaced Element layout (`el-row/el-col/el-card`) with Tailwind grid + shadcn `Card` for sections; kept Element table/timeline for now.
  - `frontend/src/views/google/SheerIDManage.vue` removed scoped SCSS + inline styles; replaced Element grid (`el-row/el-col`) with Tailwind grid and wrapped content in shadcn `Card`; kept Element input/table/dialog.
  - `frontend/src/views/google/AutoBindCard.vue` removed scoped SCSS + inline styles; replaced Element grid (`el-row/el-col`) with Tailwind grid and wrapped content in shadcn `Card`; kept Element input/table/dialog.
  - `frontend/src/views/google/AutoAllInOne.vue` removed scoped SCSS + inline styles; replaced Element layout (`el-row/el-col/el-card`) with Tailwind grid + shadcn `Card`; kept Element form/table/dialog logic.
  - `frontend/src/views/google/AccountManage.vue` removed scoped SCSS + inline styles; replaced Element `el-card/el-row/el-col` layout with Tailwind grid + shadcn `Card`; kept Element select/input/table/dialog.

- Admin (Google Business):
  - `frontend/src/views/admin/GoogleBusinessDashboard.vue` migrated to Tailwind grid + shadcn `Card` (kept charts + tables).
  - `frontend/src/views/admin/GoogleBusinessTaskDetail.vue` migrated to shadcn `Card` layout; removed scoped SCSS + inline styles.
  - `frontend/src/views/admin/GoogleBusinessTaskCreate.vue` migrated to shadcn `Card`; removed scoped SCSS; kept only minimal `:deep(...)` overrides for Element Radio/Transfer.
  - `frontend/src/views/admin/GoogleBusinessTaskList.vue`, `frontend/src/views/admin/RechargeCardManagement.vue`, `frontend/src/views/admin/CardManagement.vue` cleaned (removed empty scoped styles; aligned spacing).
  - `frontend/src/views/admin/GoogleBusinessCardManagement.vue` migrated to shadcn `Card` layout; removed scoped SCSS + inline styles.

- Admin (Integrations/Config):
  - `frontend/src/views/admin/EmailManagement.vue`, `frontend/src/views/admin/GeekezManagement.vue`, `frontend/src/views/admin/BitbrowserManagement.vue` migrated to shadcn `Card` layout; removed scoped SCSS + inline styles.

- Cleanup:
  - Removed empty `<style scoped>` blocks across remaining Views/Modules where Tailwind fully covers styling.

- Element removal:
  - `element-plus` and `@element-plus/icons-vue` uninstalled.
  - `frontend/src/main.ts` switched from `app.use(ElementPlus)` to `app.use(ElementCompat)`.
  - Added `frontend/src/components/element/` compatibility components to implement legacy `el-*` tags via shadcn-vue.
  - `ElMessage`/`ElMessageBox` migrated to `frontend/src/lib/element.ts` + `frontend/src/components/app/MessageBoxHost.vue` + shadcn toast.
