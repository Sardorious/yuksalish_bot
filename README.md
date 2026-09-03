# Exercise Tracker Bot

A Telegram bot for tracking daily student exercises and reading progress, with optional media uploads (exercise videos & book photos).

---

## Features

| Role | Capabilities |
|------|-------------|
| 👑 Admin | Add/edit/delete exercises, view student list, promote users |
| 🧑‍🎓 Student | Register, log exercises (+ optional video), log reading (+ optional photo), view daily stats |
| 👩‍🏫 Teacher | Generate Excel reports by date, view who hasn't submitted |

---

## Quick Start

### 1. Prerequisites

- Python 3.11+
- A Telegram Bot Token from [@BotFather](https://t.me/BotFather)
- Your Telegram User ID (message [@userinfobot](https://t.me/userinfobot))

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
copy .env.example .env
```

Edit `.env`:
```
BOT_TOKEN=your_actual_token_here
ADMIN_IDS=your_telegram_id
TIMEZONE=Asia/Tashkent
```

> **Note:** all dates and reminder times use `TIMEZONE`, not the server clock.
> If the server runs in UTC and you leave this unset, the default
> `Asia/Tashkent` is used.

### 4. Run

```bash
python main.py
```

---

## Running with Docker (recommended for servers)

```bash
cp .env.example .env      # fill in BOT_TOKEN / ADMIN_IDS
mkdir -p data && sudo chown -R 1000:1000 data

docker build -t yuksalish_bot:local .
IMAGE=yuksalish_bot:local docker compose up -d
docker compose logs -f
```

The SQLite database and `bot.log` live in `./data`, which is bind-mounted into
the container — they survive rebuilds and image updates. **Back up this folder.**

| Command | What it does |
|---------|--------------|
| `docker compose logs -f` | Follow the bot's logs |
| `docker compose restart` | Restart without rebuilding |
| `docker compose down` | Stop and remove the container (data is kept) |
| `docker compose pull && docker compose up -d` | Update to the latest published image |

### Deployment (CI/CD)

Pushing to `main` triggers `.github/workflows/deploy.yml`, which:

1. builds the image and pushes it to GHCR as
   `ghcr.io/<owner>/<repo>:latest` **and** `:<commit-sha>`;
2. connects to the server over SSH, pulls that exact SHA-tagged image, tags it
   locally as `:latest`, and runs `docker compose up -d --no-deps yuksalish-bot`;
3. verifies the container is actually running and fails the job (printing the
   last 50 log lines) if it isn't.

**The server needs no git clone and no source code.** On the server the bot is
one service inside a shared `docker-compose.yml` that also runs other projects.
That file and the `.env` beside it are maintained by hand — **the deploy job
never writes to them**, and it uses `--no-deps` (and never `--remove-orphans`)
so neighbouring services are left untouched.

The service block there looks like this:

```yaml
  yuksalish-bot:
    image: ghcr.io/${GITHUB_REPOSITORY_OWNER}/yuksalish_bot:latest
    container_name: yuksalish-bot
    restart: unless-stopped
    environment:
      - BOT_TOKEN=${YUKSALISH_BOT_TOKEN}
      - ADMIN_IDS=${YUKSALISH_ADMIN_IDS}
      - SUPERUSER_IDS=${YUKSALISH_SUPERUSER_IDS}
      - TZ=Asia/Tashkent
    volumes:
      - yuksalish-bot-data:/app/data   # NB: /app/data, not /data
    networks: [apps]
```

Required repository secrets:

| Secret | Purpose |
|--------|---------|
| `SSH_HOST`, `SSH_USER`, `SSH_PRIVATE_KEY` | Server access |
| `DEPLOY_PATH` | Path to the checked-out repo on the server |
| `GHCR_TOKEN`, `GHCR_USERNAME` | *Optional* — only if the GHCR package is private |

The `.env` file is **not** managed by CI; it lives on the server and the deploy
job only checks that it exists.

To roll back, SSH in and run:

```bash
IMAGE=ghcr.io/<owner>/<repo>:<older-sha> docker compose up -d
```

---

## Commands

### Admin
| Command | Description |
|---------|-------------|
| `/addexercise <name>` | Add a new exercise |
| `/exercises` | List all active exercises |
| `/deleteexercise` | Delete an exercise (interactive) |
| `/editexercise` | Rename an exercise (interactive) |
| `/promote <user_id> <role>` | Change a user's role (`teacher`/`admin`/`student`) |
| `/students` | List all registered students with IDs |

### Teacher / Admin
| Command | Description |
|---------|-------------|
| `/report` | Excel report for today |
| `/report YYYY-MM-DD` | Excel report for a specific date |
| `/missing` | Students who haven't submitted today |
| `/missing YYYY-MM-DD` | Missing students for a specific date |

### Student (via menu buttons)
| Button | Action |
|--------|--------|
| 📋 Log Exercises | Multi-select checklist of today's exercises, then optional video upload |
| 📚 Log Reading | Enter book name + pages, then optional photo upload |
| 📊 My Stats Today | Summary of everything logged today |

---

## Excel Report Columns

| # | Name | Class | Exercises Done | Video | Book | Pages | Photo |
|---|------|-------|---------------|-------|------|-------|-------|

- **Video** — ✅ Yes / ❌ No (student uploaded exercise video)
- **Photo** — ✅ Yes / ❌ No (student uploaded book photo)

---

## Project Structure

```
exercise-bot/
├── main.py               # Entry point
├── config.py             # Loads .env
├── tzutil.py             # Timezone-aware today() / now()
├── Dockerfile            # Container image
├── docker-compose.yml    # Service definition (volume, env, restart policy)
├── database.py           # Async SQLite (aiosqlite)
├── keyboards.py          # Inline & reply keyboard builders
├── states.py             # FSM state groups
├── handlers/
│   ├── admin.py          # Admin commands
│   ├── student.py        # Student registration & logging
│   └── teacher.py        # Teacher reports
├── .env.example
└── requirements.txt
```

---

## Database

- `users` — telegram_id, name, class_name, role
- `exercises` — id, name, active (soft-delete)
- `submissions` — user_id, date, type, exercise_id, book_name, pages_read, photo_file_id
- `exercise_media` — user_id, date, file_id (one video per student per day)
