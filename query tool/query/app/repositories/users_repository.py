from typing import Any

import psycopg


class UsersRepository:
    def find_by_username(self, conn: psycopg.Connection, username: str) -> dict[str, Any] | None:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, username, password_hash, role
                FROM users
                WHERE username = %s
                """,
                (username,),
            )
            return user_from_row(cur.fetchone())

    def find_by_id(self, conn: psycopg.Connection, user_id: int) -> dict[str, Any] | None:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, username, password_hash, role
                FROM users
                WHERE id = %s
                """,
                (user_id,),
            )
            return user_from_row(cur.fetchone())


def user_from_row(row: tuple[Any, ...] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    user_id, username, password_hash, role = row
    return {
        "id": user_id,
        "username": username,
        "password_hash": password_hash,
        "role": role,
    }
