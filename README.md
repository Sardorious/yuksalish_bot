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
