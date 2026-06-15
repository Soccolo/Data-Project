# Dara — web (Next.js)

This is the production web scaffold. Once configured, you'll have:
- Magic-link email auth (via Supabase)
- Postgres data with proper row-level security (private intakes stay private)
- Photos in Supabase Storage (no 5MB cap, signed URLs)
- Server-side LLM proxy with tier routing (free → Gemini, pro → Claude)
- Deployed on Vercel free tier

## Layout

```
web/
├── src/
│   ├── app/
│   │   ├── layout.tsx           # root layout + fonts
│   │   ├── page.tsx             # entry: storage shim + auth gate
│   │   ├── globals.css          # base styles + animations
│   │   └── api/llm/route.ts     # server-side LLM proxy (auth + tier routing)
│   ├── components/
│   │   ├── auth/
│   │   │   └── magic-link-sign-in.tsx
│   │   └── dara.tsx             # ← drop the migrated component here
│   └── lib/
│       ├── ai/
│       │   ├── client.ts        # browser-side callAI()
│       │   ├── providers.ts     # Anthropic / Google / DeepSeek calls
│       │   └── tiers.ts         # (tier, purpose) → model routing table
│       ├── storage/
│       │   └── adapter.ts       # window.storage → Supabase shim
│       └── supabase/
│           ├── client.ts        # browser client
│           └── server.ts        # server client (cookies)
└── README.md
```

The database schema lives once at the repo root: `../supabase/schema.sql`.

## Step 1 — Supabase project

1. Go to https://supabase.com → New project.
   - **Region: West Europe (London) or Central EU (Frankfurt)** for GDPR.
   - Strong DB password. Save it somewhere.
2. Wait ~2 min for the project to provision.
3. Open **SQL Editor** → paste the contents of `../supabase/schema.sql` → Run.
   - Should complete with no errors. Creates tables, RLS policies, and the photos bucket.
4. Open **Authentication → Providers** → make sure **Email** is enabled (it is by default).
   - Under **Settings**, set "Site URL" to wherever you'll deploy (we'll come back here after Vercel).
5. Open **Project Settings → API** → copy the **Project URL** and the **anon public** key.

## Step 2 — Local environment

```bash
cd web
cp .env.local.example .env.local
```

Edit `.env.local`:
- `NEXT_PUBLIC_SUPABASE_URL` — paste your Supabase project URL.
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` — paste your Supabase anon key.
- `GOOGLE_API_KEY` — paste your Gemini AI Studio key (the one you already have).
- `ANTHROPIC_API_KEY` — paste yours if you have one (needed for pro/x tier users).
- `DEEPSEEK_API_KEY` — leave empty unless you set up DeepSeek.

Then:
```bash
npm install
npm run dev
```
Open http://localhost:3000.

## Step 3 — Migrate the Dara component

The previous artifact (dara.jsx, ~4100 lines) needs four spots updated to use
the new `/api/llm` route instead of calling Anthropic/Gemini directly from the
browser. Drop the file in at `src/components/dara.tsx` and find the section
commented `// ── AI calls`. Replace `callClaude` / `callGemini` /
`aiCall` with the `callAI` import from `@/lib/ai/client`. Each existing
`aiInterview`, `aiProxyTurn`, etc. gains a `purpose:` parameter — see the
mapping comment in that file.

The `window.storage` calls work unchanged thanks to the shim in
`@/lib/storage/adapter`.

The adapted component is generated as a follow-up so you have the diff
explicit rather than rewriting the whole file by hand.

## Step 4 — Deploy

```bash
npx vercel
```
Follow the prompts. After deploy:
1. In **Vercel → Project → Settings → Environment Variables**, paste all the
   same keys from your `.env.local` (Supabase URL/anon key, Google key,
   optional Anthropic/DeepSeek).
2. Trigger a redeploy.
3. Back in **Supabase → Authentication → URL Configuration**, set:
   - **Site URL**: `https://your-app.vercel.app`
   - **Redirect URLs**: add `https://your-app.vercel.app/**`

That's it. The link Supabase emails will land at your deployed app.

## Tier management

Users default to `free` (all Gemini Flash). To upgrade a user, open Supabase
**Table Editor → users**, find the row, change `tier` to `pro` or `x`.

Eventually this should be a Stripe webhook. For now, manual.

The routing table is in `src/lib/ai/tiers.ts` — edit it to tune which calls use
which provider per tier.

## What's not in this first cut

- Stripe payments
- Email verification before sign-in (Supabase allows unverified sign-ins by
  default; toggle in Auth settings if you want stricter)
- GDPR delete UI (the DB cascade is in place; you just need a button that
  calls `sb.auth.admin.deleteUser` server-side)
- Rate limiting on `/api/llm` (you'll want this once it's public — Upstash
  Redis is the usual choice)
- Realtime subscriptions on conflict sessions / meets (currently polling-based
  via the existing UI; upgrade to Supabase Realtime when you want sub-second
  updates)

These are follow-up steps after the first deploy works.
