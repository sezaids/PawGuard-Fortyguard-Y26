from typing import Annotated
from uuid import UUID

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User


def get_current_user(
    db: Annotated[Session, Depends(get_db)], pawguard_session: str | None = Cookie(default=None),
) -> User:
    if not pawguard_session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    user_id: UUID = decode_access_token(pawguard_session)
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
