import json
import re
import math
from pathlib import Path

CHUNKS_PATH = Path(__file__).parent.parent / "chunks.json"

with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
    chunks: list[dict] = json.load(f)

# Optional FAISS + LangChain vector store integration
try:
    from langchain.schema import Document
    from langchain_community.vectorstores import FAISS
    from langchain_community.embeddings import HuggingFaceEmbeddings

    _faiss_docs = [
        Document(
            page_content=c.get("content", ""),
            metadata={
                "id": c.get("id", ""),
                "title": c.get("title", ""),
                "type": c.get("type", ""),
            },
        )
        for c in chunks
        if c.get("content")
    ]
    _embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    _faiss_db = FAISS.from_documents(_faiss_docs, _embeddings)
    HAS_FAISS = True
except Exception:
    HAS_FAISS = False
    _faiss_db = None


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _compute_chunk_relevance_score(query_tokens: set[str], query_text: str, chunk: dict) -> float:
    """
    Computes a relevance score between a query and a knowledge base chunk.
    Higher score = more relevant.
    """
    if not query_tokens:
        return 0.0

    title = chunk.get("title", "")
    content = chunk.get("content", "")
    cid = chunk.get("id", "")

    title_tokens = set(_tokenize(title))
    content_tokens = set(_tokenize(content))
    id_tokens = set(_tokenize(cid))

    score = 0.0

    # Exact title or ID substring matching
    query_lower = query_text.lower()
    if title.lower() in query_lower or cid.lower() in query_lower:
        score += 10.0

    # Title token overlap (high weight for project/company/section names)
    title_overlap = query_tokens.intersection(title_tokens)
    score += len(title_overlap) * 5.0

    # ID token overlap
    id_overlap = query_tokens.intersection(id_tokens)
    score += len(id_overlap) * 3.0

    # Content token overlap
    content_overlap = query_tokens.intersection(content_tokens)
    score += len(content_overlap) * 1.5

    # Specific recruiter intent category boosts (excluding generic words like 'about')
    contact_keywords = {"contact", "email", "phone", "reach", "linkedin", "github", "location", "who", "usman", "bio"}
    if query_tokens.intersection(contact_keywords) and cid == "1_profile":
        score += 5.0

    education_keywords = {"degree", "education", "university", "pucit", "cgpa", "graduate", "study", "college"}
    if query_tokens.intersection(education_keywords) and cid == "2_education":
        score += 5.0

    skills_keywords = {"skills", "tech", "stack", "languages", "frameworks", "databases", "python", "react", "fastapi", "c#"}
    if query_tokens.intersection(skills_keywords) and cid == "3_tech_stack":
        score += 5.0

    return score



def get_relevant_knowledge(
    query: str,
    history: list | None = None,
    k: int = 4,
    min_score_threshold: float = 1.0,
) -> str:
    """
    Proper RAG Retrieval Pipeline:
    1. Enriches the query using recent conversation context for follow-up turns.
    2. Retrieves ONLY genuinely relevant chunks for the user's question.
    3. Filters out non-relevant chunks below the relevance threshold.
    """
    if not query or not query.strip():
        # Fallback to profile if query is empty
        profile = next((c for c in chunks if c.get("id") == "1_profile"), None)
        return f"### {profile['title']}\n{profile['content']}" if profile else ""

    # 1. Query Enrichment for Multi-Turn Context Resolution
    search_query = query.strip()
    if history and len(history) > 0:
        last_turn = history[-1]
        last_content = getattr(last_turn, "content", None) or (last_turn.get("content") if isinstance(last_turn, dict) else "")
        if last_content:
            search_query = f"{query} {last_content[:120]}"

    selected_chunks: list[dict] = []

    # 2. Retrieval via FAISS (if available) or Semantic Scorer
    if HAS_FAISS and _faiss_db:
        results_with_scores = _faiss_db.similarity_search_with_score(search_query, k=k * 2)
        # FAISS L2 distance: lower score means higher similarity.
        # Filter top k closest matches that are reasonably similar (L2 distance < 1.6)
        valid_matches = [doc for doc, score in results_with_scores if score < 1.6][:k]
        selected_ids = {doc.metadata.get("id") for doc in valid_matches}
        selected_chunks = [c for c in chunks if c.get("id") in selected_ids]
    else:
        query_tokens = set(_tokenize(search_query))
        scored_chunks = [
            (c, _compute_chunk_relevance_score(query_tokens, search_query, c))
            for c in chunks
        ]
        # Sort by score descending and filter by threshold
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        relevant = [c for c, score in scored_chunks if score >= min_score_threshold][:k]
        selected_chunks = relevant

    # 3. Safety Fallback: If no chunk crossed the threshold, retrieve top 2 closest or Profile
    if not selected_chunks:
        profile = next((c for c in chunks if c.get("id") == "1_profile"), None)
        if profile:
            selected_chunks = [profile]

    # 4. Format ONLY the relevant chunks to send to the LLM
    formatted_sections = []
    for c in selected_chunks:
        title = c.get("title", c.get("id", ""))
        content = c.get("content", "").strip()
        formatted_sections.append(f"### {title}\n{content}")

    return "\n\n".join(formatted_sections)


def get_full_knowledge_base() -> str:
    """Returns all knowledge base chunks formatted as a structured text document."""
    sections = []
    for c in chunks:
        title = c.get("title", c.get("id", ""))
        content = c.get("content", "").strip()
        if content:
            sections.append(f"### {title}\n{content}")
    return "\n\n".join(sections)
