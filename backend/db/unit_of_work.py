# backend/unit_of_work.py

from __future__ import annotations

from types import TracebackType
from typing import Optional, Type

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .repository import (
    AccountRepository,
    GroupRepository,
    PermissionRepository,
    RoleRepository,
    ResourceRepository,
)


class UnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory
        self._session: Optional[AsyncSession] = None

    async def __aenter__(self) -> "UnitOfWork":
        self._session = self._session_factory()
        await self._session.begin()
        self.accounts = AccountRepository(self._session)
        self.groups = GroupRepository(self._session)
        self.permissions = PermissionRepository(self._session)
        self.roles = RoleRepository(self._session)
        self.resources = ResourceRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        if exc_type:
            await self.rollback()
        # Always close the session
        if self._session:
            await self._session.close()

    async def commit(self) -> None:
        if not self._session:
            return
        await self._session.commit()

    async def rollback(self) -> None:
        if not self._session:
            return
        await self._session.rollback()