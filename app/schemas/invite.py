from pydantic import BaseModel
from typing import Optional

class InviteDecisionIn(BaseModel):
    when: str
    who: Optional[str] = None
    location: Optional[str] = None
    conflicts: int = 0
    travelTime: int = 0
