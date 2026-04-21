import numpy as np
try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False


def extract_audio_features(audio_path: str) -> dict:
    if not LIBROSA_AVAILABLE:
        return {"error": "librosa not installed", "confidence_estimate": "unknown"}
    y, sr = librosa.load(audio_path, sr=16000)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13).mean(axis=1)
    zcr = float(librosa.feature.zero_crossing_rate(y).mean())
    energy = float(np.mean(y**2))
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    duration = float(len(y) / sr)
    words_per_min = None
    if duration > 0:
        words_per_min = round((len(y) / sr / 60) * 130)
    confidence = "high" if energy > 0.01 and zcr < 0.1 else "low"
    return {
        "mfcc": mfcc.tolist(),
        "zero_crossing_rate": round(zcr, 4),
        "energy": round(energy, 6),
        "speaking_tempo": float(tempo),
        "duration_seconds": round(duration, 2),
        "estimated_wpm": words_per_min,
        "confidence_estimate": confidence
    }
