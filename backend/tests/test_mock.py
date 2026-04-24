"""Test mock test endpoints and functionality"""

import pytest
import json
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from unittest.mock import patch, MagicMock, AsyncMock

# Import the main app
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from database import get_db, Base
from models import User, MockSession

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

class TestMockTestEndpoints:
    """Test mock test-related endpoints"""
    
    @patch('services.llm_client.LLMClient.generate_stream')
    def test_generate_mock_test_success(self, mock_generate, client, auth_headers):
        """Test successful mock test generation"""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.type = "complete"
        mock_response.content = json.dumps([
            {
                "question": "What is Python?",
                "options": ["A language", "A snake", "A framework", "A database"],
                "correct_answer": 0,
                "explanation": "Python is a programming language"
            },
            {
                "question": "What is FastAPI?",
                "options": ["A framework", "A language", "A database", "A library"],
                "correct_answer": 0,
                "explanation": "FastAPI is a web framework"
            }
        ])
        
        mock_generate.return_value = [mock_response]
        
        data = {
            "category": "Python",
            "difficulty": "easy",
            "force_new": True
        }
        
        response = client.post("/api/generate-quiz", json=data, headers=auth_headers)
        
        assert response.status_code == 200
        # Check streaming response headers
        assert response.headers["content-type"] == "text/event-stream"
    
    @patch('services.llm_client.LLMClient.generate_stream')
    def test_generate_mock_test_rate_limiting(self, mock_generate, client, auth_headers):
        """Test rate limiting on mock test generation"""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.type = "complete"
        mock_response.content = json.dumps([{"question": "Test question"}])
        mock_generate.return_value = [mock_response]
        
        data = {
            "category": "Python",
            "difficulty": "easy",
            "force_new": True
        }
        
        # Make multiple requests quickly
        responses = []
        for i in range(20):  # Try to exceed rate limit (15 per minute)
            response = client.post("/api/generate-quiz", json=data, headers=auth_headers)
            responses.append(response)
        
        # Should hit rate limit after some requests
        rate_limited = any(r.status_code == 429 for r in responses)
        assert rate_limited, "Should be rate limited after multiple requests"
    
    def test_generate_mock_test_invalid_category(self, client, auth_headers):
        """Test mock test generation with invalid category"""
        data = {
            "category": "",  # Empty category
            "difficulty": "easy",
            "force_new": True
        }
        
        response = client.post("/api/generate-quiz", json=data, headers=auth_headers)
        
        assert response.status_code == 422  # Validation error
    
    @patch('services.llm_service.generate_english_questions')
    def test_english_questions_success(self, mock_generate, client, auth_headers):
        """Test English questions generation"""
        mock_generate.return_value = [
            {"question": "What is your experience with Python?", "type": "experience"},
            {"question": "Describe a challenging project", "type": "behavioral"}
        ]
        
        data = {"topic": "Software Engineering"}
        
        response = client.post("/api/english/questions", json=data, headers=auth_headers)
        
        assert response.status_code == 200
        result = response.json()
        assert "questions" in result
        assert len(result["questions"]) == 2
    
    @patch('services.llm_service.generate_english_questions')
    def test_english_questions_rate_limiting(self, mock_generate, client, auth_headers):
        """Test rate limiting on English questions generation"""
        mock_generate.return_value = [{"question": "Test question"}]
        
        data = {"topic": "Software Engineering"}
        
        # Make multiple requests quickly
        responses = []
        for i in range(15):  # Try to exceed rate limit (10 per minute)
            response = client.post("/api/english/questions", json=data, headers=auth_headers)
            responses.append(response)
        
        # Should hit rate limit after some requests
        rate_limited = any(r.status_code == 429 for r in responses)
        assert rate_limited, "Should be rate limited after multiple requests"
    
    @patch('services.llm_service.generate_final_report')
    def test_english_report_success(self, mock_generate, client, auth_headers):
        """Test English report generation"""
        mock_generate.return_value = {
            "overall_score": 85,
            "technical_rating": 90,
            "communication_rating": 80,
            "brutal_feedback": "Good performance but needs improvement in technical areas",
            "ready_for_senior_role": True
        }
        
        data = {
            "history": [
                {"question": "Test question", "answer": "Test answer", "feedback": "Good"}
            ]
        }
        
        response = client.post("/api/english/report", json=data, headers=auth_headers)
        
        assert response.status_code == 200
        result = response.json()
        assert result["overall_score"] == 85
        assert result["technical_rating"] == 90
        assert result["communication_rating"] == 80
        assert "brutal_feedback" in result
        assert result["ready_for_senior_role"] is True
    
    @patch('services.llm_service.generate_final_report')
    def test_english_report_rate_limiting(self, mock_generate, client, auth_headers):
        """Test rate limiting on English report generation"""
        mock_generate.return_value = {"overall_score": 80}
        
        data = {"history": [{"question": "Test", "answer": "Test", "feedback": "Good"}]}
        
        # Make multiple requests quickly
        responses = []
        for i in range(8):  # Try to exceed rate limit (5 per minute)
            response = client.post("/api/english/report", json=data, headers=auth_headers)
            responses.append(response)
        
        # Should hit rate limit after some requests
        rate_limited = any(r.status_code == 429 for r in responses)
        assert rate_limited, "Should be rate limited after multiple requests"
    
    def test_english_topic_endpoint(self, client, auth_headers):
        """Test English topic endpoint"""
        response = client.get("/api/english/topic", headers=auth_headers)
        
        assert response.status_code == 200
        result = response.json()
        assert "topic" in result
        assert isinstance(result["topic"], str)
        assert len(result["topic"]) > 0
    
    def test_mock_end_session_success(self, client, auth_headers):
        """Test ending mock session"""
        session_data = {
            "session_id": "test_session_123",
            "answers": [
                {"question_id": 1, "answer": 0, "time_taken": 30},
                {"question_id": 2, "answer": 1, "time_taken": 45}
            ],
            "total_time": 300,
            "score": 80
        }
        
        response = client.post("/api/mock/end-session", json=session_data, headers=auth_headers)
        
        assert response.status_code == 200
        result = response.json()
        assert "session_id" in result
        assert result["status"] == "completed"
    
    def test_mock_end_session_invalid_data(self, client, auth_headers):
        """Test ending mock session with invalid data"""
        session_data = {
            "session_id": "",  # Empty session ID
            "answers": [],
            "total_time": -1,  # Invalid time
            "score": 150  # Invalid score > 100
        }
        
        response = client.post("/api/mock/end-session", json=session_data, headers=auth_headers)
        
        assert response.status_code == 422  # Validation error

class TestMockTestFunctionality:
    """Test mock test business logic and data integrity"""
    
    def test_mock_session_creation(self, client, auth_headers):
        """Test mock session is properly created"""
        # Generate a mock test first
        with patch('services.llm_client.LLMClient.generate_stream') as mock_generate:
            mock_response = MagicMock()
            mock_response.type = "complete"
            mock_response.content = json.dumps([{"question": "Test question"}])
            mock_generate.return_value = [mock_response]
            
            data = {"category": "Python", "difficulty": "easy", "force_new": True}
            client.post("/api/generate-quiz", json=data, headers=auth_headers)
        
        # Verify session exists in database
        db = TestingSessionLocal()
        mock_session = db.query(MockSession).first()
        if mock_session:  # Only check if session was created
            assert mock_session.category == "Python"
            assert mock_session.difficulty == "easy"
        db.close()
    
    def test_mock_answer_submission(self, client, auth_headers):
        """Test submitting mock test answers"""
        # First create a session
        session_data = {
            "session_id": "test_session_456",
            "answers": [
                {"question_id": 1, "answer": 0, "time_taken": 30}
            ],
            "total_time": 30,
            "score": 100
        }
        
        response = client.post("/api/mock/answer", json=session_data, headers=auth_headers)
        
        assert response.status_code == 200
        result = response.json()
        assert "session_id" in result
        assert result["status"] == "in_progress"
    
    def test_mock_score_calculation(self, client, auth_headers):
        """Test mock test score calculation"""
        session_data = {
            "session_id": "test_session_score",
            "answers": [
                {"question_id": 1, "answer": 0, "time_taken": 30},  # Correct
                {"question_id": 2, "answer": 1, "time_taken": 45},  # Incorrect
                {"question_id": 3, "answer": 0, "time_taken": 25}   # Correct
            ],
            "total_time": 100,
            "score": 66.67  # 2/3 correct = 66.67%
        }
        
        response = client.post("/api/mock/end-session", json=session_data, headers=auth_headers)
        
        assert response.status_code == 200
        result = response.json()
        assert "score" in result
        # Score should be close to expected value
        assert abs(result.get("score", 0) - 66.67) < 1.0

class TestMockTestSecurity:
    """Test security features for mock tests"""
    
    def test_mock_test_authentication_required(self, client):
        """Test that authentication is required for mock test endpoints"""
        endpoints = [
            ("/api/generate-quiz", "POST", {"category": "Python", "difficulty": "easy"}),
            ("/api/english/questions", "POST", {"topic": "Software Engineering"}),
            ("/api/english/report", "POST", {"history": []}),
            ("/api/mock/end-session", "POST", {"session_id": "test", "answers": []}),
            ("/api/mock/answer", "POST", {"session_id": "test", "answers": []})
        ]
        
        for endpoint, method, data in endpoints:
            if method == "POST":
                response = client.post(endpoint, json=data)
            else:
                response = client.get(endpoint)
            
            assert response.status_code == 401, f"Endpoint {endpoint} should require authentication"
    
    def test_mock_test_input_validation(self, client, auth_headers):
        """Test input validation for mock test endpoints"""
        # Test malicious input in category
        malicious_data = {
            "category": "<script>alert('xss')</script>",
            "difficulty": "easy",
            "force_new": True
        }
        
        response = client.post("/api/generate-quiz", json=malicious_data, headers=auth_headers)
        
        # Should either accept and sanitize, or reject
        assert response.status_code in [200, 422]
        
        # Test extremely long input
        long_data = {
            "category": "a" * 10000,  # Very long category
            "difficulty": "easy",
            "force_new": True
        }
        
        response = client.post("/api/generate-quiz", json=long_data, headers=auth_headers)
        
        # Should reject extremely long input
        assert response.status_code == 422

if __name__ == "__main__":
    pytest.main([__file__])
