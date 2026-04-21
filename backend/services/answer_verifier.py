from sentence_transformers import SentenceTransformer, util

_model = SentenceTransformer('all-MiniLM-L6-v2')


def verify_answer_relevance(question: str, answer: str) -> dict:
    if not question or not answer:
        return {"is_relevant": False, "score": 0.0, "verdict": "off-topic"}
    q_emb = _model.encode(question, convert_to_tensor=True)
    a_emb = _model.encode(answer, convert_to_tensor=True)
    score = float(util.cos_sim(q_emb, a_emb)[0][0])
    if score >= 0.55:
        verdict = "on-topic"
    elif score >= 0.35:
        verdict = "partial"
    else:
        verdict = "off-topic"
    return {
        "is_relevant": score >= 0.35,
        "score": round(score, 3),
        "verdict": verdict,
        "feedback_hint": "Your answer seems off-topic. Try to address the question directly." if verdict == "off-topic" else ""
    }
