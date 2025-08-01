"""用户组实体定义。

用户组（部门）可用于集中授予角色，实现批量权限管理。支持租户
隔离，不同租户的用户组互不影响。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import List, Optional

__all__ = ["Group"]


@dataclass(slots=True)
class Group:
    _id: str
    _tenant_id: Optional[str]
    _name: str
    _description: str
    _roles: List[str] = field(default_factory=list)

    @classmethod
    def create(cls, tenant_id: Optional[str], name: str, description: str) -> "Group":
        if not name:
            raise ValueError("group name must not be empty")
        return cls(
            _id=str(uuid.uuid4()),
            _tenant_id=tenant_id,
            _name=name,
            _description=description or "",
        )

    @property
    def id(self) -> str:
        return self._id

    @property
    def tenant_id(self) -> Optional[str]:
        return self._tenant_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def roles(self) -> List[str]:
        return list(self._roles)

    def add_role(self, role_id: str) -> None:
        if role_id not in self._roles:
            self._roles.append(role_id)

    def remove_role(self, role_id: str) -> None:
        if role_id in self._roles:
            self._roles.remove(role_id)
