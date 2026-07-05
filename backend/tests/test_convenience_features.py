"""Extended dashboard, lesson filters, data transfer, board snapshots."""

from datetime import date, timedelta

from app.database import get_db
from app.models import BoardSnapshot


def _register(client, email: str = "dash@test.example", password: str = "SecurePass99"):
    client.post("/auth/register", json={"email": email, "password": password, "name": "Tutor"})


def test_dashboard_extended(client):
    _register(client)
    sid = client.post("/students", json={"name": "Bob", "subject": "Math", "grade": "9"}).json()["id"]
    today = date.today()
    client.post(
        "/lessons",
        json={
            "student_id": sid,
            "lesson_date": (today + timedelta(days=1)).isoformat(),
            "lesson_time": "10:00",
            "duration_minutes": 60,
            "payment_amount": 50,
            "is_paid": False,
        },
    )
    r = client.get("/dashboard/extended")
    assert r.status_code == 200
    body = r.json()
    assert "stats" in body
    assert body["stats"]["students_count"] >= 1
    assert len(body["upcoming_lessons"]) >= 1


def test_lesson_filters(client):
    _register(client)
    sid = client.post("/students", json={"name": "Carol", "subject": "Math", "grade": "8"}).json()["id"]
    today = date.today()
    client.post(
        "/lessons",
        json={
            "student_id": sid,
            "lesson_date": today.isoformat(),
            "lesson_time": "12:00",
            "duration_minutes": 45,
            "payment_amount": 40,
            "is_paid": False,
            "notes": "filter-test",
        },
    )
    r = client.get(f"/lessons?student_id={sid}&is_paid=false")
    assert r.status_code == 200
    items = r.json()
    assert all(x["student_id"] == sid and x["is_paid"] is False for x in items)


def test_student_homework_list(client):
    _register(client)
    sid = client.post("/students", json={"name": "Dan", "subject": "Phys", "grade": "10"}).json()["id"]
    lesson = client.post(
        "/lessons",
        json={
            "student_id": sid,
            "lesson_date": date.today().isoformat(),
            "lesson_time": "14:00",
            "duration_minutes": 60,
            "payment_amount": 0,
            "is_paid": True,
        },
    ).json()["lesson"]
    from app.database import get_db

    db_gen = client.app.dependency_overrides[get_db]()
    db = next(db_gen)
    from app.models import Homework

    db.add(Homework(lesson_id=lesson["id"], homework_text="Test homework body"))
    db.commit()

    r = client.get(f"/students/{sid}/homework")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert "Test homework" in data["items"][0]["preview"]


def test_export_import_students(client):
    _register(client)
    exp = client.get("/data/export/students")
    assert exp.status_code == 200
    assert "text/csv" in exp.headers.get("content-type", "")
    assert b"name" in exp.content

    files = {"file": ("students.csv", exp.content, "text/csv")}
    imp = client.post("/data/import/students", files=files)
    assert imp.status_code == 200
    assert imp.json()["updated"] >= 0


def test_board_snapshots_restore(client):
    _register(client)
    board = client.post("/boards", json={"title": "Test"}).json()
    from app.database import get_db

    db_gen = client.app.dependency_overrides[get_db]()
    db = next(db_gen)
    db.add(
        BoardSnapshot(
            board_id=board["id"],
            state_json='{"version":1,"strokes":[{"id":"s1"}],"texts":[],"images":[]}',
        )
    )
    db.commit()
    snap_id = db.query(BoardSnapshot).filter(BoardSnapshot.board_id == board["id"]).first().id

    listed = client.get(f"/boards/{board['id']}/snapshots")
    assert listed.status_code == 200
    assert len(listed.json()) >= 1

    restored = client.post(f"/boards/{board['id']}/snapshots/{snap_id}/restore")
    assert restored.status_code == 200
    assert restored.json()["state_json"]["strokes"]
