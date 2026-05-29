"""
Базовый класс для всех SQLAlchemy моделей.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Базовый декларативный класс для всех моделей ORM."""
    pass
