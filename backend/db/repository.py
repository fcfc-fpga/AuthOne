# backend/repository.py

from __future__ import annotations

import abc
from typing import Generic, TypeVar, Optional, Sequence
from uuid import UUID

from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .db_models import AccountModel, GroupModel, PermissionModel, RoleModel, ResourceModel

T = TypeVar("T")


class Repository(abc.ABC, Generic[T]):
    def __init__(self, session: AsyncSession):
        self._session = session

    @abc.abstractmethod
    async def get(self, id: UUID) -> Optional[T]:
        raise NotImplementedError

    @abc.abstractmethod
    async def list(self, **filters) -> Sequence[T]:
        raise NotImplementedError

    def add(self, entity: T) -> None:
        self._session.add(entity)

    async def delete(self, id: UUID) -> bool:
        obj = await self._session.get(self._model, id)
        if not obj:
            return False
        await self._session.delete(obj) 
        return True


class PermissionRepository(Repository[PermissionModel]):
    _model = PermissionModel

    async def get(self, id: UUID) -> Optional[PermissionModel]:
        return await self._session.get(PermissionModel, id)

    async def get_by_name(self, name: str) -> Optional[PermissionModel]:
        q = select(PermissionModel).where(PermissionModel.name == name)
        return (await self._session.execute(q)).scalar_one_or_none()

    async def list(self, name: Optional[str] = None) -> Sequence[PermissionModel]:
        q = select(PermissionModel).order_by(PermissionModel.name)
        if name:
            q = q.where(PermissionModel.name == name)
        return (await self._session.execute(q)).scalars().all()


class RoleRepository(Repository[RoleModel]):
    _model = RoleModel

    async def get(self, id: UUID) -> Optional[RoleModel]:
        return await self._session.get(RoleModel, id)
    
    async def get_with_permissions(self, id: UUID) -> Optional[RoleModel]:
        return await self._session.get(RoleModel, id, options=[selectinload(RoleModel.permissions)])

    async def get_by_name(self, tenant_id: Optional[str], name: str) -> Optional[RoleModel]:
        q = select(RoleModel).where(
            and_(RoleModel.tenant_id == tenant_id, RoleModel.name == name)
        )
        return (await self._session.execute(q)).scalar_one_or_none()

    async def list(self, tenant_id: Optional[str] = None, name: Optional[str] = None) -> Sequence[RoleModel]:
        q = select(RoleModel).order_by(RoleModel.name)
        if tenant_id is not None:
            q = q.where(RoleModel.tenant_id == tenant_id)
        if name:
            q = q.where(RoleModel.name == name)
        return (await self._session.execute(q)).scalars().all()


class GroupRepository(Repository[GroupModel]):
    _model = GroupModel

    async def get(self, id: UUID) -> Optional[GroupModel]:
        return await self._session.get(GroupModel, id)
    
    async def get_with_roles(self, id: UUID) -> Optional[GroupModel]:
        return await self._session.get(GroupModel, id, options=[selectinload(GroupModel.roles)])

    async def list(self, tenant_id: Optional[str] = None) -> Sequence[GroupModel]:
        q = select(GroupModel).order_by(GroupModel.name)
        if tenant_id is not None:
            q = q.where(GroupModel.tenant_id == tenant_id)
        return (await self._session.execute(q)).scalars().all()


class AccountRepository(Repository[AccountModel]):
    _model = AccountModel

    async def get(self, id: UUID) -> Optional[AccountModel]:
        return await self._session.get(AccountModel, id)

    async def get_with_roles(self, id: UUID) -> Optional[AccountModel]:
        return await self._session.get(AccountModel, id, options=[selectinload(AccountModel.roles)])

    async def get_with_groups(self, id: UUID) -> Optional[AccountModel]:
        return await self._session.get(AccountModel, id, options=[selectinload(AccountModel.groups)])

    async def get_by_username(self, tenant_id: Optional[str], username: str) -> Optional[AccountModel]:
        q = select(AccountModel).where(
            and_(AccountModel.tenant_id == tenant_id, AccountModel.username == username)
        )
        return (await self._session.execute(q)).scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Optional[AccountModel]:
        q = select(AccountModel).where(AccountModel.email == email)
        return (await self._session.execute(q)).scalar_one_or_none()

    async def list(self, tenant_id: Optional[str] = None, username: Optional[str] = None) -> Sequence[AccountModel]:
        q = select(AccountModel).order_by(AccountModel.username)
        if tenant_id is not None:
            q = q.where(AccountModel.tenant_id == tenant_id)
        if username:
            q = q.where(AccountModel.username == username)
        return (await self._session.execute(q)).scalars().all()


class ResourceRepository(Repository[ResourceModel]):
    _model = ResourceModel

    async def get(self, id: UUID) -> Optional[ResourceModel]:
        return await self._session.get(ResourceModel, id)

    async def list(self, tenant_id: Optional[str] = None) -> Sequence[ResourceModel]:
        q = select(ResourceModel).order_by(ResourceModel.type, ResourceModel.name)
        if tenant_id is not None:
            q = q.where(ResourceModel.tenant_id == tenant_id)
        return (await self._session.execute(q)).scalars().all()