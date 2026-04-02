import aiosqlite
from datetime import date
import sqlite3

DB_PATH = "exercise_bot.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                name        TEXT NOT NULL,
                class_name  TEXT NOT NULL,
                role        TEXT NOT NULL DEFAULT 'student',
                phone       TEXT,
                is_active   BOOLEAN NOT NULL DEFAULT 1
            )
        """)
        # DB migration manually if columns don't exist
        try:
            await db.execute("ALTER TABLE users ADD COLUMN phone TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            await db.execute("ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1")
        except sqlite3.OperationalError:
            pass

        await db.execute("""
            CREATE TABLE IF NOT EXISTS exercises (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                name   TEXT UNIQUE NOT NULL,
                active BOOLEAN NOT NULL DEFAULT 1
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER NOT NULL,
                date          DATE NOT NULL,
                type          TEXT NOT NULL,          -- 'exercise' | 'reading'
                exercise_id   INTEGER,
                book_name     TEXT,
                pages_read    INTEGER,
                photo_file_id TEXT,                   -- Telegram file_id for book photo
                FOREIGN KEY (user_id)     REFERENCES users(telegram_id),
                FOREIGN KEY (exercise_id) REFERENCES exercises(id)
            )
        """)
        # Separate table: one exercise video per student per day
        await db.execute("""
            CREATE TABLE IF NOT EXISTS exercise_media (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date    DATE NOT NULL,
                file_id TEXT NOT NULL,
                UNIQUE (user_id, date),
                FOREIGN KEY (user_id) REFERENCES users(telegram_id)
            )
        """)
        # Per-class Telegram group chat IDs
        await db.execute("""
            CREATE TABLE IF NOT EXISTS class_groups (
                class_name TEXT PRIMARY KEY,
                chat_id    INTEGER NOT NULL
            )
        """)
        # Reminders table for daily notifications
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                user_id INTEGER PRIMARY KEY,
                time    TEXT NOT NULL,  -- HH:MM format
                enabled BOOLEAN NOT NULL DEFAULT 1
            )
        """)
        # Predefined classes for registration
        await db.execute("""
            CREATE TABLE IF NOT EXISTS classes (
                name TEXT PRIMARY KEY
            )
        """)
        # Track which students have pressed 'Tayyor' (submitted) today
        await db.execute("""
            CREATE TABLE IF NOT EXISTS exercise_submitted (
                user_id INTEGER NOT NULL,
                date    DATE NOT NULL,
                PRIMARY KEY (user_id, date),
                FOREIGN KEY (user_id) REFERENCES users(telegram_id)
            )
        """)
        # Predefined books for reading log
        await db.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """)
        
        # Migration: populate classes and books table from existing data
        await db.execute("""
            INSERT OR IGNORE INTO classes (name)
            SELECT DISTINCT class_name FROM users WHERE class_name IS NOT NULL
            UNION
            SELECT DISTINCT class_name FROM class_groups WHERE class_name IS NOT NULL
        """)
        await db.execute("""
            INSERT OR IGNORE INTO books (name)
            SELECT DISTINCT book_name FROM submissions WHERE type = 'reading' AND book_name IS NOT NULL
        """)
        
        await db.commit()


# ── User operations ────────────────────────────────────────────────────────────

async def get_user(telegram_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ) as cur:
            return await cur.fetchone()


async def create_user(telegram_id: int, name: str, class_name: str, phone: str = None, role: str = "student"):
    async with aiosqlite.connect(DB_PATH) as db:
        # Check if user exists
        async with db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)) as cur:
            existing = await cur.fetchone()
        
        if existing:
            await db.execute(
                "UPDATE users SET name = ?, class_name = ?, phone = COALESCE(?, phone), role = ?, is_active = 1 WHERE telegram_id = ?",
                (name, class_name, phone, role, telegram_id),
            )
        else:
            await db.execute(
                "INSERT INTO users (telegram_id, name, class_name, phone, role, is_active) VALUES (?, ?, ?, ?, ?, 1)",
                (telegram_id, name, class_name, phone, role),
            )
        await db.commit()


async def get_all_students():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE role = 'student' AND is_active = 1 ORDER BY class_name, name"
        ) as cur:
            return await cur.fetchall()

async def get_students_by_class(class_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE role = 'student' AND class_name = ? AND is_active = 1 ORDER BY name",
            (class_name,)
        ) as cur:
            return await cur.fetchall()

async def deactivate_user(telegram_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_active = 0 WHERE telegram_id = ?", (telegram_id,))
        await db.commit()

async def update_user_class(telegram_id: int, new_class_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET class_name = ? WHERE telegram_id = ?", (new_class_name, telegram_id))
        await db.commit()

async def promote_user(telegram_id: int, role: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET role = ? WHERE telegram_id = ?", (role, telegram_id)
        )
        await db.commit()


# ── Exercise operations ────────────────────────────────────────────────────────

async def add_exercise(name: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("INSERT INTO exercises (name) VALUES (?)", (name,))
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def get_active_exercises():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM exercises WHERE active = 1 ORDER BY name"
        ) as cur:
            return await cur.fetchall()


async def get_all_exercises():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM exercises ORDER BY name") as cur:
            return await cur.fetchall()


async def delete_exercise(exercise_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE exercises SET active = 0 WHERE id = ?", (exercise_id,)
        )
        await db.commit()


async def update_exercise(exercise_id: int, new_name: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "UPDATE exercises SET name = ? WHERE id = ?", (new_name, exercise_id)
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


# ── Submission operations ──────────────────────────────────────────────────────

async def get_student_exercise_ids_today(user_id: int, target_date: date | None = None) -> list[int]:
    if target_date is None:
        target_date = date.today()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT exercise_id FROM submissions WHERE user_id = ? AND date = ? AND type = 'exercise'",
            (user_id, target_date.isoformat()),
        ) as cur:
            rows = await cur.fetchall()
            return [r["exercise_id"] for r in rows]


async def has_submitted_exercises_today(user_id: int, target_date: date | None = None) -> bool:
    """Returns True if student already pressed 'Tayyor' (submitted) today."""
    if target_date is None:
        target_date = date.today()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM exercise_submitted WHERE user_id = ? AND date = ?",
            (user_id, target_date.isoformat()),
        ) as cur:
            return await cur.fetchone() is not None


async def mark_exercises_submitted(user_id: int, target_date: date | None = None):
    """Mark that student has submitted exercises for today."""
    if target_date is None:
        target_date = date.today()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO exercise_submitted (user_id, date) VALUES (?, ?)",
            (user_id, target_date.isoformat()),
        )
        await db.commit()


async def unmark_exercises_submitted(user_id: int, target_date: date | None = None):
    """Allow student to re-edit exercises (remove submitted flag)."""
    if target_date is None:
        target_date = date.today()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM exercise_submitted WHERE user_id = ? AND date = ?",
            (user_id, target_date.isoformat()),
        )
        await db.commit()


async def toggle_exercise_submission(user_id: int, exercise_id: int, target_date: date | None = None) -> bool:
    """Returns True if added, False if removed."""
    if target_date is None:
        target_date = date.today()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id FROM submissions WHERE user_id = ? AND date = ? AND type = 'exercise' AND exercise_id = ?",
            (user_id, target_date.isoformat(), exercise_id),
        ) as cur:
            existing = await cur.fetchone()
        if existing:
            await db.execute("DELETE FROM submissions WHERE id = ?", (existing[0],))
        else:
            await db.execute(
                "INSERT INTO submissions (user_id, date, type, exercise_id) VALUES (?, ?, 'exercise', ?)",
                (user_id, target_date.isoformat(), exercise_id),
            )
        await db.commit()
        return existing is None


async def save_exercise_video(user_id: int, file_id: str, target_date: date | None = None):
    if target_date is None:
        target_date = date.today()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO exercise_media (user_id, date, file_id) VALUES (?, ?, ?)",
            (user_id, target_date.isoformat(), file_id),
        )
        await db.commit()


async def get_exercise_video(user_id: int, target_date: date | None = None) -> str | None:
    if target_date is None:
        target_date = date.today()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT file_id FROM exercise_media WHERE user_id = ? AND date = ?",
            (user_id, target_date.isoformat()),
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else None


async def add_reading_submission(
    user_id: int,
    book_name: str,
    pages_read: int,
    photo_file_id: str | None = None,
    target_date: date | None = None,
):
    if target_date is None:
        target_date = date.today()
    async with aiosqlite.connect(DB_PATH) as db:
        # Replace any existing reading entry for this day
        await db.execute(
            "DELETE FROM submissions WHERE user_id = ? AND date = ? AND type = 'reading'",
            (user_id, target_date.isoformat()),
        )
        await db.execute(
            "INSERT INTO submissions (user_id, date, type, book_name, pages_read, photo_file_id) "
            "VALUES (?, ?, 'reading', ?, ?, ?)",
            (user_id, target_date.isoformat(), book_name, pages_read, photo_file_id),
        )
        await db.commit()


async def get_reading_today(user_id: int, target_date: date | None = None):
    if target_date is None:
        target_date = date.today()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT book_name, pages_read, photo_file_id FROM submissions "
            "WHERE user_id = ? AND date = ? AND type = 'reading'",
            (user_id, target_date.isoformat()),
        ) as cur:
            return await cur.fetchone()


# ── Report operations ──────────────────────────────────────────────────────────

async def get_today_media_list(target_date=None) -> dict:
    """Returns all students who uploaded video or book photo today."""
    if target_date is None:
        target_date = date.today()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT u.name, u.class_name, em.file_id as video_file_id
               FROM exercise_media em
               JOIN users u ON u.telegram_id = em.user_id
               WHERE em.date = ? AND u.is_active = 1
               ORDER BY u.class_name, u.name""",
            (target_date.isoformat(),),
        ) as cur:
            videos = [dict(r) for r in await cur.fetchall()]
        async with db.execute(
            """SELECT u.name, u.class_name, s.book_name, s.pages_read, s.photo_file_id
               FROM submissions s
               JOIN users u ON u.telegram_id = s.user_id
               WHERE s.date = ? AND s.type = 'reading' AND s.photo_file_id IS NOT NULL AND u.is_active = 1
               ORDER BY u.class_name, u.name""",
            (target_date.isoformat(),),
        ) as cur:
            photos = [dict(r) for r in await cur.fetchall()]
        return {"videos": videos, "photos": photos}


async def get_report_data(target_date: date) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE role = 'student' AND is_active = 1 ORDER BY class_name, name"
        ) as cur:
            students = await cur.fetchall()

        result = []
        for student in students:
            uid = student["telegram_id"]

            # 1. Exercises done
            async with db.execute(
                """SELECT e.name FROM submissions s
                   JOIN exercises e ON e.id = s.exercise_id
                   WHERE s.user_id = ? AND s.date = ? AND s.type = 'exercise'""",
                (uid, target_date.isoformat()),
            ) as cur:
                exercises = [r["name"] for r in await cur.fetchall()]

            # 2. Check for exercise skip
            async with db.execute(
                "SELECT 1 FROM submissions WHERE user_id = ? AND date = ? AND type = 'exercise_skip'",
                (uid, target_date.isoformat()),
            ) as cur:
                exercise_skip = await cur.fetchone() is not None

            # 3. Exercise video
            async with db.execute(
                "SELECT file_id FROM exercise_media WHERE user_id = ? AND date = ?",
                (uid, target_date.isoformat()),
            ) as cur:
                ex_media = await cur.fetchone()

            # 4. Reading
            async with db.execute(
                "SELECT type, book_name, pages_read, photo_file_id FROM submissions "
                "WHERE user_id = ? AND date = ? AND (type = 'reading' OR type = 'reading_skip')",
                (uid, target_date.isoformat()),
            ) as cur:
                reading_row = await cur.fetchone()
            
            reading_data = None
            if reading_row:
                if reading_row["type"] == "reading_skip":
                    reading_data = {"book_name": "Bajarmadi 🚫", "pages_read": 0, "photo_file_id": None}
                else:
                    reading_data = dict(reading_row)

            # Combined result
            res_exercises = exercises
            if not exercises and exercise_skip:
                res_exercises = ["Bajarmadi 🚫"]

            result.append(
                {
                    "name": student["name"],
                    "class_name": student["class_name"],
                    "telegram_id": uid,
                    "exercises": res_exercises,
                    "exercise_video": ex_media["file_id"] if ex_media else None,
                    "reading": reading_data,
                }
            )

        return result


async def get_missing_students(target_date: date | None = None):
    if target_date is None:
        target_date = date.today()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT u.* FROM users u
               WHERE u.role = 'student' AND u.is_active = 1
               AND u.telegram_id NOT IN (
                   SELECT DISTINCT user_id FROM submissions WHERE date = ?
               )
               ORDER BY u.class_name, u.name""",
            (target_date.isoformat(),),
        ) as cur:
            return await cur.fetchall()


# ── Class group operations ─────────────────────────────────────────────────────

async def set_class_group(class_name: str, chat_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO class_groups (class_name, chat_id) VALUES (?, ?)",
            (class_name, chat_id),
        )
        await db.commit()


async def get_class_group(class_name: str) -> int | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT chat_id FROM class_groups WHERE class_name = ?", (class_name,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else None


async def get_all_class_groups() -> dict[str, int]:
    """Returns {class_name: chat_id} for all linked classes."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT class_name, chat_id FROM class_groups") as cur:
            rows = await cur.fetchall()
            return {r["class_name"]: r["chat_id"] for r in rows}


async def get_distinct_classes() -> list[str]:
    """Returns all class names that have at least one student."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Check active users
        async with db.execute(
            "SELECT DISTINCT class_name FROM users WHERE role = 'student' AND is_active = 1 ORDER BY class_name"
        ) as cur:
            rows = await cur.fetchall()
            return [r[0] for r in rows]


# ── Class management ───────────────────────────────────────────────────────────

async def add_class(name: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("INSERT INTO classes (name) VALUES (?)", (name,))
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def get_all_classes() -> list[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT name FROM classes ORDER BY name") as cur:
            rows = await cur.fetchall()
            return [r[0] for r in rows]

# Reminder management
async def set_reminder(user_id: int, time_str: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO reminders (user_id, time, enabled) VALUES (?, ?, 1)",
            (user_id, time_str),
        )
        await db.commit()

async def get_reminder(user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT time, enabled FROM reminders WHERE user_id = ?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
            if row:
                return {"time": row["time"], "enabled": bool(row["enabled"])}
            return None

async def disable_reminder(user_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE reminders SET enabled = 0 WHERE user_id = ?", (user_id,)
        )
        await db.commit()

async def get_due_reminders(current_time: str) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT user_id FROM reminders WHERE time = ? AND enabled = 1", (current_time,)
        ) as cur:
            rows = await cur.fetchall()
            return [{"user_id": r["user_id"]} for r in rows]



async def delete_class(name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM classes WHERE name = ?", (name,))
        await db.commit()


async def update_class(old_name: str, new_name: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            # Atomic update across all tables using the class name
            await db.execute("UPDATE classes SET name = ? WHERE name = ?", (new_name, old_name))
            await db.execute("UPDATE users SET class_name = ? WHERE class_name = ?", (new_name, old_name))
            await db.execute("UPDATE class_groups SET class_name = ? WHERE class_name = ?", (new_name, old_name))
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


# ── Book management ────────────────────────────────────────────────────────────

async def add_book(name: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("INSERT INTO books (name) VALUES (?)", (name,))
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def get_all_books() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT id, name FROM books ORDER BY name") as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def get_book_by_id(book_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT id, name FROM books WHERE id = ?", (book_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def delete_book(book_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM books WHERE id = ?", (book_id,))
        await db.commit()


async def update_book(book_id: int, new_name: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            # We also update the book_name in submissions so history stays consistent
            await db.execute(
                "UPDATE submissions SET book_name = ? WHERE book_name = (SELECT name FROM books WHERE id = ?)",
                (new_name, book_id)
            )
            await db.execute("UPDATE books SET name = ? WHERE id = ?", (new_name, book_id))
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def get_last_read_book(user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT b.id, b.name FROM submissions s "
            "JOIN books b ON b.name = s.book_name "
            "WHERE s.user_id = ? AND s.type = 'reading' ORDER BY s.date DESC LIMIT 1",
            (user_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

async def delete_exercise_video_today(user_id: int, target_date: date | None = None):
    if target_date is None:
        target_date = date.today()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM exercise_media WHERE user_id = ? AND date = ?",
            (user_id, target_date.isoformat())
        )
        await db.commit()

async def reset_reading_today(user_id: int, target_date: date | None = None):
    if target_date is None:
        target_date = date.today()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM submissions WHERE user_id = ? AND date = ? AND type = 'reading'",
            (user_id, target_date.isoformat())
        )
        await db.commit()

async def add_skip_submission(user_id: int, skip_type: str, target_date: date | None = None):
    """
    skip_type should be 'exercise_skip' or 'reading_skip'.
    """
    if target_date is None:
        target_date = date.today()
    async with aiosqlite.connect(DB_PATH) as db:
        # For exercises: cleaning existing submissions
        if skip_type == "exercise_skip":
             await db.execute(
                 "DELETE FROM submissions WHERE user_id = ? AND date = ? AND type = 'exercise'",
                 (user_id, target_date.isoformat())
             )
             await db.execute(
                 "DELETE FROM exercise_media WHERE user_id = ? AND date = ?",
                 (user_id, target_date.isoformat())
             )
        # For reading: cleaning existing reading entries
        elif skip_type == "reading_skip":
             await db.execute(
                 "DELETE FROM submissions WHERE user_id = ? AND date = ? AND type = 'reading'",
                 (user_id, target_date.isoformat())
             )

        # Standard insertion for skip type
        await db.execute(
            "INSERT OR REPLACE INTO submissions (user_id, date, type) VALUES (?, ?, ?)",
            (user_id, target_date.isoformat(), skip_type)
        )
        await db.commit()
