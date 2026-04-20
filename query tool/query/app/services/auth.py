import secrets
from typing import Any

from passlib.context import CryptContext

from app.services.database import Database


password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthenticationError(Exception):
    pass


class AuthorizationError(Exception):
    pass


class AuthService:
    def __init__(self, database: Database) -> None:
        self.database = database
        self.sessions: dict[str, int] = {}

    def login(self, username: str, password: str) -> dict[str, Any]:
        user = self.database.find_user_by_username(username)
        if user is None or not password_context.verify(password, user["password_hash"]):
            raise AuthenticationError("Invalid username or password.")

        token = secrets.token_urlsafe(32)
        self.sessions[token] = int(user["id"])
        return {
            "token": token,
            "token_type": "bearer",
            "user": public_user(user),
        }

    def authenticate(self, authorization_header: str | None) -> dict[str, Any]:
        token = bearer_token(authorization_header)
        user_id = self.sessions.get(token)
        if user_id is None:
            raise AuthenticationError("Missing or invalid auth token.")

        user = self.database.find_user_by_id(user_id)
        if user is None:
            self.sessions.pop(token, None)
            raise AuthenticationError("Session user no longer exists.")
        return user

    def require_role(self, role: str, user: dict[str, Any]) -> dict[str, Any]:
        return require_role(role, user)


def bearer_token(authorization_header: str | None) -> str:
    if not authorization_header:
        raise AuthenticationError("Missing Authorization header.")

    scheme, _, token = authorization_header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise AuthenticationError("Authorization header must be 'Bearer <token>'.")
    return token


def public_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
    }


def require_role(role: str, user: dict[str, Any]) -> dict[str, Any]:
    if user["role"] != role:
        raise AuthorizationError(f"Role '{role}' is required.")
    return user
