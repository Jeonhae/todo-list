from datetime import datetime, timezone
from todo_desktop import models, repository


def test_db_init(tmp_path):
    dbp = tmp_path / "td.db"
    models.init_db(str(dbp))
    # add a task with timezone-aware datetime
    tid = repository.add_task(title="t1", notes="n", priority=1, due_date=datetime.now(timezone.utc))
    assert tid is not None
    tasks = repository.list_tasks(show_all=True)
    assert any(t.id == tid for t in tasks)
