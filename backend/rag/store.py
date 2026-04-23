import os
import tempfile
import logging
from typing import List, Optional

from langchain_community.document_loaders import PyPDFLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

logger = logging.getLogger(__name__)

_embedding_model: Optional[HuggingFaceEmbeddings] = None


def _chroma_dir() -> str:
    return os.getenv("CHROMA_DIR", os.path.join(os.path.dirname(__file__), "..", ".chroma"))


def _collection_name(user_id: int) -> str:
    return f"user_{user_id}_docs"


def get_embeddings() -> HuggingFaceEmbeddings:
    global _embedding_model
    if _embedding_model is None:
        model_name = os.getenv(
            "HF_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        ).strip()
        cache_folder = os.getenv("HF_HOME", "/app/.hf_cache")
        
        try:
            logger.info(f"Loading HuggingFace embedding model: {model_name}")
            
            # Ensure cache directory exists
            os.makedirs(cache_folder, exist_ok=True)
            
            _embedding_model = HuggingFaceEmbeddings(
                model_name=model_name,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
                cache_folder=cache_folder,
            )
            
            # Test the embedding model by trying to encode a simple text
            test_embedding = _embedding_model.embed_query("test")
            if not test_embedding or len(test_embedding) == 0:
                raise ValueError("Embedding model returned empty result")
                
            logger.info(f"Successfully loaded embedding model with {len(test_embedding)} dimensions")
            
        except Exception as e:
            logger.error(f"Failed to load HuggingFace embedding model '{model_name}': {e}")
            
            # Try fallback models in order of preference
            fallback_models = [
                "sentence-transformers/all-MiniLM-L6-v2",
                "sentence-transformers/paraphrase-MiniLM-L6-v2",
                "all-MiniLM-L6-v2"
            ]
            
            for fallback_model in fallback_models:
                if fallback_model == model_name:
                    continue  # Skip the one that already failed
                    
                try:
                    logger.info(f"Trying fallback model: {fallback_model}")
                    _embedding_model = HuggingFaceEmbeddings(
                        model_name=fallback_model,
                        model_kwargs={"device": "cpu"},
                        encode_kwargs={"normalize_embeddings": True},
                        cache_folder=cache_folder,
                    )
                    
                    # Test the fallback model
                    test_embedding = _embedding_model.embed_query("test")
                    if not test_embedding or len(test_embedding) == 0:
                        raise ValueError("Fallback model returned empty result")
                        
                    logger.info(f"Successfully loaded fallback model: {fallback_model}")
                    break
                    
                except Exception as fallback_error:
                    logger.warning(f"Fallback model '{fallback_model}' also failed: {fallback_error}")
                    continue
            else:
                # All fallbacks failed, raise a critical error
                critical_error = (
                    f"Failed to load any embedding model. "
                    f"Primary: '{model_name}' failed with: {e}. "
                    f"All fallback models also failed. "
                    f"Please check internet connection and model availability."
                )
                logger.critical(critical_error)
                raise RuntimeError(critical_error) from e
    
    return _embedding_model


def _extract_smart_sections(text: str) -> str:
    """Keep only candidate name, skills, and experience/top project fallback."""
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines:
        return text
    name = lines[0][:120]
    skills: list[str] = []
    experience: list[str] = []
    projects: list[str] = []

    for line in lines:
        ll = line.lower()
        if any(k in ll for k in ("skill", "technolog", "tool", "language", "framework", "stack")):
            skills.append(line)
        if any(k in ll for k in ("experience", "employment", "work history", "career", "engineer", "developer")):
            experience.append(line)
        if "project" in ll and len(projects) < 3:
            projects.append(line)

    exp_or_project = experience[:4] if experience else projects[:3]
    compact = [
        f"Name: {name}",
        f"Skills: {' | '.join(skills[:8])}",
        f"Experience: {' | '.join(exp_or_project)}",
    ]
    return "\n".join([line for line in compact if line.strip()])


def _extract_section_map(text: str) -> dict[str, str]:
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines:
        return {"name": "", "skills": "", "experience": "", "projects": ""}
    name = lines[0][:120]
    skills = []
    experience = []
    projects = []
    for line in lines:
        ll = line.lower()
        if any(k in ll for k in ("skill", "technolog", "tool", "language", "framework", "stack")):
            skills.append(line)
        if any(k in ll for k in ("experience", "employment", "work history", "career", "engineer", "developer")):
            experience.append(line)
        if "project" in ll and len(projects) < 5:
            projects.append(line)
    return {
        "name": name,
        "skills": "\n".join(skills[:12]),
        "experience": "\n".join(experience[:12]),
        "projects": "\n".join(projects[:10]),
    }


def get_vectorstore(user_id: int) -> Chroma:
    persist_directory = os.path.abspath(_chroma_dir())
    os.makedirs(persist_directory, exist_ok=True)
    return Chroma(
        collection_name=_collection_name(user_id),
        persist_directory=persist_directory,
        embedding_function=get_embeddings(),
    )


def upsert_resume(user_id: int, file_bytes: bytes, filename: str) -> int:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        try:
            old_vs = Chroma(
                collection_name=_collection_name(user_id),
                persist_directory=os.path.abspath(_chroma_dir()),
                embedding_function=get_embeddings(),
            )
            old_vs.delete_collection()
        except Exception:
            pass

        loader = PyPDFLoader(tmp_path)
        docs = loader.load()
        full_text = "\n".join([d.page_content for d in docs])
        section_map = _extract_section_map(full_text)
        smart_text = _extract_smart_sections(full_text)
        filtered_docs = [
            Document(
                page_content=smart_text,
                metadata={"user_id": user_id, "source": "resume", "filename": filename, "section": "summary"},
            )
        ]
        for section in ("skills", "experience", "projects"):
            section_text = (section_map.get(section) or "").strip()
            if section_text:
                filtered_docs.append(
                    Document(
                        page_content=section_text,
                        metadata={"user_id": user_id, "source": "resume", "filename": filename, "section": section},
                    )
                )

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", " ", ""],
        )
        chunks = splitter.split_documents(filtered_docs)

        try:
            vs = get_vectorstore(user_id)
            vs.add_documents(chunks)
            # In latest versions of Langchain-Chroma, persist is handled automatically, 
            # but we call it just in case you are on an older version.
            if hasattr(vs, 'persist'):
                vs.persist()
            return len(chunks)
        except Exception as e:
            # Keep error message actionable for container logs
            raise RuntimeError(
                f"Vector upsert failed for user_id={user_id} filename={filename}: {str(e)}"
            ) from e
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def retrieve(user_id: int, query: str, k: int = 4) -> List[str]:
    vs = get_vectorstore(user_id)
    docs = vs.similarity_search(query, k=k)
    return [d.page_content for d in docs]