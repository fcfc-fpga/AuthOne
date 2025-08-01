"""Casbin PostgreSQL 适配器和引擎封装。

为了将 Casbin 的策略持久化到数据库，我们实现了 ``DatabaseAdapter``，
它遵循 ``casbin.persist.Adapter`` 接口，负责从数据库加载策略并
将策略变更写回数据库。同时提供 ``CasbinEngine`` 类，对 ``casbin.Enforcer``
进行二次封装，简化模型加载、策略管理和权限校验的使用。

注意：本模块依赖外部安装的 ``casbin``、``psycopg2`` 等库，且运行环境
必须具备数据库访问能力。本仓库无法验证其运行效果，用户需在实际
环境中测试。
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any, Iterable, List, Optional, Sequence

import casbin
from casbin import persist

from ..config import Settings
import psycopg2
# --- FIX: Import RealDictCursor ---
from psycopg2.extras import RealDictCursor

__all__ = ["CasbinRule", "DatabaseAdapter", "CasbinEngine"]


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CasbinRule:
    """表示一条 Casbin 策略行。"""

    id: str
    ptype: str
    v0: Optional[str] = None
    v1: Optional[str] = None
    v2: Optional[str] = None
    v3: Optional[str] = None
    v4: Optional[str] = None
    v5: Optional[str] = None


class DatabaseAdapter(persist.Adapter):
    """Casbin 持久化适配器。

    使用 PostgreSQL 存储策略行。表结构应包括字段：
    id (UUID)、ptype、v0…v5，对应 Casbin 的策略类型和参数。
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        # --- FIX: Use RealDictCursor to get dictionary-like rows ---
        self._conn = psycopg2.connect(self._settings.db_url_sync, cursor_factory=RealDictCursor)
        self._conn.autocommit = True

    def _cursor(self):  # type: ignore[no-untyped-def]
        return self._conn.cursor()

    # -- helper methods -------------------------------------------------
    def _save_policy_line(self, ptype: str, rule: Sequence[str]) -> None:
        vals: List[Optional[str]] = list(rule) + [None] * (6 - len(rule))
        # FIX: Align with the auto-incrementing integer ID in the schema
        sql = f"""
            INSERT INTO {self._settings.casbin_policy_table} (ptype, v0, v1, v2, v3, v4, v5)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        with self._cursor() as cur:
            cur.execute(sql, (ptype, *vals[:6]))

    # -- Adapter interface methods --------------------------------------
    def load_policy(self, model: casbin.Model) -> None:
        sql = f"SELECT ptype, v0, v1, v2, v3, v4, v5 FROM {self._settings.casbin_policy_table}"
        with self._cursor() as cur:
            cur.execute(sql)
            for row in cur.fetchall():
                # FIX: Directly use the dictionary-like row, no need for dict()
                ptype = row.get("ptype", "")
                rule: List[str] = []
                for i in range(6):
                    val = row.get(f"v{i}")
                    if val is not None:
                        rule.append(val)
                line = ptype + ", " + ", ".join(rule)
                persist.load_policy_line(line, model)

    def save_policy(self, model: casbin.Model) -> bool:
        with self._cursor() as cur:
            cur.execute(f"DELETE FROM {self._settings.casbin_policy_table}")
        for sec in ["p", "g"]:
            if sec not in model.model:
                continue
            for ptype, ast in model.model[sec].items():
                for rule in ast.policy:
                    self._save_policy_line(ptype, rule)
        return True

    def add_policy(self, sec: str, ptype: str, rule: Sequence[str]) -> None:
        self._save_policy_line(ptype, list(rule))

    def remove_policy(self, sec: str, ptype: str, rule: Sequence[str]) -> None:
        conds = [f"v{i} = %s" for i in range(len(rule))]
        params: List[str] = list(rule)
        sql = f"DELETE FROM {self._settings.casbin_policy_table} WHERE ptype = %s"
        if conds:
            sql += " AND " + " AND ".join(conds)
        with self._cursor() as cur:
            cur.execute(sql, [ptype] + params)

    def remove_filtered_policy(
        self,
        sec: str,
        ptype: str,
        field_index: int,
        *field_values: str,
    ) -> None:
        conditions: List[str] = []
        params: List[str] = []
        for idx, val in enumerate(field_values):
            if val:
                conditions.append(f"v{field_index + idx} = %s")
                params.append(val)
        sql = f"DELETE FROM {self._settings.casbin_policy_table} WHERE ptype = %s"
        if conditions:
            sql += " AND " + " AND ".join(conditions)
        with self._cursor() as cur:
            cur.execute(sql, [ptype] + params)


class CasbinEngine:
    """Casbin 引擎封装。"""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        adapter = DatabaseAdapter(settings)
        self._enforcer = casbin.Enforcer(self._settings.casbin_model_path, adapter)
        # This explicit load is good practice
        self._enforcer.load_policy()

    def enforce(
        self,
        account: str,
        tenant_id: Optional[str],
        resource: str,
        action: str,
    ) -> bool:
        domain = tenant_id or "public"
        return bool(self._enforcer.enforce(account, domain, resource, action))

    def add_permission_for_user(
        self, subject: str, tenant_id: Optional[str], resource: str, action: str
    ) -> None:
        domain = tenant_id or "public"
        self._enforcer.add_policy(subject, domain, resource, action)
        self._enforcer.save_policy()

    def add_role_for_account(
        self, account: str, tenant_id: Optional[str], role_name: str
    ) -> None:
        domain = tenant_id or "public"
        self._enforcer.add_role_for_user_in_domain(account, role_name, domain)
        self._enforcer.save_policy()

    def add_role_for_group(
        self, group_name: str, tenant_id: Optional[str], role_name: str
    ) -> None:
        domain = tenant_id or "public"
        self._enforcer.add_role_for_user_in_domain(group_name, role_name, domain)
        self._enforcer.save_policy()

    def add_group_for_account(
        self, account: str, tenant_id: Optional[str], group_name: str
    ) -> None:
        domain = tenant_id or "public"
        self._enforcer.add_role_for_user_in_domain(account, group_name, domain)
        self._enforcer.save_policy()