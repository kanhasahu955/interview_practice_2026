from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import Settings
from app.errors import register_exception_handlers
from app.middlewares.auth_middleware import register_request_identity
from app.middlewares.cors import register_cors
from app.middlewares.rate_limit import limiter
from app.middlewares.security import register_security_headers
from app.middlewares.request_log import register_request_logging as _register_request_logging
from app.middlewares.validation import register_validation_middleware


def register_middleware_stack(app: FastAPI, settings: Settings) -> None:
    """Order: outer middlewares added last run first on incoming requests."""
    app.state.limiter = limiter
    register_exception_handlers(app, settings)
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    register_cors(app, settings)
    register_validation_middleware(app)
    register_request_identity(app)
    register_security_headers(app)
    _register_request_logging(app, settings)
