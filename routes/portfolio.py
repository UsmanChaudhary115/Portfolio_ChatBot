import os
import time
import logging
from collections import defaultdict, deque
from fastapi import APIRouter, HTTPException, Request, status
from model.askRequest import AskRequest, ChatRequest, ChatResponse
from utils.ask_utils import ask_portfolio_chatbot, plain_text

logger = logging.getLogger("portfolio-chatbot")

router = APIRouter()


RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "15"))
_request_log: dict[str, deque] = defaultdict(deque)


def check_rate_limit(client_ip: str) -> None:
    now = time.time()
    window = 60.0
    log = _request_log[client_ip]

    while log and now - log[0] > window:
        log.popleft()

    if len(log) >= RATE_LIMIT_PER_MIN:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please slow down and try again shortly.",
        )
    log.append(now)


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    check_rate_limit(client_ip)

    try:
        reply = ask_portfolio_chatbot(message=req.message, history=req.history)
        clean_reply = plain_text(reply)
        return ChatResponse(reply=clean_reply)
    except Exception as e:
        logger.error("Error generating portfolio chat response: %s", e)
        raise HTTPException(status_code=502, detail="Upstream AI service error. Please try again.")


@router.post("/ask")
async def ask(req: AskRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    check_rate_limit(client_ip)

    try:
        reply = ask_portfolio_chatbot(message=req.question)
        clean_reply = plain_text(reply)
        return {"answer": clean_reply, "reply": clean_reply}
    except Exception as e:
        logger.error("Error generating portfolio ask response: %s", e)
        raise HTTPException(status_code=502, detail="Upstream AI service error. Please try again.")
