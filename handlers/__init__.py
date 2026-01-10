from handlers.start import router as start_router
from handlers.exercises import router as exercises_router
from handlers.tracking import router as tracking_router
from handlers.history import router as history_router
from handlers.admin import router as admin_router

__all__ = [
    "start_router",
    "exercises_router",
    "tracking_router",
    "history_router",
    "admin_router",
]