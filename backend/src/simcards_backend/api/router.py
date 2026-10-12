"""Top-level API router."""

from fastapi import APIRouter

from simcards_backend.api.routes import accounts, auth, commission, flags, password_reset, reconciliation, reports, stock

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(password_reset.router)
api_router.include_router(accounts.router)
api_router.include_router(stock.router)
api_router.include_router(commission.router)
api_router.include_router(flags.router)
api_router.include_router(reconciliation.router)
api_router.include_router(reports.router)
