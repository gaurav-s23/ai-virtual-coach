# AI Virtual Coach - Technical Documentation

## Platform Architecture Overview

The AI Virtual Coach platform is a **Text-to-Text (Chat) and Vision-based** interview preparation system that focuses on:
- **Adaptive Chat Logic** - Discussion-based interview analysis
- **Vision Analysis** - Real-time eye-contact and engagement detection using OpenCV/PyTorch
- **Confidence Scoring** - Text-based delivery confidence analysis using PyTorch neural networks
- **DSA Module** - Algorithmic coding challenge generation and evaluation
- **No Audio Processing** - Platform scope excludes audio/speech processing

---

## Technical Essence

### Core Architecture
- **Frontend**: React 19 + Vite + React Router + Tailwind CSS
- **Backend API**: FastAPI + Pydantic + Uvicorn
- **Database**: PostgreSQL with SQLAlchemy ORM
- **AI/ML Stack**: 
  - PyTorch for vision and confidence analysis
  - OpenCV for computer vision
  - Sentence Transformers for text embeddings
  - ChromaDB for vector storage
  - LiteLLM for LLM integration

### Key Technical Features

#### 1. Vision Analysis System
- **Technology**: OpenCV + PyTorch
- **Functionality**: Real-time face detection, eye-contact tracking, engagement level analysis
- **Implementation**: `backend/services/vision_service.py` + `backend/routes/vision.py`
- **Frontend Integration**: Camera capture every 4 seconds with base64 encoding

#### 2. Confidence Scoring Engine
- **Technology**: PyTorch Neural Network (8-layer MLP)
- **Functionality**: Text-based confidence analysis from user responses
- **Features**: Speech rate simulation, pause frequency, volume variance analysis
- **Implementation**: `backend/services/confidence_service.py`

#### 3. Discussion-Based Interview Logic
- **Technology**: LangChain + LLM integration
- **Functionality**: Topic mastery detection, follow-up question generation
- **Implementation**: `backend/services/discussion_service.py`

#### 4. DSA Coding Module
- **Technology**: LLM-based problem generation
- **Functionality**: Algorithmic challenges with difficulty levels
- **Implementation**: `backend/services/coding_service.py`

---

## Bug Fix History

### Major Bug Fixes Applied

#### 1. Authentication Security Issues
- **Fixed**: Hardcoded user ID fallbacks in Dashboard.jsx
- **Impact**: Eliminated security vulnerability where users could access other users' data
- **Solution**: Proper session validation and redirect to auth page on corruption

#### 2. Vision Pipeline Integration
- **Fixed**: Missing real-time vision analysis
- **Impact**: Added camera capture and OpenCV processing
- **Solution**: Implemented `/api/vision/analyze` endpoint with JWT authentication

#### 3. Confidence Scoring Integration
- **Fixed**: Simulated confidence data
- **Impact**: Real PyTorch neural network scoring
- **Solution**: Integrated `confidence_service.py` into chat flow

#### 4. Import Cleanup and Dead Code
- **Fixed**: Unused imports and dependencies
- **Impact**: Cleaner, more maintainable codebase
- **Solution**: Systematic cleanup of unused libraries and imports

#### 5. Security Hardening
- **Fixed**: Unprotected endpoints
- **Impact**: All API endpoints now properly authenticated
- **Solution**: Added `get_current_user` dependency to all routes

---

## Platform Scope Clarification

### INCLUDED IN SCOPE:
- Text-based chat interviews
- Vision-based analysis (eye-contact, engagement)
- Confidence scoring from text delivery
- DSA coding challenges
- Resume-based RAG system
- Real-time feedback via WebSocket

### EXCLUDED FROM SCOPE:
- Audio processing (librosa, soundfile, torchaudio removed)
- Speech-to-text analysis
- Voice confidence scoring
- Audio file processing

---

## Technical Implementation Details

### Vision Analysis Pipeline
1. **Camera Capture**: Frontend captures frames every 4 seconds
2. **Base64 Encoding**: Frames encoded for API transmission
3. **OpenCV Processing**: Face and eye detection using Haar cascades
4. **PyTorch Analysis**: Neural network processes visual features
5. **Real-time Feedback**: Engagement metrics sent to frontend

### Confidence Scoring Pipeline
1. **Text Input**: User answers processed through NLP pipeline
2. **Feature Extraction**: 8-dimensional feature vector created
3. **Neural Network**: PyTorch MLP generates confidence score
4. **Real-time Updates**: Scores integrated into interview flow

### Discussion-Based Logic
1. **Answer Analysis**: LLM evaluates answer completeness
2. **Topic Detection**: Identifies areas needing deeper exploration
3. **Follow-up Generation**: Creates targeted follow-up questions
4. **Mastery Tracking**: Monitors topic understanding progression

---

## Performance Optimizations

### Caching Strategy
- **LLM Responses**: Redis-based caching for repeated queries
- **RAG Results**: ChromaDB persistence for resume embeddings
- **Vision Analysis**: Optimized frame processing intervals

### Rate Limiting
- **API Protection**: User-based rate limiting
- **WebSocket Security**: Token validation for real-time connections
- **Login Protection**: Brute-force prevention mechanisms

---

## Deployment Considerations

### Docker Optimization
- **Multi-stage builds**: Optimized image sizes
- **Dependency management**: Clean package.json and requirements.txt
- **Environment variables**: Proper configuration management

### Security Measures
- **JWT Tokens**: Secure authentication with refresh rotation
- **CORS Configuration**: Dynamic origin handling
- **Input Validation**: Pydantic schemas for API validation

---

## Future Technical Roadmap

### Near-term Enhancements
1. **Advanced Vision**: Emotion detection and micro-expression analysis
2. **Enhanced Confidence**: Multi-modal confidence scoring
3. **DSA Expansion**: More coding categories and difficulty levels

### Long-term Vision
1. **AI Coaching**: Personalized interview coaching strategies
2. **Performance Analytics**: Advanced skill gap analysis
3. **Enterprise Features**: Team management and reporting

---

## Conclusion

The AI Virtual Coach platform represents a sophisticated integration of modern AI technologies focused on **text and vision-based interview preparation**. The technical architecture emphasizes real-time analysis, adaptive learning, and comprehensive feedback systems while maintaining a clear scope that excludes audio processing to ensure focused development and deployment.

*This documentation consolidates all technical insights, bug fixes, and architectural decisions from the development process.*
