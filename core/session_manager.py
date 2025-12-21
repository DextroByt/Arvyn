import time
import uuid
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, Any

@dataclass
class Session:
    id: str
    task_type: str
    params: Dict[str, Any] = field(default_factory=dict)
    status: str = "active"
    created_at: float = field(default_factory=lambda: time.time())
    last_activity: float = field(default_factory=lambda: time.time())

    def touch(self):
        self.last_activity = time.time()

class SessionManager:
    def __init__(self):
        self._session: Optional[Session] = None

    def start_session(self, task_type: str, params: Optional[Dict[str, Any]] = None) -> Session:
        if self._session and self._session.status == 'active':
            # End existing session
            self.end_session()
        sid = str(uuid.uuid4())
        sess = Session(id=sid, task_type=task_type, params=params or {})
        self._session = sess
        return sess

    def get_session(self) -> Optional[Session]:
        return self._session

    def update_session(self, **kwargs) -> Optional[Session]:
        if not self._session:
            return None
        for k, v in kwargs.items():
            if hasattr(self._session, k):
                setattr(self._session, k, v)
            else:
                self._session.params[k] = v
        self._session.touch()
        return self._session

    def end_session(self) -> Optional[Session]:
        if not self._session:
            return None
        self._session.status = 'finished'
        s = self._session
        self._session = None
        return s

    def cancel_session(self) -> Optional[Session]:
        if not self._session:
            return None
        self._session.status = 'cancelled'
        s = self._session
        self._session = None
        return s
