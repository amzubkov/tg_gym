import aiosqlite
from config import DATABASE_PATH


async def init_db():
    """Инициализация базы данных и создание таблиц."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Программы тренировок (например, "Зубкова")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS programs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        """)

        # Дни в программе
        await db.execute("""
            CREATE TABLE IF NOT EXISTS days (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                program_id INTEGER NOT NULL,
                day_number INTEGER NOT NULL,
                name TEXT,
                FOREIGN KEY (program_id) REFERENCES programs(id) ON DELETE CASCADE,
                UNIQUE(program_id, day_number)
            )
        """)

        # Упражнения
        await db.execute("""
            CREATE TABLE IF NOT EXISTS exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                image_file_id TEXT,
                order_num INTEGER DEFAULT 0,
                tag TEXT,
                FOREIGN KEY (day_id) REFERENCES days(id) ON DELETE CASCADE
            )
        """)

        # Миграция: добавить tag если нет
        try:
            await db.execute("ALTER TABLE exercises ADD COLUMN tag TEXT")
        except Exception:
            pass  # Колонка уже существует

        # Логи тренировок
        await db.execute("""
            CREATE TABLE IF NOT EXISTS workout_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                exercise_id INTEGER NOT NULL,
                weight REAL NOT NULL,
                reps INTEGER NOT NULL,
                set_num INTEGER DEFAULT 1,
                date TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE
            )
        """)

        # Прогресс пользователя по программе
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_progress (
                user_id INTEGER PRIMARY KEY,
                program_id INTEGER,
                current_day_num INTEGER DEFAULT 1,
                last_completed_date TEXT,
                is_finished INTEGER DEFAULT 0,
                FOREIGN KEY (program_id) REFERENCES programs(id) ON DELETE SET NULL
            )
        """)

        # Свои упражнения (не из программы)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS custom_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                weight REAL,
                reps INTEGER,
                duration_minutes INTEGER,
                set_num INTEGER DEFAULT 1,
                date TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Миграция: добавить duration_minutes если нет
        try:
            await db.execute("ALTER TABLE custom_logs ADD COLUMN duration_minutes INTEGER")
        except Exception:
            pass  # Колонка уже существует

        # Разрешённые пользователи
        await db.execute("""
            CREATE TABLE IF NOT EXISTS allowed_users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                approved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


        await db.commit()


async def get_db():
    """Получение соединения с БД."""
    return await aiosqlite.connect(DATABASE_PATH)


# ==================== PROGRAMS ====================

async def create_program(name: str) -> int:
    """Создать программу тренировок."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO programs (name) VALUES (?)", (name,)
        )
        await db.commit()
        return cursor.lastrowid


async def get_all_programs() -> list:
    """Получить все программы."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM programs ORDER BY name")
        return await cursor.fetchall()


async def get_program(program_id: int) -> dict | None:
    """Получить программу по ID."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM programs WHERE id = ?", (program_id,)
        )
        return await cursor.fetchone()


async def delete_program(program_id: int):
    """Удалить программу."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM programs WHERE id = ?", (program_id,))
        await db.commit()


# ==================== DAYS ====================

async def create_day(program_id: int, day_number: int, name: str = None) -> int:
    """Создать день в программе."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO days (program_id, day_number, name) VALUES (?, ?, ?)",
            (program_id, day_number, name)
        )
        await db.commit()
        return cursor.lastrowid


async def get_days_by_program(program_id: int) -> list:
    """Получить все дни программы."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM days WHERE program_id = ? ORDER BY day_number",
            (program_id,)
        )
        return await cursor.fetchall()


async def get_day(day_id: int) -> dict | None:
    """Получить день по ID."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM days WHERE id = ?", (day_id,)
        )
        return await cursor.fetchone()


async def delete_day(day_id: int):
    """Удалить день."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM days WHERE id = ?", (day_id,))
        await db.commit()


# ==================== EXERCISES ====================

async def create_exercise(
    day_id: int,
    name: str,
    description: str = None,
    image_file_id: str = None,
    order_num: int = 0,
    tag: str = None
) -> int:
    """Создать упражнение."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO exercises (day_id, name, description, image_file_id, order_num, tag)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (day_id, name, description, image_file_id, order_num, tag.lower() if tag else None)
        )
        await db.commit()
        return cursor.lastrowid


async def get_exercises_by_day(day_id: int) -> list:
    """Получить все упражнения дня."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM exercises WHERE day_id = ? ORDER BY order_num, id",
            (day_id,)
        )
        return await cursor.fetchall()


async def get_exercise(exercise_id: int) -> dict | None:
    """Получить упражнение по ID."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM exercises WHERE id = ?", (exercise_id,)
        )
        return await cursor.fetchone()


async def update_exercise_image(exercise_id: int, image_file_id: str):
    """Обновить картинку упражнения."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE exercises SET image_file_id = ? WHERE id = ?",
            (image_file_id, exercise_id)
        )
        await db.commit()


async def delete_exercise(exercise_id: int):
    """Удалить упражнение."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM exercises WHERE id = ?", (exercise_id,))
        await db.commit()


# ==================== WORKOUT LOGS ====================

async def log_workout(
    user_id: int,
    exercise_id: int,
    weight: float,
    reps: int,
    set_num: int,
    date: str
) -> int:
    """Записать выполнение упражнения."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO workout_logs (user_id, exercise_id, weight, reps, set_num, date)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, exercise_id, weight, reps, set_num, date)
        )
        await db.commit()
        return cursor.lastrowid


async def get_exercise_history(user_id: int, exercise_id: int, limit: int = 20) -> list:
    """Получить историю выполнения упражнения пользователем."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT * FROM workout_logs
               WHERE user_id = ? AND exercise_id = ?
               ORDER BY date DESC, set_num
               LIMIT ?""",
            (user_id, exercise_id, limit)
        )
        return await cursor.fetchall()


async def get_last_workout(user_id: int, exercise_id: int) -> list:
    """Получить последнюю тренировку по упражнению."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        # Находим последнюю дату
        cursor = await db.execute(
            """SELECT date FROM workout_logs
               WHERE user_id = ? AND exercise_id = ?
               ORDER BY date DESC LIMIT 1""",
            (user_id, exercise_id)
        )
        row = await cursor.fetchone()
        if not row:
            return []

        last_date = row["date"]
        cursor = await db.execute(
            """SELECT * FROM workout_logs
               WHERE user_id = ? AND exercise_id = ? AND date = ?
               ORDER BY set_num""",
            (user_id, exercise_id, last_date)
        )
        return await cursor.fetchall()


async def get_user_stats(user_id: int) -> dict:
    """Получить статистику пользователя (workout_logs + custom_logs)."""
    from datetime import date

    today = date.today()
    month_start = today.replace(day=1).isoformat()

    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Тренировок в этом месяце
        cursor = await db.execute(
            """SELECT COUNT(DISTINCT date) FROM (
                SELECT date FROM workout_logs WHERE user_id = ? AND date >= ?
                UNION
                SELECT date FROM custom_logs WHERE user_id = ? AND date >= ?
            )""",
            (user_id, month_start, user_id, month_start)
        )
        month_workouts = (await cursor.fetchone())[0]

        # Последняя тренировка
        cursor = await db.execute(
            """SELECT MAX(date) FROM (
                SELECT date FROM workout_logs WHERE user_id = ?
                UNION
                SELECT date FROM custom_logs WHERE user_id = ?
            )""",
            (user_id, user_id)
        )
        last_date_row = await cursor.fetchone()
        last_date = last_date_row[0] if last_date_row and last_date_row[0] else None

        # Считаем дни с последней тренировки
        days_ago = None
        if last_date:
            last = date.fromisoformat(last_date)
            days_ago = (today - last).days

        return {
            "month_workouts": month_workouts,
            "days_ago": days_ago
        }


async def delete_workout_log(log_id: int, user_id: int):
    """Удалить запись о тренировке (только свою)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "DELETE FROM workout_logs WHERE id = ? AND user_id = ?",
            (log_id, user_id)
        )
        await db.commit()


# ==================== USER PROGRESS ====================

async def get_user_progress(user_id: int) -> dict | None:
    """Получить прогресс пользователя."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM user_progress WHERE user_id = ?",
            (user_id,)
        )
        return await cursor.fetchone()


async def set_user_program(user_id: int, program_id: int):
    """Установить активную программу для пользователя (начать с дня 1)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """INSERT INTO user_progress (user_id, program_id, current_day_num, is_finished)
               VALUES (?, ?, 1, 0)
               ON CONFLICT(user_id) DO UPDATE SET
                   program_id = excluded.program_id,
                   current_day_num = 1,
                   is_finished = 0,
                   last_completed_date = NULL""",
            (user_id, program_id)
        )
        await db.commit()


async def complete_day(user_id: int) -> bool:
    """Закончить текущий день. Возвращает True если программа завершена."""
    from datetime import date
    today = date.today().isoformat()

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Получаем текущий прогресс
        cursor = await db.execute(
            "SELECT * FROM user_progress WHERE user_id = ?",
            (user_id,)
        )
        progress = await cursor.fetchone()

        if not progress or not progress["program_id"]:
            return False

        # Считаем сколько дней в программе
        cursor = await db.execute(
            "SELECT COUNT(*) FROM days WHERE program_id = ?",
            (progress["program_id"],)
        )
        total_days = (await cursor.fetchone())[0]

        current_day = progress["current_day_num"]
        next_day = current_day + 1

        if next_day > total_days:
            # Программа завершена
            await db.execute(
                """UPDATE user_progress
                   SET is_finished = 1, last_completed_date = ?
                   WHERE user_id = ?""",
                (today, user_id)
            )
            await db.commit()
            return True
        else:
            # Переходим к следующему дню
            await db.execute(
                """UPDATE user_progress
                   SET current_day_num = ?, last_completed_date = ?
                   WHERE user_id = ?""",
                (next_day, today, user_id)
            )
            await db.commit()
            return False


async def get_current_day_info(user_id: int) -> dict | None:
    """Получить информацию о текущем дне пользователя."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Получаем прогресс
        cursor = await db.execute(
            "SELECT * FROM user_progress WHERE user_id = ?",
            (user_id,)
        )
        progress = await cursor.fetchone()

        if not progress or not progress["program_id"] or progress["is_finished"]:
            return None

        # Получаем программу
        cursor = await db.execute(
            "SELECT * FROM programs WHERE id = ?",
            (progress["program_id"],)
        )
        program = await cursor.fetchone()

        if not program:
            return None

        # Получаем день
        cursor = await db.execute(
            "SELECT * FROM days WHERE program_id = ? AND day_number = ?",
            (progress["program_id"], progress["current_day_num"])
        )
        day = await cursor.fetchone()

        if not day:
            return None

        # Считаем всего дней
        cursor = await db.execute(
            "SELECT COUNT(*) FROM days WHERE program_id = ?",
            (progress["program_id"],)
        )
        total_days = (await cursor.fetchone())[0]

        return {
            "program_name": program["name"],
            "program_id": program["id"],
            "day_id": day["id"],
            "day_number": day["day_number"],
            "day_name": day["name"],
            "total_days": total_days,
            "last_completed_date": progress["last_completed_date"]
        }


async def clear_user_progress(user_id: int):
    """Сбросить прогресс пользователя."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "DELETE FROM user_progress WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()


# ==================== CUSTOM LOGS (свои упражнения) ====================

async def log_custom_exercise(
    user_id: int,
    name: str,
    date: str,
    weight: float = None,
    reps: int = None,
    duration_minutes: int = None
) -> int:
    """Записать своё упражнение (силовое или кардио)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Считаем номер подхода за сегодня для этого упражнения
        cursor = await db.execute(
            """SELECT COUNT(*) FROM custom_logs
               WHERE user_id = ? AND name = ? AND date = ?""",
            (user_id, name, date)
        )
        count = (await cursor.fetchone())[0]
        set_num = count + 1

        cursor = await db.execute(
            """INSERT INTO custom_logs (user_id, name, weight, reps, duration_minutes, set_num, date)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, name, weight, reps, duration_minutes, set_num, date)
        )
        await db.commit()
        return cursor.lastrowid


async def get_custom_history(user_id: int, name: str, limit: int = 20) -> list:
    """Получить историю своего упражнения."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT * FROM custom_logs
               WHERE user_id = ? AND name = ?
               ORDER BY date DESC, set_num
               LIMIT ?""",
            (user_id, name, limit)
        )
        return await cursor.fetchall()


async def get_recent_custom_exercises(user_id: int, limit: int = 5) -> list:
    """Получить последние свои упражнения (уникальные названия)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """SELECT DISTINCT name FROM custom_logs
               WHERE user_id = ?
               ORDER BY date DESC, id DESC
               LIMIT ?""",
            (user_id, limit)
        )
        rows = await cursor.fetchall()
        return [row[0] for row in rows]


async def get_today_custom_logs(user_id: int, date: str) -> list:
    """Получить свои упражнения за сегодня."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT * FROM custom_logs
               WHERE user_id = ? AND date = ?
               ORDER BY id""",
            (user_id, date)
        )
        return await cursor.fetchall()


async def get_daily_activity(user_id: int, date: str) -> dict:
    """Получить активность за конкретный день."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Упражнения из программы
        cursor = await db.execute(
            """SELECT e.name, wl.weight, wl.reps, wl.set_num
               FROM workout_logs wl
               JOIN exercises e ON wl.exercise_id = e.id
               WHERE wl.user_id = ? AND wl.date = ?
               ORDER BY wl.id""",
            (user_id, date)
        )
        workout_rows = await cursor.fetchall()

        # Свои упражнения
        cursor = await db.execute(
            """SELECT name, weight, reps, duration_minutes, set_num
               FROM custom_logs
               WHERE user_id = ? AND date = ?
               ORDER BY id""",
            (user_id, date)
        )
        custom_rows = await cursor.fetchall()

        return {
            "workouts": [dict(r) for r in workout_rows],
            "custom": [dict(r) for r in custom_rows]
        }


# ==================== ALLOWED USERS ====================

async def is_user_allowed(user_id: int) -> bool:
    """Проверить, разрешён ли пользователь."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT 1 FROM allowed_users WHERE user_id = ?",
            (user_id,)
        )
        return await cursor.fetchone() is not None


async def add_allowed_user(user_id: int, username: str = None, full_name: str = None):
    """Добавить пользователя в список разрешённых."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """INSERT OR REPLACE INTO allowed_users (user_id, username, full_name)
               VALUES (?, ?, ?)""",
            (user_id, username, full_name)
        )
        await db.commit()


async def remove_allowed_user(user_id: int):
    """Удалить пользователя из списка разрешённых."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "DELETE FROM allowed_users WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()


async def get_all_allowed_users() -> list:
    """Получить всех разрешённых пользователей."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM allowed_users ORDER BY approved_at DESC"
        )
        return await cursor.fetchall()


# ==================== TAGS ====================

async def get_all_tags() -> list:
    """Получить все уникальные теги из упражнений."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """SELECT tag, COUNT(*) as exercise_count
               FROM exercises
               WHERE tag IS NOT NULL AND tag != ''
               GROUP BY tag
               ORDER BY tag"""
        )
        rows = await cursor.fetchall()
        return [{"name": row[0], "exercise_count": row[1]} for row in rows]


async def get_exercises_by_tag(tag: str) -> list:
    """Получить все упражнения с данным тегом (из всех программ)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT e.*, d.name as day_name, d.day_number, p.name as program_name
               FROM exercises e
               JOIN days d ON e.day_id = d.id
               JOIN programs p ON d.program_id = p.id
               WHERE LOWER(e.tag) = LOWER(?)
               ORDER BY p.name, d.day_number, e.order_num""",
            (tag,)
        )
        return await cursor.fetchall()


async def update_exercise_tag(exercise_id: int, tag: str | None):
    """Обновить тег упражнения."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE exercises SET tag = ? WHERE id = ?",
            (tag.lower() if tag else None, exercise_id)
        )
        await db.commit()