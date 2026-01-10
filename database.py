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
                FOREIGN KEY (day_id) REFERENCES days(id) ON DELETE CASCADE
            )
        """)

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
    order_num: int = 0
) -> int:
    """Создать упражнение."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO exercises (day_id, name, description, image_file_id, order_num)
               VALUES (?, ?, ?, ?, ?)""",
            (day_id, name, description, image_file_id, order_num)
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
    """Получить статистику пользователя."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Всего тренировок (уникальных дней)
        cursor = await db.execute(
            "SELECT COUNT(DISTINCT date) FROM workout_logs WHERE user_id = ?",
            (user_id,)
        )
        total_workouts = (await cursor.fetchone())[0]

        # Всего подходов
        cursor = await db.execute(
            "SELECT COUNT(*) FROM workout_logs WHERE user_id = ?",
            (user_id,)
        )
        total_sets = (await cursor.fetchone())[0]

        return {
            "total_workouts": total_workouts,
            "total_sets": total_sets
        }


async def delete_workout_log(log_id: int, user_id: int):
    """Удалить запись о тренировке (только свою)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "DELETE FROM workout_logs WHERE id = ? AND user_id = ?",
            (log_id, user_id)
        )
        await db.commit()