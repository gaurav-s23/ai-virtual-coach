import os
import tempfile
from typing import List

from langchain_community.document_loaders import PyPDFLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma


def _chroma_dir() -> str:
    return os.getenv("CHROMA_DIR", os.path.join(os.path.dirname(__file__), "..", ".chroma"))


def _collection_name(user_id: int) -> str:
    return f"user_{user_id}_docs"


def get_embeddings() -> HuggingFaceEmbeddings:
    # Local CPU embeddings: no Google API key required.
    model_name = os.getenv(
        "HF_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
    ).strip()
    cache_folder = os.getenv("HF_HOME", "/app/.hf_cache")
    return HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
        cache_folder=cache_folder,
    )


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
        loader = PyPDFLoader(tmp_path)
        docs = loader.load()

        for d in docs:
            d.metadata = {
                **(d.metadata or {}),
                "user_id": user_id,
                "source": "resume",
                "filename": filename,
            }

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=150,
            separators=["\n\n", "\n", " ", ""],
        )
        chunks = splitter.split_documents(docs)

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