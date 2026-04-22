from __future__ import annotations

import logging
from typing import Dict, List, Any
import json

try:
    from .llm_service import _llm_json_call
except ImportError:
    from services.llm_service import _llm_json_call

logger = logging.getLogger("ai_virtual_coach.coding_service")


class CodingProblem:
    def __init__(self, data: Dict[str, Any]):
        self.title = data.get("title", "")
        self.description = data.get("description", "")
        self.difficulty = data.get("difficulty", "Medium")
        self.constraints = data.get("constraints", [])
        self.example_input = data.get("example_input", "")
        self.example_output = data.get("example_output", "")
        self.explanation = data.get("explanation", "")
        self.hints = data.get("hints", [])
        self.time_complexity = data.get("time_complexity", "")
        self.space_complexity = data.get("space_complexity", "")


async def generate_coding_problems(difficulty: str = "Mixed", count: int = 5) -> List[CodingProblem]:
    """
    Generate coding challenges similar to LeetCode/HackerRank.
    
    Args:
        difficulty: "Easy", "Medium", "Hard", or "Mixed"
        count: Number of problems to generate
    
    Returns:
        List of CodingProblem objects
    """
    
    prompt = f"""
    Generate {count} coding challenges for technical interviews. Each problem should include:
    - Clear problem statement
    - Input/output format
    - Constraints
    - Sample test cases
    - Hints for solving
    - Time and space complexity analysis
    
    Difficulty level: {difficulty}
    
    Format each problem as JSON with this structure:
    {{
        "title": "Problem Title",
        "description": "Detailed problem description",
        "difficulty": "Easy|Medium|Hard",
        "constraints": ["constraint1", "constraint2", ...],
        "example_input": "Sample input",
        "example_output": "Sample output",
        "explanation": "Explanation of the solution approach",
        "hints": ["hint1", "hint2", ...],
        "time_complexity": "O(n) analysis",
        "space_complexity": "O(1) analysis"
    }}
    
    Return a JSON array of problems.
    """
    
    try:
        result = await _llm_json_call(
            cache_key=f"coding_problems:{difficulty}:{count}",
            prompt=prompt,
            schema=list[Dict[str, Any]],
            fallback=[]
        )
        
        if isinstance(result, list):
            return [CodingProblem(problem) for problem in result]
        else:
            logger.error("Expected list of coding problems, got: %s", type(result))
            return []
            
    except Exception as e:
        logger.error("Failed to generate coding problems: %s", str(e))
        return _get_fallback_coding_problems(difficulty, count)


def _get_fallback_coding_problems(difficulty: str, count: int) -> List[CodingProblem]:
    """Fallback coding problems when AI generation fails"""
    
    fallback_problems = [
        {
            "title": "Two Sum",
            "description": "Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.",
            "difficulty": "Easy",
            "constraints": ["2 <= nums.length <= 10^4", "-10^9 <= nums[i] <= 10^9", "-10^9 <= target <= 10^9"],
            "example_input": "nums = [2,7,11,15], target = 9",
            "example_output": "[0,1]",
            "explanation": "Because nums[0] + nums[1] == 9, we return [0, 1].",
            "hints": ["Use a hash map to store complements", "Iterate through the array once"],
            "time_complexity": "O(n)",
            "space_complexity": "O(n)"
        },
        {
            "title": "Valid Parentheses",
            "description": "Given a string s containing just the characters '(', ')', '{', '}', '[' and ']', determine if the input string is valid.",
            "difficulty": "Easy",
            "constraints": ["1 <= s.length <= 10^4", "s consists of parentheses only"],
            "example_input": "s = \"()[]{}\"",
            "example_output": "true",
            "explanation": "All brackets are properly closed and nested.",
            "hints": ["Use a stack to track opening brackets", "Check for matching pairs"],
            "time_complexity": "O(n)",
            "space_complexity": "O(n)"
        },
        {
            "title": "Binary Tree Level Order Traversal",
            "description": "Given the root of a binary tree, return the level order traversal of its nodes' values.",
            "difficulty": "Medium",
            "constraints": ["The number of nodes in the tree is in the range [0, 2000]", "-1000 <= Node.val <= 1000"],
            "example_input": "root = [3,9,20,null,null,15,7]",
            "example_output": "[[3],[9,20],[15,7]]",
            "explanation": "Level order traversal from top to bottom, left to right.",
            "hints": ["Use BFS with a queue", "Track level size for each level"],
            "time_complexity": "O(n)",
            "space_complexity": "O(n)"
        },
        {
            "title": "Longest Substring Without Repeating Characters",
            "description": "Given a string s, find the length of the longest substring without repeating characters.",
            "difficulty": "Medium",
            "constraints": ["0 <= s.length <= 5 * 10^4", "s consists of English letters, digits, symbols and spaces"],
            "example_input": "s = \"abcabcbb\"",
            "example_output": "3",
            "explanation": "The answer is \"abc\", with length 3.",
            "hints": ["Use sliding window technique", "Track character positions with a hash map"],
            "time_complexity": "O(n)",
            "space_complexity": "O(min(m,n)) where m is alphabet size"
        },
        {
            "title": "Merge K Sorted Lists",
            "description": "You are given an array of k linked-lists lists, each linked-list is sorted in ascending order. Merge all the linked-lists into one sorted linked-list.",
            "difficulty": "Hard",
            "constraints": ["k == lists.length", "0 <= k <= 10^4", "0 <= lists[i].length <= 500"],
            "example_input": "lists = [[1,4,5],[1,3,4],[2,6]]",
            "example_output": "[1,1,2,3,4,4,5,6]",
            "explanation": "The linked-lists are merged into one sorted list.",
            "hints": ["Use a min-heap priority queue", "Or use divide and conquer approach"],
            "time_complexity": "O(n log k) where n is total nodes",
            "space_complexity": "O(k)"
        }
    ]
    
    # Filter and return requested number of problems
    if difficulty != "Mixed":
        filtered = [p for p in fallback_problems if p["difficulty"] == difficulty]
        if not filtered:
            filtered = fallback_problems  # Fallback to all if no matches
    else:
        filtered = fallback_problems
    
    return [CodingProblem(p) for p in filtered[:count]]


async def generate_coding_quiz(category: str = "Coding") -> List[Dict[str, Any]]:
    """
    Generate coding quiz questions in the format expected by the mock test system.
    This converts coding problems into multiple-choice questions.
    """
    
    coding_problems = await generate_coding_problems("Mixed", 5)
    quiz_questions = []
    
    for i, problem in enumerate(coding_problems):
        # Convert coding problem to multiple choice format
        question_text = f"""
        **{problem.title} ({problem.difficulty})**
        
        {problem.description}
        
        **Constraints:**
        {chr(10).join(f"- {constraint}" for constraint in problem.constraints[:3])}
        
        **Example:**
        Input: {problem.example_input}
        Output: {problem.example_output}
        
        What is the optimal time complexity for solving this problem?
        """
        
        # Generate options based on the actual complexity
        correct_complexity = problem.time_complexity
        options = [
            correct_complexity,
            "O(n²)",
            "O(n log n)",
            "O(1)"
        ]
        
        # Shuffle options but keep track of correct answer
        import random
        random.shuffle(options)
        correct_answer = options.index(correct_complexity)
        
        quiz_question = {
            "id": f"coding_{i+1}",
            "question": question_text.strip(),
            "options": options,
            "answer": options[correct_answer],
            "explanation": f"The optimal solution has {correct_complexity} time complexity. {problem.explanation}",
            "difficulty": problem.difficulty,
            "type": "coding"
        }
        
        quiz_questions.append(quiz_question)
    
    return quiz_questions
