from __future__ import annotations

from sqlalchemy.orm import Session
from sqlalchemy import text

try:
    from .. import models
    from .llm_service import generate_quiz
except ImportError:
    import models  # type: ignore
    from services.llm_service import generate_quiz  # type: ignore


def get_current_mock(db: Session) -> "models.GlobalMock | None":
    return db.query(models.GlobalMock).order_by(models.GlobalMock.created_at.desc()).first()


def replace_mock(db: Session, questions: list[dict]) -> "models.GlobalMock":
    with db.begin():
        try:
            db.execute(text("SELECT pg_advisory_xact_lock(987654321)"))
        except Exception:
            # Non-Postgres engines won't support advisory lock.
            pass
        db.query(models.GlobalMock).delete()
        row = models.GlobalMock(questions=questions)
        db.add(row)
    db.refresh(row)
    return row


async def generate_new_mock(db: Session, category: str, context: str = "") -> "models.GlobalMock":
    # If PDF extraction failed or context is empty/very short, use AI fallback
    if not context or len(context.strip()) < 100:
        context = await generate_ai_fallback_context(category)
    
    # Use specialized coding service for Coding category
    if category == "Coding":
        from .coding_service import generate_coding_quiz
        questions = await generate_coding_quiz(category)
    else:
        questions = await generate_quiz(context, category)
    
    return replace_mock(db, questions=questions)


async def generate_ai_fallback_context(category: str) -> str:
    """
    Generate AI fallback context when PDF extraction fails.
    Creates 20 technical questions based on the category section.
    """
    from .llm_service import generate_quiz
    
    # Generate a comprehensive fallback context based on category
    category_contexts = {
        "Quant": """
        Data Structures and Algorithms: Arrays, Linked Lists, Stacks, Queues, Trees, Graphs, Hash Tables, Heaps, Tries.
        Algorithms: Sorting (Quick Sort, Merge Sort, Heap Sort), Searching (Binary Search), Dynamic Programming, Greedy Algorithms, Recursion, Backtracking.
        Mathematical Concepts: Time Complexity, Space Complexity, Big O Notation, Probability, Statistics, Combinatorics.
        Problem Solving: Two Pointers, Sliding Window, Divide and Conquer, BFS, DFS, Topological Sort, Minimum Spanning Tree, Shortest Path.
        Advanced Topics: Segment Trees, Fenwick Trees, Suffix Arrays, String Algorithms, Number Theory, Bit Manipulation.
        """,
        "Verbal": """
        Reading Comprehension: Main Idea, Inference, Tone, Purpose, Context Clues, Vocabulary, Author's Argument.
        Grammar: Subject-Verb Agreement, Tenses, Modifiers, Parallel Structure, Pronoun Agreement, Punctuation.
        Critical Reasoning: Logical Fallacies, Assumptions, Conclusions, Strengthening/Weakening Arguments, Paradox Resolution.
        Vocabulary: Synonyms, Antonyms, Analogies, Word Usage, Contextual Meaning, Etymology.
        Writing Skills: Essay Structure, Thesis Statements, Supporting Evidence, Transitions, Cohesion, Clarity.
        Advanced Concepts: Rhetorical Devices, Logical Reasoning, Argument Analysis, Textual Evidence Evaluation.
        """,
        "Reasoning": """
        Logical Reasoning: Deductive Reasoning, Inductive Reasoning, Syllogisms, Logical Connectives, Truth Tables.
        Analytical Reasoning: Arrangement Problems, Selection Problems, Network Problems, Matrix Puzzles.
        Data Interpretation: Tables, Graphs, Charts, Bar Diagrams, Pie Charts, Line Graphs, Scatter Plots.
        Pattern Recognition: Number Series, Letter Series, Figure Series, Analogical Patterns, Missing Elements.
        Spatial Reasoning: Mental Rotation, 3D Visualization, Pattern Folding, Mirror Images, Block Counting.
        Problem Solving: Logical Deduction, Elimination Method, Substitution, Working Backwards, Pattern Analysis.
        """,
        "Coding": """
        Programming Fundamentals: Variables, Data Types, Control Structures, Functions, Classes, Objects, Inheritance, Polymorphism.
        Data Structures: Arrays, Linked Lists, Stacks, Queues, Trees (Binary, BST, AVL), Graphs, Hash Tables, Heaps.
        Algorithms: Sorting (Bubble, Selection, Insertion, Quick, Merge, Heap), Searching (Linear, Binary), Recursion.
        Problem Solving Patterns: Two Pointers, Sliding Window, Divide and Conquer, Dynamic Programming, Greedy Algorithms.
        System Design: Scalability, Caching, Load Balancing, Database Design, API Design, Microservices.
        Advanced Topics: Bit Manipulation, String Processing, Tree Traversal, Graph Algorithms, Backtracking, Memoization.
        LeetCode Style Problems: Array Manipulation, String Processing, Linked List Operations, Tree Algorithms, Graph Traversal.
        Time & Space Complexity: Big O Analysis, Optimal Solutions, Trade-offs, Memory Management.
        """
    }
    
    # Use category-specific context or default
    fallback_context = category_contexts.get(category, category_contexts["Quant"])
    
    # Generate some initial questions to enrich the context
    try:
        initial_questions = await generate_quiz(fallback_context, category)
        # Add question patterns to the context
        question_patterns = "\nSample Question Patterns:\n"
        for i, q in enumerate(initial_questions[:5]):
            question_patterns += f"{i+1}. {q.get('question', '')}\n"
        
        return fallback_context + question_patterns
    except Exception:
        # If even AI generation fails, return the basic context
        return fallback_context
