from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

SessionLocal = sessionmaker(autocommit=False, autoflush=False)


class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    notes = Column(Text)
    done = Column(Boolean, default=False, nullable=False)
    priority = Column(Integer, default=0)
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=True)
    # elapsed time in seconds for the task (used-time)
    elapsed_seconds = Column(Integer, default=0, nullable=False)


def init_db(db_path: str = "todo_desktop.db"):
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    SessionLocal.configure(bind=engine)
    Base.metadata.create_all(bind=engine)
    # Ensure new columns are added for existing databases (simple migration)
    try:
        insp = inspect(engine)
        cols = [c.get('name') for c in insp.get_columns('tasks')]
        if 'elapsed_seconds' not in cols:
            # add column with default 0 and not null
            with engine.connect() as conn:
                conn.execute(text('ALTER TABLE tasks ADD COLUMN elapsed_seconds INTEGER DEFAULT 0 NOT NULL'))
                conn.commit()
    except Exception:
        # best-effort migration; ignore failures
        pass
    return engine
