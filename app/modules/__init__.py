"""Feature modules (ORM models per domain). Import side-effects register SQLModel metadata."""


def import_all_models() -> None:
    import app.modules.auth.model  # noqa: F401
    import app.modules.blog.model  # noqa: F401
    import app.modules.coding.model  # noqa: F401
    import app.modules.qa.model  # noqa: F401
    import app.modules.references.model  # noqa: F401
    import app.modules.syllabus.model  # noqa: F401
    import app.modules.topics.model  # noqa: F401
