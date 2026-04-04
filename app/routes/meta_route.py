from fastapi import APIRouter

from app.services.meta_service import get_meta_service


class MetaRoutes:
    def __init__(self) -> None:
        self.router = APIRouter()
        self._svc = get_meta_service()
        self._register()

    def _register(self) -> None:
        r = self.router
        svc = self._svc

        @r.get(
            "/health",
            summary="API health snapshot",
            description=(
                "### Purpose\n"
                "JSON health check for the API layer (distinct from plain `GET /health` on the app root).\n\n"
                "### What this endpoint does\n"
                "Returns whatever **meta_service.health()** defines — useful for richer probes."
            ),
            response_description="Arbitrary JSON health payload from the meta service.",
        )
        async def health():
            return svc.health()

        @r.get(
            "/services",
            summary="Service map",
            description=(
                "### Purpose\n"
                "Discover which logical **services** / route groups exist.\n\n"
                "### What this endpoint does\n"
                "Returns **meta_service.service_map()** — names, paths, or labels for debugging and docs."
            ),
            response_description="JSON map of service identifiers to metadata.",
        )
        async def service_map():
            return svc.service_map()
