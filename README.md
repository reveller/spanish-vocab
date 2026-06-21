# Spanish Vocab Tracker

A local web app for practising Spanish vocabulary with flashcard-style reveal and audio pronunciation.

## Features

- Flashcard reveal: click English to show Spanish, click either to hide
- Audio pronunciation via browser Web Speech API (uses Google Español es-ES if available)
- Progress tracking per lesson (not started / still learning / mastered)
- Add new lessons and words from within the app
- Delete words or entire lessons
- Data persisted in SQLite — survives restarts
- Offline study support — browse lessons and reveal translations without connectivity (see [Offline Support](#offline-support))

## Quick Start (Local)

```bash
pip3 install -r requirements.txt
chmod +x start.sh
./start.sh
```

Open **http://localhost:5050** in your browser.

## Quick Start (Docker)

```bash
docker compose up --build
```

The app runs on **http://localhost:5050**. Data is stored in a named Docker volume (`vocab-data`) so it persists across container restarts.

## Architecture

| Component | Technology |
|-----------|-----------|
| Server | Flask + Gunicorn (1 worker, 2 threads) |
| Database | SQLite with WAL mode |
| Frontend | Vanilla HTML/CSS/JS |
| Deployment | Docker + docker-compose |

### Database

Two tables with a foreign key relationship:

- **lessons** — `id`, `title`, `progress`, `sort_order`
- **words** — `id`, `lesson_id` (FK), `en`, `es`, `sort_order`

On first run, `lessons.json` is imported as seed data. Subsequent starts skip seeding.

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Serves the frontend |
| `GET` | `/sw.js` | Service worker (offline support), served at root scope |
| `GET` | `/api/health` | Health check |
| `GET` | `/api/lessons` | List all lessons with words |
| `POST` | `/api/lessons` | Create a lesson |
| `DELETE` | `/api/lessons/:id` | Delete a lesson |
| `PUT` | `/api/lessons/:id/progress` | Update lesson progress |
| `POST` | `/api/lessons/:id/words` | Add a word to a lesson |
| `DELETE` | `/api/lessons/:id/words/:index` | Delete a word by index |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_PATH` | `/data/vocab.db` | Path to SQLite database file |
| `PORT` | `5050` | Server port (dev mode only) |
| `DEBUG` | `false` | Enable Flask debug mode |

## File Structure

```
app.py              # Flask routes
db.py               # SQLite data access layer
lessons.json        # Seed data (imported on first run)
start.sh            # Local dev launcher
requirements.txt    # Python dependencies
Dockerfile          # Container image
docker-compose.yml  # Container orchestration
static/index.html   # Frontend SPA
static/login.html   # Login page
static/sw.js        # Service worker (offline caching)
```

## Offline Support

The app stays usable for **studying** without an internet connection — handy
when you're away from connectivity (e.g. off-grid while cruising). A
[service worker](static/sw.js) (`static/sw.js`) caches the app shell, lesson
data, and fonts so the app loads and renders from cache when the network is
unreachable.

**What works offline (read-only):**

- Opening the app and browsing every lesson
- Revealing translations
- Audio pronunciation — *if* the device has an on-device Spanish voice
  installed (browsers that fetch voices from the cloud go silent offline)

**What requires connectivity:**

- Changing progress, and adding/deleting words or lessons. These are **not**
  queued — the UI shows an offline banner and refuses the change with a toast,
  so nothing is silently lost.
- The **first** visit on any device/browser must be online, to install the
  service worker and populate the cache.

### How it works

| Request | Strategy |
|---------|----------|
| App shell (navigation to `/`) | Network-first, fall back to cached `/` |
| `GET /api/lessons` | Network-first (fresh online), cached copy offline |
| Google Fonts | Cache-first (immutable) |
| Writes (`POST`/`PUT`/`DELETE`) | Pass through; synthetic `503 {"offline": true}` when unreachable |

The cache is versioned (`vocab-v1` in `static/sw.js`). Bump the version to
force old caches to be cleared on the next activation after changing cached
assets. The worker is served from the root path (`/sw.js`, not `/static/`) with
`Cache-Control: no-cache` so its scope can control `/` and updates are picked
up promptly.

> **Requires HTTPS.** Service workers only register over HTTPS (or `localhost`
> for development). The production deployment is already served over HTTPS.

> **Note:** Offline is read-only by design. An installable PWA (home-screen
> icon, fullscreen) is a possible future enhancement — the service worker here
> is the prerequisite.
