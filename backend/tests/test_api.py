#!/usr/bin/env python3
"""
Comprehensive pytest tests for AI Virtual Coach API endpoints

Tests cover:
- Authentication endpoints (/api/auth/signup, /api/auth/login, /api/auth/me)
- Interview endpoints (/interview/chat)
- Vision endpoints (/vision/analyze)
- Database operations with test database
- Error handling and validation

Usage:
    pytest tests/test_api.py -v
"""

import os
import sys
import pytest
import asyncio
import json
from typing import Dict, Any
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

# Add backend to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import tempfile
import shutil

# Import application and dependencies
try:
    from main import app
    from database import get_db, Base
    from models import User
    from core.config import get_settings
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

# Test database setup
TEST_DATABASE_URL = "sqlite:///./test.db"

# Create test database engine
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False  # Disable SQL logging for tests
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# Override the database dependency
app.dependency_overrides[get_db] = override_get_db

# Create test client
client = TestClient(app)


@pytest.fixture(scope="session")
def setup_test_database():
    """Setup test database before running tests"""
    # Create all tables
    Base.metadata.create_all(bind=test_engine)
    yield
    # Clean up after tests
    Base.metadata.drop_all(bind=test_engine)
    if os.path.exists("test.db"):
        os.remove("test.db")


@pytest.fixture
def test_user_data():
    """Sample user data for testing"""
    return {
        "email": "test@example.com",
        "password": "TestPassword123!",
        "name": "Test User"
    }


@pytest.fixture
def authenticated_user(test_user_data, setup_test_database):
    """Create and authenticate a test user"""
    # Create user
    response = client.post("/api/auth/signup", json=test_user_data)
    assert response.status_code == 201
    
    # Login to get token
    login_data = {
        "email": test_user_data["email"],
        "password": test_user_data["password"]
    }
    login_response = client.post("/api/auth/login", json=login_data)
    assert login_response.status_code == 200
    
    token_data = login_response.json()
    return {
        "token": token_data["access_token"],
        "user": token_data["user"],
        "headers": {"Authorization": f"Bearer {token_data['access_token']}"}
    }


class TestAuthEndpoints:
    """Test authentication endpoints"""
    
    def test_signup_success(self, test_user_data, setup_test_database):
        """Test successful user signup"""
        response = client.post("/api/auth/signup", json=test_user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == test_user_data["email"]
        assert data["user"]["name"] == test_user_data["name"]
        assert "id" in data["user"]
    
    def test_signup_duplicate_email(self, test_user_data, setup_test_database):
        """Test signup with duplicate email"""
        # First signup
        client.post("/api/auth/signup", json=test_user_data)
        
        # Second signup with same email
        response = client.post("/api/auth/signup", json=test_user_data)
        
        assert response.status_code == 422
        assert "already registered" in response.json()["detail"].lower()
    
    def test_signup_invalid_email(self, setup_test_database):
        """Test signup with invalid email"""
        invalid_data = {
            "email": "invalid-email",
            "password": "TestPassword123!",
            "name": "Test User"
        }
        
        response = client.post("/api/auth/signup", json=invalid_data)
        assert response.status_code == 422
    
    def test_signup_weak_password(self, setup_test_database):
        """Test signup with weak password"""
        weak_data = {
            "email": "weak@example.com",
            "password": "123",
            "name": "Test User"
        }
        
        response = client.post("/api/auth/signup", json=weak_data)
        assert response.status_code == 422
    
    def test_login_success(self, test_user_data, setup_test_database):
        """Test successful login"""
        # First create user
        client.post("/api/auth/signup", json=test_user_data)
        
        # Login
        login_data = {
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        }
        response = client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == test_user_data["email"]
    
    def test_login_invalid_credentials(self, test_user_data, setup_test_database):
        """Test login with invalid credentials"""
        # Create user
        client.post("/api/auth/signup", json=test_user_data)
        
        # Try login with wrong password
        login_data = {
            "email": test_user_data["email"],
            "password": "WrongPassword123!"
        }
        response = client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 403
        assert "invalid" in response.json()["detail"].lower()
    
    def test_login_nonexistent_user(self, setup_test_database):
        """Test login with non-existent user"""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "TestPassword123!"
        }
        response = client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 403
    
    def test_auth_me_success(self, authenticated_user):
        """Test getting current user info"""
        response = client.get("/api/auth/me", headers=authenticated_user["headers"])
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == authenticated_user["user"]["email"]
        assert data["name"] == authenticated_user["user"]["name"]
        assert "id" in data
    
    def test_auth_me_unauthorized(self):
        """Test getting current user info without token"""
        response = client.get("/api/auth/me")
        
        assert response.status_code == 401
    
    def test_auth_me_invalid_token(self):
        """Test getting current user info with invalid token"""
        invalid_headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/auth/me", headers=invalid_headers)
        
        assert response.status_code == 401


class TestInterviewEndpoints:
    """Test interview endpoints"""
    
    def test_interview_chat_success(self, authenticated_user):
        """Test interview chat endpoint"""
        chat_data = {
            "question": "What is your experience with Python?",
            "answer": "I have 5 years of experience with Python, working on various projects including web development and data analysis.",
            "session_id": "test_session_123"
        }
        
        response = client.post(
            "/interview/chat",
            json=chat_data,
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "feedback" in data
        assert "confidence_score" in data
        assert isinstance(data["confidence_score"], (int, float))
    
    def test_interview_chat_unauthorized(self):
        """Test interview chat without authentication"""
        chat_data = {
            "question": "What is your experience with Python?",
            "answer": "I have 5 years of experience with Python.",
            "session_id": "test_session_123"
        }
        
        response = client.post("/interview/chat", json=chat_data)
        
        assert response.status_code == 401
    
    def test_interview_chat_invalid_data(self, authenticated_user):
        """Test interview chat with invalid data"""
        invalid_data = {
            "question": "",  # Empty question
            "answer": "Some answer",
            "session_id": "test_session_123"
        }
        
        response = client.post(
            "/interview/chat",
            json=invalid_data,
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 422
    
    @patch('services.llm_service.complete_with_fallback')
    def test_interview_chat_llm_failure(self, mock_llm, authenticated_user):
        """Test interview chat when LLM service fails"""
        # Mock LLM failure
        mock_llm.side_effect = Exception("LLM service unavailable")
        
        chat_data = {
            "question": "What is your experience with Python?",
            "answer": "I have 5 years of experience with Python.",
            "session_id": "test_session_123"
        }
        
        response = client.post(
            "/interview/chat",
            json=chat_data,
            headers=authenticated_user["headers"]
        )
        
        # Should still return a response with fallback
        assert response.status_code == 200
        data = response.json()
        assert "feedback" in data


class TestVisionEndpoints:
    """Test vision analysis endpoints"""
    
    def test_vision_analyze_success(self, authenticated_user):
        """Test vision analysis with valid image data"""
        # Create a simple test image (1x1 pixel PNG)
        import base64
        
        # Minimal PNG header for 1x1 pixel
        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/"
            "5+cHwAHwALqgXKg8WjAAAAABJRU5ErkJggg=="
        )
        
        files = {"frame": ("test.png", png_data, "image/png")}
        
        response = client.post(
            "/vision/analyze",
            files=files,
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "face_detected" in data
        assert "is_looking_at_camera" in data
        assert "confidence" in data
    
    def test_vision_analyze_unauthorized(self):
        """Test vision analysis without authentication"""
        png_data = b"fake_image_data"
        files = {"frame": ("test.png", png_data, "image/png")}
        
        response = client.post("/vision/analyze", files=files)
        
        assert response.status_code == 401
    
    def test_vision_analyze_invalid_file(self, authenticated_user):
        """Test vision analysis with invalid file"""
        invalid_files = {"frame": ("test.txt", b"not an image", "text/plain")}
        
        response = client.post(
            "/vision/analyze",
            files=invalid_files,
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 400
    
    def test_vision_analyze_no_file(self, authenticated_user):
        """Test vision analysis without file"""
        response = client.post(
            "/vision/analyze",
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 422
    
    def test_vision_status(self, authenticated_user):
        """Test vision status endpoint"""
        response = client.get(
            "/vision/status",
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "vision_service_available" in data
        assert "model_loaded" in data


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_404_endpoint(self):
        """Test non-existent endpoint returns 404"""
        response = client.get("/api/nonexistent")
        assert response.status_code == 404
    
    def test_method_not_allowed(self):
        """Test wrong HTTP method returns 405"""
        response = client.delete("/api/auth/me")
        assert response.status_code == 405
    
    def test_invalid_json(self):
        """Test invalid JSON payload"""
        response = client.post(
            "/api/auth/login",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
    
    def test_missing_required_fields(self, setup_test_database):
        """Test missing required fields in request"""
        incomplete_data = {"email": "test@example.com"}  # Missing password
        
        response = client.post("/api/auth/login", json=incomplete_data)
        assert response.status_code == 422


class TestDatabaseOperations:
    """Test database operations and data consistency"""
    
    def test_user_creation_persistence(self, test_user_data, setup_test_database):
        """Test that user data is properly persisted"""
        # Create user
        response = client.post("/api/auth/signup", json=test_user_data)
        assert response.status_code == 201
        
        user_id = response.json()["user"]["id"]
        
        # Verify user exists in database
        with TestingSessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            assert user is not None
            assert user.email == test_user_data["email"]
            assert user.name == test_user_data["name"]
    
    def test_user_data_isolation(self, setup_test_database):
        """Test that different users' data is isolated"""
        # Create two users
        user1_data = {
            "email": "user1@example.com",
            "password": "Password123!",
            "name": "User One"
        }
        user2_data = {
            "email": "user2@example.com",
            "password": "Password123!",
            "name": "User Two"
        }
        
        # Signup both users
        response1 = client.post("/api/auth/signup", json=user1_data)
        response2 = client.post("/api/auth/signup", json=user2_data)
        
        assert response1.status_code == 201
        assert response2.status_code == 201
        
        # Get tokens
        token1 = response1.json()["access_token"]
        token2 = response2.json()["access_token"]
        
        # Verify users can only access their own data
        headers1 = {"Authorization": f"Bearer {token1}"}
        headers2 = {"Authorization": f"Bearer {token2}"}
        
        me1 = client.get("/api/auth/me", headers=headers1).json()
        me2 = client.get("/api/auth/me", headers=headers2).json()
        
        assert me1["email"] == user1_data["email"]
        assert me2["email"] == user2_data["email"]
        assert me1["id"] != me2["id"]


class TestPerformanceAndConcurrency:
    """Test performance and concurrent operations"""
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, authenticated_user):
        """Test handling concurrent requests"""
        import asyncio
        import aiohttp
        
        # Test multiple concurrent requests to the same endpoint
        async def make_request():
            async with aiohttp.ClientSession() as session:
                headers = authenticated_user["headers"]
                async with session.get(
                    "http://testserver/api/auth/me",
                    headers={"Authorization": headers["Authorization"]}
                ) as response:
                    return await response.json()
        
        # Make 10 concurrent requests
        tasks = [make_request() for _ in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All requests should succeed
        for result in results:
            assert isinstance(result, dict)
            assert "email" in result
            assert "id" in result
    
    def test_response_time(self, authenticated_user):
        """Test that response times are reasonable"""
        import time
        
        start_time = time.time()
        response = client.get("/api/auth/me", headers=authenticated_user["headers"])
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 2.0  # Should respond within 2 seconds


class TestSecurity:
    """Test security aspects"""
    
    def test_sql_injection_protection(self, setup_test_database):
        """Test protection against SQL injection"""
        malicious_email = "'; DROP TABLE users; --"
        
        signup_data = {
            "email": malicious_email,
            "password": "Password123!",
            "name": "Test User"
        }
        
        response = client.post("/api/auth/signup", json=signup_data)
        
        # Should either fail validation or be safely handled
        assert response.status_code in [422, 201]
        
        # Verify users table still exists
        with TestingSessionLocal() as db:
            users = db.query(User).all()
            assert isinstance(users, list)
    
    def test_xss_protection(self, authenticated_user):
        """Test protection against XSS in user inputs"""
        xss_payload = "<script>alert('xss')</script>"
        
        chat_data = {
            "question": f"What is {xss_payload}?",
            "answer": f"I know about {xss_payload}",
            "session_id": "test_session"
        }
        
        response = client.post(
            "/interview/chat",
            json=chat_data,
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 200
        # Response should not contain executable script
        response_text = response.text.lower()
        assert "<script>" not in response_text


# Integration tests
class TestIntegration:
    """Test complete workflows"""
    
    def test_complete_interview_workflow(self, test_user_data, setup_test_database):
        """Test complete interview workflow from signup to chat"""
        # 1. Signup
        signup_response = client.post("/api/auth/signup", json=test_user_data)
        assert signup_response.status_code == 201
        
        token = signup_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Verify user info
        me_response = client.get("/api/auth/me", headers=headers)
        assert me_response.status_code == 200
        
        # 3. Interview chat
        chat_data = {
            "question": "Tell me about your programming experience",
            "answer": "I have been programming for 5 years, mainly in Python and JavaScript.",
            "session_id": "integration_test_session"
        }
        
        chat_response = client.post("/interview/chat", json=chat_data, headers=headers)
        assert chat_response.status_code == 200
        
        chat_data = chat_response.json()
        assert "feedback" in chat_data
        assert "confidence_score" in chat_data
        
        # 4. Verify data consistency
        final_me_response = client.get("/api/auth/me", headers=headers)
        assert final_me_response.json()["id"] == me_response.json()["id"]


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
