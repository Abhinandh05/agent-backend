# Frontend — AI Business OS

Detailed documentation for the Next.js UI at **`../afsuu_Frontend/`** (sibling of this backend repo).  
For the product overview, see [README.md](./README.md). For the API, see [BACKEND.md](./BACKEND.md).

> **Repo layout:** Backend and frontend are separate git repos under the same parent folder:
> ```text
> afsuu/
> ├── agent-backend/     ← you are here (API)
> └── afsuu_Frontend/    ← Next.js app documented below
> ```

This doc is written for a **brand-new developer**. Read it top to bottom the first time. Later, jump to a page or component section when you need details.

---

## Tech stack

| Item | Value |
|------|--------|
| Framework | **Next.js 16.2.9** (App Router) |
| UI library | **React 19.2.4** |
| Language | **JavaScript** (`.jsx`) — not TypeScript |
| Styling | **Tailwind CSS v4** (`@tailwindcss/postcss`) |
| Fonts | Geist / Geist Mono via `next/font/google` |
| Markdown rendering | `react-markdown` |
| Code highlighting | `highlight.js` + `rehype-highlight` |
| Path alias | `@/*` → project root (`jsconfig.json`) |
| Lint | ESLint 9 + `eslint-config-next` |
| Package name | `fronted` (typo in `package.json`) |

No shadcn/MUI/Radix, no Zustand/Redux, no React Query.

All UI pages that talk to the API are **`"use client"`** components. The root `app/layout.jsx` is a server layout (fonts + metadata only).

---

## How the frontend works (big picture)

### What the UI is for

The frontend is the **control panel** for AI Business OS. A signed-in user can:

- Open specialist agents (Research, Finance, Analytics, Coding, Email)
- Run the **Manager** agent (plans and orchestrates several specialists)
- Upload documents and ask RAG questions
- Browse **Task History** for past agent runs
- Log in / register (JWT stored in the browser)

The UI does **not** run LLMs, train models, or hold secret API keys. It only:

1. Collects user input (forms, file pickers)
2. Calls the FastAPI backend with a JWT
3. Shows loading, errors, and results (often as markdown)

### Request path (ASCII)

```text
  ┌─────────────┐     Next.js App Router      ┌──────────────────┐
  │   Browser   │ ──── pages + components ─── │  localStorage    │
  │  (user)     │                             │  key: "token"    │
  └──────┬──────┘                             └────────┬─────────┘
         │                                             │
         │  fetch(NEXT_PUBLIC_API_URL + path)          │
         │  Authorization: Bearer <JWT>                │
         ▼                                             │
  ┌────────────────────────────────────────────────────┘
  │
  ▼
  ┌─────────────────┐
  │  FastAPI backend│  (agents, auth, docs, tasks, ML)
  │  :8000          │
  └─────────────────┘
```

Simpler one-liner:

```text
User → Next.js page → read JWT from localStorage → HTTP to FastAPI → show result
```

### What happens on first visit (no token)

```text
1. Open http://localhost:3000
2. app/page.jsx runs checkAuth
3. No localStorage "token" → isLoggedIn stays false
4. User sees LandingPage (marketing hero + Sign In / Get Started)
5. User can go to /login or /register
6. Protected routes (/agents/*, /documents, /history) still load JS,
   but DashboardShell redirects to /login if there is no valid token
```

### What happens after login

```text
1. POST /api/v1/auth/login with email + password
2. Response includes access_token
3. localStorage.setItem("token", access_token)
4. Full page navigate to /
5. Home checks token + GET /api/v1/auth/me → dashboard view
6. Every protected page wraps content in DashboardShell
   (sidebar + another /auth/me check)
7. Agent / docs / history calls send Authorization: Bearer <token>
```

### What the UI never does

| Never does | Why |
|------------|-----|
| Store or send `GROQ_API_KEY` | Keys live only on the backend |
| Train or load `.pkl` models in the browser | ML runs on FastAPI |
| Call Groq / HuggingFace / Chroma directly | Backend owns those |
| Issue JWTs or hash passwords | Backend `/auth/*` |
| Send email itself | Backend `/agents/email/send` + SendGrid |
| Persist agent results in a frontend DB | Backend creates `Task` rows |

If you need a new capability, ask: **“Is this a UI form, or does it need a backend route?”** Almost always the heavy work is backend.

---

## Why we use this / why we do not use that

This section explains every major frontend choice in plain language. For each topic: what we picked, **why it is used here**, and **what we deliberately did not use** (and why).

### 1. Next.js App Router (not Create React App / Vite-only / Pages Router)

| | |
|--|--|
| **Used** | Next.js 16 with the **App Router** (`app/` folders) |
| **Not used** | Create React App, Vite+React as the only shell, Next.js Pages Router (`pages/`) |

**Why Next.js is used**

- File-based routes match how the product is organized: `/login`, `/agents/research`, `/documents`, `/history`.
- Built-in `next/font`, fast refresh, and a standard `npm run build` path for later deploy.
- Same React ecosystem the team already knows; pairs cleanly with a separate FastAPI backend.

**Why CRA / Vite-only are not used**

- CRA is deprecated and heavier for no benefit here.
- Vite alone is excellent for SPAs, but Next gives routing + conventions out of the box for a multi-page product dashboard.

**Why App Router (not Pages Router)**

- New Next.js projects default to `app/`; layouts and nested `agents/` routes fit App Router naturally.
- We are not maintaining a legacy `pages/` codebase.

---

### 2. JavaScript `.jsx` (not TypeScript)

| | |
|--|--|
| **Used** | JavaScript with `.jsx` files + `jsconfig.json` |
| **Not used** | TypeScript (`*.tsx`, strict types) |

**Why JavaScript is used**

- Faster day-by-day learning and prototyping against a changing API.
- Fewer tooling steps for a small UI (login, chat, documents, history).

**Why TypeScript is not used (yet)**

- Not required for the local demo OS.
- Tradeoff: less compile-time safety when API shapes change — acceptable for this stage; a later migration is possible.

---

### 3. Tailwind CSS v4 (not MUI / Bootstrap / CSS Modules-only)

| | |
|--|--|
| **Used** | Tailwind CSS v4 utility classes in components |
| **Not used** | Material UI, Chakra, Bootstrap, styled-components as the system |

**Why Tailwind is used**

- Rapid layout for dashboard shell, forms, and agent pages without inventing a design system.
- Styles live next to markup — easy to tweak spacing/colors while building features.

**Why component libraries (MUI, etc.) are not used**

- Extra bundle size and opinionated components for a custom dark dashboard look.
- No need for a full Design System dependency for this project size.
- Inline SVG icons in `DashboardShell` are used instead of an icon package (fewer deps).

---

### 4. Separate Next.js app (not server-rendered pages from FastAPI)

| | |
|--|--|
| **Used** | Frontend repo `afsuu_Frontend` talking to backend over HTTP |
| **Not used** | Jinja/HTML templates from FastAPI, embedding the UI inside the API repo |

**Why a separate frontend is used**

- Clear split: FastAPI owns agents/ML/DB; Next owns UX.
- Frontend can be deployed or developed independently (`npm run dev` vs `uvicorn`).
- Matches how real products ship (API + SPA/SSR client).

**Why not serving HTML from FastAPI**

- Agent UIs need rich client state (loading, markdown, editable email fields). React fits better than server templates for that.
- CORS + `NEXT_PUBLIC_API_URL` keep the contract explicit.

---

### 5. `localStorage` JWT (not cookies / NextAuth / Auth.js)

| | |
|--|--|
| **Used** | Store `access_token` in `localStorage` under key `"token"` |
| **Not used** | httpOnly cookies, NextAuth/Auth.js, refresh-token rotation |

**Why `localStorage` + Bearer header is used**

- Matches the backend’s **stateless JWT** design (see [BACKEND.md](./BACKEND.md)).
- Simple for a learning SPA: login → save token → send `Authorization: Bearer …` on every API call.
- Logout = delete the key and redirect.

**Why httpOnly cookies / NextAuth are not used**

- Would require backend cookie/CSRF setup and more frontend middleware.
- NextAuth is great for OAuth providers; this app only needs email/password against our own `/auth/login`.
- Tradeoff: XSS can steal `localStorage` tokens — acceptable for local demo, not hardened production.

**Why there is no refresh token flow**

- Backend issues one access token with expiry (`ACCESS_TOKEN_EXPIRE_MINUTES`). When it expires, UI gets `401` and sends the user to `/login`.

---

### 6. Client-side auth gate in `DashboardShell` (not `middleware.ts`)

| | |
|--|--|
| **Used** | Client check: token + `GET /api/v1/auth/me` inside `DashboardShell` |
| **Not used** | Next.js `middleware.ts` edge protection, server session |

**Why client-side gating is used**

- Backend is the real authority; the UI only needs to hide pages and redirect when the token is missing/invalid.
- No shared cookie session to inspect at the Edge.

**Why `middleware.ts` is not used**

- Without cookies, middleware cannot reliably know if a JWT is valid without calling the API on every navigation (extra complexity).
- Tradeoff: unauthenticated users can briefly download page JS for `/agents/*` before redirect — fine for a private local app.

**Why login/register are outside the shell**

- You must be able to open `/login` and `/register` without already being authenticated.

---

### 7. Local React state only (not Zustand / Redux / React Query)

| | |
|--|--|
| **Used** | `useState` / `useEffect` / `useCallback` per page |
| **Not used** | Zustand, Redux Toolkit, Jotai, React Query / TanStack Query, global Auth Context |

**Why local state is used**

- Most screens are independent: one agent request → one result. No complex shared client cache required.
- Auth is “token in `localStorage` + fetch `/me`” — no need for a global store yet.

**Why Redux / Zustand are not used**

- Overhead and boilerplate for a small number of pages.
- Note: frontend `AGENTS.md` may mention Zustand — that file is **aspirational and does not match** this codebase. Ignore it.

**Why React Query is not used**

- Nice for caching lists/refetch, but documents/history can load with a simple `useEffect` + `fetch` for now.
- Agent calls are long-running POSTs (not classic CRUD cache).

---

### 8. Shared `AgentChat` (not a different chat UI per agent)

| | |
|--|--|
| **Used** | One `AgentChat` component for research / finance / analytics / coding |
| **Not used** | Four near-duplicate chat pages with different markup |

**Why `AgentChat` is used**

- Same UX: prompt → loading → markdown answer → errors / 401 handling.
- Only the endpoint and field name change (`topic` vs `request`).
- Coding page reuses it with syntax highlighting via `rehype-highlight`.

**Why Email and Manager do not use plain `AgentChat`**

| Page | Custom UI because… |
|------|--------------------|
| **Email** | Needs editable To / Subject / Body, sentiment badge/warning, and a separate **Send** action — not a single “result string.” |
| **Manager** | Needs to show **plan**, **step_results**, and **final_response** from Approach B — a flat markdown box is not enough. |

**Why PPT has no page**

- Backend PPT agent is not built. A nav/filter label may appear elsewhere, but there is **no** `/agents/ppt` route on purpose.

---

### 9. `react-markdown` + highlight.js (not raw `dangerouslySetInnerHTML` / plain `<pre>`)

| | |
|--|--|
| **Used** | `react-markdown` for agent answers; `rehype-highlight` + highlight.js for code |
| **Not used** | Dumping HTML from the LLM with `dangerouslySetInnerHTML`, or monospace-only text |

**Why markdown rendering is used**

- Agents return structured text (headings, lists, code fences). Markdown makes that readable in the dashboard.
- Safer than injecting arbitrary HTML from the model.

**Why highlighting is used on Coding**

- Users need to read generated Python clearly; highlight.js makes fences usable.

---

### 10. `lib/api.js` `runAgent` helper (not axios / not OpenAPI client)

| | |
|--|--|
| **Used** | Thin `fetch` wrapper `runAgent` + `ApiError` |
| **Not used** | Axios, RTK Query, generated OpenAPI SDK |

**Why `runAgent` is used**

- Backend agents/ML/docs often return `{ success, data, message, error }`. One helper unwraps `data` and maps failures.
- Central place for Bearer header and 401 handling.

**Why axios is not used**

- Browser `fetch` is enough; one less dependency.

**Why upload/download sometimes skip `runAgent`**

- Multipart `FormData` (document upload) and binary file download need raw `fetch` / blob handling — JSON helpers do not fit cleanly.

**Why no Next.js rewrite proxy**

- `next.config.mjs` is empty; the browser calls `NEXT_PUBLIC_API_URL` directly.
- Backend CORS must allow `http://localhost:3000`. A proxy would hide CORS but add config we did not need for local dev.

---

### 11. Chat / agent pages first (not dedicated ML forms)

| | |
|--|--|
| **Used** | Agent chat UIs that call `/api/v1/agents/...` |
| **Not used (yet)** | Forms that POST directly to `/api/v1/ml/churn`, `/credit-risk`, etc. |

**Why agent chat is used first**

- Matches the product story: talk to a specialist agent; the agent calls tools (including ML) when needed.
- One UI pattern ships many capabilities quickly.

**Why direct ML forms are not built yet**

- Backend `/ml/*` routes already exist for curl/Swagger and future widgets.
- Analytics page text even notes widgets “can be added” — intentional gap, not a missing API.

**When you would use `/ml/*` from the UI later**

- Faster scoring without LLM latency/cost; power-user dashboards.

---

### 12. `/history` for tasks (not a `/tasks` CRUD page / not Settings)

| | |
|--|--|
| **Used** | Task **History** at `/history` (list, filter, detail, delete, download) |
| **Not used** | Full Settings page; creating tasks manually as the main UX |

**Why history is used**

- Every agent run already creates a `Task` row on the backend. The UI’s job is to **review** past runs, not to be the primary “create task” form (agents create tasks when you submit a prompt).

**Why Settings is in the nav but not implemented**

- Placeholder for future profile/API-key UI. It has **no `href`** so it renders as a non-navigating button — better than a broken link to a 404, but still incomplete.

**Why dashboard stat cards are hardcoded**

- Quick visual for the landing dashboard layout. **Recent tasks** are live from the API; the big numbers (“12”, “1,432”, …) are placeholders until real metrics exist.

---

### 13. Register → login (not auto-login after register)

| | |
|--|--|
| **Used** | Register succeeds → redirect to `/login` |
| **Not used** | Immediately store token and enter the app after register |

**Why**

- Keeps a simple, explicit “create account, then sign in” flow.
- Avoids special-casing register responses that might not return a token the same way as login (backend register returns `UserResponse`, login returns `TokenResponse`).

---

### 14. One env var for the API (not baking `localhost` into every file)

| | |
|--|--|
| **Used** | `NEXT_PUBLIC_API_URL` (see `.env.local.example`) |
| **Not used** | Hardcoded production URLs in components (except fallbacks) |

**Why `NEXT_PUBLIC_*`**

- Next.js only exposes env vars to the browser if they are prefixed with `NEXT_PUBLIC_`.
- One change points the UI at another backend host.

**Why fallback exists in `lib/api.js`**

- Local default `http://localhost:8000` if env is missing — convenient for demos.

**Caveat (TODO)**

- Some pages read `process.env.NEXT_PUBLIC_API_URL` **without** the fallback. Always set `.env.local` so login/shell/home do not call `undefined/api/...`.

---

### 15. What the frontend does **not** own

These belong to the **backend** (by design). The UI only triggers them:

| Capability | Where it lives | Frontend role |
|------------|----------------|---------------|
| LLM agents, Groq, CrewAI | Backend | Send prompt, show result |
| Training / `.pkl` ML | Backend `ml/` | Optional later forms; today via agent chat |
| Chroma / embeddings | Backend | Upload + ask on `/documents` |
| Password hashing / JWT issue | Backend | Store and attach token only |
| SendGrid | Backend | Call `/agents/email/send` after user edits draft |

**Why the frontend does not train models or call Groq directly**

- Keeps API keys (`GROQ_API_KEY`, `SECRET_KEY`) off the browser.
- One security boundary: the JWT user can only do what FastAPI allows.

---

## Folder and file structure

```text
afsuu_Frontend/
├── app/
│   ├── layout.jsx              # Root layout, fonts, metadata
│   ├── globals.css             # Tailwind + CSS variables
│   ├── page.jsx                # Landing (logged out) OR dashboard (logged in)
│   ├── login/page.jsx
│   ├── register/page.jsx
│   ├── documents/page.jsx      # Upload + RAG Q&A
│   ├── history/page.jsx        # Task history (list / detail / download)
│   └── agents/
│       ├── research/page.jsx
│       ├── finance/page.jsx
│       ├── analytics/page.jsx
│       ├── coding/page.jsx
│       ├── email/page.jsx      # Custom draft + send UI
│       └── manager/page.jsx    # Plan + step results UI
│
├── components/
│   ├── DashboardShell.jsx      # Auth gate, sidebar, top bar
│   └── AgentChat.jsx           # Shared agent form + markdown result
│
├── lib/
│   ├── api.js                  # API_BASE, runAgent, getToken, ApiError
│   └── time.js                 # Relative time formatting
│
├── public/                     # Static images / SVGs
├── .env.local.example
├── next.config.mjs             # Empty defaults
├── package.json
└── README.md                   # Still mostly create-next-app boilerplate
```

### Every important file (purpose / opens when / depends on)

#### `app/` — routes

| File | Purpose | Opens when | Depends on |
|------|---------|------------|------------|
| `app/layout.jsx` | Root HTML shell; loads Geist fonts; sets page metadata | Every route | `globals.css`, `next/font` |
| `app/globals.css` | Tailwind import + basic CSS variables | Every route (via layout) | Tailwind v4 |
| `app/page.jsx` | Dual home: marketing landing **or** logged-in dashboard | `/` | `DashboardShell`, `lib/api`, `lib/time`, `public/hero-image.png`, `public/robot-banner.png` |
| `app/login/page.jsx` | Email/password sign-in | `/login` | Raw `fetch` + `NEXT_PUBLIC_API_URL` (no shell) |
| `app/register/page.jsx` | Create account, then redirect to login | `/register` | Raw `fetch` + `NEXT_PUBLIC_API_URL` (no shell) |
| `app/agents/research/page.jsx` | Research Agent screen | `/agents/research` | `DashboardShell`, `AgentChat` |
| `app/agents/finance/page.jsx` | Finance Agent screen | `/agents/finance` | `DashboardShell`, `AgentChat` |
| `app/agents/analytics/page.jsx` | Analytics Agent screen | `/agents/analytics` | `DashboardShell`, `AgentChat` |
| `app/agents/coding/page.jsx` | Coding Agent screen (`maxChars=2000`) | `/agents/coding` | `DashboardShell`, `AgentChat` |
| `app/agents/email/page.jsx` | Draft → edit → sentiment → send | `/agents/email` | `DashboardShell`, `lib/api` |
| `app/agents/manager/page.jsx` | Manager plan / steps / final answer | `/agents/manager` | `DashboardShell`, `lib/api`, `react-markdown` |
| `app/documents/page.jsx` | Upload docs, list status, RAG ask | `/documents` | `DashboardShell`, `lib/api` (`runAgent` + raw `FormData` fetch) |
| `app/history/page.jsx` | Task list, filters, detail drawer, delete, download | `/history` | `DashboardShell`, `lib/api`, `lib/time` |

There is **no** `app/agents/ppt/page.jsx` and **no** `app/settings/page.jsx`.

#### `components/`

| File | Purpose | Opens when | Depends on |
|------|---------|------------|------------|
| `components/DashboardShell.jsx` | Auth gate + sidebar + top bar + logout | Every protected page that wraps children in it | `next/navigation`, raw `fetch` for `/auth/me` |
| `components/AgentChat.jsx` | Shared prompt form + loading + markdown result | Research / Finance / Analytics / Coding pages | `lib/api`, `react-markdown`, `rehype-highlight` |

#### `lib/`

| File | Purpose | Opens when | Depends on |
|------|---------|------------|------------|
| `lib/api.js` | `API_BASE`, `runAgent`, `getToken`, `ApiError` | Imported by chat/docs/history/home helpers | Browser `fetch`, `localStorage` |
| `lib/time.js` | `formatRelativeTime(...)` (“5 min ago”) | Home recent tasks + History table | None |

#### Root / config / static

| File | Purpose |
|------|---------|
| `public/hero-image.png` | Landing page hero image |
| `public/robot-banner.png` | Dashboard welcome banner image |
| `public/*.svg` | Default Next.js scaffold SVGs (mostly unused by product pages) |
| `.env.local.example` | Documents `NEXT_PUBLIC_API_URL` |
| `.env.local` | Your local env (gitignored) — **create this** |
| `next.config.mjs` | Empty defaults — **no** rewrites/proxy |
| `jsconfig.json` | `@/*` path alias |
| `package.json` | Scripts + deps; name `"fronted"` is a typo |
| `README.md` | Mostly create-next-app boilerplate — prefer this doc |

---

## Install and run locally

### Prerequisites

1. **Node.js** — a current LTS is fine (**TODO: confirm** exact minimum; Next 16 typically wants a recent Node).
2. **npm** (comes with Node).
3. **Backend already running** at the URL you put in `.env.local` (default `http://localhost:8000`). See [BACKEND.md](./BACKEND.md).
4. Frontend folder at `../afsuu_Frontend/` relative to this repo.

### Steps (with “what this does”)

```bash
# 1) Enter the frontend repo
cd ../afsuu_Frontend
# What this does: leave agent-backend; work in the Next.js project.

# 2) Install dependencies
npm install
# What this does: installs next, react, react-markdown, highlight.js, tailwind, eslint, etc.
# Creates / updates node_modules and uses package-lock.json.

# 3) Create env file
cp .env.local.example .env.local
# What this does: copies the template so Next can read NEXT_PUBLIC_API_URL.

# 4) Edit .env.local if needed
# NEXT_PUBLIC_API_URL=http://localhost:8000
# What this does: tells the browser where FastAPI lives (no trailing slash).

# 5) Start the Next.js dev server
npm run dev
# What this does: runs `next dev` with hot reload. Default URL: http://localhost:3000
```

Open **http://localhost:3000** in your browser.

### npm scripts

| Script | Command | What it does |
|--------|---------|--------------|
| Dev | `npm run dev` → `next dev` | Local development with fast refresh |
| Build | `npm run build` → `next build` | Production compile into `.next/` |
| Production serve | `npm run start` → `next start` | Serve the built app (after build) |
| Lint | `npm run lint` → `eslint` | Lint JS/JSX with Next’s ESLint config |

### Common errors (and what to check)

| Symptom | Likely cause | What to do |
|---------|--------------|------------|
| Login fails / Network error / “Unable to reach the server” | Backend down, or wrong port | Start FastAPI; confirm URL in browser can open `http://localhost:8000/docs` |
| Browser console: CORS error | Backend CORS does not allow `http://localhost:3000` | Fix backend CORS allowlist (see BACKEND.md). Frontend has **no** proxy. |
| Requests go to `undefined/api/v1/...` | `.env.local` missing; page used `process.env.NEXT_PUBLIC_API_URL` without fallback | Create `.env.local`, restart `npm run dev` |
| Login works in one tab but agents fail | Stale env / wrong API host | Hard refresh; confirm `NEXT_PUBLIC_API_URL` |
| 401 right after login | Bad token / clock / wrong SECRET on backend | Re-login; check backend JWT settings |
| Agent spins a long time then errors | Backend agent timeout / Groq / tool failure | Check backend logs; UI only shows the error message |
| Document upload fails | File type/size, or multipart handling | Use allowed types (pdf/docx/xlsx/csv/txt), max ~10MB as UI text says |
| Images missing on landing/dashboard | Missing `public/hero-image.png` or `robot-banner.png` | They should exist in `public/` — restore if deleted |

**Remember:** changing `.env.local` requires **restarting** `npm run dev`. `NEXT_PUBLIC_*` values are baked into the client bundle at start/build time.

---

## Environment variables

**File:** `.env.local` (copy from `.env.local.example`)

| Variable | Required? | Purpose |
|----------|-----------|---------|
| `NEXT_PUBLIC_API_URL` | **Yes in practice** | Backend base URL, **no trailing slash**. Example: `http://localhost:8000` |

No other `NEXT_PUBLIC_*` variables are used today.

### What `NEXT_PUBLIC_API_URL` means

- Prefix `NEXT_PUBLIC_` = Next.js exposes this value to **browser** JavaScript.
- It is the **origin only**: scheme + host + port. Paths like `/api/v1/...` are appended in code.
- Correct: `http://localhost:8000`
- Wrong: `http://localhost:8000/` (trailing slash can create `//api/...`)
- Wrong: `http://localhost:8000/api/v1` (paths already include `/api/v1/...`)

### Fallback caveat (important)

In `lib/api.js`:

```js
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
```

So **`runAgent` / `API_BASE` / `getToken` callers** still work if env is missing (local default).

But these places read the env **directly** with **no** fallback:

- `app/login/page.jsx`
- `app/register/page.jsx`
- `app/page.jsx` (`/auth/me` check)
- `components/DashboardShell.jsx` (`/auth/me` check)

If `.env.local` is missing, those become `undefined/api/v1/...` and auth breaks even though agent helpers might still hit localhost.

**Always set `.env.local`.** Then restart the dev server.

`next.config.mjs` does **not** add rewrites or an API proxy. The browser talks to FastAPI directly → CORS must allow the frontend origin.

---

## Pages / routes (in depth)

Quick map:

| Route | File | Protected? |
|-------|------|------------|
| `/` | `app/page.jsx` | Dual: public landing OR dashboard |
| `/login` | `app/login/page.jsx` | Public |
| `/register` | `app/register/page.jsx` | Public |
| `/agents/research` | `app/agents/research/page.jsx` | Yes (`DashboardShell`) |
| `/agents/finance` | `app/agents/finance/page.jsx` | Yes |
| `/agents/analytics` | `app/agents/analytics/page.jsx` | Yes |
| `/agents/coding` | `app/agents/coding/page.jsx` | Yes |
| `/agents/email` | `app/agents/email/page.jsx` | Yes |
| `/agents/manager` | `app/agents/manager/page.jsx` | Yes |
| `/documents` | `app/documents/page.jsx` | Yes |
| `/history` | `app/history/page.jsx` | Yes |

### Missing / incomplete UI

| Item | Status |
|------|--------|
| Settings | Nav label exists; **no `href` and no page** |
| PPT agent page | Filter label exists on History; **no route** (backend PPT agent not built) |
| Dedicated ML forms | Backend `/api/v1/ml/*` ready; **no dedicated frontend forms** |
| Dashboard stat cards | Hardcoded numbers (“12”, “1,432”, etc.); recent tasks are live |

---

### `/` — Home (`app/page.jsx`)

**Why this page exists**

One URL for newcomers (marketing) and returning users (dashboard). Avoids a separate `/dashboard` route.

**What the user sees**

1. **While checking auth:** centered spinner.
2. **Not logged in → `LandingPage`:** brand “AI Business OS”, hero copy, CTAs to Register / Login, `hero-image.png`.
3. **Logged in → dashboard inside `DashboardShell`:** welcome banner (`robot-banner.png`), **hardcoded** stat cards, **live** Recent Activity (last 5 tasks), Quick Actions links.

**Buttons / links**

| Control | Action |
|---------|--------|
| Landing “Sign In” / “Sign In to Dashboard” | Navigate to `/login` |
| Landing “Get Started” / “Deploy Your Agents Now” | Navigate to `/register` |
| “View All” on Recent Activity | `/history` |
| Quick Action cards | Links to agents, `/documents`, `/history` |
| Recent task row | Links to `/history` (does not deep-link a task id) |

**API endpoints**

| When | Method | Path |
|------|--------|------|
| Mount auth check | `GET` | `/api/v1/auth/me` (raw `fetch`, not `runAgent`) |
| Dashboard recent tasks | `GET` | `/api/v1/tasks?limit=5` via `runAgent` |

**Important React state**

- `isLoggedIn`, `loading`, `user` on `Home`
- Inside `DashboardContent`: `recentTasks`, `recentLoading`

**Error / loading / 401**

- Auth failure or network error on `/me`: token cleared only when response is not ok; network errors are logged and user may still see landing.
- Recent tasks failure: empty list + `console.error` (no big red banner).
- When logged in, `DashboardShell` also checks `/me` again (double check).

---

### `/login` — Sign in (`app/login/page.jsx`)

**Why this page exists**

Obtain a JWT and enter the app. Not wrapped in `DashboardShell` so it works while logged out.

**What the user sees**

Centered form: email, password, “Sign in”, link to register. Optional red error text.

**What the form does**

1. `POST` login with `{ email, password }`
2. On success: `localStorage.setItem("token", data.access_token)`
3. `window.location.href = "/"` (full reload — not only `router.push`)

**API**

- `POST /api/v1/auth/login` (raw `fetch`)
- Expects JSON with `access_token` (**TODO: confirm** exact backend field names match; UI uses `data.access_token`)

**State:** `email`, `password`, `error`, `loading`

**Errors**

- Non-OK response → “Invalid credentials”
- Network / other → generic message
- No special CORS message in UI — browser console shows CORS failures

---

### `/register` — Create account (`app/register/page.jsx`)

**Why this page exists**

Create a user row on the backend. Does **not** auto-login (see Why §13).

**What the user sees**

Form: first name, second name, email, password. Link to login. Green success text before redirect.

**What the form does**

1. `POST /api/v1/auth/register` with `{ name, second_name, email, password }`
2. On success: show “Registration successful…”, wait 2 seconds, `window.location.href = "/login"`
3. Does **not** store a token

**API:** `POST /api/v1/auth/register` (raw `fetch`)

**State:** `name`, `secondName`, `email`, `password`, `error`, `success`, `loading`

**Errors:** uses `errorData.detail` when present, else “Failed to register”.

---

### `/agents/research` — Research Agent

**Why:** Talk to the research specialist (web/business topic summaries via backend).

**What user sees:** Title, short description, shared `AgentChat` UI.

**`AgentChat` props**

| Prop | Value |
|------|--------|
| `agentName` | `"Research"` |
| `endpoint` | `"/api/v1/agents/research"` |
| `payloadKey` | `"topic"` |
| `inputLabel` | `"Topic"` |
| `placeholder` | example topic string |
| `maxChars` | default `500` |

**API:** `POST /api/v1/agents/research` with `{ topic: "..." }` via `runAgent`  
**Result field shown:** `data.result` as markdown

**401:** `AgentChat` clears token and redirects to `/login`.

---

### `/agents/finance` — Finance Agent

**Why:** Financial analysis / credit-risk style requests through the finance agent (ML tools on backend).

**`AgentChat` props:** `agentName="Finance"`, `endpoint="/api/v1/agents/finance"`, `payloadKey="request"`, `inputLabel="Request"`, default `maxChars=500`.

**API:** `POST /api/v1/agents/finance` with `{ request }` → show `data.result`.

---

### `/agents/analytics` — Analytics Agent

**Why:** Churn / forecast / segmentation style questions via analytics agent.

**Same pattern as Finance** with endpoint `/api/v1/agents/analytics`.

**Extra UI note** on the page: standalone widgets for `/api/v1/ml/churn`, `/sales-forecast`, `/customer-segment` are **not built yet** — intentional gap.

---

### `/agents/coding` — Coding Agent

**Why:** Ask for Python write/review/debug; backend sandbox executes code safely-ish for demos.

**Difference:** `maxChars={2000}` (longer prompts/snippets). Same `AgentChat` markdown + highlight.js path.

**API:** `POST /api/v1/agents/coding` with `{ request }`.

---

### `/agents/email` — Email Agent (custom page)

**Why this page exists**

Needs a **draft → edit → optional send** flow, not a single markdown string. Sentiment is advisory and never blocks Send.

**What the user sees**

1. Brief textarea (“What should the email say?”) + **Draft email**
2. After draft: tone badge or amber `tone_warning`, editable **To / Subject / Body**, **Send** button
3. Success / error banners

**Flow (ASCII)**

```text
  brief ──POST /agents/email──► subject, body, sentiment
                                      │
                                      ▼
                         user edits To / Subject / Body
                                      │
                         POST /agents/email/send
                                      │
                                      ▼
                              “Email sent to …”
```

**Buttons**

| Button | Calls | Body |
|--------|-------|------|
| Draft email | `POST /api/v1/agents/email` | `{ request: brief }` |
| Send | `POST /api/v1/agents/email/send` | `{ to, subject, body }` |

**Important state:** `brief`, `to`, `subject`, `body`, `sentiment`, `hasDraft`, `loading`, `sending`, `error`, `sendMessage`

**Loading / errors / 401**

- Drafting/sending disable their buttons and show “Drafting…” / “Sending…”
- `ApiError` with `code === "unauthorized"` → clear token → `/login`
- Send requires backend `SENDGRID_API_KEY` / `SENDGRID_FROM_EMAIL` (noted in UI helper text)

**Sentiment display**

- If `sentiment.tone_warning` → amber warning box
- Else badge with `label`, optional confidence %, optional “checked first portion only” if `sentiment.truncated`

---

### `/agents/manager` — Manager Agent (custom page)

**Why this page exists**

Flagship multi-agent orchestration. Must show **plan**, **step_results**, and **final_response**, not one flat `result` string.

**What the user sees**

- Long request textarea (max 8000)
- Loading: “Orchestrating specialists…”
- **Final response** (markdown) + optional Task `#id`
- **Plan** ordered list (`agent` + `subtask`)
- **Step results** accordion (status colors: completed / failed / skipped)

**API:** `POST /api/v1/agents/manager` with `{ request }`

Expected `data` fields used by UI:

- `plan` — array of `{ agent, subtask }`
- `step_results` — array of `{ agent, status, subtask, output }`
- `final_response` — markdown string
- `task_id` — optional number

**State:** `request`, `loading`, `error`, `plan`, `stepResults`, `finalResponse`, `taskId`, `openSteps`

**401:** clear token → `/login`.  
**Note:** PPT may appear in label maps / filters, but Manager cannot successfully run a real PPT specialist if the backend agent is missing (**TODO: confirm** backend skip behavior).

---

### `/documents` — Documents & RAG

**Why:** Upload user files, wait for indexing, ask grounded questions with sources.

**What the user sees**

1. Upload input (`.pdf,.docx,.xlsx,.csv,.txt`, max 10MB in UI copy)
2. Document list with status badges + chunk counts + **Refresh**
3. Ask form → Answer (markdown) + Sources list

**Status badges:** `uploaded` | `processing` | `indexed` | `failed`

**API**

| Action | How | Path |
|--------|-----|------|
| List | `runAgent` GET | `/api/v1/documents` |
| Upload | raw `fetch` + `FormData` | `POST /api/v1/documents/upload` |
| Ask | `runAgent` POST | `/api/v1/documents/query` `{ question }` |

**Poll / refresh?**

- After upload: `loadDocs()` immediately, then **`setTimeout(() => loadDocs(), 4000)`** once (one delayed refresh — not a continuous poll loop).
- Manual **Refresh** button calls `loadDocs()` again.

**State:** `docs`, `listError`, `uploading`, `uploadMsg`, `question`, `asking`, `answer`, `sources`, `queryError`

**401:** `authRedirect()` clears token → `/login`.

---

### `/history` — Task History

**Why:** Review past agent runs (backend already creates tasks). Filter, open detail, delete, download file if present.

**What the user sees**

- Filters: agent type + status
- Table: agent badge, prompt, status, relative time; “file” tag if `has_file`
- Load more (pages of 20)
- Right-side detail drawer: prompt, markdown result, optional `plan_details` JSON, Download / Delete / Close

**Filters**

- Agents: All, research, finance, analytics, coding, email, **ppt** (label only — agent not built), manager
- Statuses: All, pending, running, completed, failed

**API**

| Action | Method | Path |
|--------|--------|------|
| List | GET | `/api/v1/tasks?limit=20&offset=…&agent_type=…&status=…` |
| Detail | GET | `/api/v1/tasks/{id}` |
| Delete | DELETE | `/api/v1/tasks/{id}` |
| Download | GET (raw blob) | `/api/v1/tasks/{id}/download` |

**State (high level):** `agentType`, `status`, `tasks`, `totalCount`, `offset`, list loading flags, `selectedId`, `detail`, detail loading/error, `deleting`

**Delete:** `window.confirm` then DELETE; refreshes list from offset 0.  
**Download:** blob + filename from `Content-Disposition` when possible.  
**Changing filters:** `loadTasks` dependency reloads from the start.

---

## Key components

*(Rationale: [§8 AgentChat vs custom pages](#8-shared-agentchat-not-a-different-chat-ui-per-agent), [§6 auth gate](#6-client-side-auth-gate-in-dashboardshell-not-middlewarets).)*

### `DashboardShell` (`components/DashboardShell.jsx`)

**Role:** Shared chrome for every protected screen: auth gate, sidebar, top bar, logout, main content area.

**Props**

| Prop | Default | Meaning |
|------|---------|---------|
| `children` | — | Page content |
| `contentClassName` | `"p-6 lg:p-8 overflow-y-auto"` | Classes on `<main>` |

**Nav items (`NAV_ITEMS`)**

| Label | href | Notes |
|-------|------|-------|
| Dashboard | `/` | Active only when pathname is exactly `/` |
| Manager Agent | `/agents/manager` | |
| Research Agent | `/agents/research` | |
| Finance Agent | `/agents/finance` | |
| Analytics Agent | `/agents/analytics` | |
| Coding Agent | `/agents/coding` | |
| Email Agent | `/agents/email` | |
| Documents | `/documents` | |
| Task History | `/history` | |
| Settings | *(none)* | Renders as a **`<button>`** — dead / no navigation |

Icons are inline SVGs (`NavIcon`), not an icon library.

**Auth check sequence**

```text
mount DashboardShell
  → localStorage.getItem("token")
  → if missing: router.replace("/login")  (spinner may stay; loading never cleared)
  → else GET `${NEXT_PUBLIC_API_URL}/api/v1/auth/me` with Bearer token
  → if ok: setUser(json), setLoading(false), render shell
  → if not ok: remove token, replace /login
  → if network error: console.error, replace /login
```

While `loading || !user`, user only sees a full-screen spinner.

**Top bar:** avatar initial from `user.name`, full `user.name` + `user.second_name`, Logout button (`removeItem("token")` → `/login`).

**Sidebar footer:** decorative “System Online” card (not a live health API).

**Not used on:** `/login`, `/register`. Used on agents, documents, history, and the logged-in home dashboard.

---

### `AgentChat` (`components/AgentChat.jsx`)

**Role:** One reusable “prompt → wait → markdown result” UI for Research / Finance / Analytics / Coding.

**Props**

| Prop | Default | Meaning |
|------|---------|---------|
| `agentName` | required | Button label: `Run {agentName}` |
| `endpoint` | required | e.g. `/api/v1/agents/research` |
| `placeholder` | `"Enter your topic or task…"` | Textarea placeholder |
| `inputLabel` | `"Topic"` | Label above textarea |
| `payloadKey` | `"topic"` | JSON field name (`topic` or `request`) |
| `maxChars` | `500` | Max length + counter |

**Submit rules:** not loading; trimmed length ≥ 3 and ≤ `maxChars`.

**Submit flow**

```text
submit
  → getToken(); if none → /login
  → setLoading, clear error/result
  → runAgent(endpoint, { [payloadKey]: trimmed }, token)
  → setResult(data?.result ?? "")
  → on 401 ApiError: clear token → /login
  → other errors: show message + “Try again” (clears error only)
  → finally: setLoading(false)
```

**Markdown:** `ReactMarkdown` + `rehypeHighlight` + `highlight.js` github-dark CSS.

**Not used by:** Email, Manager (custom UIs).

---

### Email / Manager pages

Documented under their routes above. They import `DashboardShell` + `lib/api` directly and manage richer state than `AgentChat`.

---

## State management

*(Rationale: [§7 local state](#7-local-react-state-only-not-zustand--redux--react-query).)*

### What state lives where

| Kind of state | Where it lives | Examples |
|---------------|----------------|----------|
| Auth token | `localStorage` key `"token"` | Source of truth for “logged in?” |
| Current user profile | `DashboardShell` `user` (and home `user`) | From `/auth/me` |
| Agent prompt/result | Per-page / `AgentChat` `useState` | `input`, `result`, `loading` |
| Email draft fields | Email page only | `to`, `subject`, `body`, `sentiment` |
| Manager orchestration | Manager page only | `plan`, `stepResults`, `finalResponse` |
| Documents list / RAG | Documents page only | `docs`, `answer`, `sources` |
| History list / detail | History page only | `tasks`, `detail`, filters |

### Why no global store

- Screens are mostly independent: one request → one response.
- Sharing is already covered by **JWT in `localStorage`** + navigation.
- No need yet for cached lists across pages (History and Documents each fetch on mount).

### Token as source of truth

```text
Has valid token?  →  UI may show protected screens
No / bad token?   →  clear storage, go to /login
```

There is **no** React Context for auth and **no** `middleware.ts`. Each shell/page that cares re-reads `localStorage` and often calls `/auth/me` or relies on 401 from `runAgent`.

---

## How it talks to the backend

*(Rationale: [§10 `runAgent`](#10-libapijs-runagent-helper-not-axios--not-openapi-client), [§4 separate app](#4-separate-nextjs-app-not-server-rendered-pages-from-fastapi), [§15 what UI does not own](#15-what-the-frontend-does-not-own).)*

### Base URL

```js
// lib/api.js
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
```

### Auth token helpers

| Step | Behavior |
|------|----------|
| Login | `localStorage.setItem("token", data.access_token)` |
| Read | `getToken()` → `localStorage.getItem("token")` (null on server) |
| Requests | `Authorization: Bearer ${token}` |
| Logout / 401 | Remove `token`, redirect to `/login` |

### Full lifecycle of `runAgent`

```text
runAgent(endpoint, payload, token, method="POST")
  1. Build URL: API_BASE + endpoint
  2. Set Authorization header
  3. If not GET/HEAD: Content-Type application/json + JSON body
  4. fetch(...)
     └─ network failure → ApiError(code="network_error", status=0)
  5. Parse JSON (or null if body not JSON)
  6. If HTTP 401 → ApiError(code="unauthorized", status=401)
  7. If body.success === false → ApiError(code="agent_error")
  8. If !response.ok → ApiError(code="http_error")
  9. If body.success === true → return body.data
 10. Else return body as-is (fallback for unwrapped responses)
```

Expected success shape from most agent/doc/task routes:

```json
{ "success": true, "data": { }, "message": "...", "error": null }
```

### `ApiError` codes

| `code` | When |
|--------|------|
| `network_error` | `fetch` threw (backend down, CORS blocked as network fail, etc.) |
| `unauthorized` | HTTP 401 |
| `agent_error` | JSON `success: false` |
| `http_error` | Other non-OK HTTP |
| `api_error` | Default constructor code |

UI code usually checks `err.status === 401` and/or `err.code === "unauthorized"`.

### When raw `fetch` is used (not `runAgent`)

| Place | Why |
|-------|-----|
| Login / register | Auth responses are not the `{success,data}` agent wrapper |
| Home + DashboardShell `/auth/me` | User JSON handled directly |
| Documents upload | `multipart/form-data` (`FormData`) — do not set JSON Content-Type |
| History download | Binary blob + `Content-Disposition` filename |

### Endpoints used by the UI

| Area | Paths |
|------|--------|
| Auth | `POST /api/v1/auth/login`, `POST /api/v1/auth/register`, `GET /api/v1/auth/me` |
| Agents | `POST /api/v1/agents/{research,finance,analytics,coding,email,manager}`, `POST /api/v1/agents/email/send` |
| Documents | `GET /api/v1/documents`, `POST /api/v1/documents/upload`, `POST /api/v1/documents/query` |
| Tasks | `GET /api/v1/tasks`, `GET /api/v1/tasks/{id}`, `DELETE /api/v1/tasks/{id}`, `GET /api/v1/tasks/{id}/download` |

**Not called from the UI today:** `/api/v1/ml/*`, `/api/v1/tools/execute-code` (available in Swagger / via agents instead).

### CORS note

Backend must allow the frontend origin (typically `http://localhost:3000`). There is **no** Next.js rewrite proxy. If CORS fails, the UI often looks like a network error.

---

## Auth flow (end-to-end)

*(Rationale: [§5 localStorage JWT](#5-localstorage-jwt-not-cookies--nextauth--authjs), [§13 register then login](#13-register--login-not-auto-login-after-register).)*

### Sequence diagram

```text
Register  →  POST /auth/register  →  wait 2s  →  /login
Login     →  POST /auth/login     →  store JWT  →  window.location = /
Home `/`  →  GET /auth/me (raw)   →  dashboard OR landing
Protected →  DashboardShell       →  GET /auth/me again
API call  →  Bearer token         →  401? clear token → /login
Logout    →  remove token         →  /login
```

### Double-check on home + shell

When you open `/` while logged in:

1. **`Home`** checks token + `/auth/me` to decide landing vs dashboard.
2. If dashboard, it wraps **`DashboardShell`**, which checks token + `/auth/me` **again**.

That is intentional redundancy with today’s simple architecture (no shared Auth Context). Cost: two `/me` calls on home load.

Login/register are **not** wrapped in `DashboardShell`.

### Token expiry

There is no refresh-token rotation. When the access token expires, the next authenticated call returns 401 and the UI sends the user to login.

---

## Build and deployment

```bash
cd ../afsuu_Frontend
npm run build    # compiles the app into .next/
npm run start    # serves the production build
```

### What `npm run build` produces

- A `.next/` directory with optimized server/client bundles for Next.js.
- `NEXT_PUBLIC_API_URL` from the environment **at build time** is inlined into the client bundle.
- **TODO: confirm** whether your host sets env at build or runtime; for `NEXT_PUBLIC_*`, build-time is what matters for the browser.

### Production caveats

| Topic | Reality today |
|-------|----------------|
| Docker / Vercel / Netlify config | **Not found** in the frontend repo |
| Frontend README | Still says “Deploy on Vercel” (scaffold leftover) |
| CORS | Must allow your real frontend origin, not only `localhost:3000` |
| Secrets | Stay on the backend; frontend only needs public API URL |
| Metadata | `app/layout.jsx` still says “Create Next App” |
| Auth security | `localStorage` JWT is fine for local demo, not hardened production (XSS risk) |

**TODO: confirm** intended production host and how backend CORS will be updated.

---

## Known gaps

| Gap | Why it is this way / what to do | How a newcomer is affected |
|-----|----------------------------------|----------------------------|
| Settings nav with no page | Placeholder only (§12) — add `/settings` when profile UI exists | Clicking Settings does nothing — not a broken 404, but confusing |
| No TypeScript / no frontend tests | Speed for learning build (§2) — optional later | Easier to introduce API shape bugs; no automated UI safety net |
| Package name `"fronted"` | Typo in `package.json` — cosmetic | Ignore when searching npm name; folder is `afsuu_Frontend` |
| Metadata may still say “Create Next App” | Scaffold leftover — update `app/layout.jsx` when polishing | Browser tab title looks unfinished |
| `AGENTS.md` ≠ real structure | Ignore that file; this doc is the source of truth | Do not implement Zustand because an old note said so |
| Hardcoded dashboard stats | Layout placeholder; tasks list is live (§12) | “12 agents / 1,432 tasks” are fake — do not trust them |
| No direct ML forms | Agent chat first (§11); use `/docs` or add widgets later | You talk to Analytics/Finance agents instead of posting to `/ml/*` |
| Env fallback inconsistency | Some pages skip `api.js` fallback (§14) | Missing `.env.local` breaks login/shell even if agents “almost” work |
| PPT filter label, no PPT page | Backend PPT agent not built (§8) | History filter “PPT” may show empty forever |
| No continuous document polling | One 4s refresh after upload | Status may stay `processing` until user hits Refresh |
| Double `/auth/me` on home | No shared auth context | Slightly more API traffic; fine for local demo |

---

## Quick onboarding checklist

1. Backend up at `http://localhost:8000` (Swagger `/docs` opens).
2. `cd ../afsuu_Frontend && npm install`.
3. `cp .env.local.example .env.local` and restart nothing yet — then `npm run dev`.
4. Register → Login → land on dashboard.
5. Run Research (short topic) → see markdown result.
6. Open History → find the task.
7. Upload a small `.txt` on Documents → Refresh until `indexed` → Ask a question.

If step 4 fails with `undefined/api`, your env file is wrong. If agents fail with network/CORS, fix backend allow origin for `http://localhost:3000`.
