"""Test interview endpoints and functionality"""

import pytest
import json
import io
import base64
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from unittest.mock import patch, MagicMock

# Import the main app
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from database import get_db, Base
from models import User, Interview

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
def auth_headers(client):
    """Get authenticated user headers"""
    # Create test user
    user_data = {
        "email": "test@example.com",
        "password": "TestPassword123!",
        "name": "Test User"
    }
    client.post("/api/auth/signup", json=user_data)
    
    # Login to get token
    login_response = client.post("/api/auth/login", json={
        "email": user_data["email"],
        "password": user_data["password"]
    })
    token = login_response.json()["access_token"]
    
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def sample_pdf():
    """Create a sample PDF file for testing"""
    # Create a minimal PDF content
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n174\n%%EOF"
    return ("sample.pdf", io.BytesIO(pdf_content), "application/pdf")

@pytest.fixture
def large_pdf():
    """Create a large PDF file for testing size limits"""
    # Create a PDF larger than 8MB
    large_content = b"%PDF-1.4\n" + b"x" * (9 * 1024 * 1024)  # 9MB
    return ("large.pdf", io.BytesIO(large_content), "application/pdf")

class TestInterviewEndpoints:
    """Test interview-related endpoints"""
    
    def test_start_interview_success(self, client, auth_headers, sample_pdf):
        """Test successful interview start"""
        files = {"resume": sample_pdf}
        data = {
            "name": "John Doe",
            "role": "Software Engineer",
            "jd": "Senior software engineer position"
        }
        
        response = client.post(
            "/api/interview/start",
            files=files,
            data=data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        result = response.json()
        assert "session_id" in result
        assert "intro" in result
        assert "questions" in result
        assert result["status"] == "success"
    
    def test_start_interview_missing_file(self, client, auth_headers):
        """Test interview start without resume file"""
        data = {
            "name": "John Doe",
            "role": "Software Engineer",
            "jd": "Senior software engineer position"
        }
        
        response = client.post(
            "/api/interview/start",
            data=data,
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_start_interview_invalid_file_type(self, client, auth_headers):
        """Test interview start with non-PDF file"""
        files = {"resume": ("test.txt", io.BytesIO(b"not a pdf"), "text/plain")}
        data = {
            "name": "John Doe",
            "role": "Software Engineer",
            "jd": "Senior software engineer position"
        }
        
        response = client.post(
            "/api/interview/start",
            files=files,
            data=data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "Only PDF files are allowed" in response.json()["detail"]
    
    def test_start_interview_file_too_large(self, client, auth_headers, large_pdf):
        """Test interview start with file too large"""
        files = {"resume": large_pdf}
        data = {
            "name": "John Doe",
            "role": "Software Engineer",
            "jd": "Senior software engineer position"
        }
        
        response = client.post(
            "/api/interview/start",
            files=files,
            data=data,
            headers=auth_headers
        )
        
        assert response.status_code == 413
        assert "too large" in response.json()["detail"]
    
    def test_start_interview_input_validation(self, client, auth_headers, sample_pdf):
        """Test input validation for interview start"""
        # Test malicious job description
        files = {"resume": sample_pdf}
        data = {
            "name": "<script>alert('xss')</script>",
            "role": "Software Engineer",
            "jd": "<script>document.location='http://evil.com'</script>"
        }
        
        response = client.post(
            "/api/interview/start",
            files=files,
            data=data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "malicious content" in response.json()["detail"]
    
    def test_start_interview_rate_limiting(self, client, auth_headers, sample_pdf):
        """Test rate limiting on interview start"""
        files = {"resume": sample_pdf}
        data = {
            "name": "John Doe",
            "role": "Software Engineer",
            "jd": "Senior software engineer position"
        }
        
        # Make multiple requests quickly
        responses = []
        for i in range(4):  # Try to exceed rate limit
            response = client.post(
                "/api/interview/start",
                files=files,
                data=data,
                headers=auth_headers
            )
            responses.append(response)
        
        # Should hit rate limit after a few requests
        rate_limited = any(r.status_code == 429 for r in responses)
        assert rate_limited, "Should be rate limited after multiple requests"
    
    def test_interview_chat_success(self, client, auth_headers):
        """Test interview chat endpoint"""
        # First start an interview
        files = {"resume": ("resume.pdf", io.BytesIO(b"sample pdf content"), "application/pdf")}
        data = {
            "name": "John Doe",
            "role": "Software Engineer",
            "jd": "Senior software engineer position"
        }
        
        start_response = client.post(
            "/api/interview/start",
            files=files,
            data=data,
            headers=auth_headers
        )
        
        session_id = start_response.json()["session_id"]
        
        # Send a chat message
        chat_data = {
            "session_id": session_id,
            "message": "I'm ready to begin the interview"
        }
        
        response = client.post(
            "/api/interview/chat",
            json=chat_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        result = response.json()
        assert "response" in result
        assert "session_id" in result
    
    def test_interview_chat_invalid_session(self, client, auth_headers):
        """Test chat with invalid session ID"""
        chat_data = {
            "session_id": "invalid_session_id",
            "message": "Hello"
        }
        
        response = client.post(
            "/api/interview/chat",
            json=chat_data,
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    def test_interview_chat_unauthorized_session(self, client, auth_headers, sample_pdf):
        """Test chat with session belonging to another user"""
        # Create another user and start interview
        other_user_data = {
            "email": "other@example.com",
            "password": "TestPassword123!",
            "name": "Other User"
        }
        client.post("/api/auth/signup", json=other_user_data)
        other_login = client.post("/api/auth/login", json={
            "email": other_user_data["email"],
            "password": other_user_data["password"]
        })
        other_token = other_login.json()["access_token"]
        other_headers = {"Authorization": f"Bearer {other_token}"}
        
        # Start interview with other user
        files = {"resume": sample_pdf}
        data = {
            "name": "Other User",
            "role": "Software Engineer",
            "jd": "Senior software engineer position"
        }
        
        start_response = client.post(
            "/api/interview/start",
            files=files,
            data=data,
            headers=other_headers
        )
        
        session_id = start_response.json()["session_id"]
        
        # Try to chat with original user (should fail)
        chat_data = {
            "session_id": session_id,
            "message": "Hello"
        }
        
        response = client.post(
            "/api/interview/chat",
            json=chat_data,
            headers=auth_headers
        )
        
        assert response.status_code == 403

class TestWebSocketInterview:
    """Test WebSocket interview functionality"""
    
    def test_websocket_connection_with_token(self, client, auth_headers, sample_pdf):
        """Test WebSocket connection with valid token"""
        # Start an interview first
        files = {"resume": sample_pdf}
        data = {
            "name": "John Doe",
            "role": "Software Engineer",
            "jd": "Senior software engineer position"
        }
        
        start_response = client.post(
            "/api/interview/start",
            files=files,
            data=data,
            headers=auth_headers
        )
        
        session_id = start_response.json()["session_id"]
        token = auth_headers["Authorization"].replace("Bearer ", "")
        
        # Test WebSocket connection (simulated)
        with client.websocket_connect(f"/ws/interview/{session_id}?token={token}") as websocket:
            # Should connect successfully
            assert websocket is not None
    
    def test_websocket_connection_without_token(self, client):
        """Test WebSocket connection without token"""
        with pytest.raises(Exception):  # Should fail to connect
            client.websocket_connect("/ws/interview/test_session")
    
    def test_websocket_connection_invalid_token(self, client):
        """Test WebSocket connection with invalid token"""
        with pytest.raises(Exception):  # Should fail to connect
            client.websocket_connect("/ws/interview/test_session?token=invalid_token")

class TestInterviewDataIntegrity:
    """Test interview data integrity and storage"""
    
    def test_interview_session_creation(self, client, auth_headers, sample_pdf):
        """Test interview session is properly created in database"""
        files = {"resume": sample_pdf}
        data = {
            "name": "John Doe",
            "role": "Software Engineer",
            "jd": "Senior software engineer position"
        }
        
        response = client.post(
            "/api/interview/start",
            files=files,
            data=data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        session_id = response.json()["session_id"]
        
        # Verify session exists in database
        db = TestingSessionLocal()
        interview = db.query(Interview).filter(Interview.session_id == session_id).first()
        assert interview is not None
        assert interview.candidate_name == "John Doe"
        assert interview.role == "Software Engineer"
        assert interview.status == "starting"
        db.close()
    
    def test_interview_transcript_compression(self, client, auth_headers, sample_pdf):
        """Test interview transcript is compressed"""
        files = {"resume": sample_pdf}
        data = {
            "name": "John Doe",
            "role": "Software Engineer",
            "jd": "Senior software engineer position"
        }
        
        start_response = client.post(
            "/api/interview/start",
            files=files,
            data=data,
            headers=auth_headers
        )
        
        session_id = start_response.json()["session_id"]
        
        # Send multiple chat messages to build transcript
        for i in range(3):
            chat_data = {
                "session_id": session_id,
                "message": f"Test message {i+1}"
            }
            client.post("/api/interview/chat", json=chat_data, headers=auth_headers)
        
        # Verify transcript is stored (should be compressed)
        db = TestingSessionLocal()
        interview = db.query(Interview).filter(Interview.session_id == session_id).first()
        assert interview is not None
        assert interview.transcript is not None
        
        # Verify transcript can be decompressed
        from services.interview_service import decompress_transcript
        if isinstance(interview.transcript, str):
            transcript = decompress_transcript(interview.transcript)
            assert isinstance(transcript, list)
            assert len(transcript) > 0
        
        db.close()

if __name__ == "__main__":
    pytest.main([__file__])
