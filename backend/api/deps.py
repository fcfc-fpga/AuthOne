from __future__ import annotations
from typing import AsyncGenerator, Awaitable, Callable, TypeVar

from fastapi import HTTPException, Request, status
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy.exc import IntegrityError

from ..db.unit_of_work import UnitOfWork
from ..db.db_models import get_sessionmaker
from ..service.auth_service import AuthService
from ..service.exceptions import DuplicateError, NotFoundError, ConcurrencyError

T = TypeVar("T")

def get_auth_service(request: Request) -> AuthService:
    return request.app.state.svc  # type: ignore[attr-defined]

async def get_uow() -> AsyncGenerator[UnitOfWork, None]:
    uow = UnitOfWork(get_sessionmaker())
    async with uow:
        yield uow

async def handle_errors(coro: Awaitable[T]) -> T:
    try:
        return await coro
    except DuplicateError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ConcurrencyError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except IntegrityError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"DB integrity error: {e.orig}")



async def run_tx(uow: UnitOfWork, fn: Callable[[], Awaitable[T]]) -> T:
    try:
        result = await fn()
        await uow.commit()
        return result
    except IntegrityError:
        await uow.rollback()
        raise
    except Exception:
        await uow.rollback()
        raise
