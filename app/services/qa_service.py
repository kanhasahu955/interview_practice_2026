from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlmodel.ext.asyncio.session import AsyncSession

from app.modules.auth.model import User, UserRole
from app.modules.qa.model import Answer, Question
from app.modules.topics.model import LearningTopic
from app.schema.qa import AnswerCreate, QuestionCreate


class QAService:
    async def list_questions(self, session: AsyncSession) -> list[Question]:
        stmt = select(Question).options(selectinload(Question.answers)).order_by(Question.id.desc())
        r = await session.exec(stmt)
        return r.unique().all()

    async def get_question(self, session: AsyncSession, question_id: int) -> Question | None:
        stmt = select(Question).options(selectinload(Question.answers)).where(Question.id == question_id)
        r = await session.exec(stmt)
        return r.unique().first()

    async def create_question(self, session: AsyncSession, body: QuestionCreate, *, user: User) -> Question:
        if body.topic_id is not None and await session.get(LearningTopic, body.topic_id) is None:
            raise ValueError("unknown_topic")
        q = Question(
            author_id=user.id,
            topic_id=body.topic_id,
            title=body.title,
            body_md=body.body_md,
            difficulty=body.difficulty,
        )
        session.add(q)
        await session.commit()
        await session.refresh(q)
        return q

    async def create_answer(
        self,
        session: AsyncSession,
        question_id: int,
        body: AnswerCreate,
        *,
        user: User,
    ) -> Answer:
        q = await session.get(Question, question_id)
        if not q:
            raise ValueError("question_not_found")
        a = Answer(
            question_id=question_id,
            author_id=user.id,
            body_md=body.body_md,
            is_official=body.is_official,
        )
        session.add(a)
        await session.commit()
        await session.refresh(a)
        return a

    async def accept_answer(self, session: AsyncSession, answer_id: int, *, user: User) -> Answer:
        a = await session.get(Answer, answer_id)
        if not a:
            raise ValueError("not_found")
        stmt = select(Question).options(selectinload(Question.answers)).where(Question.id == a.question_id)
        r = await session.exec(stmt)
        q = r.unique().one()
        if q.author_id != user.id and user.role != UserRole.admin:
            raise ValueError("forbidden")
        for other in q.answers:
            other.accepted = False
        a.accepted = True
        await session.commit()
        await session.refresh(a)
        return a


_qa: QAService | None = None


def get_qa_service() -> QAService:
    global _qa
    if _qa is None:
        _qa = QAService()
    return _qa
