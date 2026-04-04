from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlmodel.ext.asyncio.session import AsyncSession

from app.modules.syllabus.model import SyllabusItem, SyllabusModule
from app.schema.syllabus import SyllabusItemCreate, SyllabusModuleCreate


class SyllabusService:
    async def list_modules(self, session: AsyncSession) -> list[SyllabusModule]:
        stmt = (
            select(SyllabusModule)
            .options(selectinload(SyllabusModule.items))
            .order_by(SyllabusModule.sort_order, SyllabusModule.id)
        )
        r = await session.exec(stmt)
        return r.unique().all()

    async def create_module(self, session: AsyncSession, body: SyllabusModuleCreate) -> SyllabusModule:
        m = SyllabusModule(
            title=body.title,
            description=body.description,
            sort_order=body.sort_order,
        )
        session.add(m)
        await session.commit()
        await session.refresh(m)
        return m

    async def create_item(self, session: AsyncSession, module_id: int, body: SyllabusItemCreate) -> SyllabusItem:
        mod = await session.get(SyllabusModule, module_id)
        if not mod:
            raise ValueError("module_not_found")
        item = SyllabusItem(
            module_id=module_id,
            title=body.title,
            content_md=body.content_md,
            sort_order=body.sort_order,
        )
        session.add(item)
        await session.commit()
        await session.refresh(item)
        return item


_syllabus: SyllabusService | None = None


def get_syllabus_service() -> SyllabusService:
    global _syllabus
    if _syllabus is None:
        _syllabus = SyllabusService()
    return _syllabus
