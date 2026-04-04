"""Browser HTML pages (Jinja2)."""

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from app.config import Settings


class PagesRoutes:
    def __init__(self, settings: Settings) -> None:
        self.router = APIRouter(tags=["PAGES"])
        self._templates = Jinja2Templates(directory=str(settings.templates_root))
        self._settings = settings
        self._register()

    def _register(self) -> None:
        r = self.router
        tpl = self._templates
        s = self._settings

        @r.get(
            "/",
            summary="Home page (HTML)",
            description=(
                "### Purpose\n"
                "Human-facing landing page for the product.\n\n"
                "### Response\n"
                "Not JSON — **text/html** from Jinja2 (**index.html**). "
                "Open `/` in a browser; Swagger **Try it out** will show raw HTML."
            ),
            response_description="HTML document (`text/html`).",
        )
        async def index(request: Request):
            return tpl.TemplateResponse(
                "index.html",
                {
                    "request": request,
                    "title": s.app_name,
                    "api_prefix": s.api_v1_prefix,
                },
            )
