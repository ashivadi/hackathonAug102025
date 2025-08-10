from datetime import datetime
import uuid
def gen_id() -> str: return uuid.uuid4().hex
def now_utc() -> datetime: return datetime.utcnow()
