from sqlalchemy.orm import Session
from app.models.preference import Preference

def upsert_preference(db: Session, user_id: str, key: str, value, confidence: float = 0.8):
    pref = db.query(Preference).filter_by(user_id=user_id, key=key).one_or_none()
    if pref:
        pref.value = value
        pref.confidence = confidence
        db.add(pref)
        return pref
    pref = Preference(user_id=user_id, key=key, value=value, confidence=confidence)
    db.add(pref)
    return pref
