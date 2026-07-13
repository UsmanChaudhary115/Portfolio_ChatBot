import json
import re
import math
from difflib import SequenceMatcher
from pathlib import Path

# Common typo aliases — maps misspelling → canonical token(s)
TYPO_ALIASES: dict[str, list[str]] = {
    "delloite": ["deloitte"],
    "delloitte": ["deloitte"],
    "deloite": ["deloitte"],
    "folio": ["folio3"],
    "binarytech": ["binarytech"],
    "binaryteck": ["binarytech"],
    "snopvault": ["snapvault"],
    "crickvisoin": ["crickvision"],
    "langchan": ["langchain"],
}

CHUNKS_PATH = Path(__file__).parent.parent / "chunks.json"

with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
    chunks: list[dict] = json.load(f)




def _tokenize(text: str, expand_aliases: bool = False) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    normalized_tokens = []
    for token in tokens:
        if token in {"internships", "internship"}:
            normalized_tokens.append("intern")
        elif token == "projects":
            normalized_tokens.append("project")
        elif token == "experiences":
            normalized_tokens.append("experience")
        elif token == "jobs":
            normalized_tokens.append("job")
        else:
            normalized_tokens.append(token)
        # Expand known typo aliases
        if expand_aliases and token in TYPO_ALIASES:
            normalized_tokens.extend(TYPO_ALIASES[token])
    return normalized_tokens


def _fuzzy_token_bonus(query_tokens: set[str], chunk_tokens: set[str], threshold: float = 0.82) -> float:
    """Returns a bonus score for near-match tokens (handles typos like 'delloite' -> 'deloitte')."""
    bonus = 0.0
    for qt in query_tokens:
        if len(qt) < 4:
            continue  # skip short tokens — too many false positives
        for ct in chunk_tokens:
            if len(ct) < 4:
                continue
            if qt == ct:
                continue  # already counted in exact overlap
            ratio = SequenceMatcher(None, qt, ct).ratio()
            if ratio >= threshold:
                bonus += ratio * 3.0  # weighted by similarity strength
                break
    return bonus


def _is_experience_chunk(chunk: dict) -> bool:
    """Use the 'category' field first, then fall back to token heuristics.
    Category field takes full precedence — a 'certification' is never an experience chunk.
    """
    category = chunk.get("category", "")
    if category:
        return category == "experience"
    # Fallback for chunks without a category field
    cid = chunk.get("id", "")
    title = chunk.get("title", "")
    id_tokens = set(_tokenize(cid))
    title_tokens = set(_tokenize(title))
    experience_keywords = {"intern", "experience", "worked", "work", "role", "employment", "job"}
    return bool((id_tokens | title_tokens).intersection(experience_keywords))


def _is_project_chunk(chunk: dict) -> bool:
    """Use the 'category' field first, then fall back to token heuristics."""
    if chunk.get("category") == "project":
        return True
    cid = chunk.get("id", "")
    title = chunk.get("title", "")
    content = chunk.get("content", "")
    chunk_tokens = set(_tokenize(title)) | set(_tokenize(content)) | set(_tokenize(cid))
    project_keywords = {"project", "built", "developed", "website", "app", "platform", "system", "featured"}
    return bool(chunk_tokens.intersection(project_keywords))


def _get_profile_chunk() -> dict | None:
    """Return the profile/overview chunk regardless of ID format."""
    # Try category first
    for c in chunks:
        if c.get("category") == "profile":
            return c
    # Fallback: try common id patterns
    for pattern in ("profile_overview", "1_profile", "profile"):
        for c in chunks:
            if c.get("id", "") == pattern:
                return c
    return chunks[0] if chunks else None


def _compute_chunk_relevance_score(query_tokens: set[str], query_text: str, chunk: dict) -> float:
    """
    Computes a relevance score between a query and a knowledge base chunk.
    Higher score = more relevant. Uses category field for intent matching.
    """
    if not query_tokens:
        return 0.0

    title = chunk.get("title", "")
    content = chunk.get("content", "")
    cid = chunk.get("id", "")
    category = chunk.get("category", "")
    tags = chunk.get("tags", [])

    title_tokens = set(_tokenize(title))
    content_tokens = set(_tokenize(content))
    id_tokens = set(_tokenize(cid))
    tag_tokens = set(_tokenize(" ".join(tags)))

    chunk_tokens = title_tokens | content_tokens | id_tokens | tag_tokens

    # Expand query aliases so typos like 'delloite' match 'deloitte'
    expanded_query_tokens = set(_tokenize(query_text, expand_aliases=True))

    experience_intent_keywords = {"experience", "intern", "internship", "job", "jobs", "work", "worked", "role", "roles", "employment"}
    project_intent_keywords = {"project", "projects", "built", "developed", "website", "app", "platform", "system"}

    query_experience_intent = bool(expanded_query_tokens.intersection(experience_intent_keywords))
    query_project_intent = bool(expanded_query_tokens.intersection(project_intent_keywords))
    chunk_is_experience = _is_experience_chunk(chunk)
    chunk_is_project = _is_project_chunk(chunk)

    score = 0.0

    # Exact title or ID substring matching
    query_lower = query_text.lower()
    if title.lower() in query_lower or cid.lower() in query_lower:
        score += 10.0

    # Fuzzy bonus: catches typos (e.g. 'delloite' → 'deloitte')
    score += _fuzzy_token_bonus(expanded_query_tokens, chunk_tokens)

    # Check for company name / keyword matches in query vs tags (very strong signal)
    tag_overlap = expanded_query_tokens.intersection(tag_tokens)
    score += len(tag_overlap) * 4.0

    # Title token overlap (high weight for project/company/section names)
    title_overlap = expanded_query_tokens.intersection(title_tokens)
    score += len(title_overlap) * 5.0

    # ID token overlap
    id_overlap = expanded_query_tokens.intersection(id_tokens)
    score += len(id_overlap) * 3.0

    # Content token overlap
    content_overlap = expanded_query_tokens.intersection(content_tokens)
    score += len(content_overlap) * 1.5

    # Category-based intent boosting — uses the reliable 'category' field
    if query_experience_intent and chunk_is_experience:
        score += 10.0
    elif query_experience_intent and not query_project_intent and chunk_is_project:
        score -= 2.0

    if query_project_intent and chunk_is_project:
        score += 3.0

    # Category-specific keyword boosts for common recruiter queries
    contact_keywords = {"contact", "email", "phone", "reach", "linkedin", "github", "location", "who", "usman", "bio"}
    if expanded_query_tokens.intersection(contact_keywords) and category == "profile":
        score += 5.0

    education_keywords = {"degree", "education", "university", "pucit", "cgpa", "graduate", "study", "college"}
    if expanded_query_tokens.intersection(education_keywords) and category == "education":
        score += 5.0

    skills_keywords = {"skills", "tech", "stack", "languages", "frameworks", "databases", "python", "react", "fastapi", "c#"}
    if expanded_query_tokens.intersection(skills_keywords) and category == "skill_index":
        score += 5.0

    certification_keywords = {"certification", "certifications", "certificate", "certified", "course", "courses"}
    if expanded_query_tokens.intersection(certification_keywords) and category == "certification":
        score += 5.0

    return score


def get_relevant_knowledge(
    query: str,
    history: list | None = None,
    k: int = 8,
    min_score_threshold: float = 1.0,
) -> str:
    """
    Proper RAG Retrieval Pipeline:
    1. Enriches the query using recent conversation context for follow-up turns.
    2. Retrieves ONLY genuinely relevant chunks for the user's question.
    3. Filters out non-relevant chunks below the relevance threshold.
    """
    if not query or not query.strip():
        profile = _get_profile_chunk()
        return f"### {profile['title']}\n{profile['content']}" if profile else ""

    # 1. Multi-Turn Query Enrichment
    # For vague follow-ups ("any other", "what else", "more"), scan the last
    # 3 turns of history to reconstruct the topic being discussed.
    search_query = query.strip()
    FOLLOWUP_TRIGGERS = {"other", "else", "more", "another", "also", "too", "further", "additional"}
    query_tokens_raw = set(_tokenize(search_query))
    is_followup = bool(query_tokens_raw.intersection(FOLLOWUP_TRIGGERS)) or len(query_tokens_raw) <= 3

    if history and len(history) > 0:
        # Gather content from the last 3 turns (most recent first)
        context_parts = []
        turns_to_scan = list(history)[-6:]  # up to 3 user+assistant turn pairs
        for turn in reversed(turns_to_scan):
            content = getattr(turn, "content", None) or (turn.get("content") if isinstance(turn, dict) else "")
            if content:
                context_parts.append(content[:200])
            if len(context_parts) >= 3:
                break
        if context_parts:
            if is_followup:
                # For follow-ups, lean heavily on history context to resolve the topic
                search_query = f"{query} {' '.join(context_parts)}"
            else:
                # For standalone queries, just append the immediate last turn for disambiguation
                search_query = f"{query} {context_parts[0][:120]}"

    selected_chunks: list[dict] = []

    # -- Category-complete listing detection --
    # When a query is clearly asking to LIST ALL items in a category (e.g. "certifications?",
    # "what projects does he have?"), retrieve EVERY chunk of that category so the LLM
    # never silently omits items.
    LISTING_CATEGORY_MAP = {
        "certification":  {"certification", "certifications", "certificate", "certificates", "certified"},
        "project":        {"projects"},   # plural only — raw token checked below before normalization
        "experience":     {"experiences"},
        "skill_index":    {"skills"},
    }
    # Check raw tokens (before normalization) so 'projects' isn't silently reduced to 'project'
    import re as _re
    raw_query_tokens = set(_re.findall(r"[a-z0-9]+", query.strip().lower()))
    # Also include normalized tokens so 'certifications' → 'certification' still matches
    plain_query_tokens = set(_tokenize(query.strip(), expand_aliases=True)) | raw_query_tokens
    for cat, triggers in LISTING_CATEGORY_MAP.items():
        if plain_query_tokens.intersection(triggers):
            category_chunks = [c for c in chunks if c.get("category") == cat]
            if category_chunks:
                selected_chunks = category_chunks
                break

    if selected_chunks:
        # Skip scoring — we already have the full category
        formatted_sections = []
        for c in selected_chunks:
            title = c.get("title", c.get("id", ""))
            content = c.get("content", "").strip()
            formatted_sections.append(f"### {title}\n{content}")
        return "\n\n".join(formatted_sections)

    # 2. Retrieval via keyword scorer
    query_tokens = set(_tokenize(search_query, expand_aliases=True))
    query_experience_intent = bool(query_tokens.intersection({"experience", "intern", "internship", "job", "jobs", "work", "worked", "role", "roles", "employment"}))
    query_project_intent = bool(query_tokens.intersection({"project", "projects", "built", "developed", "website", "app", "platform", "system"}))

    scored_chunks = [
        (c, _compute_chunk_relevance_score(query_tokens, search_query, c))
        for c in chunks
    ]
    # Sort by score descending and filter by threshold
    scored_chunks.sort(key=lambda x: x[1], reverse=True)

    # For pure experience queries: prioritize experience chunks, allow some project context
    if query_experience_intent and not query_project_intent:
        experience_chunks = [c for c, score in scored_chunks if score >= min_score_threshold and _is_experience_chunk(c)]
        other_chunks = [c for c, score in scored_chunks if score >= min_score_threshold and not _is_experience_chunk(c)]
        # Take up to k experience chunks, fill remaining with other high-scoring chunks
        relevant = experience_chunks[:k]
        if len(relevant) < k:
            relevant.extend(other_chunks[: max(0, k - len(relevant))])
    else:
        relevant = [c for c, score in scored_chunks if score >= min_score_threshold][:k]

    # If both project and experience intent, also add relevant project chunks
    if query_experience_intent and query_project_intent and len(relevant) < k:
        project_support = [c for c, score in scored_chunks if score >= min_score_threshold and _is_project_chunk(c) and c not in relevant]
        relevant.extend(project_support[: max(0, k - len(relevant))])

    selected_chunks = relevant

    # 3. Safety Fallback: If no chunk crossed the threshold, return profile overview
    if not selected_chunks:
        profile = _get_profile_chunk()
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
