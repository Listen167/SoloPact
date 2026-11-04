from __future__ import annotations

from collections.abc import Generator
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.services.seed import reset_demo_data


@pytest.fixture
def db() -> Generator[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        with session_factory() as session:
            reset_demo_data(session, date(2026, 11, 4))
            yield session
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def client(db: Session) -> Generator[TestClient]:
    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
