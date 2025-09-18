# Pydantic models for API requests
from pydantic import BaseModel

class EssayPrompt(BaseModel):
    topic: str
    session_id: str

class EssayRequest(BaseModel):
    session_id: str
    topic: str
    # session_id: str
