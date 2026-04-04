from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.modules.topics.model import LearningTopic
from app.schema.topics import TopicCreate


class TopicsService:
    async def list_topics(self, session: AsyncSession) -> list[LearningTopic]:
        stmt = select(LearningTopic).order_by(LearningTopic.sort_order, LearningTopic.id)
        return (await session.exec(stmt)).all()

    async def get_topic(self, session: AsyncSession, topic_id: int) -> LearningTopic | None:
        return await session.get(LearningTopic, topic_id)

    async def create_topic(self, session: AsyncSession, body: TopicCreate) -> LearningTopic:
        r = await session.exec(select(LearningTopic).where(LearningTopic.slug == body.slug))
        if r.first():
            raise ValueError("slug_exists")
        topic = LearningTopic(
            title=body.title,
            slug=body.slug,
            summary=body.summary,
            sort_order=body.sort_order,
        )
        session.add(topic)
        await session.commit()
        await session.refresh(topic)
        return topic


_topics: TopicsService | None = None


def get_topics_service() -> TopicsService:
    global _topics
    if _topics is None:
        _topics = TopicsService()
    return _topics
