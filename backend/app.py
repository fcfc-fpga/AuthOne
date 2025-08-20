# backend/app.py
from __future__ import annotations
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from casbin.async_enforcer import AsyncEnforcer
from casbin.util import key_match_func, regex_match_func
from casbin_async_sqlalchemy_adapter import Adapter as AsyncCasbinAdapter

from .config import get_settings, AppSettings
from .db.db_models import init_engine, init_db, dispose_engine, get_sessionmaker
from .service.auth_service import AuthService
from .api.__all_routers__ import all_routers

async def _build_enforcer(settings: AppSettings) -> AsyncEnforcer:
    adapter = AsyncCasbinAdapter(settings.db_url)
    await adapter.create_table()  # 确保存在默认表

    # 用默认表即可，确保存在
    # （若要自定义表，请改成自己的表模型，并不要调用 create_table）
    enforcer = AsyncEnforcer(settings.casbin.model_path, adapter)
    if settings.casbin.register_key_match:
        enforcer.add_function("keyMatch", key_match_func)
    if settings.casbin.register_regex_match:
        enforcer.add_function("regexMatch", regex_match_func)
    return enforcer

def _install_cors(app: FastAPI, settings: AppSettings) -> None:
    cors = settings.cors
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors.allow_origins,
        allow_methods=cors.allow_methods,
        allow_headers=cors.allow_headers,
    )

def _install_routers(app: FastAPI) -> None:
    for r in all_routers:
        app.include_router(r)

def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # DB
        await init_engine(settings.db_url)
        await init_db(settings.init_db_drop_all)

        # Casbin
        enforcer = await _build_enforcer(settings)
        await enforcer.load_policy()
        enforcer.enable_auto_save(settings.casbin.enable_auto_save)

        # Service
        svc = AuthService(enforcer)
        
        # TODO RESOURCE_TO_PATTERN 这个操作很烂，建议改掉
        svc.RESOURCE_TO_PATTERN = settings.resource_to_pattern  # type: ignore[attr-defined]

        app.state.svc = svc
        app.state.enforcer = enforcer
        app.state.settings = settings

        try:
            yield
        finally:
            await dispose_engine()

    app = FastAPI(title = settings.app_name, lifespan = lifespan)
    _install_cors(app, settings)
    _install_routers(app)
    return app
