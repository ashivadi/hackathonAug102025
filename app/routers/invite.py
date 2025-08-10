from fastapi import APIRouter
from app.schemas.invite import InviteDecisionIn
from app.services.decision import score_decision

router = APIRouter(prefix="/v1/invite", tags=["invite"])

@router.post("/decide")
async def decide(inv: InviteDecisionIn):
    schedule_cost = min(1.0, inv.conflicts*0.5 + inv.travelTime/90)
    s = score_decision(relationship_value=0.8, wellbeing_delta=0.2, goal_disruption=0.6, schedule_cost=schedule_cost)
    accept = s > 0.1
    tradeoffs = ["Shift strength to 18:00", "Shorten deep work by 30m"] if accept else ["Keep existing workout & deep work intact"]
    alternatives = [
        {"when": "Wed 19:30", "reason": "no conflicts"},
        {"when": "Thu 19:00", "reason": "keeps Health needle"},
    ]
    return {"ok": True, "data": {"accept": accept, "tradeoffs": tradeoffs, "alternatives": alternatives}}
