from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.modules.references.model import Reference
from app.modules.topics.model import LearningTopic
from app.schema.references import ReferenceCreate


class ReferencesService:
    async def list_references(self, session: AsyncSession) -> list[Reference]:
        stmt = select(Reference).order_by(Reference.id)
        return (await session.exec(stmt)).all()

    async def get_reference(self, session: AsyncSession, ref_id: int) -> Reference | None:
        return await session.get(Reference, ref_id)

    async def create_reference(self, session: AsyncSession, body: ReferenceCreate) -> Reference:
        if body.topic_id is not None and await session.get(LearningTopic, body.topic_id) is None:
            raise ValueError("unknown_topic")
        r = Reference(
            topic_id=body.topic_id,
            title=body.title,
            url=body.url,
            description=body.description,
        )
        session.add(r)
        await session.commit()
        await session.refresh(r)
        return r


_refs: ReferencesService | None = None


def get_references_service() -> ReferencesService:
    global _refs
    if _refs is None:
        _refs = ReferencesService()
    return _refs
