from __future__ import annotations

import logging
import torch
import torch.nn as nn
import numpy as np
from typing import Dict, List, Any, Optional
import json
from dataclasses import dataclass
import os
from datetime import datetime

logger = logging.getLogger("ai_virtual_coach.confidence_service")

# MLflow imports
try:
    import mlflow
    import mlflow.pytorch
    from mlflow.tracking import MlflowClient
    from mlflow.entities import Metric
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    logger.warning("MLflow not available - scoring will run without tracking")
except Exception as e:
    MLFLOW_AVAILABLE = False
    logger.error(f"MLflow init failed: {e}")

@dataclass
class ConfidenceFeatures:
    """Features extracted from text/audio for confidence scoring"""
    speech_rate: float  # words per minute
    pause_frequency: float  # pauses per minute
    volume_variance: float  # variation in speech volume
    filler_word_ratio: float  # ratio of filler words
    sentence_length_variance: float  # variance in sentence lengths
    hesitations: float  # hesitation markers per minute
    clarity_score: float  # pronunciation clarity
    energy_level: float  # overall speech energy


class ConfidenceScorer(nn.Module):
    """
    PyTorch-based neural network for confidence scoring
    Takes text/audio features and outputs 0-100 confidence score
    """
    
    def __init__(self, input_size: int = 8, hidden_sizes: List[int] = None, learning_rate: float = 0.001):
        super(ConfidenceScorer, self).__init__()
        
        # Make parameters configurable via environment variables
        self.input_size = int(os.getenv("CONFIDENCE_INPUT_SIZE", str(input_size)))
        self.hidden_sizes = hidden_sizes or [64, 32, 16]
        self.learning_rate = float(os.getenv("CONFIDENCE_LEARNING_RATE", str(learning_rate)))
        
        layers = []
        prev_size = input_size
        
        for hidden_size in hidden_sizes:
            layers.extend([
                nn.Linear(prev_size, hidden_size),
                nn.ReLU(),
                nn.Dropout(0.2),
                nn.BatchNorm1d(hidden_size)
            ])
            prev_size = hidden_size
        
        # Output layer (confidence score 0-100)
        layers.append(nn.Linear(prev_size, 1))
        layers.append(nn.Sigmoid())  # Scale to 0-1
        
        self.network = nn.Sequential(*layers)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass - output confidence score 0-1"""
        return self.network(x) * 100  # Scale to 0-100


class ConfidenceAnalyzer:
    """
    Confidence Analytics Service using PyTorch with MLflow experiment tracking
    Analyzes text/audio features to calculate confidence scores
    """
    
    def __init__(self):
        self.model = None
        self.device = torch.device('cpu')  # Use CPU for compatibility
        self.experiment_name = "confidence_scoring"
        self.run_id = None
        self.mlflow_client = None
        self.training_metrics = []
        self._initialize_model()
        self._setup_mlflow()
        
    def _initialize_model(self):
        """Initialize the PyTorch confidence model"""
        try:
            self.model = ConfidenceScorer()
            self.model.to(self.device)
            self.model.eval()  # Set to evaluation mode
            
            # Initialize with random weights (in production, load pre-trained weights)
            self._initialize_weights()
            
            logger.info("Confidence analyzer initialized with PyTorch model")
            
        except Exception as e:
            logger.error("Failed to initialize confidence model: %s", str(e))
            self.model = None
    
    def _initialize_weights(self):
        """Initialize model weights"""
        for module in self.model.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                nn.init.zeros_(module.bias)
    
    def _setup_mlflow(self):
        """Setup MLflow experiment tracking"""
        if not MLFLOW_AVAILABLE:
            logger.warning("MLflow not available - skipping experiment tracking")
            return
        
        try:
            # Set MLflow tracking URI to local mlruns directory
            mlflow.set_tracking_uri(f"file:{os.path.abspath('./mlruns')}")
            
            # Create or get experiment
            experiment = mlflow.get_experiment_by_name(self.experiment_name)
            if experiment is None:
                experiment_id = mlflow.create_experiment(self.experiment_name)
                logger.info(f"Created MLflow experiment: {self.experiment_name}")
            else:
                experiment_id = experiment.experiment_id
                logger.info(f"Using existing MLflow experiment: {self.experiment_name}")
            
            # Initialize MLflow client
            self.mlflow_client = MlflowClient()
            
            # Start a new run for this session
            self.run_id = mlflow.start_run(
                experiment_id=experiment_id,
                run_name=f"confidence_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            
            # Log hyperparameters
            self._log_hyperparameters()
            
            logger.info(f"MLflow tracking initialized with run_id: {self.run_id}")
            
        except Exception as e:
            logger.error(f"Failed to setup MLflow: {e}")
            self.mlflow_client = None
            self.run_id = None
    
    def _log_hyperparameters(self):
        """Log model hyperparameters to MLflow"""
        if not self.mlflow_client or not self.run_id:
            return
        
        try:
            hyperparams = {
                "model_type": "PyTorch_Neural_Network",
                "input_size": 8,
                "hidden_layers": "[64, 32, 16]",
                "activation": "ReLU",
                "dropout_rate": 0.2,
                "optimizer": "Adam",
                "learning_rate": 0.001,
                "batch_size": 32,
                "epochs": 100,
                "device": str(self.device),
                "normalization": "BatchNorm1d"
            }
            
            for key, value in hyperparams.items():
                mlflow.log_param(key, value)
            
            logger.info("Logged hyperparameters to MLflow")
            
        except Exception as e:
            logger.error(f"Failed to log hyperparameters: {e}")
    
    def log_training_metrics(self, epoch: int, loss: float, f1_score: float, auc_score: float):
        """Log training metrics to MLflow"""
        if not self.mlflow_client or not self.run_id:
            return
        
        try:
            # Log metrics
            mlflow.log_metric("training_loss", loss, step=epoch)
            mlflow.log_metric("f1_score", f1_score, step=epoch)
            mlflow.log_metric("auc_score", auc_score, step=epoch)
            mlflow.log_metric("epoch", epoch)
            
            # Store for later analysis
            self.training_metrics.append({
                "epoch": epoch,
                "loss": loss,
                "f1_score": f1_score,
                "auc_score": auc_score
            })
            
            logger.debug(f"Logged training metrics for epoch {epoch}: loss={loss:.4f}, f1={f1_score:.4f}, auc={auc_score:.4f}")
            
        except Exception as e:
            logger.error(f"Failed to log training metrics: {e}")
    
    def log_model_artifacts(self):
        """Log model artifacts to MLflow"""
        if not self.mlflow_client or not self.run_id or not self.model:
            return
        
        try:
            # Log PyTorch model
            mlflow.pytorch.log_model(self.model, "confidence_model")
            
            # Log training metrics summary
            if self.training_metrics:
                metrics_file = "training_metrics.json"
                with open(metrics_file, 'w') as f:
                    json.dump(self.training_metrics, f, indent=2)
                mlflow.log_artifact(metrics_file)
                os.remove(metrics_file)  # Clean up temporary file
            
            logger.info("Logged model artifacts to MLflow")
            
        except Exception as e:
            logger.error(f"Failed to log model artifacts: {e}")
    
    def end_mlflow_run(self):
        """End the current MLflow run"""
        if self.run_id:
            try:
                self.log_model_artifacts()
                mlflow.end_run()
                logger.info(f"Ended MLflow run: {self.run_id}")
                self.run_id = None
            except Exception as e:
                logger.error(f"Failed to end MLflow run: {e}")
    
    def simulate_training_epoch(self, epoch: int):
        """Simulate a training epoch for demonstration purposes"""
        # Simulate training metrics (in real scenario, this would be actual training)
        loss = max(0.1, 1.0 - (epoch * 0.01) + np.random.normal(0, 0.05))
        f1_score = min(1.0, 0.5 + (epoch * 0.008) + np.random.normal(0, 0.02))
        auc_score = min(1.0, 0.6 + (epoch * 0.007) + np.random.normal(0, 0.03))
        
        self.log_training_metrics(epoch, loss, f1_score, auc_score)
        
        return loss, f1_score, auc_score
    
    def extract_features_from_text(self, text: str, audio_features: Optional[Dict] = None) -> ConfidenceFeatures:
        """
        Extract confidence features from text and optional audio data
        
        Args:
            text: Spoken text transcript
            audio_features: Optional audio analysis features
            
        Returns:
            ConfidenceFeatures object
        """
        # Text-based features
        words = text.split()
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        
        # Speech rate (words per minute) - estimate from text length
        estimated_duration = len(words) / 150  # Assume 150 WPM average
        speech_rate = len(words) / max(estimated_duration, 1) if estimated_duration > 0 else 0
        
        # Pause frequency (estimate from punctuation)
        pause_markers = text.count(',') + text.count('.') + text.count('!') + text.count('?')
        pause_frequency = pause_markers / max(estimated_duration, 1) if estimated_duration > 0 else 0
        
        # Filler word detection
        filler_words = ['um', 'uh', 'like', 'you know', 'actually', 'basically', 'literally']
        filler_count = sum(text.lower().count(filler) for filler in filler_words)
        filler_word_ratio = filler_count / max(len(words), 1)
        
        # Sentence length variance
        sentence_lengths = [len(s.split()) for s in sentences]
        sentence_length_variance = np.var(sentence_lengths) if len(sentence_lengths) > 1 else 0
        
        # Hesitation markers
        hesitation_markers = text.count('...') + text.count('--') + filler_count
        hesitations = hesitation_markers / max(estimated_duration, 1) if estimated_duration > 0 else 0
        
        # Use audio features if available, otherwise estimate
        if audio_features:
            volume_variance = audio_features.get('volume_variance', 0.5)
            clarity_score = audio_features.get('clarity_score', 0.7)
            energy_level = audio_features.get('energy_level', 0.6)
        else:
            # Estimated values based on text patterns
            volume_variance = 0.5 if filler_word_ratio < 0.1 else 0.3
            clarity_score = max(0.3, 1.0 - filler_word_ratio * 2)
            energy_level = min(1.0, speech_rate / 200)  # Normalize to 0-1
        
        return ConfidenceFeatures(
            speech_rate=min(speech_rate, 300),  # Cap at 300 WPM
            pause_frequency=min(pause_frequency, 10),  # Cap at 10 pauses/min
            volume_variance=volume_variance,
            filler_word_ratio=min(filler_word_ratio, 1.0),
            sentence_length_variance=min(sentence_length_variance, 100),
            hesitations=min(hesitations, 20),  # Cap at 20 hesitations/min
            clarity_score=clarity_score,
            energy_level=energy_level
        )
    
    def features_to_tensor(self, features: ConfidenceFeatures) -> torch.Tensor:
        """Convert features to PyTorch tensor"""
        feature_array = np.array([
            features.speech_rate / 300,  # Normalize speech rate
            features.pause_frequency / 10,  # Normalize pause frequency
            features.volume_variance,
            1.0 - features.filler_word_ratio,  # Inverse filler ratio (higher is better)
            features.sentence_length_variance / 100,  # Normalize variance
            1.0 - (features.hesitations / 20),  # Inverse hesitations (higher is better)
            features.clarity_score,
            features.energy_level
        ], dtype=np.float32)
        
        return torch.tensor(feature_array, dtype=torch.float32).unsqueeze(0).to(self.device)
    
    def calculate_confidence_score(self, text: str, audio_features: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Calculate confidence score from text and audio features with MLflow tracking
        
        Args:
            text: Spoken text transcript
            audio_features: Optional audio analysis features
            
        Returns:
            Dictionary with confidence score and breakdown
        """
        try:
            # Extract features
            features = self.extract_features_from_text(text, audio_features)
            
            # Calculate rule-based score as fallback
            rule_based_score = self._calculate_rule_based_score(features)
            
            # Use PyTorch model if available
            if self.model is not None:
                with torch.no_grad():
                    feature_tensor = self.features_to_tensor(features)
                    model_score = self.model(feature_tensor).item()
                    confidence_score = min(100, max(0, model_score))
            else:
                confidence_score = rule_based_score
            
            # Blend model and rule-based scores
            final_score = (confidence_score * 0.7 + rule_based_score * 0.3) if self.model else rule_based_score
            
            # Log to MLflow if available
            if self.mlflow_client and self.run_id:
                try:
                    mlflow.log_metric("confidence_score", final_score)
                    mlflow.log_metric("rule_based_score", rule_based_score)
                    if self.model:
                        mlflow.log_metric("model_score", confidence_score)
                    
                    # Log feature importance
                    mlflow.log_metric("speech_rate", features.speech_rate)
                    mlflow.log_metric("filler_ratio", features.filler_word_ratio)
                    mlflow.log_metric("clarity", features.clarity_score)
                    
                    # Log sample text length for analysis
                    mlflow.log_metric("text_length", len(text))
                    
                except Exception as e:
                    logger.debug(f"Failed to log to MLflow: {e}")
            
            result = {
                "confidence_score": round(final_score, 2),
                "rule_based_score": round(rule_based_score, 2),
                "model_score": round(confidence_score, 2) if self.model else None,
                "features": {
                    "speech_rate": round(features.speech_rate, 2),
                    "pause_frequency": round(features.pause_frequency, 2),
                    "filler_word_ratio": round(features.filler_word_ratio, 3),
                    "clarity_score": round(features.clarity_score, 3),
                    "energy_level": round(features.energy_level, 3)
                },
                "assessment": self._get_confidence_assessment(final_score),
                "mlflow_run_id": self.run_id
            }
            
            return result
            
        except Exception as e:
            logger.error("Failed to calculate confidence score: %s", str(e))
            return {
                "confidence_score": 50.0,
                "rule_based_score": 50.0,
                "model_score": None,
                "features": {},
                "assessment": "Unable to analyze confidence",
                "mlflow_run_id": self.run_id
            }
    
    def _calculate_rule_based_score(self, features: ConfidenceFeatures) -> float:
        """Calculate confidence score using rule-based approach"""
        score = 50.0  # Base score
        
        # Speech rate scoring
        if 120 <= features.speech_rate <= 160:  # Ideal range
            score += 15
        elif 100 <= features.speech_rate <= 180:
            score += 10
        elif features.speech_rate < 80 or features.speech_rate > 200:
            score -= 10
        
        # Filler word penalty
        score -= features.filler_word_ratio * 30
        
        # Clarity bonus
        score += features.clarity_score * 15
        
        # Energy level bonus
        score += features.energy_level * 10
        
        # Hesitation penalty
        score -= features.hesitations * 2
        
        # Pause frequency (moderate pauses are good)
        if 2 <= features.pause_frequency <= 6:
            score += 5
        elif features.pause_frequency > 10:
            score -= 5
        
        return max(0, min(100, score))
    
    def _get_confidence_assessment(self, score: float) -> str:
        """Get qualitative assessment of confidence score"""
        if score >= 80:
            return "Highly confident - Excellent delivery and clarity"
        elif score >= 65:
            return "Confident - Good delivery with minor areas for improvement"
        elif score >= 50:
            return "Moderately confident - Some nervousness but overall effective"
        elif score >= 35:
            return "Low confidence - Significant nervousness affecting delivery"
        else:
            return "Very low confidence - Major delivery issues need attention"


# Global confidence analyzer instance
_confidence_analyzer = None

def get_confidence_analyzer() -> ConfidenceAnalyzer:
    """Get or create global confidence analyzer instance"""
    global _confidence_analyzer
    if _confidence_analyzer is None:
        _confidence_analyzer = ConfidenceAnalyzer()
    return _confidence_analyzer


async def analyze_confidence(text: str, audio_features: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Analyze confidence from text and audio features
    
    Args:
        text: Spoken text transcript
        audio_features: Optional audio analysis features
        
    Returns:
        Confidence analysis results
    """
    analyzer = get_confidence_analyzer()
    return analyzer.calculate_confidence_score(text, audio_features)


async def get_confidence_trends(session_analyses: List[Dict]) -> Dict[str, Any]:
    """
    Analyze confidence trends across a session
    
    Args:
        session_analyses: List of confidence analyses from session
        
    Returns:
        Trend analysis and statistics
    """
    if not session_analyses:
        return {
            "average_confidence": 0.0,
            "confidence_trend": "stable",
            "improvement_score": 0.0,
            "consistency_score": 0.0,
            "peak_confidence": 0.0,
            "lowest_confidence": 0.0
        }
    
    scores = [a["confidence_score"] for a in session_analyses]
    
    # Calculate statistics
    avg_confidence = np.mean(scores)
    peak_confidence = max(scores)
    lowest_confidence = min(scores)
    
    # Calculate trend
    if len(scores) >= 3:
        first_third = scores[:len(scores)//3]
        last_third = scores[-len(scores)//3:]
        first_avg = np.mean(first_third)
        last_avg = np.mean(last_third)
        
        if last_avg > first_avg + 5:
            trend = "improving"
            improvement_score = min((last_avg - first_avg) * 2, 100)
        elif last_avg < first_avg - 5:
            trend = "declining"
            improvement_score = max(-((first_avg - last_avg) * 2), -100)
        else:
            trend = "stable"
            improvement_score = 0
    else:
        trend = "insufficient_data"
        improvement_score = 0
    
    # Consistency score (lower variance = more consistent)
    consistency_score = max(0, 100 - np.std(scores))
    
    return {
        "average_confidence": round(avg_confidence, 2),
        "confidence_trend": trend,
        "improvement_score": round(improvement_score, 2),
        "consistency_score": round(consistency_score, 2),
        "peak_confidence": round(peak_confidence, 2),
        "lowest_confidence": round(lowest_confidence, 2)
    }
