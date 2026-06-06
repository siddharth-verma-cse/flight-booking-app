from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

BCRYPT_MAX_LENGTH = 72


def get_password_hash(password: str) -> str:
    password = password[:BCRYPT_MAX_LENGTH]
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    plain_password = plain_password[:BCRYPT_MAX_LENGTH]
    return pwd_context.verify(plain_password, hashed_password)
