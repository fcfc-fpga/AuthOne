#  backend/db/db_models.py

from __future__ import annotations

import uuid
from typing import Optional, Any

from sqlalchemy import String, Text, Boolean, ForeignKey, UniqueConstraint, JSON, Index, Integer, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


class Base(DeclarativeBase):
    pass


# ---------------- Association tables ----------------
class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"),
                                               primary_key=True)
    permission_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),
                                                     ForeignKey("permissions.id", ondelete="CASCADE"),
                                                     primary_key=True)
    __table_args__ = (UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),)


class GroupRole(Base):
    __tablename__ = "group_roles"
    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"),
                                                primary_key=True)
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"),
                                               primary_key=True)
    __table_args__ = (UniqueConstraint("group_id", "role_id", name="uq_group_role"),)


class UserRole(Base):
    __tablename__ = "user_roles"
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"),
                                                  primary_key=True)
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"),
                                               primary_key=True)
    __table_args__ = (UniqueConstraint("account_id", "role_id", name="uq_user_role"),)


class UserGroup(Base):
    __tablename__ = "user_groups"
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"),
                                                  primary_key=True)
    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"),
                                                primary_key=True)
    __table_args__ = (UniqueConstraint("account_id", "group_id", name="uq_user_group"),)


# ---------------- Core entities ----------------
class PermissionModel(Base):
    __tablename__ = "permissions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version_id: Mapped[int] = mapped_column(Integer, nullable=False, server_default='1')

    roles: Mapped[list["RoleModel"]] = relationship(
        "RoleModel", secondary="role_permissions", back_populates="permissions", lazy="selectin"
    )
    __mapper_args__ = {"version_id_col": version_id}


class RoleModel(Base):
    __tablename__ = "roles"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version_id: Mapped[int] = mapped_column(Integer, nullable=False, server_default='1')

    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_role_tenant_name"),)
    permissions: Mapped[list[PermissionModel]] = relationship(PermissionModel, secondary="role_permissions",
                                                              back_populates="roles", lazy="selectin",
                                                              cascade="save-update")
    __mapper_args__ = {"version_id_col": version_id}


class GroupModel(Base):
    __tablename__ = "groups"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version_id: Mapped[int] = mapped_column(Integer, nullable=False, server_default='1')

    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_group_tenant_name"),)
    roles: Mapped[list[RoleModel]] = relationship(RoleModel, secondary="group_roles", lazy="selectin")
    __mapper_args__ = {"version_id_col": version_id}


class AccountModel(Base):
    __tablename__ = "accounts"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    version_id: Mapped[int] = mapped_column(Integer, nullable=False, server_default='1')

    __table_args__ = (UniqueConstraint("tenant_id", "username", name="uq_account_tenant_username"),)
    roles: Mapped[list[RoleModel]] = relationship(RoleModel, secondary="user_roles", lazy="selectin")
    groups: Mapped[list[GroupModel]] = relationship(GroupModel, secondary="user_groups", lazy="selectin")
    __mapper_args__ = {"version_id_col": version_id}


class ResourceModel(Base):
    __tablename__ = "resources"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True),
                                                          ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    # --- THIS LINE IS CORRECTED ---
    resource_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    # ------------------------------
    version_id: Mapped[int] = mapped_column(Integer, nullable=False, server_default='1')

    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_resource_tenant_name"),)
    __mapper_args__ = {"version_id_col": version_id}


class AuditLogModel(Base):
    __tablename__ = "audit_logs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True),
                                                            ForeignKey("accounts.id", ondelete="SET NULL"),
                                                            nullable=True)
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    resource: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    result: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)


async def init_engine(db_url: str) -> None:
    global _engine, _session_factory
    _engine = create_async_engine(db_url, echo=False, pool_pre_ping=True)

    async with _engine.connect() as conn:
        await conn.execute(select(1))

    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def init_db(drop_all: bool = False) -> None:
    assert _engine is not None
    async with _engine.begin() as conn:
        if drop_all:
            await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


async def dispose_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    assert _session_factory is not None
    return _session_factory