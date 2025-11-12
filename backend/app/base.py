"""
SQLAlchemy Base Configuration

Purpose: Provides the declarative base for all SQLAlchemy models
This base class is used by all database models to inherit common functionality

Usage:
All models should inherit from this Base class:
    from app.base import Base
    class MyModel(Base):
        ...

@author Orbit Skill Development Team
@date 2025
"""

from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()