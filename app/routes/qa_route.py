from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db import get_db
from app.openapi_common import R_400, R_401, R_403, R_404, merge_responses
from app.deps import get_current_user
from app.modules.auth.model import User
from app.schema.qa import AnswerCreate, AnswerOut, QuestionCreate, QuestionOut
from app.services.qa_service import get_qa_service


class QARoutes:
    def __init__(self) -> None:
        self.router = APIRouter()
        self._svc = get_qa_service()
        self._register()

    def _register(self) -> None:
        r = self.router
        svc = self._svc

        @r.get(
            "/questions",
            response_model=list[QuestionOut],
            summary="List Q&A questions",
            description=(
                "### Purpose\n"
                "See all questions, usually with nested **answers** (see **QuestionOut** schema).\n\n"
                "### What this endpoint does\n"
                "Public read; no JWT required unless you add rules later."
            ),
            response_description="List of **QuestionOut**.",
        )
        async def list_questions(session: AsyncSession = Depends(get_db)):
            return await svc.list_questions(session)

        @r.get(
            "/questions/{question_id}",
            response_model=QuestionOut,
            summary="Get question",
            description="### Purpose\nThread view: one question plus its **answers** list.\n\n### Errors\n**404** if missing.",
            responses=merge_responses(R_404),
            response_description="**QuestionOut** including **answers**.",
        )
        async def get_question(question_id: int, session: AsyncSession = Depends(get_db)):
            q = await svc.get_question(session, question_id)
            if not q:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
            return q

        @r.post(
            "/questions",
            response_model=QuestionOut,
            status_code=status.HTTP_201_CREATED,
            summary="Create question",
            description=(
                "### Request body\n"
                "**QuestionCreate** — **title**, **body_md**, optional **topic_id** / **difficulty**.\n\n"
                "### Auth\n"
                "Valid JWT; author becomes **author_id**.\n\n"
                "### What this endpoint does\n"
                "Creates question; **400** if **topic_id** invalid."
            ),
            responses=merge_responses(R_400, R_401),
            response_description="**QuestionOut** (201), often with empty **answers**.",
        )
        async def create_question(
            body: QuestionCreate,
            session: AsyncSession = Depends(get_db),
            user: User = Depends(get_current_user),
        ):
            try:
                return await svc.create_question(session, body, user=user)
            except ValueError as e:
                if str(e) == "unknown_topic":
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown topic_id") from e
                raise

        @r.post(
            "/questions/{question_id}/answers",
            response_model=AnswerOut,
            status_code=status.HTTP_201_CREATED,
            summary="Add answer to question",
            description=(
                "### Request body\n"
                "**AnswerCreate** — **body_md**, optional **is_official**.\n\n"
                "### What this endpoint does\n"
                "Appends answer to **question_id**; **404** if question missing."
            ),
            responses=merge_responses(R_401, R_404),
            response_description="**AnswerOut** (201).",
        )
        async def create_answer(
            question_id: int,
            body: AnswerCreate,
            session: AsyncSession = Depends(get_db),
            user: User = Depends(get_current_user),
        ):
            try:
                return await svc.create_answer(session, question_id, body, user=user)
            except ValueError as e:
                if str(e) == "question_not_found":
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found") from e
                raise

        @r.patch(
            "/answers/{answer_id}/accept",
            response_model=AnswerOut,
            summary="Accept answer",
            description=(
                "### Purpose\n"
                "Mark the canonical “accepted” solution for a thread.\n\n"
                "### Rules\n"
                "Only the **question author** may accept; others get **403**.\n\n"
                "### What this endpoint does\n"
                "Sets **accepted** on the answer; returns updated **AnswerOut**."
            ),
            responses=merge_responses(R_401, R_403, R_404),
            response_description="**AnswerOut** with **accepted: true**.",
        )
        async def accept_answer(
            answer_id: int,
            session: AsyncSession = Depends(get_db),
            user: User = Depends(get_current_user),
        ):
            try:
                return await svc.accept_answer(session, answer_id, user=user)
            except ValueError as e:
                msg = str(e)
                if msg == "not_found":
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found") from e
                if msg == "forbidden":
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Only question author can accept",
                    ) from e
                raise
