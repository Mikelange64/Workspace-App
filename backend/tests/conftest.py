import os
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = (
    "postgresql+psycopg://mikelange64@localhost/test_workspaceapp"
)
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["S3_BUCKET_NAME"] = "test-bucket"
os.environ["S3_ACCESS_KEY_ID"] = "testing"
os.environ["S3_SECRET_ACCESS_KEY"] = "testing"
os.environ["S3_REGION"] = "us-east-2"
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_DEFAULT_REGION"] = "us-east-2"
os.environ["MAIL_HOST"] = "localhost"
os.environ["MAIL_PORT"] = "587"
os.environ["MAIL_USERNAME"] = ""
os.environ["MAIL_PASSWORD"] = ""
os.environ["MAIL_FROM"] = "test@example.com"
os.environ["MAIL_USE_TLS"] = "False"
os.environ["FRONTEND_URL"] = "http://localhost:3000"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"

from app.database import Base, get_db
from app.main import app
from app.redis_client import redis_client
from tests.auth_helpers import (
    auth_header,
    create_test_user,
    create_workspace,
    login_user,
)


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(os.environ["DATABASE_URL"])
    return engine


@pytest.fixture(scope="session")
def setup_database(test_engine):
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


@pytest.fixture
def db_session(setup_database, test_engine):
    connection = test_engine.connect()
    transaction = connection.begin()

    session_factory = sessionmaker(bind=connection)
    session = session_factory()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(autouse=True)
def _flush_test_redis():
    """Isolated DB index (15) from dev/prod, flushed before every test so the
    rate limiters (register/login/password-reset) never bleed state across tests."""
    redis_client.flushdb()
    yield


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


# ========================================================================================
# SHARED FIXTURES
# ========================================================================================


@pytest.fixture
def user(client, db_session):
    """Create and return a default test user (pre-verified to bypass email flow)."""
    from app.models import User as UserModel
    user_data = create_test_user(client)
    u = db_session.get(UserModel, user_data["id"])
    u.is_verified = True
    db_session.flush()
    return user_data


@pytest.fixture
def premium_user(user, db_session):
    """Upgrade the default test user to premium (needed for Filobelo bot access)."""
    from app.models import User as UserModel
    u = db_session.get(UserModel, user["id"])
    u.is_premium = True
    db_session.flush()
    return user


@pytest.fixture
def non_premium_user(user, db_session):
    """Downgrade the default test user to non-premium - new users default to
    premium (portfolio project, every signup should be able to try Filobelo),
    so tests exercising the premium gate itself need this explicitly."""
    from app.models import User as UserModel
    u = db_session.get(UserModel, user["id"])
    u.is_premium = False
    db_session.flush()
    return user


@pytest.fixture
def user_token(client, user):
    """Return a valid auth token for the default user."""
    return login_user(client)


@pytest.fixture
def user_auth_headers(user_token):
    """Return Authorization headers for the default user."""
    return auth_header(user_token)


@pytest.fixture
def workspace(client, user_token):
    """Create and return a workspace owned by the default user."""
    return create_workspace(client, user_token)


@pytest.fixture
def second_user(client, db_session):
    """Create and return a second user (pre-verified to bypass email flow)."""
    from app.models import User as UserModel
    user_data = create_test_user(client, username="user2", email="user2@example.com")
    u = db_session.get(UserModel, user_data["id"])
    u.is_verified = True
    db_session.flush()
    return user_data


@pytest.fixture
def second_user_token(client, second_user):
    """Return a valid auth token for the second user."""
    return login_user(client, email="user2@example.com")


@pytest.fixture
def mocked_s3():
    """Create an in-memory mock S3 bucket for testing."""
    with mock_aws():
        s3 = boto3.client("s3", region_name=os.environ["S3_REGION"])
        s3.create_bucket(
            Bucket=os.environ["S3_BUCKET_NAME"],
            CreateBucketConfiguration={"LocationConstraint": os.environ["S3_REGION"]},
        )
        yield s3


@pytest.fixture
def test_image() -> bytes:
    """Generate a small valid JPEG image in memory."""
    img = Image.new("RGB", (100, 100), color="red")
    buf = BytesIO()
    img.save(buf, "JPEG")
    return buf.getvalue()


class FakeCompletions:
    """Stands in for client.chat.completions - records every create() call and
    lets a test control the response (or force an error) without touching
    the real DeepSeek API."""

    def __init__(self):
        self.output_text = "This is Filobelo's reply."
        self.exception: Exception | None = None
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.exception is not None:
            raise self.exception
        message = SimpleNamespace(content=self.output_text, tool_calls=None)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


@pytest.fixture
def fake_bot_client(monkeypatch):
    """Swaps filobelo_bot's real OpenAI-compatible client for a fake one for
    the duration of the test. monkeypatch reverts this automatically on
    teardown."""
    from app.bot_service import filobelo_bot

    fake = FakeCompletions()
    monkeypatch.setattr(
        filobelo_bot, "client", SimpleNamespace(chat=SimpleNamespace(completions=fake))
    )
    return fake
