"""Shared ORM metadata; connections are owned by database.py."""
from sqlalchemy.orm import declarative_base
Base = declarative_base()
