"""Map request URL path → logical API / surface name for logging."""

from app.constant.constants import ApiConstants


def infer_route_service(*, path: str, api_v1_prefix: str) -> str:
    """
    First path segment after `api_v1_prefix` for versioned APIs (auth, blog, topics, …).
    Static mounts, health, OpenAPI, WebSocket log stream, and HTML pages get stable labels.
    """
    raw = path.split("?", 1)[0]
    p = raw if raw.startswith("/") else f"/{raw}"
    v1 = api_v1_prefix.rstrip("/") or "/api/v1"

    if p == "/ws/logs" or p.startswith("/ws/logs/"):
        return "log-stream"
    if p.startswith("/ws/"):
        return "websocket"

    if p == ApiConstants.HEALTH_PATH or p.startswith(f"{ApiConstants.HEALTH_PATH}/"):
        return "health"
    if (
        p.startswith("/docs")
        or p.startswith("/redoc")
        or p == "/openapi.json"
        or p == "/reference"
        or p.startswith("/reference/")
    ):
        return "openapi"

    if p.startswith(ApiConstants.STATIC_MOUNT_PATH):
        return "static"
    if p.startswith(ApiConstants.MEDIA_MOUNT_PATH):
        return "media"
    if p.startswith(ApiConstants.DOCUMENTS_MOUNT_PATH):
        return "documents"
    if p.startswith(ApiConstants.STUDY_TOPICS_MOUNT_PATH):
        return "study-topics"

    if p == v1 or p == f"{v1}/":
        return "api-root"

    prefix_with_slash = f"{v1}/"
    if p.startswith(prefix_with_slash):
        rest = p[len(prefix_with_slash) :]
        segment = rest.split("/")[0] if rest else ""
        return segment if segment else "api"

    if p == "/" or p == "":
        return "home"
    return "pages"
