from app.routes.github import router as github_router
from app.routes.health import router as health_router
from app.routes.log_parser import router as parser_router
from app.routes.root import router as root_router

__all__ = ["github_router", "health_router", "parser_router", "root_router"]
