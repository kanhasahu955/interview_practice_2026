from app.config import get_settings


class MetaService:
    def health(self) -> dict[str, str]:
        return {"status": "ok"}

    def service_map(self) -> dict[str, list[str] | str]:
        s = get_settings()
        return {
            "domains": [
                "auth — users, JWT",
                "blog — posts",
                "topics — learning_topics",
                "syllabus — modules + items",
                "coding — problems",
                "qa — questions + answers",
                "references — links",
            ],
            "api_prefix": s.api_v1_prefix,
        }


_meta: MetaService | None = None


def get_meta_service() -> MetaService:
    global _meta
    if _meta is None:
        _meta = MetaService()
    return _meta
