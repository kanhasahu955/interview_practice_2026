from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.modules.coding.model import CodingProblem
from app.modules.topics.model import LearningTopic
from app.schema.coding import CodingProblemCreate


class CodingService:
    async def list_problems(self, session: AsyncSession) -> list[CodingProblem]:
        stmt = select(CodingProblem).order_by(CodingProblem.difficulty, CodingProblem.id)
        return (await session.exec(stmt)).all()

    async def get_problem(self, session: AsyncSession, problem_id: int) -> CodingProblem | None:
        return await session.get(CodingProblem, problem_id)

    async def create_problem(self, session: AsyncSession, body: CodingProblemCreate) -> CodingProblem:
        if body.topic_id is not None and await session.get(LearningTopic, body.topic_id) is None:
            raise ValueError("unknown_topic")
        p = CodingProblem(
            topic_id=body.topic_id,
            title=body.title,
            problem_md=body.problem_md,
            difficulty=body.difficulty,
            starter_code=body.starter_code,
            hints_md=body.hints_md,
        )
        session.add(p)
        await session.commit()
        await session.refresh(p)
        return p


_coding: CodingService | None = None


def get_coding_service() -> CodingService:
    global _coding
    if _coding is None:
        _coding = CodingService()
    return _coding
