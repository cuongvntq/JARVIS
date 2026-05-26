# JARVIS Frontend

Next.js 15 + React 19 + Tailwind CSS 4 + TypeScript.

## Setup

```powershell
# 1. Install deps
pnpm install

# 2. Copy env
Copy-Item .env.local.example .env.local
# Mở .env.local và confirm NEXT_PUBLIC_API_URL=http://localhost:8000

# 3. Run dev
pnpm dev
```

→ http://localhost:3000

## Commands

```powershell
pnpm dev           # Dev server
pnpm build         # Production build
pnpm start         # Production server
pnpm lint          # Biome lint
pnpm format        # Biome format
pnpm check         # Biome lint + format combined
pnpm typecheck     # TS type check
pnpm test          # Vitest
```

## Cấu trúc (sẽ mở rộng theo sprint)

```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx          # Root layout
│   │   ├── page.tsx            # Sprint 0 chat test
│   │   └── globals.css
│   ├── components/             # Sprint 1+: shared UI
│   ├── lib/                    # Sprint 1+: API client, utils
│   └── stores/                 # Sprint 1+: zustand stores
├── public/                     # Static assets
├── package.json
├── next.config.ts
├── tsconfig.json
├── biome.json
└── postcss.config.mjs
```

## Test backend connection

Khi backend chạy tại `localhost:8000`:
1. Mở http://localhost:3000.
2. Gõ "Xin chào" vào ô input → Gửi.
3. Nhận phản hồi từ JARVIS + thấy `model: gemini/gemini-2.5-flash` hoặc `gpt-4o-mini`.
