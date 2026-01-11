from handlers.access import router as access_router
from handlers.start import router as start_router
from handlers.exercises import router as exercises_router
from handlers.tracking import router as tracking_router
from handlers.history import router as history_router
from handlers.admin import router as admin_router
from handlers.custom import router as custom_router
from handlers.ai_generate import router as ai_router

__all__ = [
    "access_router",
    "start_router",
    "exercises_router",
    "tracking_router",
    "history_router",
    "admin_router",
    "custom_router",
    "ai_router",
]