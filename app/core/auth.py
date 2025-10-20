from fastapi import Header, HTTPException
from app.core.config import TOKEN

def require_auth(authorization: str | None = Header(None)) -> None:
    if not authorization:
        authorization = f"Bearer {TOKEN}"
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization 형식이 잘못되었습니다. (Bearer ...)")
    token = authorization.split(" ", 1)[1].strip()
    if token != TOKEN:
        raise HTTPException(status_code=403, detail="토큰이 올바르지 않습니다.")
