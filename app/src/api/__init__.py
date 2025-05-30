from fastapi import APIRouter

# Import all route modules
from .chat_routes import router as chat_router
from .performance_routes import router as performance_router
from .screening_routes import router as screening_router
from .admin_routes import router as admin_router
from .coaching_routes import router as coaching_router

# Create a combined router
router = APIRouter()

# Include all routers
router.include_router(chat_router)
router.include_router(performance_router)
router.include_router(screening_router)
router.include_router(admin_router)
router.include_router(coaching_router)
