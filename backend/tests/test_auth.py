"""Test authentication endpoints and security features"""

import pytest
import json
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import tempfile
from unittest.mock import patch

# Import the main app
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from database import get_db, Base
from core.config import get_settings

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def test_user_data():
    return {
        "email": "test@example.com",
        "password": "TestPassword123!",
        "name": "Test User"
    }

@pytest.fixture
def admin_credentials():
    return {
        "email": os.getenv("ADMIN_EMAIL", "admin@example.com"),
        "password": os.getenv("ADMIN_PASSWORD", "admin123")
    }

class TestAuthentication:
    """Test authentication endpoints"""
    
    def test_user_signup_success(self, client, test_user_data):
        """Test successful user signup"""
        response = client.post("/api/auth/signup", json=test_user_data)
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == test_user_data["email"]
        assert data["name"] == test_user_data["name"]
        assert "id" in data
    
    def test_user_signup_duplicate_email(self, client, test_user_data):
        """Test signup with duplicate email fails"""
        # First signup
        client.post("/api/auth/signup", json=test_user_data)
        # Second signup with same email
        response = client.post("/api/auth/signup", json=test_user_data)
        assert response.status_code == 409
        assert "already registered" in response.json()["detail"]
    
    def test_user_signup_invalid_email(self, client):
        """Test signup with invalid email fails"""
        response = client.post("/api/auth/signup", json={
            "email": "invalid-email",
            "password": "TestPassword123!",
            "name": "Test User"
        })
        assert response.status_code == 422
        assert "Invalid email format" in response.json()["detail"]
    
    def test_user_signup_weak_password(self, client):
        """Test signup with weak password fails"""
        response = client.post("/api/auth/signup", json={
            "email": "test@example.com",
            "password": "123",
            "name": "Test User"
        })
        assert response.status_code == 422
    
    def test_user_login_success(self, client, test_user_data):
        """Test successful user login"""
        # First signup
        client.post("/api/auth/signup", json=test_user_data)
        # Then login
        response = client.post("/api/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == test_user_data["email"]
    
    def test_user_login_invalid_credentials(self, client, test_user_data):
        """Test login with invalid credentials fails"""
        # First signup
        client.post("/api/auth/signup", json=test_user_data)
        # Then login with wrong password
        response = client.post("/api/auth/login", json={
            "email": test_user_data["email"],
            "password": "wrongpassword"
        })
        assert response.status_code == 400
        assert "Invalid email or password" in response.json()["detail"]
    
    def test_admin_login_success(self, client, admin_credentials):
        """Test successful admin login"""
        response = client.post("/api/admin/login", json=admin_credentials)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["access_token"] is not None
    
    def test_admin_login_invalid_credentials(self, client):
        """Test admin login with invalid credentials fails"""
        response = client.post("/api/admin/login", json={
            "email": "wrong@admin.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 403
        assert "Invalid admin credentials" in response.json()["detail"]
    
    def test_verify_token_success(self, client, test_user_data):
        """Test token verification"""
        # Signup and login to get token
        client.post("/api/auth/signup", json=test_user_data)
        login_response = client.post("/api/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })
        token = login_response.json()["access_token"]
        
        # Verify token
        response = client.post("/api/auth/verify-token", json={"token": token})
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert "user_id" in data
    
    def test_verify_token_invalid(self, client):
        """Test verification of invalid token"""
        response = client.post("/api/auth/verify-token", json={"token": "invalid_token"})
        assert response.status_code == 401
    
    def test_protected_endpoint_without_token(self, client):
        """Test accessing protected endpoint without token"""
        response = client.get("/api/auth/me")
        assert response.status_code == 401
    
    def test_protected_endpoint_with_valid_token(self, client, test_user_data):
        """Test accessing protected endpoint with valid token"""
        # Signup and login to get token
        client.post("/api/auth/signup", json=test_user_data)
        login_response = client.post("/api/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        })
        token = login_response.json()["access_token"]
        
        # Access protected endpoint
        response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user_data["email"]

class TestSecurityFeatures:
    """Test security features"""
    
    def test_token_validation_input_sanitization(self, client):
        """Test token validation with malicious input"""
        malicious_tokens = [
            "<script>alert('xss')</script>",
            "'; DROP TABLE users; --",
            "../../../etc/passwd",
            "a" * 10000  # Very long token
        ]
        
        for malicious_token in malicious_tokens:
            response = client.post("/api/auth/verify-token", json={"token": malicious_token})
            assert response.status_code in [400, 401, 422]  # Should reject malicious input
    
    def test_rate_limiting_login(self, client, test_user_data):
        """Test rate limiting on login endpoint"""
        # Create user first
        client.post("/api/auth/signup", json=test_user_data)
        
        # Make multiple failed login attempts
        for i in range(5):
            response = client.post("/api/auth/login", json={
                "email": test_user_data["email"],
                "password": "wrongpassword"
            })
            if i < 3:  # Should allow first few attempts
                assert response.status_code == 400
            else:  # Should rate limit after several attempts
                assert response.status_code == 429
    
    def test_password_complexity_validation(self, client):
        """Test password complexity requirements"""
        weak_passwords = [
            "123",  # Too short
            "password",  # No numbers or special chars
            "12345678",  # No letters
            "Password123",  # No special chars
        ]
        
        for weak_password in weak_passwords:
            response = client.post("/api/auth/signup", json={
                "email": f"test{weak_password}@example.com",
                "password": weak_password,
                "name": "Test User"
            })
            assert response.status_code == 422

if __name__ == "__main__":
    pytest.main([__file__])
