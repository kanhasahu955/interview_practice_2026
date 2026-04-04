from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db import get_db
from app.openapi_common import R_401, R_403, R_404, merge_responses
from app.deps import require_roles
from app.modules.auth.model import User, UserRole
from app.schema.syllabus import (
    SyllabusItemCreate,
    SyllabusItemOut,
    SyllabusModuleCreate,
    SyllabusModuleOut,
)
from app.services.syllabus_service import get_syllabus_service


class SyllabusRoutes:
    def __init__(self) -> None:
        self.router = APIRouter()
        self._svc = get_syllabus_service()
        self._register()

    def _register(self) -> None:
        r = self.router
        svc = self._svc

        @r.get(
            "/syllabus/modules",
            response_model=list[SyllabusModuleOut],
            summary="List syllabus modules",
            description=(
                "### Purpose\n"
                "Load the course outline (modules, often with nested **items**).\n\n"
                "### What this endpoint does\n"
                "Returns **SyllabusModuleOut** list — see schema for **items** array."
            ),
            response_description="Array of **SyllabusModuleOut**.",
        )
        async def list_modules(session: AsyncSession = Depends(get_db)):
            return await svc.list_modules(session)

        @r.post(
            "/syllabus/modules",
            response_model=SyllabusModuleOut,
            status_code=status.HTTP_201_CREATED,
            summary="Create syllabus module",
            description=(
                "### Purpose\n"
                "Add a chapter/section bucket before attaching **items**.\n\n"
                "### Request body\n"
                "**SyllabusModuleCreate** — **title**, optional **description**, **sort_order**.\n\n"
                "### Auth\n"
                "**Author** or **admin** JWT.\n\n"
                "### What this endpoint does\n"
                "Inserts module; returns **SyllabusModuleOut** (**201**)."
            ),
            responses=merge_responses(R_401, R_403),
            response_description="Created **SyllabusModuleOut**.",
        )
        async def create_module(
            body: SyllabusModuleCreate,
            session: AsyncSession = Depends(get_db),
            _: User = Depends(require_roles(UserRole.author)),
        ):
            return await svc.create_module(session, body)

        @r.post(
            "/syllabus/modules/{module_id}/items",
            response_model=SyllabusItemOut,
            status_code=status.HTTP_201_CREATED,
            summary="Create item under module",
            description=(
                "### Purpose\n"
                "Add a lesson row under an existing **module_id**.\n\n"
                "### Request body\n"
                "**SyllabusItemCreate** — **title**, **content_md**, **sort_order**.\n\n"
                "### What this endpoint does\n"
                "Creates child item; **404** if **module_id** unknown."
            ),
            responses=merge_responses(R_401, R_403, R_404),
            response_description="Created **SyllabusItemOut**.",
        )
        async def create_item(
            module_id: int,
            body: SyllabusItemCreate,
            session: AsyncSession = Depends(get_db),
            _: User = Depends(require_roles(UserRole.author)),
        ):
            try:
                return await svc.create_item(session, module_id, body)
            except ValueError as e:
                if str(e) == "module_not_found":
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found") from e
                raise
