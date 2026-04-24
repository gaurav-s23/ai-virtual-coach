#!/usr/bin/env python3
"""
RAGAS Evaluation for AI Virtual Coach RAG Pipeline

This script evaluates the RAG (Retrieval Augmented Generation) pipeline 
using the RAGAS framework with comprehensive metrics.

Metrics evaluated:
- Answer Relevance: How relevant is the generated answer to the question
- Faithfulness: How factually consistent is the answer with the retrieved context
- Context Recall: How well does the retrieved context cover the information needed

Usage:
    python evaluate.py
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import List, Dict, Any
import asyncio
from pathlib import Path

# Add backend to path for imports
sys.path.append(str(Path(__file__).parent))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

try:
    from ragas import evaluate
    from ragas.metrics import AnswerRelevancy, Faithfulness, ContextRecall
    from ragas.dataset import Dataset
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_chroma import Chroma
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_core.documents import Document
    from core.config import get_settings
    from services.rag_service import extract_resume_brief, queue_resume_embedding
    from llm.router import complete_with_fallback
except ImportError as e:
    logger.error(f"Missing required dependencies for RAGAS evaluation: {e}")
    logger.error("Please install: ragas, langchain, langchain-community, langchain-huggingface")
    sys.exit(1)


class RAGEvaluator:
    """RAG Pipeline Evaluator using RAGAS framework"""
    
    def __init__(self):
        self.settings = get_settings()
        self.embeddings = None
        self.chroma_client = None
        self.results = {}
        
    async def setup(self):
        """Initialize embeddings and ChromaDB client"""
        try:
            # Setup embeddings
            model_name = os.getenv("HF_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
            cache_folder = os.getenv("HF_HOME", "/app/.hf_cache")
            
            logger.info(f"Loading embedding model: {model_name}")
            self.embeddings = HuggingFaceEmbeddings(
                model_name=model_name,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
                cache_folder=cache_folder,
            )
            
            # Setup ChromaDB
            chroma_dir = os.getenv("CHROMA_DIR", "./.chroma")
            self.chroma_client = Chroma(
                embedding_function=self.embeddings,
                persist_directory=chroma_dir,
            )
            
            logger.info("RAG evaluator setup completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup RAG evaluator: {e}")
            raise
    
    def get_sample_qa_pairs(self) -> List[Dict[str, str]]:
        """
        Generate sample QA pairs based on resume/interview context
        These are realistic questions that would be asked in an interview setting
        """
        return [
            {
                "question": "What programming languages are you proficient in?",
                "ground_truth": "Python, JavaScript, TypeScript, Java, SQL, and Go with 5+ years of experience in Python and JavaScript"
            },
            {
                "question": "Describe your experience with cloud technologies.",
                "ground_truth": "Extensive experience with AWS services including EC2, S3, Lambda, and RDS. Also worked with Google Cloud Platform and Azure for multi-cloud deployments."
            },
            {
                "question": "What machine learning frameworks have you worked with?",
                "ground_truth": "PyTorch, TensorFlow, Scikit-learn, and Keras. Built several ML models for classification, regression, and NLP tasks."
            },
            {
                "question": "How do you approach system design challenges?",
                "ground_truth": "Start with requirements gathering, create high-level architecture, consider scalability and reliability, then dive into component design with proper documentation."
            },
            {
                "question": "What databases have you worked with?",
                "ground_truth": "PostgreSQL, MySQL, MongoDB, Redis, and Elasticsearch. Experience with both SQL and NoSQL databases for different use cases."
            },
            {
                "question": "Describe your experience with DevOps practices.",
                "ground_truth": "CI/CD pipelines using GitHub Actions and Jenkins, Docker containerization, Kubernetes orchestration, and infrastructure as code with Terraform."
            },
            {
                "question": "What's your experience with microservices architecture?",
                "ground_truth": "Designed and implemented microservices using Docker and Kubernetes, handled inter-service communication with REST APIs and message queues."
            },
            {
                "question": "How do you ensure code quality in your projects?",
                "ground_truth": "Code reviews, unit testing with pytest, integration testing, static analysis tools, and maintaining comprehensive documentation."
            },
            {
                "question": "What's your experience with frontend development?",
                "ground_truth": "React, Vue.js, Angular, HTML5, CSS3, JavaScript/TypeScript. Built responsive web applications with modern frameworks."
            },
            {
                "question": "Describe your experience with API design.",
                "ground_truth": "RESTful API design, GraphQL, OpenAPI specification, authentication with JWT/OAuth, and API versioning strategies."
            },
            {
                "question": "What testing strategies do you employ?",
                "ground_truth": "Unit tests, integration tests, end-to-end tests, performance testing, and test-driven development practices."
            },
            {
                "question": "How do you handle performance optimization?",
                "ground_truth": "Database query optimization, caching strategies, code profiling, load testing, and implementing efficient algorithms."
            },
            {
                "question": "What's your experience with data structures and algorithms?",
                "ground_truth": "Strong foundation in algorithms, data structures, problem-solving, and optimizing code for time and space complexity."
            },
            {
                "question": "Describe your experience with version control.",
                "ground_truth": "Git workflows, branching strategies, merge conflict resolution, and collaborative development using GitHub/GitLab."
            },
            {
                "question": "What security practices do you follow?",
                "ground_truth": "Input validation, authentication/authorization, encryption, secure coding practices, and regular security audits."
            },
            {
                "question": "How do you approach debugging complex issues?",
                "ground_truth": "Systematic approach with logging, debugging tools, root cause analysis, and reproducing issues in controlled environments."
            },
            {
                "question": "What's your experience with real-time systems?",
                "ground_truth": "WebSockets, message queues, event-driven architecture, and low-latency systems for financial and gaming applications."
            },
            {
                "question": "Describe your project management experience.",
                "ground_truth": "Agile methodologies, Scrum, Kanban, project planning, stakeholder communication, and delivering projects on time."
            },
            {
                "question": "What's your experience with mobile development?",
                "ground_truth": "React Native, Flutter, and native iOS/Android development. Built cross-platform mobile applications."
            },
            {
                "question": "How do you stay updated with technology trends?",
                "ground_truth": "Regular reading of tech blogs, attending conferences, online courses, experimenting with new technologies, and contributing to open source."
            },
            {
                "question": "What's your experience with blockchain technologies?",
                "ground_truth": "Smart contracts with Solidity, decentralized applications, Web3.js, and understanding of blockchain principles."
            },
            {
                "question": "Describe your experience with data engineering.",
                "ground_truth": "ETL pipelines, data warehousing, stream processing, data quality management, and big data technologies."
            },
            {
                "question": "What's your approach to technical documentation?",
                "ground_truth": "Comprehensive API documentation, code comments, architecture diagrams, user guides, and maintaining living documentation."
            },
            {
                "question": "How do you handle team collaboration?",
                "ground_truth": "Clear communication, code reviews, pair programming, knowledge sharing, and fostering an inclusive team environment."
            }
        ]
    
    async def create_sample_resume_content(self) -> str:
        """Create sample resume content for testing"""
        return """
        JOHN DOE
        Senior Software Engineer | Full Stack Developer
        
        SUMMARY
        Experienced software engineer with 8+ years in full-stack development, 
        cloud architecture, and machine learning. Proficient in Python, JavaScript, 
        and various cloud platforms. Led multiple projects from conception to deployment.
        
        TECHNICAL SKILLS
        Programming Languages: Python, JavaScript, TypeScript, Java, SQL, Go, C++
        Frameworks: React, Vue.js, Django, Flask, Spring Boot, FastAPI
        Databases: PostgreSQL, MySQL, MongoDB, Redis, Elasticsearch
        Cloud Platforms: AWS, GCP, Azure, Docker, Kubernetes
        ML/AI: PyTorch, TensorFlow, Scikit-learn, NLP, Computer Vision
        DevOps: CI/CD, GitHub Actions, Jenkins, Terraform, Ansible
        
        PROFESSIONAL EXPERIENCE
        
        Senior Software Engineer | Tech Corp Inc. | 2020-Present
        - Led development of microservices architecture serving 1M+ users
        - Implemented ML models for fraud detection reducing false positives by 40%
        - Designed and deployed CI/CD pipelines reducing deployment time by 60%
        - Mentored junior developers and conducted code reviews
        
        Full Stack Developer | StartupXYZ | 2018-2020
        - Built React-based frontend with TypeScript for SaaS platform
        - Developed RESTful APIs using Python and Django
        - Implemented real-time features using WebSockets
        - Optimized database queries improving performance by 50%
        
        Software Engineer | Solutions Inc. | 2016-2018
        - Developed Java-based enterprise applications
        - Worked with Oracle databases and PL/SQL
        - Participated in agile development processes
        - Maintained and enhanced legacy systems
        
        PROJECTS
        
        ML-Powered Chatbot
        - Built NLP-based chatbot using PyTorch and BERT
        - Achieved 85% accuracy in intent classification
        - Deployed using Docker and Kubernetes
        - Integrated with Slack and Microsoft Teams
        
        Real-time Analytics Dashboard
        - Developed streaming analytics platform using Apache Kafka
        - Processed 100K+ events per second
        - Built responsive frontend with D3.js visualizations
        - Implemented automated alerting system
        
        EDUCATION
        Bachelor of Science in Computer Science
        University of Technology | 2012-2016
        GPA: 3.8/4.0
        
        CERTIFICATIONS
        - AWS Certified Solutions Architect
        - Google Cloud Professional Developer
        - Certified Kubernetes Administrator
        """
    
    async def setup_test_data(self) -> None:
        """Setup test data in ChromaDB for evaluation"""
        try:
            # Create sample resume content
            resume_content = await self.create_sample_resume_content()
            
            # Process and store in ChromaDB
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len,
            )
            
            documents = [Document(page_content=resume_content, metadata={"source": "sample_resume"})]
            chunks = text_splitter.split_documents(documents)
            
            # Add to ChromaDB
            test_user_id = 999  # Use a test user ID
            collection_name = f"user_{test_user_id}_docs"
            
            # Clear existing test data
            try:
                self.chroma_client._client.delete_collection(name=collection_name)
            except:
                pass
            
            # Add new test data
            self.chroma_client._client.get_or_create_collection(name=collection_name)
            self.chroma_client.add_documents(chunks, collection_name)
            
            logger.info(f"Test data setup completed with {len(chunks)} chunks")
            
        except Exception as e:
            logger.error(f"Failed to setup test data: {e}")
            raise
    
    async def generate_answers(self, questions: List[str]) -> List[str]:
        """Generate answers using the RAG pipeline"""
        answers = []
        
        for question in questions:
            try:
                # Retrieve relevant context
                test_user_id = 999
                collection_name = f"user_{test_user_id}_docs"
                
                # Search for relevant documents
                results = self.chroma_client.similarity_search(
                    question,
                    k=3,
                    collection_name=collection_name
                )
                
                context = "\n".join([doc.page_content for doc in results])
                
                # Generate answer using LLM
                prompt = f"""Based on the following resume context, answer the question accurately and professionally.

Context:
{context}

Question: {question}

Provide a concise and accurate answer based only on the given context:"""
                
                response = await complete_with_fallback(
                    prompt=prompt,
                    max_tokens=200,
                    temperature=0.1
                )
                
                answer = response.get("content", "").strip()
                answers.append(answer)
                
            except Exception as e:
                logger.error(f"Failed to generate answer for question '{question}': {e}")
                answers.append("Unable to generate answer due to technical issues.")
        
        return answers
    
    async def retrieve_contexts(self, questions: List[str]) -> List[List[str]]:
        """Retrieve relevant contexts for questions"""
        contexts = []
        
        for question in questions:
            try:
                test_user_id = 999
                collection_name = f"user_{test_user_id}_docs"
                
                results = self.chroma_client.similarity_search(
                    question,
                    k=3,
                    collection_name=collection_name
                )
                
                context_texts = [doc.page_content for doc in results]
                contexts.append(context_texts)
                
            except Exception as e:
                logger.error(f"Failed to retrieve context for question '{question}': {e}")
                contexts.append([])
        
        return contexts
    
    async def run_evaluation(self) -> Dict[str, Any]:
        """Run the complete RAGAS evaluation"""
        logger.info("Starting RAGAS evaluation...")
        
        try:
            # Setup test data
            await self.setup_test_data()
            
            # Get sample QA pairs
            qa_pairs = self.get_sample_qa_pairs()
            questions = [qa["question"] for qa in qa_pairs]
            ground_truths = [qa["ground_truth"] for qa in qa_pairs]
            
            logger.info(f"Evaluating {len(qa_pairs)} question-answer pairs...")
            
            # Generate answers and retrieve contexts
            answers = await self.generate_answers(questions)
            contexts = await self.retrieve_contexts(questions)
            
            # Create dataset for RAGAS
            dataset_dict = {
                "question": questions,
                "answer": answers,
                "contexts": contexts,
                "ground_truth": ground_truths
            }
            
            dataset = Dataset.from_dict(dataset_dict)
            
            # Define metrics
            metrics = [
                AnswerRelevancy(),
                Faithfulness(),
                ContextRecall()
            ]
            
            # Run evaluation
            logger.info("Running RAGAS metrics evaluation...")
            result = evaluate(
                dataset=dataset,
                metrics=metrics
            )
            
            # Process results
            scores = {}
            for metric in metrics:
                metric_name = metric.__class__.__name__.lower()
                scores[metric_name] = result[metric_name]
            
            # Calculate overall score
            overall_score = sum(scores.values()) / len(scores)
            scores["overall_score"] = overall_score
            
            # Store detailed results
            self.results = {
                "timestamp": datetime.now().isoformat(),
                "num_questions": len(qa_pairs),
                "metrics": scores,
                "detailed_results": result.to_dict(),
                "sample_questions": questions[:5],  # Include first 5 questions for reference
                "sample_answers": answers[:5],
                "sample_contexts": [ctx[:2] for ctx in contexts[:5]],  # First 2 contexts per question
                "sample_ground_truths": ground_truths[:5]
            }
            
            logger.info("RAGAS evaluation completed successfully!")
            return self.results
            
        except Exception as e:
            logger.error(f"RAGAS evaluation failed: {e}")
            raise
    
    def save_results(self, filename: str = "ragas_evaluation_results.json") -> None:
        """Save evaluation results to JSON file"""
        try:
            with open(filename, 'w') as f:
                json.dump(self.results, f, indent=2, default=str)
            logger.info(f"Evaluation results saved to {filename}")
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
    
    def print_results(self) -> None:
        """Print formatted evaluation results"""
        if not self.results:
            logger.warning("No results to display")
            return
        
        print("\n" + "="*60)
        print("RAGAS EVALUATION RESULTS")
        print("="*60)
        
        print(f"\nEvaluation Date: {self.results['timestamp']}")
        print(f"Number of Questions: {self.results['num_questions']}")
        
        print("\nMetric Scores:")
        print("-" * 30)
        
        metrics = self.results['metrics']
        for metric_name, score in metrics.items():
            if metric_name != 'overall_score':
                print(f"{metric_name.replace('_', ' ').title()}: {score:.4f}")
        
        print(f"\n{'Overall Score':<20}: {metrics['overall_score']:.4f}")
        
        # Performance interpretation
        overall = metrics['overall_score']
        if overall >= 0.8:
            performance = "Excellent"
        elif overall >= 0.7:
            performance = "Good"
        elif overall >= 0.6:
            performance = "Fair"
        else:
            performance = "Needs Improvement"
        
        print(f"\nPerformance Rating: {performance}")
        
        print("\nSample Questions and Answers:")
        print("-" * 40)
        
        for i, (question, answer, ground_truth) in enumerate(zip(
            self.results['sample_questions'],
            self.results['sample_answers'],
            self.results['sample_ground_truths']
        )):
            print(f"\nQ{i+1}: {question}")
            print(f"A{i+1}: {answer[:100]}...")
            print(f"Expected: {ground_truth[:100]}...")
        
        print("\n" + "="*60)


async def main():
    """Main evaluation function"""
    evaluator = RAGEvaluator()
    
    try:
        # Setup evaluator
        await evaluator.setup()
        
        # Run evaluation
        results = await evaluator.run_evaluation()
        
        # Save and display results
        evaluator.save_results()
        evaluator.print_results()
        
        print(f"\n📊 Evaluation completed successfully!")
        print(f"📁 Results saved to: ragas_evaluation_results.json")
        print(f"🎯 Overall Score: {results['metrics']['overall_score']:.4f}")
        
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
