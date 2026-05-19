from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import AuthUser, get_current_user
from app.config import get_settings

settings = get_settings()

app = FastAPI(title="ProdReady AI API", version="0.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/me")
def me(user: AuthUser = Depends(get_current_user)) -> dict[str, str]:
    return {"id": str(user.id), "email": user.email or ""}
