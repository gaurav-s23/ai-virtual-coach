"""Pytest configuration and shared fixtures"""

import pytest
import os
import tempfile
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch

# Import the main app
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from database import get_db, Base

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def test_db():
    """Create test database"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db_session(test_db):
    """Create database session"""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()

@pytest.fixture(scope="function")
def client(test_db):
    """Create test client"""
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as c:
        yield c
    
    app.dependency_overrides.clear()

@pytest.fixture
def temp_dir():
    """Create temporary directory"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

@pytest.fixture
def mock_env_vars():
    """Mock environment variables"""
    env_vars = {
        "JWT_SECRET_KEY": "test_secret_key_for_testing_only",
        "ADMIN_EMAIL": "admin@test.com",
        "ADMIN_PASSWORD": "admin123",
        "GOOGLE_API_KEY": "test_google_key",
        "OPENROUTER_API_KEY": "sk-or-v1-test-key",
        "PROCTOR_LOG_DIR": tempfile.gettempdir(),
        "DATABASE_URL": "sqlite:///./test.db",
        "ENVIRONMENT": "test",
        "FRONTEND_URL": "http://localhost:3000"
    }
    
    with patch.dict(os.environ, env_vars):
        yield env_vars

@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "email": "test@example.com",
        "password": "TestPassword123!",
        "name": "Test User"
    }

@pytest.fixture
def admin_credentials():
    """Admin credentials for testing"""
    return {
        "email": "admin@test.com",
        "password": "admin123"
    }

@pytest.fixture
def authenticated_client(client, sample_user_data):
    """Create authenticated client"""
    # Create user
    client.post("/api/auth/signup", json=sample_user_data)
    
    # Login
    login_response = client.post("/api/auth/login", json={
        "email": sample_user_data["email"],
        "password": sample_user_data["password"]
    })
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Return client with headers
    client.headers.update(headers)
    return client

@pytest.fixture
def admin_client(client, admin_credentials):
    """Create admin authenticated client"""
    # Login as admin
    login_response = client.post("/api/admin/login", json=admin_credentials)
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Return client with headers
    client.headers.update(headers)
    return client

# Mock fixtures for external services
@pytest.fixture
def mock_llm_client():
    """Mock LLM client"""
    with patch('services.llm_client.LLMClient') as mock:
        yield mock

@pytest.fixture
def mock_vision_service():
    """Mock vision service"""
    with patch('services.vision_service.VisionService') as mock:
        yield mock

@pytest.fixture
def mock_rag_service():
    """Mock RAG service"""
    with patch('services.rag_service.RAGService') as mock:
        yield mock

# Test data fixtures
@pytest.fixture
def sample_pdf_content():
    """Sample PDF content"""
    return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n174\n%%EOF"

@pytest.fixture
def sample_image_data():
    """Sample base64 image data"""
    return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/w8AAwEB/6P/4gAAAABJRU5ErkJggg=="

@pytest.fixture
def mock_interview_data():
    """Mock interview session data"""
    return {
        "session_id": "test_session_123",
        "candidate_name": "Test Candidate",
        "role": "Software Engineer",
        "status": "in_progress",
        "current_question": 1,
        "transcript": []
    }

@pytest.fixture
def mock_vision_analysis():
    """Mock vision analysis result"""
    return {
        "is_looking_at_camera": True,
        "confidence_score": 0.85,
        "face_detected": True,
        "eye_contact_score": 0.90,
        "posture_score": 0.80,
        "engagement_level": "high",
        "timestamp": 1234567890.0
    }

@pytest.fixture
def mock_proctor_event():
    """Mock proctor event data"""
    return {
        "session_id": "test_session_123",
        "event_type": "eye_contact",
        "timestamp": 1234567890.0,
        "data": {
            "looking_at_camera": True,
            "confidence": 0.85
        }
    }

# Rate limiting test fixture
@pytest.fixture
def rate_limit_test_data():
    """Data for rate limiting tests"""
    return {
        "login_credentials": {
            "email": "ratelimit@test.com",
            "password": "TestPassword123!"
        },
        "interview_data": {
            "name": "Rate Limit Test",
            "role": "Software Engineer",
            "jd": "Test job description"
        },
        "mock_test_data": {
            "category": "Python",
            "difficulty": "easy"
        }
    }

# Security test fixtures
@pytest.fixture
def malicious_inputs():
    """Collection of malicious inputs for security testing"""
    return {
        "xss": "<script>alert('xss')</script>",
        "sql_injection": "'; DROP TABLE users; --",
        "path_traversal": "../../../etc/passwd",
        "command_injection": "; cat /etc/passwd",
        "very_long": "A" * 10000,
        "null_bytes": "\x00\x00\x00",
        "unicode_exploits": "𝕿𝕳𝕴𝕾 𝕴𝕾 𝕬 𝕿𝕰𝕾𝕿"
    }

# Performance test fixtures
@pytest.fixture
def performance_thresholds():
    """Performance thresholds for testing"""
    return {
        "max_response_time": 2.0,  # seconds
        "max_memory_usage": 100 * 1024 * 1024,  # 100MB
        "max_cpu_time": 1.0,  # seconds
        "min_throughput": 10  # requests per second
    }

# Integration test fixtures
@pytest.fixture
def integration_test_data():
    """Data for integration tests"""
    return {
        "user_flow": {
            "signup": {"email": "integration@test.com", "password": "TestPassword123!", "name": "Integration User"},
            "login": {"email": "integration@test.com", "password": "TestPassword123!"},
            "interview": {"name": "Integration User", "role": "Software Engineer", "jd": "Integration test job"},
            "mock_test": {"category": "Integration", "difficulty": "medium"}
        }
    }
