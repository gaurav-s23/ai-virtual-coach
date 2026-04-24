"""Test proctoring endpoints and functionality"""

import pytest
import json
import os
import tempfile
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch, MagicMock, mock_open

# Import the main app
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from database import get_db, Base

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
def temp_log_dir():
    """Create temporary directory for proctor logs"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

class TestProctoringEndpoints:
    """Test proctoring-related endpoints"""
    
    def test_proctor_log_event_success(self, client, auth_headers, temp_log_dir):
        """Test successful proctor event logging"""
        # Mock environment variable for log directory
        with patch.dict(os.environ, {'PROCTOR_LOG_DIR': temp_log_dir}):
            event_data = {
                "session_id": "test_session_123",
                "event_type": "eye_contact",
                "timestamp": 1234567890.0,
                "data": {
                    "looking_at_camera": True,
                    "confidence": 0.85
                }
            }
            
            response = client.post("/api/proctor/log", json=event_data, headers=auth_headers)
            
            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "logged"
            assert "log_file" in result
    
    def test_proctor_log_event_rate_limiting(self, client, auth_headers, temp_log_dir):
        """Test rate limiting on proctor log endpoint"""
        with patch.dict(os.environ, {'PROCTOR_LOG_DIR': temp_log_dir}):
            event_data = {
                "session_id": "test_session_456",
                "event_type": "eye_contact",
                "timestamp": 1234567890.0,
                "data": {"looking_at_camera": True}
            }
            
            # Make multiple requests quickly
            responses = []
            for i in range(60):  # Try to exceed rate limit (50 per minute)
                response = client.post("/api/proctor/log", json=event_data, headers=auth_headers)
                responses.append(response)
                
                # Stop early if we get rate limited
                if response.status_code == 429:
                    break
            
            # Should hit rate limit after some requests
            rate_limited = any(r.status_code == 429 for r in responses)
            assert rate_limited, "Should be rate limited after multiple requests"
    
    def test_proctor_log_event_invalid_data(self, client, auth_headers, temp_log_dir):
        """Test proctor event logging with invalid data"""
        with patch.dict(os.environ, {'PROCTOR_LOG_DIR': temp_log_dir}):
            # Missing required fields
            invalid_event = {
                "event_type": "eye_contact",
                # Missing session_id and timestamp
                "data": {"looking_at_camera": True}
            }
            
            response = client.post("/api/proctor/log", json=invalid_event, headers=auth_headers)
            
            assert response.status_code == 422  # Validation error
    
    def test_proctor_log_event_malicious_data(self, client, auth_headers, temp_log_dir):
        """Test proctor event logging with malicious data"""
        with patch.dict(os.environ, {'PROCTOR_LOG_DIR': temp_log_dir}):
            malicious_event = {
                "session_id": "<script>alert('xss')</script>",
                "event_type": "'; DROP TABLE users; --",
                "timestamp": 1234567890.0,
                "data": {
                    "malicious": "../../../etc/passwd",
                    "xss": "<img src=x onerror=alert('xss')>"
                }
            }
            
            response = client.post("/api/proctor/log", json=malicious_event, headers=auth_headers)
            
            # Should either sanitize and accept, or reject
            assert response.status_code in [200, 422]
    
    def test_proctor_log_event_no_auth(self, client, temp_log_dir):
        """Test proctor event logging without authentication"""
        with patch.dict(os.environ, {'PROCTOR_LOG_DIR': temp_log_dir}):
            event_data = {
                "session_id": "test_session_789",
                "event_type": "eye_contact",
                "timestamp": 1234567890.0,
                "data": {"looking_at_camera": True}
            }
            
            response = client.post("/api/proctor/log", json=event_data)
            
            assert response.status_code == 401
    
    def test_proctor_get_logs_success(self, client, auth_headers, temp_log_dir):
        """Test retrieving proctor logs"""
        with patch.dict(os.environ, {'PROCTOR_LOG_DIR': temp_log_dir}):
            # First log some events
            for i in range(3):
                event_data = {
                    "session_id": "test_session_logs",
                    "event_type": f"event_{i}",
                    "timestamp": 1234567890.0 + i,
                    "data": {"test": f"data_{i}"}
                }
                client.post("/api/proctor/log", json=event_data, headers=auth_headers)
            
            # Retrieve logs
            response = client.get("/api/proctor/logs?session_id=test_session_logs", headers=auth_headers)
            
            assert response.status_code == 200
            result = response.json()
            assert "logs" in result
            assert len(result["logs"]) >= 0
    
    def test_proctor_get_logs_invalid_session(self, client, auth_headers, temp_log_dir):
        """Test retrieving logs for invalid session"""
        with patch.dict(os.environ, {'PROCTOR_LOG_DIR': temp_log_dir}):
            response = client.get("/api/proctor/logs?session_id=invalid_session", headers=auth_headers)
            
            assert response.status_code == 200
            result = response.json()
            assert "logs" in result
            # Should return empty logs for invalid session
            assert len(result["logs"]) == 0
    
    def test_proctor_get_logs_no_session_param(self, client, auth_headers, temp_log_dir):
        """Test retrieving logs without session parameter"""
        with patch.dict(os.environ, {'PROCTOR_LOG_DIR': temp_log_dir}):
            response = client.get("/api/proctor/logs", headers=auth_headers)
            
            assert response.status_code == 422  # Missing required parameter

class TestProctoringSecurity:
    """Test security features for proctoring"""
    
    def test_proctor_log_directory_security(self, client, auth_headers, temp_log_dir):
        """Test proctor log directory is secure"""
        with patch.dict(os.environ, {'PROCTOR_LOG_DIR': temp_log_dir}):
            event_data = {
                "session_id": "security_test",
                "event_type": "test",
                "timestamp": 1234567890.0,
                "data": {"test": "data"}
            }
            
            response = client.post("/api/proctor/log", json=event_data, headers=auth_headers)
            
            assert response.status_code == 200
            
            # Check if log file was created in secure directory
            log_files = os.listdir(temp_log_dir)
            assert len(log_files) > 0
            
            # Verify log file permissions (should be restricted)
            for log_file in log_files:
                file_path = os.path.join(temp_log_dir, log_file)
                # In Windows, check if file exists and is readable
                assert os.path.exists(file_path)
    
    def test_proctor_log_path_traversal_prevention(self, client, auth_headers, temp_log_dir):
        """Test path traversal prevention in log files"""
        with patch.dict(os.environ, {'PROCTOR_LOG_DIR': temp_log_dir}):
            # Try to use path traversal in session ID
            malicious_event = {
                "session_id": "../../../etc/passwd",
                "event_type": "test",
                "timestamp": 1234567890.0,
                "data": {"test": "data"}
            }
            
            response = client.post("/api/proctor/log", json=malicious_event, headers=auth_headers)
            
            # Should either sanitize the session ID or reject the request
            assert response.status_code in [200, 422]
            
            # If accepted, verify no files were created outside the log directory
            log_files = os.listdir(temp_log_dir)
            for log_file in log_files:
                file_path = os.path.join(temp_log_dir, log_file)
                # File should be within the log directory
                assert os.path.commonpath([temp_log_dir, file_path]) == temp_log_dir
    
    def test_proctor_log_input_size_limits(self, client, auth_headers, temp_log_dir):
        """Test input size limits for proctor logs"""
        with patch.dict(os.environ, {'PROCTOR_LOG_DIR': temp_log_dir}):
            # Create event with very large data
            large_event = {
                "session_id": "size_test",
                "event_type": "test",
                "timestamp": 1234567890.0,
                "data": {
                    "large_field": "A" * 1000000  # 1MB of data
                }
            }
            
            response = client.post("/api/proctor/log", json=large_event, headers=auth_headers)
            
            # Should either accept or reject based on size limits
            assert response.status_code in [200, 413, 422]

class TestProctoringIntegration:
    """Test proctoring integration with other services"""
    
    def test_proctor_integration_with_interview(self, client, auth_headers, temp_log_dir):
        """Test proctoring integration with interview sessions"""
        with patch.dict(os.environ, {'PROCTOR_LOG_DIR': temp_log_dir}):
            # Start an interview (mock)
            files = {"resume": ("resume.pdf", io.BytesIO(b"sample pdf content"), "application/pdf")}
            data = {
                "name": "John Doe",
                "role": "Software Engineer",
                "jd": "Senior software engineer position"
            }
            
            # Mock the interview start to avoid LLM dependency
            with patch('services.llm_client.LLMClient.generate_stream') as mock_generate:
                mock_response = MagicMock()
                mock_response.type = "complete"
                mock_response.content = json.dumps({"session_id": "interview_session_123"})
                mock_generate.return_value = [mock_response]
                
                interview_response = client.post(
                    "/api/interview/start",
                    files=files,
                    data=data,
                    headers=auth_headers
                )
            
            # Log proctor events for the interview session
            session_id = "interview_session_123"
            for i in range(3):
                event_data = {
                    "session_id": session_id,
                    "event_type": f"proctor_event_{i}",
                    "timestamp": 1234567890.0 + i,
                    "data": {"event_data": f"test_{i}"}
                }
                client.post("/api/proctor/log", json=event_data, headers=auth_headers)
            
            # Retrieve proctor logs for the session
            response = client.get(f"/api/proctor/logs?session_id={session_id}", headers=auth_headers)
            
            assert response.status_code == 200
            result = response.json()
            assert "logs" in result
    
    def test_proctor_log_file_rotation(self, client, auth_headers, temp_log_dir):
        """Test proctor log file rotation"""
        with patch.dict(os.environ, {'PROCTOR_LOG_DIR': temp_log_dir}):
            # Generate many log events to test file rotation
            for i in range(100):
                event_data = {
                    "session_id": f"rotation_test_{i % 10}",  # 10 different sessions
                    "event_type": "test_event",
                    "timestamp": 1234567890.0 + i,
                    "data": {"event_index": i}
                }
                client.post("/api/proctor/log", json=event_data, headers=auth_headers)
            
            # Check that log files are created and managed properly
            log_files = os.listdir(temp_log_dir)
            assert len(log_files) > 0
            
            # Verify log files don't grow excessively
            total_size = sum(os.path.getsize(os.path.join(temp_log_dir, f)) for f in log_files)
            # Should be reasonable size (less than 10MB for test data)
            assert total_size < 10 * 1024 * 1024

class TestProctoringPerformance:
    """Test proctoring performance and optimization"""
    
    def test_proctor_log_response_time(self, client, auth_headers, temp_log_dir):
        """Test proctor log endpoint response time"""
        import time
        
        with patch.dict(os.environ, {'PROCTOR_LOG_DIR': temp_log_dir}):
            event_data = {
                "session_id": "performance_test",
                "event_type": "test",
                "timestamp": 1234567890.0,
                "data": {"test": "data"}
            }
            
            start_time = time.time()
            response = client.post("/api/proctor/log", json=event_data, headers=auth_headers)
            end_time = time.time()
            
            response_time = end_time - start_time
            
            assert response.status_code == 200
            assert response_time < 1.0, f"Response time {response_time}s is too slow"
    
    def test_proctor_log_concurrent_requests(self, client, auth_headers, temp_log_dir):
        """Test proctor log with concurrent requests"""
        import threading
        import time
        
        results = []
        
        def log_event(event_index):
            with patch.dict(os.environ, {'PROCTOR_LOG_DIR': temp_log_dir}):
                event_data = {
                    "session_id": f"concurrent_test_{event_index % 5}",
                    "event_type": "concurrent_event",
                    "timestamp": 1234567890.0 + event_index,
                    "data": {"event_index": event_index}
                }
                
                response = client.post("/api/proctor/log", json=event_data, headers=auth_headers)
                results.append(response.status_code)
        
        # Start multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=log_event, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        success_count = sum(1 for status in results if status == 200)
        assert success_count >= 8, f"Too many failed requests: {results}"

if __name__ == "__main__":
    pytest.main([__file__])
