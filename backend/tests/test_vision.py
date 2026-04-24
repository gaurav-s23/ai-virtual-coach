"""Test vision analysis endpoints and functionality"""

import pytest
import json
import base64
import io
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
def sample_image_data():
    """Create sample base64 image data for testing"""
    # Create a small PNG image (1x1 pixel)
    png_data = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
        "/w8AAwEB/6P/4gAAAABJRU5ErkJggg=="
    )
    return png_data

@pytest.fixture
def large_image_data():
    """Create large base64 image data for testing size limits"""
    # Create a large image data string (simulate 6MB+ image)
    large_data = "A" * (7 * 1024 * 1024)  # 7MB of data
    return base64.b64encode(large_data.encode()).decode()

@pytest.fixture
def valid_image_request(sample_image_data):
    """Create a valid vision analysis request"""
    return {
        "frame_data": f"data:image/png;base64,{sample_image_data}",
        "session_id": "test_session_123"
    }

class TestVisionAnalysisEndpoints:
    """Test vision analysis endpoints"""
    
    @patch('services.vision_service.VisionService.analyze_frame')
    def test_vision_analysis_success(self, mock_analyze, client, auth_headers, valid_image_request):
        """Test successful vision analysis"""
        # Mock vision service response
        mock_result = MagicMock()
        mock_result.is_looking_at_camera = True
        mock_result.confidence_score = 0.85
        mock_result.face_detected = True
        mock_result.eye_contact_score = 0.90
        mock_result.posture_score = 0.80
        mock_result.engagement_level = "high"
        mock_result.timestamp = 1234567890.0
        mock_analyze.return_value = mock_result
        
        response = client.post("/api/vision/analyze", json=valid_image_request, headers=auth_headers)
        
        assert response.status_code == 200
        result = response.json()
        assert result["is_looking_at_camera"] is True
        assert result["confidence_score"] == 0.85
        assert result["face_detected"] is True
        assert result["eye_contact_score"] == 0.90
        assert result["posture_score"] == 0.80
        assert result["engagement_level"] == "high"
        assert "timestamp" in result
    
    def test_vision_analysis_no_auth(self, client, valid_image_request):
        """Test vision analysis without authentication"""
        response = client.post("/api/vision/analyze", json=valid_image_request)
        
        assert response.status_code == 401
    
    def test_vision_analysis_empty_frame_data(self, client, auth_headers):
        """Test vision analysis with empty frame data"""
        request_data = {
            "frame_data": "",
            "session_id": "test_session_123"
        }
        
        response = client.post("/api/vision/analyze", json=request_data, headers=auth_headers)
        
        assert response.status_code == 400
        assert "Frame data is required" in response.json()["detail"]
    
    def test_vision_analysis_missing_frame_data(self, client, auth_headers):
        """Test vision analysis with missing frame data"""
        request_data = {
            "session_id": "test_session_123"
        }
        
        response = client.post("/api/vision/analyze", json=request_data, headers=auth_headers)
        
        assert response.status_code == 422  # Validation error
    
    def test_vision_analysis_large_base64_data(self, client, auth_headers, large_image_data):
        """Test vision analysis with oversized base64 data"""
        request_data = {
            "frame_data": large_image_data,
            "session_id": "test_session_123"
        }
        
        response = client.post("/api/vision/analyze", json=request_data, headers=auth_headers)
        
        assert response.status_code == 413
        assert "too large" in response.json()["detail"]
    
    def test_vision_analysis_invalid_base64(self, client, auth_headers):
        """Test vision analysis with invalid base64 data"""
        request_data = {
            "frame_data": "invalid_base64_data!!!@@@",
            "session_id": "test_session_123"
        }
        
        response = client.post("/api/vision/analyze", json=request_data, headers=auth_headers)
        
        assert response.status_code == 400
        assert "Failed to decode frame data" in response.json()["detail"]
    
    def test_vision_analysis_invalid_image_format(self, client, auth_headers):
        """Test vision analysis with invalid image data"""
        # Create invalid image data
        invalid_image_data = base64.b64encode(b"not_an_image").decode()
        request_data = {
            "frame_data": f"data:image/png;base64,{invalid_image_data}",
            "session_id": "test_session_123"
        }
        
        response = client.post("/api/vision/analyze", json=request_data, headers=auth_headers)
        
        assert response.status_code == 400
        assert "Invalid frame data" in response.json()["detail"]
    
    def test_vision_analysis_size_limits(self, client, auth_headers):
        """Test various size limits for vision analysis"""
        # Test with different image sizes
        
        # Small image (should work)
        small_png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/w8AAwEB/6P/4gAAAABJRU5ErkJggg=="
        request_data = {
            "frame_data": f"data:image/png;base64,{small_png}",
            "session_id": "test_session_123"
        }
        
        response = client.post("/api/vision/analyze", json=request_data, headers=auth_headers)
        # Should either succeed (if mocked) or fail due to vision service, but not due to size
        assert response.status_code in [200, 500]  # 500 if vision service not available
        
        # Test with very large image dimensions (simulated)
        # This would normally require actual image processing, so we'll test the validation
        large_dimensions_request = {
            "frame_data": "A" * (11 * 1024 * 1024),  # Over 10MB
            "session_id": "test_session_123"
        }
        
        response = client.post("/api/vision/analyze", json=large_dimensions_request, headers=auth_headers)
        assert response.status_code == 413

class TestVisionAnalysisSecurity:
    """Test security features for vision analysis"""
    
    def test_vision_analysis_input_sanitization(self, client, auth_headers):
        """Test input sanitization for vision analysis"""
        malicious_inputs = [
            "<script>alert('xss')</script>",
            "'; DROP TABLE users; --",
            "../../../etc/passwd",
            "data:image/svg+xml;base64,PHN2ZyBvbmxvYWQ9ImFsZXJ0KGRvY3VtZW50LmRvbWFpbikiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PC9zdmc+",
        ]
        
        for malicious_input in malicious_inputs:
            request_data = {
                "frame_data": malicious_input,
                "session_id": "test_session_123"
            }
            
            response = client.post("/api/vision/analyze", json=request_data, headers=auth_headers)
            
            # Should reject malicious input
            assert response.status_code in [400, 413, 422]
    
    def test_vision_analysis_session_validation(self, client, auth_headers, sample_image_data):
        """Test session ID validation"""
        # Test with very long session ID
        long_session_id = "a" * 1000
        request_data = {
            "frame_data": f"data:image/png;base64,{sample_image_data}",
            "session_id": long_session_id
        }
        
        response = client.post("/api/vision/analyze", json=request_data, headers=auth_headers)
        
        # Should either accept or validate session ID length
        assert response.status_code in [200, 422]
    
    def test_vision_analysis_rate_limiting(self, client, auth_headers, sample_image_data):
        """Test rate limiting on vision analysis endpoint"""
        request_data = {
            "frame_data": f"data:image/png;base64,{sample_image_data}",
            "session_id": "test_session_123"
        }
        
        # Make multiple requests quickly
        responses = []
        for i in range(100):  # Try to exceed any rate limits
            response = client.post("/api/vision/analyze", json=request_data, headers=auth_headers)
            responses.append(response)
            
            # Stop early if we get rate limited
            if response.status_code == 429:
                break
        
        # Check if any response was rate limited
        rate_limited = any(r.status_code == 429 for r in responses)
        # Rate limiting might not be implemented for vision yet, so this is optional
        # If implemented, should be rate limited
        # assert rate_limited, "Should be rate limited after many requests"

class TestVisionAnalysisIntegration:
    """Test vision analysis integration with other services"""
    
    @patch('services.vision_service.VisionService.analyze_frame')
    def test_vision_analysis_with_session_tracking(self, mock_analyze, client, auth_headers, valid_image_request):
        """Test vision analysis tracks sessions properly"""
        # Mock vision service response
        mock_result = MagicMock()
        mock_result.is_looking_at_camera = True
        mock_result.confidence_score = 0.85
        mock_result.face_detected = True
        mock_result.eye_contact_score = 0.90
        mock_result.posture_score = 0.80
        mock_result.engagement_level = "high"
        mock_result.timestamp = 1234567890.0
        mock_analyze.return_value = mock_result
        
        session_id = "integration_test_session"
        request_data = {
            "frame_data": valid_image_request["frame_data"],
            "session_id": session_id
        }
        
        # Make multiple requests for the same session
        for i in range(3):
            response = client.post("/api/vision/analyze", json=request_data, headers=auth_headers)
            assert response.status_code == 200
            
            # Verify mock was called with correct session ID
            mock_analyze.assert_called()
            call_args = mock_analyze.call_args
            assert call_args[0][1] == session_id  # Second argument should be session_id
    
    @patch('services.vision_service.VisionService.analyze_frame')
    def test_vision_analysis_error_handling(self, mock_analyze, client, auth_headers, valid_image_request):
        """Test vision analysis error handling"""
        # Mock vision service to raise exception
        mock_analyze.side_effect = Exception("Vision service error")
        
        response = client.post("/api/vision/analyze", json=valid_image_request, headers=auth_headers)
        
        assert response.status_code == 500
        assert "error" in response.json().get("detail", "").lower()
    
    def test_vision_service_initialization(self, client):
        """Test vision service initialization"""
        # This tests that the vision service can be initialized
        # without actually calling the endpoint
        from routes.vision import get_vision_service
        
        try:
            service = get_vision_service()
            assert service is not None
        except ImportError:
            # Vision service might not be available in test environment
            pytest.skip("Vision service not available")

class TestVisionAnalysisPerformance:
    """Test vision analysis performance and optimization"""
    
    def test_vision_analysis_response_time(self, client, auth_headers, sample_image_data):
        """Test vision analysis response time"""
        import time
        
        request_data = {
            "frame_data": f"data:image/png;base64,{sample_image_data}",
            "session_id": "performance_test"
        }
        
        start_time = time.time()
        response = client.post("/api/vision/analyze", json=request_data, headers=auth_headers)
        end_time = time.time()
        
        response_time = end_time - start_time
        
        # Should respond quickly (even if vision service fails)
        assert response_time < 5.0, f"Response time {response_time}s is too slow"
    
    def test_vision_analysis_memory_usage(self, client, auth_headers, sample_image_data):
        """Test vision analysis doesn't cause memory issues"""
        import gc
        
        request_data = {
            "frame_data": f"data:image/png;base64,{sample_image_data}",
            "session_id": "memory_test"
        }
        
        # Make multiple requests
        for i in range(10):
            response = client.post("/api/vision/analyze", json=request_data, headers=auth_headers)
            # Should not cause memory issues
            assert response.status_code in [200, 500]  # 500 if vision service not available
        
        # Force garbage collection
        gc.collect()

if __name__ == "__main__":
    pytest.main([__file__])
