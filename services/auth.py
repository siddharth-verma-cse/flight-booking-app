from sqlmodel import Session
from backend.models.users import UserInDB
from backend.crud.users import get_user_by_email
from backend.utils.security import verify_password


def authenticate_user(session: Session, email: str, password: str) -> UserInDB | None:
    user = get_user_by_email(session, email)
    if not user:
        return False
    if not verify_password(password, user.password):
        return False
    return user
