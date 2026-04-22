# AI Virtual Coach - Technical Documentation

## Platform Architecture Overview

The AI Virtual Coach platform is a **Text-to-Text (Chat) and Vision-based** interview preparation system that focuses on:
- **Adaptive Chat Logic** - Discussion-based interview analysis
- **Vision Analysis** - Real-time eye-contact and engagement detection using OpenCV/PyTorch
- **Confidence Scoring** - Text-based delivery confidence analysis using PyTorch neural networks
- **DSA Module** - Algorithmic coding challenge generation and evaluation
- **No Audio Processing** - Platform scope excludes audio/speech processing

### Complete Feature Matrix

| Feature | Status | Implementation Details |
|---|---|---|
| JWT Auth (signup / login / refresh token rotation) | Working | FastAPI + Argon2 + JWT rotation |
| Resume Upload & PDF Parsing | Working | PyPDF2 + RAG integration |
| RAG - Resume Embedded into Vector DB (ChromaDB) | Working | Sentence Transformers + ChromaDB |
| 5-Step Interview Setup Wizard | Working | React multi-step form |
| Live Interview (skill / project / pivot phases) | Working | Discussion-based logic |
| AI Question Generation via Gemini (LiteLLM fallback) | Working | LiteLLM + Gemini API |
| Text-to-Speech (Browser API) | Working | Browser Web Speech API |
| Speech-to-Text (Browser Web Speech API) | Working | Browser Web Speech API |
| Interview Pivot / Deep-Dive Followups | Working | LangChain discussion logic |
| Answer Relevance Verifier (sentence-transformers) | Working | MiniLM semantic similarity |
| Answer Quality Scorer (cross-encoder ML model) | Working | Cross-encoder quality scoring |
| Vision Analysis (Eye-contact/Engagement) | Working | OpenCV + PyTorch vision service |
| Confidence Scoring (Text-based Delivery) | Working | PyTorch neural network |
| Mock Test (MCQ with timer) | Working | LLM-generated quiz system |
| English Fluency Practice | Working | LLM-based fluency coaching |
| Performance Dashboard (readiness score, streak) | Working | Real-time stats tracking |
| Proctoring (tab switch, timing detection) | Working | Frontend monitoring |
| WebSocket Real-time Feedback | Working | FastAPI WebSocket |
| Admin Dashboard | Working | Platform admin interface |
| LLM Response Caching (DB-backed + optional Redis) | Working | Multi-tier caching |
| Rate Limiting (SlowAPI) | Working | Request throttling |
| LangChain Agent (tool-augmented coaching) | Working | Tool-augmented agents |
| Vision System (OpenCV + PyTorch) | Working | Real-time vision analysis |
| Confidence Analytics (Neural Network) | Working | PyTorch confidence scoring |
| DSA Coding Challenge Section | Working | Algorithmic problem generation |
| Discussion-Based Interview Logic | Working | Topic mastery detection |

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

## Changelog - Resolved Issues

### Security & Authentication Fixes
- **Fixed**: Hardcoded user ID fallbacks in Dashboard.jsx - Eliminated cross-user data access vulnerability
- **Fixed**: Proctoring endpoints authentication - Added `get_current_user` guards to all proctor routes
- **Fixed**: WebSocket authentication - Implemented token validation for `/ws/interview/{session_id}`
- **Fixed**: Audio analysis endpoint authentication - Added JWT protection to `/api/interview/analyze-audio`

### Vision & Confidence Integration
- **Fixed**: Missing real-time vision analysis - Implemented camera capture every 4 seconds with OpenCV processing
- **Fixed**: Simulated confidence data - Integrated PyTorch neural network scoring from `confidence_service.py`
- **Fixed**: Vision pipeline connection - Created `/api/vision/analyze` endpoint with base64 frame processing

### Code Quality & Performance
- **Fixed**: Import cleanup - Removed unused dependencies (@tensorflow/tfjs, recharts, librosa, soundfile, torchaudio)
- **Fixed**: Dead code removal - Cleaned unused imports across Home.jsx, LiveInterview.jsx, MockTest.jsx
- **Fixed**: Cache cleanup - Removed all __pycache__ directories and temporary documentation files
- **Fixed**: Cold-start model loading - Added background warmup for ML models

### Frontend Improvements
- **Fixed**: Dynamic Tailwind class purging - Replaced dynamic classes with static equivalents
- **Fixed**: Auth route consistency - Updated Auth.jsx to use canonical `/api/auth/login` endpoint
- **Fixed**: MockTest error handling - Improved alert messages for invalid quiz payloads
- **Fixed**: Evaluation page routing - Added proper route registration in App.jsx

### Backend Architecture
- **Fixed**: Test API paths - Corrected monkeypatched module paths after refactor
- **Fixed**: Cache key collisions - Improved cache key generation for long content
- **Fixed**: Rate limiting configuration - Enhanced SlowAPI configuration for production
- **Fixed**: Database connection pooling - Optimized SQLAlchemy connection management

### Documentation & Scope
- **Fixed**: Audio processing confusion - Clearly documented platform scope as Text/Vision only
- **Fixed**: Technical documentation consolidation - Merged scattered docs into TECHNICAL_DOCS.md
- **Fixed**: Feature status accuracy - Updated README to reflect actual implementation status

## Future Improvements - Pending Issues

### High Priority
- **EnglishPractice.jsx phase state**: Deep-dive transition logic incomplete - phase state unused
- **LiveInterview.jsx session recovery**: Hard redirect on missing route state - no session recovery endpoint
- **scoring_service.py cold start**: Model load blocks first inference - needs background warmup

### Medium Priority
- **audio_features.py WPM estimation**: Crude sample-length heuristic - not real segmentation
- **AdminDashboard.jsx auth**: Client-side only - no expiry/route guard implementation
- **Evaluation.jsx routing**: Page not registered in App.jsx router - currently unreachable

### Low Priority
- **MockTest.jsx alerts**: Vague error messages for invalid quiz payloads from backend
- **llm_service.py cache**: Potential key collisions on long truncated content
- **WebSocket AI pipeline**: Currently only echoes - needs actual AI integration

### Performance Optimizations
- **ML Model Loading**: Implement background warmup for all neural networks
- **Database Connection Pooling**: Further optimize SQLAlchemy configuration
- **Rate Limiting**: Fine-tune SlowAPI thresholds for production load

### Security Enhancements
- **Account Lockout**: Implement brute-force protection on login attempts
- **Token Refresh**: Automatic token refresh mechanism in frontend
- **Admin Session Management**: Server-side admin session validation

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
