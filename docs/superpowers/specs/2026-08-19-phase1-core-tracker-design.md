# Phase 1 — Core Tracker (MVP) Design

**Date:** 2026-08-19
**Status:** Approved for planning
**Scope:** Phase 1 only. Phases 2–5 (vision, RAG, agent, MCP) get their own spec → plan cycles.

## 1. Goal

A working nutrition tracker you can use on your own phone: sign up, search real USDA foods,
log them to a daily diary, see calories/macros against a calculated goal, and track weight
over time. Everything runs locally — laptop backend, Docker Postgres, Expo Go on a real
Android device.

**Done means:** you can log a full day of eating on your phone without touching the terminal.

### In scope

Auth (signup/login) · USDA food import + search · food diary with daily totals · TDEE-based
calorie and macro goals · weight tracking with a chart.

### Out of scope for Phase 1

Photo recognition, barcode scanning, RAG, recipes/"my meals", exercise logging, water
tracking, social features, deployment, CI/CD. Recipes, exercise, and water are Phase 1.5 —
independent slices to add once the core loop works.

## 2. Repository layout

```
CalApp/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app, router registration, exception handlers
│   │   ├── config.py          # pydantic-settings, reads .env
│   │   ├── db.py              # async engine, session dependency
│   │   ├── models/            # SQLAlchemy ORM models (one file per domain)
│   │   ├── schemas/           # Pydantic request/response models
│   │   ├── routers/           # HTTP layer only — parse, call service, return
│   │   ├── services/          # business logic, no HTTP awareness
│   │   └── core/              # security.py (hashing, JWT), deps.py (current_user)
│   ├── scripts/import_usda.py
│   ├── alembic/
│   ├── tests/
│   └── requirements.txt
├── mobile/
│   ├── app/                   # expo-router file-based routes
│   ├── src/
│   │   ├── api/               # typed fetch client + per-domain functions
│   │   ├── components/
│   │   ├── hooks/             # react-query hooks
│   │   └── lib/               # auth context, secure storage, formatting
│   └── package.json
├── docker-compose.yml         # Postgres only
└── docs/
```

The routers/services/models split matters more than it looks: it's what keeps the Phase 4
agent and Phase 5 MCP server from having to re-implement logic. Both will call the same
service functions the HTTP routes call. **Business logic never lives in a router.**

## 3. Data model

All quantities stored **metric** (grams, kilograms, centimeters). Imperial is a display-layer
concern only — converting at the boundary avoids the class of bug where stored units are
ambiguous.

### `users`
`id` (uuid, pk) · `email` (text, unique, stored lowercased) · `external_auth_id` (text, unique,
nullable) · `is_dev_stub` (bool, default false) · `created_at`

**No `password_hash` column** — passwords are never stored here; see §4. `external_auth_id` holds
the provider's subject claim once auth exists, and stays null for the seeded dev user.
Email is normalized to lowercase in the service layer rather than using the `citext`
extension — one fewer extension to enable, and the normalization is visible in code.

### `user_profiles`
`user_id` (fk, pk) · `birth_date` · `sex` · `height_cm` · `activity_level` (enum) ·
`goal_type` (lose/maintain/gain) · `weekly_rate_kg` · `calorie_goal` · `protein_g_goal` ·
`carb_g_goal` · `fat_g_goal` · `updated_at`

Goals are **stored, not computed on read.** TDEE is calculated when the profile is saved and
persisted. Otherwise a user's historical diary days would silently re-baseline against
today's goal every time they viewed them.

### `foods`
`fdc_id` (bigint, pk — USDA's own key) · `description` · `data_type` (foundation /
sr_legacy / branded) · `brand_owner` (nullable) · per-100g nutrient columns: `kcal`,
`protein_g`, `carb_g`, `fat_g`, `fiber_g`, `sugar_g`, `sodium_mg` · `search_text` (generated,
lowercased description)

**Denormalized nutrient columns rather than an EAV `food_nutrients` table.** USDA ships
nutrients as one row per nutrient per food; joining that on every search would be slow and
awkward. We care about seven values, so they become columns. Adding an eighth later is a
migration, which is an acceptable trade for simple, fast queries.

Keying on `fdc_id` and storing `data_type` is what makes the later Branded Foods import a
data load rather than a redesign — re-running the importer with a new dataset inserts
without collisions, and search can rank Foundation above Branded so brand variants don't
flood results.

Index: `CREATE INDEX foods_search_trgm ON foods USING GIN (search_text gin_trgm_ops)`

### `food_portions`
`id` · `fdc_id` (fk) · `description` ("1 cup, chopped") · `gram_weight`

From USDA's portion data. Without it, users must enter everything in grams, which nobody does.

### `food_entries`
`id` · `user_id` (fk) · `fdc_id` (fk, **nullable** — Phase 2 AI-estimated items and future
custom foods won't always have one) · `meal_type` (breakfast/lunch/dinner/snack) ·
`grams` · `portion_description` (what the user picked, denormalized) ·
snapshot columns `kcal`, `protein_g`, `carb_g`, `fat_g`, `fiber_g`, `sugar_g`, `sodium_mg` ·
`logged_on` (date) · `created_at` (timestamptz)

**Nutrients are snapshotted at log time, not recomputed from `foods` on read.** If a future
USDA import corrects a food's calories, it must not silently rewrite what the user ate in
March. This also means the diary keeps working for entries whose `fdc_id` is null.

`logged_on` is a plain `DATE` in the *user's local timezone*, sent by the client. A
timestamptz alone would put a 9pm meal on the wrong day for anyone not on UTC, and "which
day is this food on" is the single most user-visible thing in the app.

Index: `(user_id, logged_on)` — the diary's only hot query.

### `weight_entries`
`id` · `user_id` (fk) · `weight_kg` · `recorded_on` (date) · unique `(user_id, recorded_on)`

One weigh-in per day; a second submission updates the existing row.

## 4. Auth

**Phase 1 has no authentication.** A seeded dev user is returned unconditionally by the
`current_user` dependency. Real auth is a managed cloud provider, added as its own milestone
before anything is deployed.

**Consequence, stated plainly:** the API is completely open in this state. Bind uvicorn to the
LAN and never port-forward it or expose it through a public tunnel until auth is real.

**Provider: deliberately undecided.** Microsoft Entra External ID (the Azure-native option),
Clerk, and Auth0 all fit the same shape. These constraints are what keep every option cheap,
and they are the part that matters now:

- `current_user` is a **FastAPI dependency from M0**, even while it returns a constant.
  Swapping the stub for real verification touches one function, not every route.
- **Every service function takes `user_id` as an explicit parameter.** No module-level or
  context-global "current user" — this is what keeps the retrofit to one line per route.
- Users are keyed on `external_auth_id` (the provider's `sub` claim). We keep our own `users`
  row regardless, because profiles, diary entries, and weights all foreign-key to it.
- Verification will be **JWKS-based**: fetch the provider's public keys, verify signature,
  issuer, and audience. Nothing signs tokens on our side.
- Tokens live in `expo-secure-store` (OS keystore), never AsyncStorage.

This replaces the hand-rolled JWT + bcrypt plan; CLAUDE.md is updated to match. The trade: less
learned about auth internals, against no password storage to get wrong and password reset /
email verification / MFA arriving for free rather than as three more milestones.

## 5. Nutrition data and search

**Import** (`scripts/import_usda.py`): takes a dataset directory as an argument, streams the
CSVs, and upserts on `fdc_id`. Idempotent — safe to re-run. Phase 1 loads Foundation +
SR Legacy (~10k high-quality generic foods). Branded (~2M) is a later invocation of the same
script.

**Search** (`GET /foods/search?q=`): `pg_trgm` similarity against `search_text`, filtered by a
minimum similarity threshold, ordered by `similarity DESC`, then by `data_type` rank
(foundation > sr_legacy > branded), limit 25. Trigram matching, not vector search — "skim
milk" must never semantically match "whole milk" and corrupt the macros. Vector search enters
in Phase 3, for personal meal history only.

**Portion selection:** the food detail response includes its `food_portions` plus a raw grams
option. The client sends resolved `grams`; the server recomputes nutrients from per-100g
values and snapshots them. **The client never sends nutrient values** — it would let a
modified app write arbitrary numbers, and it would put the same math in two places.

## 6. Goals and the diary

**TDEE:** Mifflin-St Jeor for BMR, × activity multiplier (sedentary 1.2 → very active 1.9),
then the goal delta (−500 kcal/day ≈ −0.5 kg/week). Floored at 1200 kcal for safety.

**Macro split:** protein 1.6 g/kg bodyweight, fat 25% of calories, carbs fill the remainder.
Editable by the user; the calculation only supplies defaults.

**Daily summary** (`GET /diary?date=`): entries grouped by meal, plus totals and
`remaining = goal − consumed`. Computed server-side so the mobile app, the Phase 4 agent, and
the Phase 5 MCP server all report identical numbers.

## 7. Mobile architecture

- **Routing:** `expo-router`, file-based. Built on React Navigation, so the spec's choice
  holds. Route groups: `(auth)` for login/signup, `(tabs)` for Diary / Search / Progress /
  Profile.
- **Server state:** `@tanstack/react-query`. Logging a food from the search screen invalidates
  the diary query, so the diary is correct when the user navigates back — the alternative is
  hand-wired `useState` refresh logic in every screen.
- **Auth state:** a context provider holding the user + tokens, hydrated from SecureStore on
  launch. A splash gate blocks rendering until hydration finishes, avoiding a login-screen
  flash on every cold start.
- **API client:** one typed `fetch` wrapper that attaches the bearer token, and on 401
  attempts a refresh once, retries, and on failure clears tokens and redirects to login.
- **Styling:** NativeWind, with color and spacing tokens defined once in the Tailwind config.
- **Charts:** `react-native-gifted-charts` for the weight trend.

## 8. Error handling

- **Server:** one exception handler producing `{"detail": "...", "code": "..."}` for every
  error. Pydantic handles input validation; services raise typed domain exceptions that map
  to status codes in one place.
- **Client:** react-query surfaces error state per screen; mutations roll back optimistic
  updates on failure. Network failure shows a retry affordance rather than an empty state —
  on a phone, "no connection" and "no data" look identical otherwise, and confusing them is
  the fastest way to make the app feel broken.
- **Auth:** 401 triggers the single refresh attempt described above; anything else logs out.

## 9. Testing

- **Backend logic** — `pytest` for the parts where wrong answers are invisible: TDEE and macro
  math, portion → gram → nutrient conversion, JWT issue/verify/expire, refresh rotation.
  These are pure functions; test them from milestone 1 rather than "once it stabilizes."
- **Endpoints** — `httpx` + `pytest-asyncio` against a throwaway test database. Added at
  milestone 3, once the request shapes settle.
- **Manual API** — FastAPI `/docs`, against the local Docker database only.
- **Mobile** — Expo Go on a real Android device. No automated UI tests in Phase 1.

## 10. Milestones

Each is a complete path through DB → API → screen, demoable on a phone before starting the next.

**M0 — Walking skeleton.** docker-compose Postgres up with pg_trgm + pgvector enabled;
FastAPI `/health` returning a real DB round-trip; Expo app displaying that response on a
physical device. *Proves the toolchain and, critically, that a phone can reach the laptop —
this is where Windows firewall rules and LAN-IP-vs-localhost problems surface, and finding
them now costs an hour instead of derailing a feature later.*

**M1 — Food data.** USDA importer, `foods` + `food_portions` tables, GIN index, search endpoint,
search screen with results and a food detail view.

**M2 — Diary.** `food_entries`, create/list/delete, portion picker, diary screen grouped by meal
with running totals.

**M3 — Goals.** Profile onboarding, TDEE + macro calculation, goals persisted, diary dashboard
showing remaining calories and macro progress.

**M4 — Weight.** Weight entries, list + chart, progress tab.

**M5 — Auth (gates deployment).** Choose the provider, add JWKS verification behind the existing
`current_user` dependency, provider sign-in in the app, and a migration that either reassigns the
dev user's rows to the first real account or discards them. **Nothing is exposed beyond the LAN
until this milestone lands.**

## 11. Forward compatibility

Decisions made now specifically to keep later phases cheap:

- Business logic in services, not routers → Phase 4 agent and Phase 5 MCP server call the
  same functions.
- `food_entries.fdc_id` nullable + snapshotted nutrients → Phase 2 AI-estimated items fit the
  existing table.
- `foods` keyed on `fdc_id` with `data_type` → Branded import is additive.
- pgvector installed in the container from M0 → Phase 3 adds a column, not infrastructure.
- Vision/confidence fields are **not** added preemptively. They'd be guesses today.

## 12. Dependencies

**Infrastructure:** Docker image `pgvector/pgvector:pg17` — Postgres with pgvector
preinstalled; `pg_trgm` ships as a bundled contrib module.

**Backend** — Python 3.14, `venv` + `pip`. All verified to have cp314 wheels (2026-08-19):
`fastapi[standard]` · `sqlalchemy[asyncio]` 2.0.52 · `alembic` 1.19.1 · `asyncpg` 0.31.0 ·
`pydantic-settings` · `ruff` · `pytest` + `pytest-asyncio`

Added at the auth milestone, not before: `pyjwt` + `cryptography` for JWKS verification, and the
chosen provider's Expo SDK. `bcrypt` is not needed at all now — no passwords are ever stored.

**Mobile** — `create-expo-app` TypeScript template: `expo` · `expo-router` · `nativewind` +
`tailwindcss` · `expo-secure-store` · `@tanstack/react-query` · `react-native-gifted-charts` +
`react-native-svg`

Deliberately excluded: `passlib` (unmaintained, breaks with bcrypt 4+), `python-jose` (stale;
`pyjwt` is maintained), Redis (nothing in Phase 1 needs a cache).

## 13. Deferred decisions

- **Meal photo storage** — nothing to store until Phase 2. Local disk first, Cloudflare R2 when
  deploying.
- **Rate limiting** — the vision endpoint is the expensive one and doesn't exist yet. Add with
  Phase 2.
- **Email verification / password reset** — needs an email provider; not needed while the only
  user is you.
- **App name and branding** — placeholder `CalMap` until decided.
