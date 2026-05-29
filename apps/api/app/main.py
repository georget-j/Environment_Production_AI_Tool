from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import AuthUser, get_current_user
from app.config import get_settings
from app.routers import ai, billing, challenges, concepts, me, submissions, tracks

settings = get_settings()

app = FastAPI(title="ProdReady AI API", version="0.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tracks.router)
app.include_router(challenges.router)
app.include_router(submissions.router)
app.include_router(ai.router)
app.include_router(billing.router)
app.include_router(me.router)
app.include_router(concepts.router)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/me")
def me(user: AuthUser = Depends(get_current_user)) -> dict[str, str]:
    return {"id": str(user.id), "email": user.email or ""}
