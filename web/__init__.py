"""
Web package initialization and public interface.
"""

from .router import Router
from .routes import create_router
from .server import run_server, AppRequestHandler

__all__ = [
    "Router",
    "create_router",
    "run_server",
    "AppRequestHandler"
]
