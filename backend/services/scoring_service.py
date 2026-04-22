from transformers import pipeline as hf_pipeline
import threading

_scorer = None
_lock = threading.Lock()


def _get_scorer():
    global _scorer
    if _scorer is None:
        with _lock:
            if _scorer is None:
                _scorer = hf_pipeline(
                    "text-classification",
                    model="cross-encoder/ms-marco-MiniLM-L-6-v2"
                )
    return _scorer


def warmup_scorer() -> None:
    try:
        _get_scorer()
    except Exception:
        return


def score_answer_quality(question: str, answer: str) -> float:
    if not question or not answer:
        return 0.0
    try:
        scorer = _get_scorer()
        result = scorer(f"{question} [SEP] {answer}")[0]
        return round(float(result["score"]), 3)
    except Exception:
        return 0.0
