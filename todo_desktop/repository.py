from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from .models import Task, SessionLocal

# Simple in-memory cache for list_tasks(show_all=True)
_tasks_cache: Optional[List[Task]] = None

def _invalidate_cache():
    global _tasks_cache
    _tasks_cache = None


def get_session() -> Session:
    return SessionLocal()


def add_task(title: str, notes: Optional[str] = None, priority: int = 0, due_date=None, db_path: str = None) -> int:
    s = get_session()
    try:
        t = Task(title=title, notes=notes, priority=priority, due_date=due_date, created_at=datetime.now(timezone.utc))
        s.add(t)
        s.commit()
        s.refresh(t)
        # invalidate cache when data changes
        _invalidate_cache()
        return t.id
    finally:
        s.close()


def list_tasks(show_all: bool = True) -> List[Task]:
    s = get_session()
    try:
        if show_all:
            global _tasks_cache
            if _tasks_cache is not None:
                return _tasks_cache
            res = s.query(Task).order_by(Task.done.asc(), Task.priority.desc(), Task.created_at.asc()).all()
            _tasks_cache = res
            return res
        return s.query(Task).filter(Task.done.is_(False)).order_by(Task.priority.desc(), Task.created_at.asc()).all()
    finally:
        s.close()


def get_task(task_id: int) -> Optional[Task]:
    s = get_session()
    try:
        return s.query(Task).filter(Task.id == task_id).first()
    finally:
        s.close()


def set_done(task_id: int, done: bool = True) -> bool:
    s = get_session()
    try:
        t = s.query(Task).filter(Task.id == task_id).first()
        if not t:
            return False
        t.done = done
        t.updated_at = datetime.now(timezone.utc)
        s.commit()
        _invalidate_cache()
        return True
    finally:
        s.close()


def delete_task(task_id: int) -> bool:
    s = get_session()
    try:
        t = s.query(Task).filter(Task.id == task_id).first()
        if not t:
            return False
        s.delete(t)
        s.commit()
        _invalidate_cache()
        return True
    finally:
        s.close()


def update_task(task_id: int, **fields) -> bool:
    s = get_session()
    try:
        t = s.query(Task).filter(Task.id == task_id).first()
        if not t:
            return False
        for k, v in fields.items():
            if hasattr(t, k):
                setattr(t, k, v)
        t.updated_at = datetime.now(timezone.utc)
        s.commit()
        _invalidate_cache()
        return True
    finally:
        s.close()
