from __future__ import annotations

import logging
import cv2
import numpy as np
from typing import Dict, Any, Optional, Tuple
import json
import asyncio
from dataclasses import dataclass

logger = logging.getLogger("ai_virtual_coach.vision_service")

@dataclass
class VisionAnalysis:
    is_looking_at_camera: bool
    confidence_score: float
    face_detected: bool
    eye_contact_score: float
    posture_score: float
    engagement_level: str  # "high", "medium", "low"
    timestamp: float


class VisionService:
    """
    Vision-Aware AI Coach Service using OpenCV and PyTorch
    Detects if user is looking at camera and analyzes engagement
    """
    
    def __init__(self):
        self.face_cascade = None
        self.eye_cascade = None
        self.confidence_model = None
        self._initialize_models()
        
    def _initialize_models(self):
        """Initialize OpenCV cascades and PyTorch models"""
        try:
            # Load OpenCV face detection cascade
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            
            # Load eye detection cascade
            self.eye_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_eye.xml'
            )
            
            logger.info("Vision service initialized with OpenCV cascades")
            
        except Exception as e:
            logger.error("Failed to initialize vision models: %s", str(e))
            self.face_cascade = None
            self.eye_cascade = None
    
    def analyze_frame(self, frame_bytes: bytes) -> VisionAnalysis:
        """
        Analyze a video frame for user engagement and camera focus
        
        Args:
            frame_bytes: Raw frame bytes from camera
            
        Returns:
            VisionAnalysis with engagement metrics
        """
        try:
            # Convert bytes to numpy array
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                return self._create_default_analysis()
            
            # Convert to grayscale for detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 4) if self.face_cascade else []
            
            if len(faces) == 0:
                return VisionAnalysis(
                    is_looking_at_camera=False,
                    confidence_score=0.0,
                    face_detected=False,
                    eye_contact_score=0.0,
                    posture_score=0.0,
                    engagement_level="low",
                    timestamp=asyncio.get_event_loop().time()
                )
            
            # Use the largest face
            face = max(faces, key=lambda f: f[2] * f[3])
            x, y, w, h = face
            
            # Extract face region
            face_region = gray[y:y+h, x:x+w]
            
            # Detect eyes in face region
            eyes = self.eye_cascade.detectMultiScale(face_region) if self.eye_cascade else []
            
            # Calculate metrics
            eye_contact_score = self._calculate_eye_contact_score(eyes, face)
            posture_score = self._calculate_posture_score(face, frame.shape)
            confidence_score = self._calculate_confidence_score(eye_contact_score, posture_score)
            is_looking = self._determine_looking_at_camera(eye_contact_score, posture_score)
            engagement_level = self._determine_engagement_level(confidence_score)
            
            return VisionAnalysis(
                is_looking_at_camera=is_looking,
                confidence_score=confidence_score,
                face_detected=True,
                eye_contact_score=eye_contact_score,
                posture_score=posture_score,
                engagement_level=engagement_level,
                timestamp=asyncio.get_event_loop().time()
            )
            
        except Exception as e:
            logger.error("Failed to analyze frame: %s", str(e))
            return self._create_default_analysis()
    
    def _calculate_eye_contact_score(self, eyes: list, face: tuple) -> float:
        """Calculate eye contact score based on eye detection"""
        if len(eyes) == 0:
            return 0.0
        
        # Basic heuristic: more eyes detected = better eye contact
        eye_score = min(len(eyes) / 2.0, 1.0) * 100
        
        # Consider face size (larger face = more engaged)
        _, _, w, h = face
        face_area = w * h
        size_bonus = min(face_area / 50000, 1.0) * 20  # Max 20 points bonus
        
        return min(eye_score + size_bonus, 100.0)
    
    def _calculate_posture_score(self, face: tuple, frame_shape: tuple) -> float:
        """Calculate posture score based on face position and size"""
        x, y, w, h = face
        frame_h, frame_w = frame_shape[:2]
        
        # Center alignment score (face should be somewhat centered)
        face_center_x = x + w / 2
        frame_center_x = frame_w / 2
        horizontal_alignment = 1.0 - abs(face_center_x - frame_center_x) / (frame_w / 2)
        
        # Vertical position score (face should be in upper half)
        vertical_position = 1.0 - (y / (frame_h / 2))
        
        # Size score (face should occupy reasonable portion of frame)
        face_area = w * h
        frame_area = frame_w * frame_h
        size_ratio = face_area / frame_area
        size_score = min(size_ratio * 10, 1.0)  # Expect face to be ~10% of frame
        
        # Combine scores
        total_score = (horizontal_alignment * 0.4 + vertical_position * 0.3 + size_score * 0.3) * 100
        return max(0.0, min(100.0, total_score))
    
    def _calculate_confidence_score(self, eye_contact: float, posture: float) -> float:
        """Calculate overall confidence score"""
        return (eye_contact * 0.6 + posture * 0.4)
    
    def _determine_looking_at_camera(self, eye_contact: float, posture: float) -> bool:
        """Determine if user is looking at camera"""
        return eye_contact > 30 and posture > 40
    
    def _determine_engagement_level(self, confidence_score: float) -> str:
        """Determine engagement level based on confidence score"""
        if confidence_score >= 70:
            return "high"
        elif confidence_score >= 40:
            return "medium"
        else:
            return "low"
    
    def _create_default_analysis(self) -> VisionAnalysis:
        """Create default analysis when no face detected"""
        return VisionAnalysis(
            is_looking_at_camera=False,
            confidence_score=0.0,
            face_detected=False,
            eye_contact_score=0.0,
            posture_score=0.0,
            engagement_level="low",
            timestamp=asyncio.get_event_loop().time()
        )


# Global vision service instance
_vision_service = None

def get_vision_service() -> VisionService:
    """Get or create global vision service instance"""
    global _vision_service
    if _vision_service is None:
        _vision_service = VisionService()
    return _vision_service


async def analyze_vision_frame(frame_data: bytes) -> Dict[str, Any]:
    """
    Analyze vision frame and return results
    
    Args:
        frame_data: Raw frame bytes from camera
        
    Returns:
        Dictionary with vision analysis results
    """
    vision_service = get_vision_service()
    analysis = vision_service.analyze_frame(frame_data)
    
    return {
        "is_looking_at_camera": analysis.is_looking_at_camera,
        "confidence_score": round(analysis.confidence_score, 2),
        "face_detected": analysis.face_detected,
        "eye_contact_score": round(analysis.eye_contact_score, 2),
        "posture_score": round(analysis.posture_score, 2),
        "engagement_level": analysis.engagement_level,
        "timestamp": analysis.timestamp
    }


async def get_vision_summary(session_analyses: list) -> Dict[str, Any]:
    """
    Generate summary of vision analysis for a session
    
    Args:
        session_analyses: List of vision analyses from session
        
    Returns:
        Summary statistics
    """
    if not session_analyses:
        return {
            "total_frames": 0,
            "average_confidence": 0.0,
            "engagement_distribution": {"high": 0, "medium": 0, "low": 0},
            "camera_focus_percentage": 0.0,
            "session_duration": 0.0
        }
    
    # Calculate statistics
    total_frames = len(session_analyses)
    avg_confidence = sum(a["confidence_score"] for a in session_analyses) / total_frames
    camera_focus_count = sum(1 for a in session_analyses if a["is_looking_at_camera"])
    camera_focus_percentage = (camera_focus_count / total_frames) * 100
    
    # Engagement distribution
    engagement_dist = {"high": 0, "medium": 0, "low": 0}
    for analysis in session_analyses:
        engagement_dist[analysis["engagement_level"]] += 1
    
    # Session duration
    if len(session_analyses) >= 2:
        duration = session_analyses[-1]["timestamp"] - session_analyses[0]["timestamp"]
    else:
        duration = 0.0
    
    return {
        "total_frames": total_frames,
        "average_confidence": round(avg_confidence, 2),
        "engagement_distribution": engagement_dist,
        "camera_focus_percentage": round(camera_focus_percentage, 2),
        "session_duration": round(duration, 2)
    }
