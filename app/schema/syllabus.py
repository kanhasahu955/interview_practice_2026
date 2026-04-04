from pydantic import ConfigDict
from sqlmodel import Field, SQLModel


class SyllabusItemCreate(SQLModel):
    model_config = ConfigDict(
        json_schema_extra={
            "description": (
                "### Purpose\n"
                "Add a **lesson/item** under an existing syllabus **module**.\n\n"
                "### Request body\n"
                "Markdown **content_md** is the main material; **sort_order** controls order within the module.\n\n"
                "### What the API does\n"
                "Creates the item under **module_id** from the path; **404** if the module is missing."
            ),
        }
    )

    title: str = Field(description="Item heading (e.g. lesson title).")
    content_md: str = Field(description="Lesson content in **Markdown**.")
    sort_order: int = Field(default=0, description="Order within the parent module (lower first).")


class SyllabusItemOut(SQLModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"description": "One syllabus item belonging to a module."},
    )

    id: int = Field(description="Item id.")
    module_id: int = Field(description="Parent module id.")
    title: str = Field(description="Item title.")
    content_md: str = Field(description="Markdown body.")
    sort_order: int = Field(description="Sort key within module.")


class SyllabusModuleCreate(SQLModel):
    model_config = ConfigDict(
        json_schema_extra={
            "description": (
                "### Purpose\n"
                "Create a top-level **syllabus module** (chapter/section bucket).\n\n"
                "### What the API does\n"
                "Inserts a module you can later attach **items** to via the nested route."
            ),
        }
    )

    title: str = Field(description="Module name.")
    description: str | None = Field(default=None, description="Optional module summary.")
    sort_order: int = Field(default=0, description="Order among sibling modules.")


class SyllabusModuleOut(SQLModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "description": "Module with optional nested **items** when the service includes them.",
        },
    )

    id: int = Field(description="Module id.")
    title: str = Field(description="Module title.")
    description: str | None = Field(description="Optional description.")
    sort_order: int = Field(description="Sort order.")
    items: list[SyllabusItemOut] = Field(default_factory=list, description="Child items when expanded.")
