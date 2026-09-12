# Sutradhar

A document verification desk for a government office.

An officer uploads a citizen's document. The system runs a set of checks against
a records database and a rules file, and returns the document annotated with
every finding, each one backed by visible evidence. Then it **stops and waits for
a human.** The officer approves or rejects. Only that click writes a decision.

The system prepares the decision. It never makes it.

---

## Status: Phase 1 complete

Phase 1 is the skeleton: the two services wired together over a real database,
with the design system rendering a real screen and a working session.

**Working now**

- Next.js frontend and FastAPI backend, talking to one SQLite database
- UX4G Design System 3.0 rendering the sign-in and home screens, light and dark
- Sign in, session refresh, sign out — JWT in an httpOnly, `SameSite=Strict` cookie
- Health endpoint probing both database engines
- Full schema under Alembic, reversible
- Seed script creating the two office users
- English and Hindi, with every user-facing string in the locale files
- Keyboard operation and screen-reader labelling throughout

**Not built yet** — document upload, the verification checks, the review screen,
the audit hash chain, the dept head dashboard. Those are Phases 2–5.

---

## Running it from a clean clone

Requires Python 3.11+ and Node 20+.

```bash
git clone https://github.com/utk042/Sutradhar.git
cd Sutradhar
```

**1. Configure**

```bash
cp .env.example .env
```

Fill in the three required values in `.env`:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"   # SUTRADHAR_JWT_SECRET
python3 -c "import secrets; print(secrets.token_urlsafe(16))"   # each seed password
```

For local development also set `SUTRADHAR_COOKIE_SECURE=false`, because the
development server is plain http and a `Secure` cookie would never be stored.

**2. Backend**

```bash
cd backend
python3 -m venv .venv
./.venv/bin/pip install -e ".[dev]"
set -a && . ../.env && set +a          # load .env into the shell
./.venv/bin/alembic upgrade head       # create the schema
./.venv/bin/python scripts/seed.py     # create the two users
./.venv/bin/uvicorn app.main:app --port 8000
```

**3. Frontend** — in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000**. Sign in with `9000000001` and the officer
password you set. The section head is `9000000002`.

Interactive API documentation is at http://localhost:8000/api/docs in
development; it is switched off when `SUTRADHAR_ENVIRONMENT=production`.

### Useful commands

| | |
|---|---|
| `npm run build` / `npm start` | Production build and serve |
| `npm run typecheck` | TypeScript, no emit |
| `./.venv/bin/alembic revision --autogenerate -m "..."` | New migration |
| `./.venv/bin/alembic downgrade -1` | Roll back one migration |

---

## The guarantee: the system can read, it can never write

This is the core claim, and it is enforced at the connection layer rather than by
code discipline.

There are two database engines:

- **`backend/app/db/readonly.py`** opens SQLite through a URI with `mode=ro`.
  This is the only database module the verification checks may import.
- **`backend/app/db/app.py`** is read-write, and nothing under `app/agents/` may
  import it.

`mode=ro` is enforced by the SQLite driver. A write raises
`OperationalError: attempt to write a readonly database` before it reaches the
database file — not because the application chose to refuse it:

```
read engine SELECT:  v
read engine INSERT:  OperationalError — attempt to write a readonly database
```

The checks never hold a write session at all. They return typed findings, and the
application layer persists them. That keeps the guarantee true even for the
system's own bookkeeping.

### The same guarantee on Postgres

Porting changes `readonly.py` and nothing else. Point its URL at a role created
with:

```sql
CREATE ROLE sutradhar_agent LOGIN PASSWORD '...';
GRANT CONNECT ON DATABASE sutradhar TO sutradhar_agent;
GRANT USAGE  ON SCHEMA public TO sutradhar_agent;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO sutradhar_agent;
```

That role holds `SELECT` and nothing else. The guarantee is identical, and it is
still the database refusing the write. Everything else moves across unchanged:
all access is through SQLAlchemy and Alembic, and there is no SQLite-specific SQL
anywhere.

Automated tests asserting both halves — the import graph, and a write raising —
land in Phase 4.

---

## Where the data comes from

**`registry_records` is seeded sample data standing in for a real records
system.** It is not a live government database, and Sutradhar has no connection
to DigiLocker or any state registry. Every row carries `is_sample`, and the
interface says so on screen.

A real integration would be a second implementation of the same
`RecordsProvider` interface, not a change to this one.

---

## How it is put together

```
Next.js (UX4G)  ──/api/* proxied──>  FastAPI  ──>  SQLite
                                        │
                                        ├── Session (JWT, httpOnly cookie)
                                        └── Verification checks (read-only)
```

The browser only ever talks to the Next.js origin, which proxies `/api/*` to
FastAPI. That is deliberate: the session cookie is `SameSite=Strict`, and a
browser will not send a Strict cookie on a cross-site request. Serving both from
one origin is what makes Strict do its job — and it removes CORS from the picture
entirely.

```
backend/
  app/
    db/          readonly.py (mode=ro) · app.py (read-write)
    models/      the nine tables
    schemas/     Pydantic v2 request/response types
    api/         auth · health  (review, documents, stream: later phases)
    services/    security (Argon2id, JWT)
  alembic/       migrations
  scripts/seed.py
frontend/
  messages/      en.json · hi.json
  src/app/[locale]/    layout · login · home
  src/components/      Logo · Ux4gRuntime · LanguageSwitcher
  src/lib/api.ts
  src/styles/app.css   the only custom CSS in the project
```

### The schema

`users` · `documents` · `extracted_fields` · `agent_runs` · `findings` ·
`registry_records` · `rules` · `audit_log` · `settings`

Two columns worth calling out. `agent_runs.duration_ms` records each check's
execution window, so the claim that checks run in parallel is provable from the
data rather than asserted. `audit_log` carries `prev_hash` and `row_hash` to
chain rows against tampering; the chain is implemented in Phase 4.

Application logs carry document and user IDs only — never names, dates of birth
or document numbers.

---

## Accessibility

Baseline is WCAG 2.1 AA, as a government service requires. Verified in a browser
at 1366×768:

- Keyboard-only sign-in works end to end; tab order is skip link → language →
  text size → fields → sign in
- Visible focus on every control: 2px solid `Focus/Outline`
- Interactive controls are ≥44×44px (`ux4g-btn-lg` is 48px; the default `md`
  size is 40px and is deliberately not used for officer-facing actions)
- Every state is labelled in words, never colour alone
- Errors say what happened and what to do next; no status code, stack trace or
  technical vocabulary reaches an officer

There is no on-screen text-resize widget. Accessibility here is structural —
label associations, focus order, landmarks, a skip link — rather than a control
panel bolted onto the header.

**One upstream accessibility defect is fixed here.** UX4G's resting control
border measures 1.26:1 against the input's own background — far below the 3:1
WCAG 1.4.11 requires for a control boundary, and effectively invisible to a
low-vision user. `src/styles/app.css` repoints it to
`--ux4g-border-color-neutral-strong`, giving 4.74:1 in light and 7.66:1 in dark.
Both are UX4G semantic tokens; no new colour is introduced.

### Known constraint: stylesheet size

`ux4g-web-components` ships an 8.0 MB stylesheet, of which 90.5% is seven fonts
embedded as base64 — including four Material Icons variants this service does not
use. It gzips to 3.9 MB; with the fonts removed the same stylesheet is 112 KB
gzipped, a 36× difference. Because it is render-blocking, that is blank-screen
time on a constrained connection.

We serve it from our own origin under an immutable cache header, making it a
once-per-release cost rather than a per-visit one. Our own CSS is 714 bytes.

The real fix is upstream: ship WOFF2 as separate files, drop the unused icon
variants, and split Latin and Devanagari by `unicode-range`. Note that
`font-display: swap` is already set on all seven faces and cannot help, because
the fonts are inlined into the blocking stylesheet — there is no separate
resource to swap in.

---

## Design system

All UI is built with the UX4G Design System via npm `ux4g-web-components@2.1.0`,
against the contract in `.claude/skills/ux4g-design/Design.md`. The default UX4G
theme is used; there are no brand colour overrides.

No second CSS framework is present, and no UX4G component is rebuilt with custom
markup. Custom CSS is limited to `frontend/src/styles/app.css` — a page shell, a
reading-width container, a screen-reader utility, a skip link, a quiet footer,
the logo's brand colour, and the contrast repoint above. Each carries an inline
note saying which UX4G capability is missing.

Sutradhar is a product built with UX4G, not a government portal. It does not
carry a national emblem, a ministry masthead, or a "Government of India"
attribution, because it is a demonstration system and claiming otherwise would
be untrue.

### The logo

A sūtradhāra is the one who holds the thread — the stage-manager of a Sanskrit
play, who ties the parts into a whole without performing it. The mark draws that
thread as an S with a bead at the tail where it is held, which is also the
product's job: gather the separate checks, hold them, hand them to a person.

It is one inline SVG using `currentColor`, so a single asset serves both themes,
and the wordmark is live text in Noto Sans SemiBold rather than outlined paths.
The mark is strokes on a transparent ground with no knocked-out counters,
because UX4G applies `filter: brightness(0) invert(1)` to `.ux4g-navbar-logo` in
dark mode — every opaque pixel becomes white, so the mark has to read as a
silhouette.
