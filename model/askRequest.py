from pydantic import BaseModel, Field, field_validator

MAX_MESSAGE_LENGTH = 500
MAX_HISTORY_TURNS = 6


class AskRequest(BaseModel):
    question: str


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., max_length=MAX_MESSAGE_LENGTH)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=MAX_MESSAGE_LENGTH)
    history: list[ChatMessage] = Field(default_factory=list)

    @field_validator("message")
    @classmethod
    def strip_message(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("message cannot be empty")
        return v

    @field_validator("history")
    @classmethod
    def trim_history(cls, v: list[ChatMessage]) -> list[ChatMessage]:
        max_msgs = MAX_HISTORY_TURNS * 2
        return v[-max_msgs:]


class ChatResponse(BaseModel):
    reply: str
 