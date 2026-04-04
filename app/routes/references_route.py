from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db import get_db
from app.openapi_common import R_400, R_401, R_403, R_404, merge_responses
from app.deps import require_roles
from app.modules.auth.model import User, UserRole
from app.schema.references import ReferenceCreate, ReferenceOut
from app.services.references_service import get_references_service


class ReferencesRoutes:
    def __init__(self) -> None:
        self.router = APIRouter()
        self._svc = get_references_service()
        self._register()

    def _register(self) -> None:
        r = self.router
        svc = self._svc

        @r.get(
            "/references",
            response_model=list[ReferenceOut],
            summary="List references",
            description=(
                "### Purpose\n"
                "Browse curated learning links grouped by optional **topic_id**.\n\n"
                "### Response\n"
                "Each **ReferenceOut** exposes **url**, **title**, **description**."
            ),
            response_description="List of **ReferenceOut**.",
        )
        async def list_references(session: AsyncSession = Depends(get_db)):
            return await svc.list_references(session)

        @r.get(
            "/references/{ref_id}",
            response_model=ReferenceOut,
            summary="Get reference",
            description="### Purpose\nFetch one bookmarked resource by primary key.\n\n### Errors\n**404** if not found.",
            responses=merge_responses(R_404),
            response_description="**ReferenceOut**.",
        )
        async def get_reference(ref_id: int, session: AsyncSession = Depends(get_db)):
            ref = await svc.get_reference(session, ref_id)
            if not ref:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
            return ref

        @r.post(
            "/references",
            response_model=ReferenceOut,
            status_code=status.HTTP_201_CREATED,
            summary="Create reference",
            description=(
                "### Request body\n"
                "**ReferenceCreate** — **title**, **url**, optional **topic_id** / **description**.\n\n"
                "### Auth\n"
                "**Author**/**admin**.\n\n"
                "### What this endpoint does\n"
                "Saves link; **400** if **topic_id** invalid."
            ),
            responses=merge_responses(R_400, R_401, R_403),
            response_description="**ReferenceOut** (201).",
        )
        async def create_reference(
            body: ReferenceCreate,
            session: AsyncSession = Depends(get_db),
            _: User = Depends(require_roles(UserRole.author)),
        ):
            try:
                return await svc.create_reference(session, body)
            except ValueError as e:
                if str(e) == "unknown_topic":
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown topic_id") from e
                raise
