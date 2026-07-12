from fastapi import APIRouter
from model.askRequest import AskRequest
from utils.ask_utils import ask_portfolio_chatbot, plain_text

router = APIRouter()

@router.post("/ask")
def ask(request: AskRequest):
    reply = ask_portfolio_chatbot(request.question)
    clean_reply = plain_text(reply)
    return {"answer": clean_reply, "reply": clean_reply}

