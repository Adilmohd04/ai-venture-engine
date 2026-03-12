import heapq
import threading
import time
from dataclasses import dataclass, field

PRIORITY_MAP = {"business": 1, "pro": 2, "free": 3}


@dataclass(order=True)
class QueuedJob:
    priority: int
    timestamp: float = field(compare=True)
    analysis_id: str = field(compare=False)
    user_id: str = field(compare=False)
    plan: str = field(compare=False)


class AnalysisQueue:
    def __init__(self):
        self._heap: list[QueuedJob] = []
        self._lock = threading.Lock()

    def enqueue(self, analysis_id: str, user_id: str, plan: str) -> QueuedJob:
        job = QueuedJob(
            priority=PRIORITY_MAP.get(plan, 3),
            timestamp=time.time(),
            analysis_id=analysis_id,
            user_id=user_id,
            plan=plan,
        )
        with self._lock:
            heapq.heappush(self._heap, job)
        return job

    def dequeue(self) -> QueuedJob | None:
        with self._lock:
            return heapq.heappop(self._heap) if self._heap else None

    def peek(self) -> QueuedJob | None:
        with self._lock:
            return self._heap[0] if self._heap else None

    def size(self) -> int:
        with self._lock:
            return len(self._heap)
