# Dara — Streamlit

A Python/Streamlit app mirroring the web scaffold's architecture: tier-based
model routing, multi-provider AI calls, and a Supabase backend (one schema,
shared at `../supabase/schema.sql`).

It runs in two modes, decided automatically:

- **PoC mode** (no Supabase keys) — sign-in is decoupled and AI is mocked, so
  the public demo runs with zero configuration. Home picker → matchmaking
  interview and conflict mediation.
- **Accounts mode** (Supabase configured) — full email + password account
  system: sign up / in / out, first-run onboarding, profile + photos, plan /
  billing (simulated), settings, and GDPR account deletion.

## Layout

```
streamlit/
├── app.py                       # router: PoC mode ↔ accounts mode
├── requirements.txt
├── .env.example
├── .streamlit/
│   ├── config.toml              # theme
│   └── secrets.toml.example     # Supabase + provider keys
├── dara/                        # domain + AI library (no Streamlit deps)
│   ├── config.py                # env / st.secrets loading + mode flags
│   ├── tiers.py                 # routing table + tier metadata
│   ├── providers.py             # Anthropic / Google / DeepSeek calls
│   ├── mock.py                  # canned responses for PoC mode
│   ├── ai_client.py             # call_ai() + resolve_model()
│   ├── supabase_client.py       # client factories (anon + admin)
│   ├── auth.py                  # email+password auth service
│   └── profile.py               # users row + photo storage service
└── flows/                       # Streamlit presentation layer
    ├── session.py               # per-session client + cookie persistence
    ├── auth.py                  # sign in / create account / forgot password
    ├── onboarding.py            # first-run username + kind
    ├── account.py               # profile · photos · plan · settings · delete
    ├── home.py / interview.py / mediation.py
    └── common.py                # sidebar, tier, nav helpers
```

## Run the PoC (no setup)

```bash
cd streamlit
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```
Opens at http://localhost:8501 in PoC mode.

## Turn on accounts

1. **Schema** — in the Supabase SQL Editor, run `../supabase/schema.sql`
   (safe to re-run). It includes the `handle_new_user` trigger that
   auto-creates a profile row on sign-up.
2. **Auth** — Supabase → Authentication → Providers → enable **Email**.
   Email confirmation on (recommended) or off both work; with it on, users
   confirm via email once, then sign in with their password.
3. **Secrets** — copy `.streamlit/secrets.toml.example` to
   `.streamlit/secrets.toml` and fill in:
   ```toml
   SUPABASE_URL = "https://YOUR-PROJECT.supabase.co"
   SUPABASE_ANON_KEY = "your-anon-or-publishable-key"
   # optional, server-side only — enables hard account deletion:
   SUPABASE_SERVICE_ROLE_KEY = "your-service-role-key"
   ```
   Accounts switch on automatically once `SUPABASE_URL` + `SUPABASE_ANON_KEY`
   are present.

### How deletion works
With `SUPABASE_SERVICE_ROLE_KEY` set, "Delete my account" removes the auth
identity, which cascades all app data. Without it, the user's own RLS-scoped
session deletes their app data and signs them out, leaving the auth identity
for an admin to purge. The service-role key is read server-side only and must
never be committed or exposed to a browser.

## Go live with AI

Set `DARA_AI_MODE = "live"` and supply at least `GOOGLE_API_KEY`. Call sites
don't change — routing in `dara/tiers.py` picks the model per (tier, purpose).

## Deploy (Streamlit Community Cloud)

Push to GitHub, deploy `streamlit/app.py`. Paste the same keys into the app's
**Secrets** box. With no secrets it runs the public PoC; add Supabase keys to
turn on accounts.
