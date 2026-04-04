from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db import get_db
from app.openapi_common import R_400, R_401, R_403, R_404, merge_responses
from app.deps import require_roles
from app.modules.auth.model import User, UserRole
from app.schema.coding import CodingProblemCreate, CodingProblemOut
from app.services.coding_service import get_coding_service


class CodingRoutes:
    def __init__(self) -> None:
        self.router = APIRouter()
        self._svc = get_coding_service()
        self._register()

    def _register(self) -> None:
        r = self.router
        svc = self._svc

        @r.get(
            "/coding/problems",
            response_model=list[CodingProblemOut],
            summary="List coding problems",
            description=(
                "### Purpose\n"
                "Browse interview-style coding tasks.\n\n"
                "### Response\n"
                "Each **CodingProblemOut** includes **problem_md**, **difficulty**, **starter_code**, **hints_md**."
            ),
            response_description="List of **CodingProblemOut**.",
        )
        async def list_problems(session: AsyncSession = Depends(get_db)):
            return await svc.list_problems(session)

        @r.get(
            "/coding/problems/{problem_id}",
            response_model=CodingProblemOut,
            summary="Get coding problem",
            description=(
                "### Purpose\n"
                "Load full statement and metadata for one problem.\n\n"
                "### Errors\n"
                "**404** if id unknown."
            ),
            responses=merge_responses(R_404),
            response_description="**CodingProblemOut** for the given id.",
        )
        async def get_problem(problem_id: int, session: AsyncSession = Depends(get_db)):
            p = await svc.get_problem(session, problem_id)
            if not p:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
            return p

        @r.post(
            "/coding/problems",
            response_model=CodingProblemOut,
            status_code=status.HTTP_201_CREATED,
            summary="Create coding problem",
            description=(
                "### Request body\n"
                "**CodingProblemCreate** — optional **topic_id** (must exist).\n\n"
                "### Auth\n"
                "**Author**/**admin**.\n\n"
                "### What this endpoint does\n"
                "Persists problem Markdown and metadata; **400** for bad **topic_id**."
            ),
            responses=merge_responses(R_400, R_401, R_403),
            response_description="**CodingProblemOut** (201).",
        )
        async def create_problem(
            body: CodingProblemCreate,
            session: AsyncSession = Depends(get_db),
            _: User = Depends(require_roles(UserRole.author)),
        ):
            try:
                return await svc.create_problem(session, body)
            except ValueError as e:
                if str(e) == "unknown_topic":
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown topic_id") from e
                raise
