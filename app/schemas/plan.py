from pydantic import BaseModel
from typing import List, Dict

class Eisenhower(BaseModel):
    urgent_important: List[str] = []
    urgent_not_important: List[str] = []
    not_urgent_important: List[str] = []
    not_urgent_not_important: List[str] = []

class ScheduleItem(BaseModel):
    start: str
    end: str
    item: str

class StressRule(BaseModel):
    trigger: str
    action: str

class PlanPayload(BaseModel):
    eisenhower: Eisenhower
    three_needles: Dict[str, str]
    schedule: List[ScheduleItem]
    affirmations: Dict[str, str]
    stress_guide: List[StressRule]
    nudges: List[dict]
