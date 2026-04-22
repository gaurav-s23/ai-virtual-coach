from __future__ import annotations

import logging
from typing import Dict, List, Any, Tuple, Optional
import json

try:
    from .llm_service import _llm_json_call
    from .answer_verifier import verify_answer_relevance
    from .scoring_service import score_answer_quality
except ImportError:
    from services.llm_service import _llm_json_call  # type: ignore
    from services.answer_verifier import verify_answer_relevance  # type: ignore
    from services.scoring_service import score_answer_quality  # type: ignore

logger = logging.getLogger("ai_virtual_coach.discussion_service")


class DiscussionState:
    def __init__(self, question: str, original_answer: str, context: str):
        self.question = question
        self.original_answer = original_answer
        self.context = context
        self.discussion_rounds = 0
        self.max_discussion_rounds = 3
        self.topic_mastered = False
        self.missing_points = []
        self.followup_questions = []


async def analyze_answer_quality(question: str, answer: str, context: str) -> Dict[str, Any]:
    """
    Analyze answer quality and identify if discussion is needed.
    Returns analysis with discussion recommendations.
    """
    
    prompt = f'''
    Question: {question}
    Answer: {answer}
    Context: {context[:500]}
    
    Analyze this interview answer and determine:
    1. Is the answer complete and correct?
    2. What key points are missing (if any)?
    3. Should we continue discussing this topic or move to the next question?
    
    Consider technical accuracy, completeness, and depth.
    
    Output schema: {{
        "is_correct": true/false,
        "completeness_score": 0-100,
        "missing_points": ["point1", "point2", ...],
        "should_discuss": true/false,
        "discussion_reason": "Why discussion is needed",
        "expert_tip": "A valuable tip if answer is correct",
        "appreciation": "Positive reinforcement for good answers"
    }}
    '''
    
    try:
        result = await _llm_json_call(
            cache_key=f"analyze_answer:{_hash(question)}:{_hash(answer)}",
            prompt=prompt,
            schema=Dict[str, Any],
            fallback={
                "is_correct": False,
                "completeness_score": 50,
                "missing_points": ["Need more details"],
                "should_discuss": True,
                "discussion_reason": "Answer needs more depth",
                "expert_tip": "Consider the broader implications",
                "appreciation": "Good attempt"
            }
        )
        return result
        
    except Exception as e:
        logger.error("Failed to analyze answer quality: %s", str(e))
        return {
            "is_correct": False,
            "completeness_score": 50,
            "missing_points": ["Need more details"],
            "should_discuss": True,
            "discussion_reason": "Answer needs more depth",
            "expert_tip": "Consider the broader implications",
            "appreciation": "Good attempt"
        }


async def generate_discussion_question(
    original_question: str, 
    original_answer: str, 
    missing_points: List[str],
    context: str
) -> str:
    """
    Generate a follow-up discussion question based on missing points.
    """
    
    missing_points_text = ", ".join(missing_points[:3])
    
    prompt = f'''
    Original Question: {original_question}
    Student's Answer: {original_answer}
    Missing Points: {missing_points_text}
    Context: {context[:300]}
    
    Generate a follow-up discussion question that helps the student address the missing points.
    This should be a natural continuation of the conversation, not a new topic.
    
    Style: Encouraging, guiding, conversational
    Goal: Help student think deeper about the specific missing areas
    
    Output a single discussion question (no JSON, just the question text).
    
    Examples:
    - "That's a good start! Now, could you elaborate more about..."
    - "I see what you're saying. Let's dig deeper into..."
    - "Interesting point! How would you handle the case where..."
    - "Good thinking! What about the scenario where..."
    '''
    
    try:
        response = await _llm_json_call(
            cache_key=f"discussion_q:{_hash(original_question)}:{_hash(missing_points_text)}",
            prompt=prompt,
            schema=str,
            fallback=f"That's a good start! Could you tell me more about {missing_points_text}?"
        )
        return response
        
    except Exception as e:
        logger.error("Failed to generate discussion question: %s", str(e))
        return f"That's a good start! Could you tell me more about {missing_points_text}?"


async def generate_appreciation_feedback(
    question: str, 
    answer: str, 
    expert_tip: str, 
    context: str
) -> str:
    """
    Generate appreciation and expert tip for correct answers.
    """
    
    prompt = f'''
    Question: {question}
    Student's Answer: {answer}
    Expert Tip: {expert_tip}
    Context: {context[:300]}
    
    Generate appreciative feedback that:
    1. Acknowledges the correct answer
    2. Provides the expert tip as additional value
    3. Encourages the student and builds confidence
    4. Smoothly transitions to the next question
    
    Style: Positive, encouraging, professional yet friendly
    Length: 2-3 sentences
    
    Output the feedback text (no JSON).
    '''
    
    try:
        response = await _llm_json_call(
            cache_key=f"appreciation:{_hash(question)}:{_hash(answer)}",
            prompt=prompt,
            schema=str,
            fallback=f"Excellent answer! {expert_tip} You're ready for the next question."
        )
        return response
        
    except Exception as e:
        logger.error("Failed to generate appreciation feedback: %s", str(e))
        return f"Excellent answer! {expert_tip} You're ready for the next question."


async def process_discussion_first_interview(
    question: str, 
    answer: str, 
    context: str, 
    discussion_state: Optional[Dict[str, Any]] = None
) -> Tuple[str, Dict[str, Any]]:
    """
    Process an answer using Discussion-First logic.
    
    Returns:
        Tuple of (feedback_response, updated_discussion_state)
    """
    
    # Analyze answer quality
    analysis = await analyze_answer_quality(question, answer, context)
    
    # Initialize or update discussion state
    if discussion_state is None:
        discussion_state = {
            "question": question,
            "original_answer": answer,
            "context": context,
            "discussion_rounds": 0,
            "max_discussion_rounds": 3,
            "topic_mastered": False,
            "missing_points": analysis["missing_points"]
        }
    
    # If answer is correct and complete
    if analysis["is_correct"] and analysis["completeness_score"] >= 80:
        appreciation_feedback = await generate_appreciation_feedback(
            question, answer, analysis["expert_tip"], context
        )
        
        # Mark topic as mastered
        discussion_state["topic_mastered"] = True
        
        return appreciation_feedback, discussion_state
    
    # If answer needs discussion and we haven't exceeded discussion rounds
    elif analysis["should_discuss"] and discussion_state["discussion_rounds"] < discussion_state["max_discussion_rounds"]:
        
        # Generate follow-up discussion question
        discussion_question = await generate_discussion_question(
            question, answer, analysis["missing_points"], context
        )
        
        # Update discussion state
        discussion_state["discussion_rounds"] += 1
        discussion_state["missing_points"] = analysis["missing_points"]
        
        # Add context about why we're discussing
        feedback = f"{analysis['appreciation']} {analysis['discussion_reason']}\n\n{discussion_question}"
        
        return feedback, discussion_state
    
    # If we've exhausted discussion rounds or answer is good enough
    else:
        if discussion_state["discussion_rounds"] >= discussion_state["max_discussion_rounds"]:
            feedback = f"Good discussion on this topic! You've made good progress. {analysis['expert_tip']}\n\nLet's move to the next question."
        else:
            feedback = f"Nice work! You've covered the key points. {analysis['expert_tip']}\n\nReady for the next question?"
        
        discussion_state["topic_mastered"] = True
        return feedback, discussion_state


def _hash(value: str) -> str:
    """Simple hash function for cache keys"""
    import hashlib
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()[:32]
