"""app/repositories/user_repo.py"""
from __future__ import annotations

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def get_by_email(self, email: str) -> User | None:
        """Backs both login and the duplicate-email guard on every invite."""
        return self.db.query(User).filter(User.email == email).first()

    def exists_with_email(self, email: str) -> bool:
        return self.get_by_email(email) is not None
