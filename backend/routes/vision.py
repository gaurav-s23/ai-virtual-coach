from __future__ import annotations

import logging
import base64
import cv2
import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

try:
    from database import get_db
    from core.security import get_current_user
    from models import User
    from services.vision_service import VisionService, VisionAnalysis
except ImportError as e:
    logger.error(f"Import error in vision.py: {e}")
    # Fallback imports for development
    try:
        from database import get_db
        from core.security import get_current_user
        from models import User
        from services.vision_service import VisionService, VisionAnalysis
    except ImportError as fallback_error:
        logger.error(f"Fallback import error in vision.py: {fallback_error}")
        raise SystemExit(f"Failed to import required modules in vision.py: {fallback_error}")

logger = logging.getLogger("ai_virtual_coach.vision")

router = APIRouter(prefix="/api/vision", tags=["vision"])

# Pydantic models for request/response
class VisionAnalysisRequest(BaseModel):
    frame_data: str  # Base64 encoded image data
    session_id: str = None

class VisionAnalysisResponse(BaseModel):
    is_looking_at_camera: bool
    confidence_score: float
    face_detected: bool
    eye_contact_score: float
    posture_score: float
    engagement_level: str
    timestamp: float

# Initialize vision service
_vision_service = None

def get_vision_service() -> VisionService:
    """Get or create vision service instance"""
    global _vision_service
    if _vision_service is None:
        _vision_service = VisionService()
        logger.info("Vision service initialized")
    return _vision_service

@router.post("/analyze", response_model=VisionAnalysisResponse)
async def analyze_vision_frame(
    request: VisionAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analyze vision frame for eye contact and engagement metrics
    
    Args:
        request: Base64 encoded frame data and session ID
        current_user: Authenticated user
        db: Database session
        
    Returns:
        VisionAnalysisResponse: Analysis results
    """
    try:
        # Validate frame data size before processing
        if not request.frame_data:
            raise HTTPException(status_code=400, detail="Frame data is required")
        
        # Check base64 data size (limit to 10MB)
        frame_data_size = len(request.frame_data.encode('utf-8'))
        if frame_data_size > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(status_code=413, detail="Frame data too large (max 10MB)")
        
        # Decode base64 frame
        try:
            # Remove data URL prefix if present
            if request.frame_data.startswith('data:image'):
                frame_data = request.frame_data.split(',')[1]
            else:
                frame_data = request.frame_data
            
            # Check decoded data size
            frame_bytes = base64.b64decode(frame_data)
            if len(frame_bytes) > 5 * 1024 * 1024:  # 5MB limit for decoded image
                raise HTTPException(status_code=413, detail="Decoded image too large (max 5MB)")
            
            # Decode to numpy array
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                logger.warning("Failed to decode frame data")
                raise HTTPException(status_code=400, detail="Invalid frame data")
            
            # Validate image dimensions
            height, width = frame.shape[:2]
            if height > 2160 or width > 3840:  # 4K limit
                raise HTTPException(status_code=413, detail="Image resolution too high (max 4K)")
            
            # Check total pixels (prevent extremely large images)
            total_pixels = height * width
            if total_pixels > 8 * 1024 * 1024:  # 8MP limit
                raise HTTPException(status_code=413, detail="Image has too many pixels (max 8MP)")
                
        except Exception as e:
            logger.error(f"Frame decoding error: {str(e)}")
            raise HTTPException(status_code=400, detail="Failed to decode frame data")
        
        # Get vision service and analyze frame
        vision_service = get_vision_service()
        analysis = vision_service.analyze_frame(frame, request.session_id)
        
        # Convert to response model
        response = VisionAnalysisResponse(
            is_looking_at_camera=analysis.is_looking_at_camera,
            confidence_score=analysis.confidence_score,
            face_detected=analysis.face_detected,
            eye_contact_score=analysis.eye_contact_score,
            posture_score=analysis.posture_score,
            engagement_level=analysis.engagement_level,
            timestamp=analysis.timestamp
        )
        
        logger.info(f"Vision analysis completed for user {current_user.id}: "
                   f"face_detected={analysis.face_detected}, "
                   f"looking_at_camera={analysis.is_looking_at_camera}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Vision analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Vision analysis failed")

@router.get("/status")
async def get_vision_status(
    current_user: User = Depends(get_current_user)
):
    """
    Get vision service status
    
    Returns:
        Status information about vision service
    """
    try:
        vision_service = get_vision_service()
        return {
            "status": "active",
            "service_initialized": vision_service is not None,
            "models_loaded": (
                vision_service.face_cascade is not None and 
                vision_service.eye_cascade is not None
            )
        }
    except Exception as e:
        logger.error(f"Vision status check failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get vision status")
