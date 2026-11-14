import asyncio
import sqlite3
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

BOOTSTRAP_TOKEN = "identity-test-bootstrap-token-never-use-outside-tests"


def _csrf(response):
    assert response.status_code in {200, 201}, response.text
    return {"X-CSRF-Token": response.json()["csrf_token"]}


def test_teacher_cannot_approve_their_own_note(client, staff):
    admin = client.post(
        "/api/auth/bootstrap",
        headers=staff,
        json={
            "username": "notesadmin",
            "display_name": "Notes Admin",
            "password": "Notes-Admin-Password-2026!",
        },
    )
    assert admin.status_code == 201
    teacher = client.post(
        "/api/admin/users",
        headers=_csrf(admin),
        json={
            "username": "notesteacher",
            "display_name": "Notes Teacher",
            "password": "Notes-Teacher-Initial-2026!",
            "role": "teacher",
        },
    )
    assert teacher.status_code == 201
    login = client.post(
        "/api/auth/login",
        json={"username": "notesteacher", "password": "Notes-Teacher-Initial-2026!"},
    )
    changed = client.post(
        "/api/auth/password",
        headers=_csrf(login),
        json={
            "current_password": "Notes-Teacher-Initial-2026!",
            "new_password": "Notes-Teacher-Private-2026!",
        },
    )
    teacher_csrf = _csrf(changed)
    imported = client.post(
        "/api/admin/documents",
        headers=teacher_csrf,
        data={
            "title": "Review workflow book",
            "grade": "8",
            "subject": "Science",
            "chapter": "Review",
            "license": "Test fixture",
            "source": "Original test fixture",
        },
        files={"file": ("review.txt", b"A note review workflow fixture.", "text/plain")},
    )
    assert imported.status_code == 201
    note = client.post(
        "/api/admin/notes",
        headers=teacher_csrf,
        json={
            "title": "Teacher-authored note",
            "grade": 8,
            "subject": "Science",
            "chapter": "Review",
            "document_id": imported.json()["id"],
            "pages": [{"start": 1, "end": 1}],
            "key_ideas": ["The reviewer must be another staff member."],
        },
    )
    assert note.status_code == 201
    review_path = f"/api/admin/notes/{note.json()['id']}/review"
    assert (
        client.post(review_path, headers=teacher_csrf, json={"status": "in_review"}).status_code
        == 200
    )
    assert (
        client.post(review_path, headers=teacher_csrf, json={"status": "approved"}).status_code
        == 403
    )
    with TestClient(client.app) as admin_client:
        admin_login = admin_client.post(
            "/api/auth/login",
            json={"username": "notesadmin", "password": "Notes-Admin-Password-2026!"},
        )
        approved = admin_client.post(
            review_path,
            headers=_csrf(admin_login),
            json={"status": "approved"},
        )
        assert approved.status_code == 200


def test_bootstrap_roles_persistent_chat_and_assigned_transcripts(tmp_path: Path, stack):
    settings = Settings(
        _env_file=None,
        data_dir=tmp_path,
        ai_enabled=True,
        require_auth=True,
        chat_provider="ollama",
        ollama_base_url="http://ollama.test",
        qdrant_url="http://qdrant.test",
        admin_token=BOOTSTRAP_TOKEN,
    )
    upstream = httpx.AsyncClient(transport=httpx.MockTransport(stack))
    app = create_app(settings, upstream)
    with TestClient(app) as client:
        assert client.get("/api/auth/status").json() == {
            "users_exist": False,
            "authentication_required": True,
        }
        assert client.post("/api/tutor/chat", json={"message": "Explain force"}).status_code == 401
        invalid_bootstrap = client.post(
            "/api/auth/bootstrap",
            headers={"Authorization": "Bearer wrong-token"},
            json={
                "username": "schooladmin",
                "display_name": "School Admin",
                "password": "School-Admin-Test-2026!",
            },
        )
        assert invalid_bootstrap.status_code == 401
        admin = client.post(
            "/api/auth/bootstrap",
            headers={"Authorization": f"Bearer {BOOTSTRAP_TOKEN}"},
            json={
                "username": "schooladmin",
                "display_name": "School Admin",
                "password": "School-Admin-Test-2026!",
            },
        )
        assert admin.status_code == 201
        assert admin.json()["user"]["role"] == "admin"
        assert admin.json()["user"]["must_change_password"] is False
        admin_csrf = _csrf(admin)
        teacher1 = client.post(
            "/api/admin/users",
            headers=admin_csrf,
            json={
                "username": "teacher1",
                "display_name": "Teacher One",
                "password": "Teacher-One-Temporary-2026!",
                "role": "teacher",
            },
        )
        teacher2 = client.post(
            "/api/admin/users",
            headers=admin_csrf,
            json={
                "username": "teacher2",
                "display_name": "Teacher Two",
                "password": "Teacher-Two-Temporary-2026!",
                "role": "teacher",
            },
        )
        assert teacher1.status_code == teacher2.status_code == 201
        assert teacher1.json()["must_change_password"] is True
        assert (
            client.post(
                "/api/auth/bootstrap",
                headers={"Authorization": f"Bearer {BOOTSTRAP_TOKEN}"},
                json={
                    "username": "otheradmin",
                    "display_name": "Other Admin",
                    "password": "Other-Admin-Temporary-2026!",
                },
            ).status_code
            == 409
        )

        assert client.post("/api/auth/logout", headers=admin_csrf).status_code == 204
        token_only = client.get(
            "/api/admin/index-status", headers={"Authorization": f"Bearer {BOOTSTRAP_TOKEN}"}
        )
        assert token_only.status_code == 401

        teacher_login = client.post(
            "/api/auth/login",
            json={"username": "teacher1", "password": "Teacher-One-Temporary-2026!"},
        )
        assert teacher_login.status_code == 200
        assert teacher_login.json()["user"]["must_change_password"] is True
        assert client.get("/api/teacher/dashboard").status_code == 403
        teacher_csrf = _csrf(teacher_login)
        password_changed = client.post(
            "/api/auth/password",
            headers=teacher_csrf,
            json={
                "current_password": "Teacher-One-Temporary-2026!",
                "new_password": "Teacher-One-Private-2026!",
            },
        )
        assert password_changed.status_code == 200
        assert password_changed.json()["user"]["must_change_password"] is False
        teacher_csrf = _csrf(password_changed)

        classroom = client.post(
            "/api/teacher/classes",
            headers=teacher_csrf,
            json={"name": "Grade 8 A", "grade": 8},
        )
        assert classroom.status_code == 201
        class_id = classroom.json()["id"]
        learner = client.post(
            "/api/teacher/students",
            headers=teacher_csrf,
            json={
                "username": "learner1",
                "display_name": "Learner One",
                "password": "Learner-One-Temporary-2026!",
                "grade": 8,
                "class_id": class_id,
            },
        )
        assert learner.status_code == 201
        assert learner.json()["must_change_password"] is True
        assert (
            client.get(f"/api/teacher/classes/{class_id}/students").json()[0]["id"]
            == learner.json()["id"]
        )

        assert client.post("/api/auth/logout", headers=teacher_csrf).status_code == 204
        learner_login = client.post(
            "/api/auth/login",
            json={"username": "learner1", "password": "Learner-One-Temporary-2026!"},
        )
        learner_csrf = _csrf(learner_login)
        assert learner_login.json()["user"]["must_change_password"] is True
        assert client.get("/api/student/dashboard").status_code == 403
        assert client.get("/api/teacher/dashboard").status_code == 403
        changed = client.post(
            "/api/auth/password",
            headers=learner_csrf,
            json={
                "current_password": "Learner-One-Temporary-2026!",
                "new_password": "Learner-One-Private-2026!",
            },
        )
        learner_csrf = _csrf(changed)
        assert client.get("/api/student/dashboard").status_code == 200

        chat_data = {
            "message": "Explain force in one sentence.",
            "grade": 8,
            "subject": "Science",
            "mode": "explain",
        }
        assert client.post("/api/tutor/chat", json=chat_data).status_code == 403
        reply = client.post("/api/tutor/chat", headers=learner_csrf, json=chat_data)
        assert reply.status_code == 200, reply.text
        session_id = reply.json()["session_id"]
        sessions = client.get("/api/account/sessions").json()
        assert len(sessions) == 1 and sessions[0]["id"] == session_id
        transcript = client.get(f"/api/account/sessions/{session_id}")
        assert transcript.status_code == 200
        assert [message["role"] for message in transcript.json()["messages"]] == [
            "user",
            "assistant",
        ]
        assert client.get("/api/teacher/dashboard").status_code == 403

        assert client.post("/api/auth/logout", headers=learner_csrf).status_code == 204
        teacher_login = client.post(
            "/api/auth/login",
            json={"username": "teacher1", "password": "Teacher-One-Private-2026!"},
        )
        teacher_csrf = _csrf(teacher_login)
        class_sessions = client.get(f"/api/teacher/classes/{class_id}/sessions")
        assert class_sessions.status_code == 200
        assert class_sessions.json()[0]["id"] == session_id
        teacher_view = client.get(f"/api/teacher/sessions/{session_id}?class_id={class_id}")
        assert teacher_view.status_code == 200
        with sqlite3.connect(settings.data_dir / "catalog.sqlite3") as db:
            assert db.execute("SELECT count(*) FROM transcript_audit").fetchone()[0] == 2
            assert db.execute("SELECT action FROM transcript_audit ORDER BY action").fetchall() == [
                ("list",),
                ("view",),
            ]

        reset_student = client.post(
            f"/api/teacher/classes/{class_id}/students/{learner.json()['id']}/password",
            headers=teacher_csrf,
            json={"temporary_password": "Learner-Reset-Temporary-2026!"},
        )
        assert reset_student.status_code == 204
        with TestClient(app) as reset_student_client:
            assert (
                reset_student_client.post(
                    "/api/auth/login",
                    json={"username": "learner1", "password": "Learner-One-Private-2026!"},
                ).status_code
                == 401
            )
            learner_reset_login = reset_student_client.post(
                "/api/auth/login",
                json={"username": "learner1", "password": "Learner-Reset-Temporary-2026!"},
            )
            assert learner_reset_login.status_code == 200
            assert learner_reset_login.json()["user"]["must_change_password"] is True
            assert reset_student_client.get("/api/student/dashboard").status_code == 403

        assert client.post("/api/auth/logout", headers=teacher_csrf).status_code == 204
        other_teacher = client.post(
            "/api/auth/login",
            json={"username": "teacher2", "password": "Teacher-Two-Temporary-2026!"},
        )
        other_teacher_csrf = _csrf(other_teacher)
        other_teacher_password = client.post(
            "/api/auth/password",
            headers=other_teacher_csrf,
            json={
                "current_password": "Teacher-Two-Temporary-2026!",
                "new_password": "Teacher-Two-Private-2026!",
            },
        )
        assert other_teacher_password.status_code == 200
        other_teacher_csrf = _csrf(other_teacher_password)
        assert client.get("/api/teacher/dashboard").json()["classes"] == []
        other_class = client.post(
            "/api/teacher/classes",
            headers=other_teacher_csrf,
            json={"name": "Grade 8 B", "grade": 8},
        )
        assert other_class.status_code == 201
        cross_class_enrollment = client.post(
            f"/api/teacher/classes/{other_class.json()['id']}/students",
            headers=other_teacher_csrf,
            json={"student_id": learner.json()["id"]},
        )
        assert cross_class_enrollment.status_code == 422
        assert (
            client.get(f"/api/teacher/sessions/{session_id}?class_id={class_id}").status_code == 404
        )

        assert client.post("/api/auth/logout", headers=other_teacher_csrf).status_code == 204
        admin_login = client.post(
            "/api/auth/login",
            json={"username": "schooladmin", "password": "School-Admin-Test-2026!"},
        )
        admin_csrf = _csrf(admin_login)
        audit = client.get("/api/admin/transcript-audit")
        assert audit.status_code == 200
        assert sorted(item["action"] for item in audit.json()) == ["list", "view"]

        with TestClient(app) as teacher_audit_client:
            teacher_session = teacher_audit_client.post(
                "/api/auth/login",
                json={"username": "teacher1", "password": "Teacher-One-Private-2026!"},
            )
            assert teacher_session.status_code == 200
            assert (
                client.patch(
                    f"/api/admin/users/{learner.json()['id']}",
                    headers=admin_csrf,
                    json={"disabled": True},
                ).status_code
                == 200
            )
            disabled_teacher_sessions = teacher_audit_client.get(
                f"/api/teacher/classes/{class_id}/sessions"
            )
            assert disabled_teacher_sessions.json() == []
            assert (
                teacher_audit_client.get(
                    f"/api/teacher/sessions/{session_id}?class_id={class_id}"
                ).status_code
                == 404
            )
            admin_disabled_view = client.get(f"/api/teacher/sessions/{session_id}")
            assert admin_disabled_view.status_code == 200
            assert admin_disabled_view.json()["student_id"] == learner.json()["id"]
            assert any(
                item["action"] == "view" and item["viewer_id"] == admin_login.json()["user"]["id"]
                for item in client.get("/api/admin/transcript-audit").json()
            )
            assert (
                client.patch(
                    f"/api/admin/users/{learner.json()['id']}",
                    headers=admin_csrf,
                    json={"disabled": False},
                ).status_code
                == 200
            )
            restored_learner = next(
                user
                for user in client.get("/api/admin/users").json()
                if user["id"] == learner.json()["id"]
            )
            assert restored_learner["must_change_password"] is True
        target_teacher_id = teacher1.json()["id"]
        reset_teacher = client.post(
            f"/api/admin/users/{target_teacher_id}/password",
            headers=admin_csrf,
            json={"temporary_password": "Teacher-Reset-Temporary-2026!"},
        )
        assert reset_teacher.status_code == 204
        assert (
            client.patch(
                f"/api/admin/users/{admin_login.json()['user']['id']}",
                headers=admin_csrf,
                json={"disabled": True},
            ).status_code
            == 422
        )
        disabled_user_client = TestClient(app)
        active_teacher_login = disabled_user_client.post(
            "/api/auth/login",
            json={"username": "teacher1", "password": "Teacher-Reset-Temporary-2026!"},
        )
        assert active_teacher_login.status_code == 200
        assert disabled_user_client.get("/api/auth/me").status_code == 200
        assert (
            client.patch(
                f"/api/admin/users/{target_teacher_id}",
                headers=admin_csrf,
                json={"disabled": True},
            ).status_code
            == 200
        )
        assert disabled_user_client.get("/api/auth/me").status_code == 401
        assert (
            disabled_user_client.post(
                "/api/auth/login",
                json={"username": "teacher1", "password": "Teacher-Reset-Temporary-2026!"},
            ).status_code
            == 401
        )
        disabled_accounts = client.get("/api/admin/users?include_disabled=true").json()
        assert (
            next(user for user in disabled_accounts if user["id"] == target_teacher_id)["disabled"]
            is True
        )
        disabled_user_client.close()
        assert (
            client.patch(
                f"/api/admin/users/{target_teacher_id}",
                headers=admin_csrf,
                json={"disabled": False},
            ).status_code
            == 200
        )
        with TestClient(app) as restored_user_client:
            restored_login = restored_user_client.post(
                "/api/auth/login",
                json={"username": "teacher1", "password": "Teacher-Reset-Temporary-2026!"},
            )
            assert restored_login.status_code == 200
            assert restored_login.json()["user"]["must_change_password"] is True

    asyncio.run(upstream.aclose())
