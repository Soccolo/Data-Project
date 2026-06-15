# Dara

AI matchmaker and mediator. Dara acts on each user's behalf in two domains:

- **Matchmaking** — Dara interviews you, analyses photos, runs *Dara-to-Dara*
  proxy conversations against other users' agents, and produces a match verdict.
- **Conflict mediation** — private conflict intake, safety prescreening, then
  *Dara-to-Dara* mediation between two parties, ending in synthesised takeaways.

## Repository layout

```
dara/
├── supabase/
│   └── schema.sql        # shared Postgres schema + RLS + storage bucket
├── web/                  # Next.js 14 app (App Router, src/ layout)
├── streamlit/            # Python / Streamlit app (same architecture)
├── MIGRATION.md          # end-to-end production setup walkthrough
└── README.md            # you are here
```

Both apps share one Supabase project. The schema is defined once in
`supabase/schema.sql`; load it into the SQL Editor before running either app.

## Architecture

- **Auth & data** — Supabase magic-link email auth; Postgres with row-level
  security so private intakes stay private; photos in Supabase Storage.
- **Tier-based model routing** — every AI call declares a `purpose`; the
  `(tier, purpose)` routing table picks the provider/model. Free → Gemini
  Flash; pro/x → Claude on the calls that matter. Defined in
  `web/src/lib/ai/tiers.ts` and mirrored in `streamlit/dara/tiers.py`.
- **Server-side AI** — provider API keys never reach the browser. The web app
  proxies through `/api/llm`; Streamlit calls providers in-process.

## Getting started

- **Web:** see [`web/README.md`](web/README.md).
- **Streamlit:** see [`streamlit/README.md`](streamlit/README.md).
- **Full production walkthrough (Supabase → deploy):** see
  [`MIGRATION.md`](MIGRATION.md).
