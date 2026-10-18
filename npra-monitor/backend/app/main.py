from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, exports, records, runs, schedule
from app.db.bootstrap import bootstrap


@asynccontextmanager
async def lifespan(app: FastAPI):
    bootstrap()
    yield


app = FastAPI(title="NPRA Monitor API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4201"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def origin_guard(request: Request, call_next):
    if request.url.path.startswith("/api/") and request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        origin = request.headers.get("origin")
        if origin and origin not in {"http://localhost:4201", "http://127.0.0.1:4201"}:
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail": "Origin not allowed"}, status_code=403)
    return await call_next(request)

@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(auth.router, prefix="/api")
app.include_router(records.router, prefix="/api")
app.include_router(runs.router, prefix="/api")
app.include_router(schedule.router, prefix="/api")
app.include_router(exports.router, prefix="/api")
