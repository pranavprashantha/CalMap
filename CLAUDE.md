# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current State of This Repo

`CalApp/` currently contains **no code** — this file is the only thing in it. Everything below is the agreed project spec/context, not a description of existing code. Update the "Commands" and architecture sections as real code lands.

Two things to know before writing code here:
- This directory is **not its own git repo**. `git rev-parse --show-toplevel` resolves to `C:/Users/raopr` (the user's home directory, which happens to be under version control). Run `git init` inside `CalApp/` before the first real commit so this project has its own history.
- Primary dev environment is Windows 11 / PowerShell.

## Project Overview

A mobile nutrition-tracking app (MyFitnessPal-style core) with AI-powered photo food recognition (Cal AI-style feature) as one of several food-logging input methods. Not a 1:1 clone of either — a unified app with its own name/branding, where AI vision is one input method among several feeding a single food diary system.

**Current priority: build a working MVP first.** Infrastructure concerns (CI/CD, cloud hosting choice beyond a simple free-tier deploy, Docker, staging environments) are explicitly deferred — see "Deferred: Infra & Deployment Stage" at the bottom. Do not set these up until the MVP is functionally complete.

### Core Concept

Three logging methods, all normalizing into the same `FoodEntry` schema before persistence:
1. Manual search/entry
2. Barcode scan
3. Photo → vision model → structured food guess (differentiator feature)

## Commands (planned — nothing is wired up yet)

- Backend dev server: `uvicorn main:app --reload`
- Backend manual testing: FastAPI's auto-generated `/docs` UI, pointed at a local or dev-only Postgres instance — never production data
- Mobile dev: Expo Go on an Android emulator or a real Android phone (covers most UI/logic/navigation work)
- Real camera / barcode testing: sideload a debug/dev EAS build as an `.apk` onto a real Android phone (free, no Play Store account). Emulator cameras are simulated and cannot validate capture.
- iOS: optional for MVP. iOS Simulator (Mac) is free and covers most flows but also has no real camera; real-device testing needs a paid Apple Developer account ($99/yr) — not needed for MVP.
- Tests: add `pytest` coverage for core logic once it stabilizes (auth, macro calculations, confidence-marker logic, nutrition matching). Not required from day one — add once there's real logic worth protecting from regressions.

## Tech Stack (MVP)

**Mobile Frontend**
- React Native + Expo
- NativeWind (Tailwind for RN)
- React Navigation
- Victory Native / react-native-gifted-charts (macro/calorie dashboards)
- Expo Camera / expo-image-picker
- Expo SecureStore (encrypted token storage — required since the app handles health data; not AsyncStorage)

**Backend**
- FastAPI (Python) — async support for vision API calls, auto-generated OpenAPI docs, strong AI/RAG ecosystem

**Database**
- PostgreSQL (Supabase free tier is fine for MVP; local Postgres also fine for early dev)
- `pg_trgm` extension with GIN index for fuzzy/exact nutrition lookups
- `pgvector` extension for personal meal-history similarity search (Phase 3, not needed at launch scale)

**Auth**
- JWT + bcrypt (hand-rolled for learning purposes)

**AI / Vision**
- **Gemini Vision API** (chosen for development to bypass usage fees)
- All vision calls happen server-side only — API keys never touch the mobile client

**Nutrition Data**
- USDA FoodData Central — bulk download imported into our own Postgres table (avoids live API latency per lookup)
- Open Food Facts API — queried live for barcode-scanned packaged goods

**File Storage**
- Cloudflare R2 (meal photos — no egress fees). Can be deferred to local/temp storage during earliest MVP dev if simpler.

## Key Feature: Photo Food Recognition Pipeline

```
1. User photographs meal
2. Photo sent to Gemini Vision (server-side)
3. Model prompted with CONSTRAINED vocabulary instructions —
   output generic/canonical-style food names, not arbitrary phrasing
4. For each identified food + estimated portion:
   a. Check synonym/alias table first (exact lookup: "soda" → "Carbonated Soft Drink")
   b. Run pg_trgm fuzzy search on canonical name against nutrition DB
   c. If confident match (above similarity threshold): use real DB macros
   d. If no confident match: fall back to pgvector similarity search,
      surfaced to user as "did you mean X?" — never silently auto-applied
   e. If still not found: AI estimates the value, item is flagged
      low-confidence in the UI
5. Calculate macros using photo-estimated portion × real per-unit data
6. AI combines all items into final meal summary
7. Each item displays a confidence marker (high/medium/low) based on:
   - whether it was DB-matched vs AI-estimated
   - whether portion had a size reference in the photo (plate, hand, utensil)
   - whether it was a mixed/occluded dish (auto low-confidence)
```

## Confidence Marker System

- Not a numeric AI self-reported score (unreliable) — use structural signals instead
- Qualitative tiers (high/medium/low) with a stated reason per item
- High-confidence items log automatically; low-confidence items prompt user confirmation before saving
- Same design principle reused for RAG-based personal history suggestions — surfaced as suggestions, never silent overwrites

## RAG Usage (two distinct applications, different retrieval methods)

**1. Nutrition grounding (exact/fuzzy matching, NOT vector search)**
- Reasoning: vector similarity is bad here — "skim milk" could semantically match "whole milk," corrupting macro accuracy
- Use `pg_trgm` for fuzzy/typo-tolerant exact-ish matching on canonical food names
- Add a GIN index (`CREATE INDEX ON foods USING GIN (food_name gin_trgm_ops)`) — turns fuzzy search on millions of rows into near-O(log n), not a full table scan

**2. Personal meal history matching (vector search, via pgvector) — Phase 3**
- Reasoning: the user's own phrasing varies run to run ("chicken curry with rice" vs "curry chicken bowl" — same dish, different words), so semantic similarity is the correct tool here
- Embed meal descriptions via an embedding model at save time, store the vector in Postgres
- At query time, embed the new meal description and run cosine similarity search against stored vectors
- Use a similarity threshold — discard low-confidence matches rather than force-using the nearest one regardless of score
- Brute-force search is fine at expected per-user scale (hundreds–low thousands of entries); no ANN index (IVFFlat/HNSW) needed for v1

## MyFitnessPal Baseline Features (Phase 1)

**Build:**
- Auth (signup/login)
- Manual food search/logging via nutrition DB
- TDEE-based calorie/macro goal calculation (Mifflin-St Jeor or similar)
- Daily food diary view with remaining-calories dashboard (goal − consumed − exercise)
- Macro tracking (protein/carbs/fat) + secondary metrics (fiber, sodium, sugar)
- Weight tracking with progress charts
- Custom recipes/"my meals" (composite food items, many-to-many modeling)
- Exercise logging with calorie burn estimates (METs lookup table)
- Water tracking

**Explicitly skip / lean on free APIs instead of building:**
- Custom food database (use USDA FoodData Central + Open Food Facts)
- Restaurant menu database (same — lean on existing APIs)
- Social features (friends, feed, community) — low resume value for the engineering effort required

## Build Phases (each independently shippable/demoable)

1. **Core tracker (MVP)** — auth, manual logging, nutrition DB lookup, diary view, goals, weight tracking
2. **AI photo scan** — vision recognition, confidence markers, barcode scanning
3. **RAG grounding** — nutrition DB fuzzy matching (pg_trgm) + personal history matching (pgvector)
4. **In-app agent** — chat-based logging via LLM tool/function calling ("log a banana and 2 eggs")
5. **MCP server** — expose backend functions (`log_food`, `get_daily_summary`, `search_food_history`, `get_weight_trend`) via MCP protocol for external clients like Claude Desktop

## Security Notes (apply from the start, not deferred)

- Health data app — encrypt tokens at rest (Expo SecureStore, not AsyncStorage)
- Rate limit the vision-API endpoint (cost control + abuse prevention)
- Input validation via Pydantic models (FastAPI)
- Environment variables for secrets, never committed
- Never call vision APIs directly from the mobile client — server-side only

## Branding Note

Do not name the app "MyFitnessPal clone" or "Cal AI clone" anywhere public-facing. Frame it as an original product (e.g., "AI-assisted nutrition tracker with confidence-scored food recognition").

---

## Deferred: Infra & Deployment Stage (do not build until MVP is working)

Once the MVP (Phase 1, and ideally through Phase 2–3) is functional and tested locally, revisit:

- **Backend hosting**: deploy to Railway or Render first (fast, free-tier, auto-deploy from GitHub push) — get something live with minimal friction
- **Docker**: containerize the backend with a `Dockerfile` — not strictly required by Railway/Render (they support buildpack auto-detection), but worth adding for portability and as a resume/learning item
- **Cloud migration exercise (optional, later)**: after Railway/Render deployment works, consider redeploying the same backend on Azure (App Service or Container Apps) as a deliberate learning exercise — frame as "started on Railway for velocity, migrated to Azure for hands-on cloud experience," not as the first deployment target
- **CI/CD**: add a GitHub Actions workflow to run `pytest` on push/PR before merge — worth adding once there are real tests to gate on, not before
- **Staging environment**: optional; a second small Supabase project + a second Railway deployment can serve as a staging step once there's a reason to protect prod (e.g., real users) — not necessary while solo-testing
- **Mobile release pipeline**: EAS Build + EAS Submit for TestFlight (iOS, requires $99/yr Apple Developer account) or Play Store — only needed if distributing beyond direct APK sideloading and personal device testing
- **File storage**: move meal photos to Cloudflare R2 if not already in place from the MVP stage
