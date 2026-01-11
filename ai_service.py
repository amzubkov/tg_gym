"""AI сервис для генерации упражнений."""
import os
from openai import AsyncOpenAI

# DeepSeek API (OpenAI-compatible)
_client = None


def get_client():
    """Получить клиент API (ленивая инициализация)."""
    global _client
    api_key = os.environ.get('DEEPSEEK_API_KEY')
    if not api_key:
        return None
    if _client is None:
        _client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
    return _client

MUSCLE_GROUPS = {
    "chest": "грудь",
    "back": "спина",
    "shoulders": "плечи",
    "biceps": "бицепс",
    "triceps": "трицепс",
    "legs": "ноги",
    "abs": "пресс",
    "glutes": "ягодицы",
}

MUSCLE_GROUPS_RU = {v: k for k, v in MUSCLE_GROUPS.items()}


async def generate_exercises(muscles: list[str], count: int = 5) -> str | None:
    """
    Генерирует упражнения для выбранных мышц.

    Args:
        muscles: список мышц на русском (грудь, спина, бицепс...)
        count: количество упражнений

    Returns:
        Текст с упражнениями или None при ошибке
    """
    client = get_client()
    if not client:
        return None

    muscles_str = ", ".join(muscles)

    prompt = f"""Составь {count} упражнений для тренировки: {muscles_str}.

Формат ответа - только список упражнений:
1. Название упражнения - краткое описание техники (1 предложение)
2. ...

Без вступления и заключения. Только упражнения."""

    try:
        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": "Ты фитнес-тренер. Отвечай кратко и по делу на русском языке."
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"AI error: {e}")
        return None