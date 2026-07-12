import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import portfolio, lawyer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("portfolio-chatbot")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not GROQ_API_KEY:
        logger.warning("GROQ_API_KEY is not set — chatbot requests will fail until it is configured.")
    yield


app = FastAPI(
    title="Usman Portfolio Chatbot API",
    version="1.0.0",
    description="Backend AI Assistant for Muhammad Usman Ali's Portfolio",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(portfolio.router, tags=["Portfolio Chatbot"])
app.include_router(portfolio.router, prefix="/portfolio", tags=["Portfolio Chatbot"])
app.include_router(lawyer.router, prefix="/lawyer", tags=["Legacy Route"])


@app.get("/health")
async def health():
    return {"status": "ok", "model": GROQ_MODEL}


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "Usman Portfolio Chatbot Backend",
        "model": GROQ_MODEL,
        "endpoints": ["/chat", "/ask", "/health"],
    }


