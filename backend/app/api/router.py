"""
app/api/router.py

Root router aggregation.

v1 is mounted without a prefix, so the public URLs stay `/auth/login`,
`/tickets`, and so on. The version lives in the file layout for now; when a v2
arrives, v1 can be pinned to `/v1` and the unprefixed mount kept as an alias so
existing clients don't break.
"""
from fastapi import APIRouter

from app.api.v1.router import router as v1_router

api_router = APIRouter()
api_router.include_router(v1_router)
