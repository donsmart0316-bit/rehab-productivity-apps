from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path
import sys
import time

from fastapi.testclient import TestClient


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

if not os.getenv("DATABASE_URL"):
    raise SystemExit("DATABASE_URL is required. Set it to your PostgreSQL connection string before running this test.")

import app.main as main  # noqa: E402


# Keep workflow tests fast and deterministic. Delivery configuration is tested separately.
main.SMTP_HOST = ""
main.SMTP_USERNAME = ""
main.SMTP_PASSWORD = ""
main.TWILIO_ACCOUNT_SID = ""
main.TWILIO_AUTH_TOKEN = ""
main.TWILIO_FROM_PHONE = ""
if os.getenv("PHYSIO_E2E_USE_LIVE_AI", "").lower() not in {"1", "true", "yes"}:
    os.environ["GROQ_API_KEY"] = ""
    os.environ["GROK_API_KEY"] = ""

client = TestClient(main.app)


class Workflow:
    def __init__(self):
        stamp = f"{int(time.time())}"
        self.password = "TestPass123!"
        self.patient_email = f"e2e.patient.{stamp}@example.com"
        self.therapist_email = f"e2e.therapist.{stamp}@example.com"
        self.admin_email = f"e2e.admin.{stamp}@example.com"
        self.patient_token = ""
        self.therapist_token = ""
        self.admin_token = ""
        self.patient_id = None
        self.therapist_user_id = None
        self.exercise_id = None
        self.document_id = None
        self.message_upload_id = None
        self.goal_id = None
        self.ai_suggestion_id = None
        self.appointment_id = None

    def headers(self, role: str) -> dict[str, str]:
        token = {
            "patient": self.patient_token,
            "therapist": self.therapist_token,
            "admin": self.admin_token,
        }[role]
        return {"Authorization": f"Bearer {token}"}

    def request(self, method: str, path: str, *, role: str | None = None, expect: int | tuple[int, ...] = 200, **kwargs):
        headers = kwargs.pop("headers", {})
        if role:
            headers.update(self.headers(role))
        response = client.request(method, path, headers=headers, **kwargs)
        expected = expect if isinstance(expect, tuple) else (expect,)
        if response.status_code not in expected:
            raise AssertionError(f"{method} {path} expected {expected}, got {response.status_code}: {response.text[:800]}")
        if response.content:
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                return response.json()
            return response.content
        return None

    def register_and_login(self):
        consents = ["Telehealth Consent", "Treatment Consent", "Data Privacy Agreement"]
        patient = self.request(
            "POST",
            "/api/auth/register",
            json={"full_name": "John Ibrahim", "email": self.patient_email, "phone_number": f"+1555{int(time.time()) % 10000000:07d}", "password": self.password, "role": "patient", "accepted_consents": consents},
        )
        self.patient_token = patient["access_token"]
        main.run("UPDATE users SET email_verified=TRUE WHERE email=:email", {"email": self.patient_email})
        therapist = self.request(
            "POST",
            "/api/auth/register",
            json={"full_name": "Dr Test Therapist", "email": self.therapist_email, "password": self.password, "role": "therapist", "clinical_role": "Physiotherapist", "accepted_consents": []},
        )
        self.therapist_token = therapist["access_token"]
        self.therapist_user_id = therapist["user_id"]
        admin = self.request(
            "POST",
            "/api/auth/register",
            json={"full_name": "Clinic Admin", "email": self.admin_email, "password": self.password, "role": "admin", "clinical_role": "Clinic Administrator", "accepted_consents": []},
        )
        self.admin_token = admin["access_token"]
        patient_login = self.request("POST", "/api/auth/login", json={"identifier": self.patient_email, "password": self.password})
        therapist_login = self.request("POST", "/api/auth/login", json={"identifier": self.therapist_email, "password": self.password})
        admin_login = self.request("POST", "/api/auth/login", json={"identifier": self.admin_email, "password": self.password})
        assert patient_login["role"] == "patient"
        assert therapist_login["role"] == "therapist"
        assert admin_login["role"] == "admin"

    def patient_setup_and_assignment(self):
        profile = self.request(
            "POST",
            "/api/onboarding/",
            role="patient",
            json={
                "full_name": "John Ibrahim",
                "date_of_birth": "1990-01-01",
                "gender": "Male",
                "phone": "+15550101010",
                "email": self.patient_email,
                "address": "1 Test Street",
                "city": "Lagos",
                "state": "LA",
                "country": "Nigeria",
                "occupation": "Teacher",
                "language": "English",
                "emergency_name": "Jane Ibrahim",
                "emergency_phone": "+15550101011",
                "emergency_relation": "Spouse",
                "condition": "Knee Pain",
                "age": 34,
                "weight_kg": 76,
                "height_cm": 178,
                "notes": "Anterior knee pain with stairs.",
            },
        )
        self.patient_id = profile["id"]
        assert profile["patient_identifier"]
        required = self.request("GET", "/api/consents/required", role="patient")
        assert len(required["required"]) == 3
        for consent in required["required"]:
            self.request("POST", "/api/consents/", role="patient", json={"patient_id": self.patient_id, "consent_type": consent["type"], "consent_text": consent["content"], "signature": "John Ibrahim"})
        status = self.request("GET", f"/api/consents/patient/{self.patient_id}/status", role="patient")
        assert status["complete"] is True
        queue = self.request("GET", "/api/therapist-assignments/unassigned-patients", role="therapist")
        assert any(item["id"] == self.patient_id for item in queue)
        self.request("POST", "/api/therapist-assignments/assign-therapist", role="therapist", json={"patient_id": self.patient_id, "therapist_id": self.therapist_user_id, "role": "primary"})
        patients = self.request("GET", "/api/therapist/patients", role="therapist")
        assert any(item["id"] == self.patient_id for item in patients)

    def plans_sessions_and_progress(self):
        exercise = self.request(
            "POST",
            "/api/exercises/",
            role="therapist",
            json={
                "name": f"E2E Quad Set {int(time.time())}",
                "description": "Isometric quadriceps activation.",
                "condition": "Knee Pain",
                "target_muscles": ["Quadriceps"],
                "body_region": "Knee",
                "difficulty": "Beginner",
                "equipment_needed": [],
                "reps": "10",
                "sets": "3",
                "duration_seconds": 10,
                "safety_precautions": "Stop if sharp pain.",
            },
        )
        self.exercise_id = exercise["id"]
        assessment = self.request(
            "POST",
            "/api/assessments/create",
            role="therapist",
            json={
                "patient_id": self.patient_id,
                "assessment_type": "Initial",
                "subjective": "Pain with stairs.",
                "objective": "Reduced quad control.",
                "range_of_motion": "Full",
                "muscle_strength": "4/5",
                "balance": "Stable",
                "gait": "Mild antalgia",
                "functional_testing": "Step-down painful",
                "clinical_diagnosis": "Patellofemoral pain presentation",
                "assessment": "Needs graded strengthening.",
                "plan": "Strength and symptom monitoring.",
                "outcome_measures": "NPRS, LEFS",
                "follow_up_recommendation": "Weekly review",
                "clinical_note": "Initial SOAP note.",
            },
        )
        assert assessment["patient_id"] == self.patient_id
        recommendation = self.request("POST", "/api/recommendations/plan", role="therapist", json={"condition": "Knee Pain", "assessment_summary": "Anterior knee pain with weak quads", "goals": "stairs", "precautions": "pain-limited"})
        assert recommendation["therapist_review_required"] is True
        assert recommendation["recommendations"]
        plan = self.request(
            "POST",
            "/api/exercise-plans/create",
            role="therapist",
            json={
                "patient_id": self.patient_id,
                "assessment_id": assessment["id"],
                "title": "Knee Strength Starter Plan",
                "diagnosis_summary": "Knee pain",
                "clinical_notes": "Pain-limited quad and hip strengthening.",
                "plan_notes": "Monitor symptoms.",
                "frequency_per_week": 4,
                "duration_weeks": 3,
                "sessions_per_day": 1,
                "progression_notes": "Progress when pain remains below 3/10.",
                "progression_criteria": "Good form and stable symptoms.",
                "goals": ["Stairs with less pain"],
                "precautions": "Stop if swelling increases.",
                "contraindications": [],
                "exercise_prescriptions": [self.exercise_id],
                "daily_schedule": [{"day": "Monday", "exercise_id": self.exercise_id}],
            },
        )
        assert plan["patient_id"] == self.patient_id
        patient_plans = self.request("GET", "/api/exercise-plans/my-plans", role="patient")
        assert any(item["id"] == plan["id"] for item in patient_plans)
        session = self.request("POST", "/api/session-logs/", role="patient", json={"patient_id": self.patient_id, "exercise_id": self.exercise_id, "pain_before": 8, "pain_after": 7, "adherence": 0.4, "patient_feedback": "Hard but completed."})
        assert session["pain_change"] == 1
        progress = self.request("GET", "/api/progress/me", role="patient")
        assert progress["total_sessions"] >= 1

    def communications_and_documents(self):
        therapist_message = self.request("POST", "/api/communications/", role="therapist", json={"patient_id": self.patient_id, "message_type": "text", "content": "Please continue the plan today."})
        patient_message = self.request("POST", "/api/communications/", role="patient", json={"patient_id": self.patient_id, "message_type": "text", "content": "I completed my session."})
        messages = self.request("GET", f"/api/communications/patient/{self.patient_id}", role="patient")
        assert any(item["id"] == therapist_message["id"] for item in messages)
        assert any(item["id"] == patient_message["id"] for item in messages)
        upload = self.request(
            "POST",
            "/api/communications/upload",
            role="patient",
            data={"patient_id": str(self.patient_id), "message_type": "document", "content": "Pain diary attached."},
            files={"file": ("pain-diary.txt", b"Pain diary test file", "text/plain")},
        )
        self.message_upload_id = upload["id"]
        attachment = self.request("GET", f"/api/communications/attachment/{self.message_upload_id}", role="therapist")
        assert b"Pain diary test file" in attachment
        document = self.request(
            "POST",
            "/api/clinical-records/documents/upload",
            role="patient",
            data={"patient_id": str(self.patient_id), "document_type": "Referral", "title": "Referral Letter", "description": "Uploaded by patient."},
            files={"file": ("referral.txt", b"Referral document test file", "text/plain")},
        )
        self.document_id = document["id"]
        docs_for_therapist = self.request("GET", f"/api/clinical-records/documents/patient/{self.patient_id}", role="therapist")
        assert any(item["id"] == self.document_id for item in docs_for_therapist)
        doc_file = self.request("GET", f"/api/clinical-records/documents/{self.document_id}/file", role="therapist")
        assert b"Referral document test file" in doc_file

    def clinical_records_ai_and_discharge(self):
        outcome = self.request("POST", "/api/clinical-records/outcome-measures", role="therapist", json={"patient_id": self.patient_id, "measure_name": "LEFS", "score": 45, "max_score": 80, "interpretation": "Moderate functional limitation; continue strengthening."})
        outcomes_for_patient = self.request("GET", f"/api/clinical-records/outcome-measures/patient/{self.patient_id}", role="patient")
        assert any(item["id"] == outcome["id"] and item["interpretation"] for item in outcomes_for_patient)
        objective = self.request("POST", "/api/clinical-records/objective-progress", role="therapist", json={"patient_id": self.patient_id, "metric_type": "Strength", "metric_name": "Knee Extension", "value": 4, "unit": "MMT", "notes": "Improving"})
        assert objective["patient_id"] == self.patient_id
        goal = self.request("POST", "/api/clinical-records/goals", role="therapist", json={"patient_id": self.patient_id, "description": "Climb stairs with pain under 3/10", "target_date": str((datetime.utcnow() + timedelta(days=30)).date()), "completion_percentage": 10, "status": "in_progress"})
        self.goal_id = goal["id"]
        updated_goal = self.request("PUT", f"/api/clinical-records/goals/{self.goal_id}", role="therapist", json={"completion_percentage": 30, "status": "in_progress"})
        assert updated_goal["completion_percentage"] == 30
        rag_status = self.request("GET", "/api/clinical-records/textbook-rag/status", role="therapist")
        assert "available" in rag_status
        rag_search = self.request("GET", "/api/clinical-records/textbook-rag/search", role="therapist", params={"q": "knee pain exercise progression"})
        assert "results" in rag_search
        ai = self.request("POST", "/api/clinical-records/ai-suggestions", role="therapist", json={"patient_id": self.patient_id, "request_type": "exercise plan review", "source_text": "Knee pain, high pain after exercise, needs graded strengthening."})
        self.ai_suggestion_id = ai["id"]
        reviewed = self.request("PUT", f"/api/clinical-records/ai-suggestions/{self.ai_suggestion_id}/review", role="therapist", json={"approved": True})
        assert reviewed["approved"] is True
        visible_ai = self.request("GET", f"/api/clinical-records/ai-suggestions/patient/{self.patient_id}", role="patient")
        assert any(item["id"] == self.ai_suggestion_id for item in visible_ai)
        discharge = self.request("POST", "/api/clinical-records/discharge", role="therapist", json={"patient_id": self.patient_id, "final_assessment": "Improved", "outcome_measures_summary": "LEFS improved", "achieved_goals": "Partial", "home_exercise_program": "Continue plan", "discharge_summary": "Test discharge summary"})
        assert discharge["patient_id"] == self.patient_id
        visible_discharge = self.request("GET", f"/api/clinical-records/discharge/patient/{self.patient_id}", role="patient")
        assert any(item["id"] == discharge["id"] for item in visible_discharge)

    def appointments_alerts_video_and_admin(self):
        start = (datetime.utcnow() + timedelta(days=2)).isoformat()
        appointment = self.request("POST", "/api/appointments/", role="therapist", json={"patient_id": self.patient_id, "appointment_type": "Tele-Rehabilitation", "scheduled_start": start, "reason": "Review progress"})
        self.appointment_id = appointment["id"]
        patient_appts = self.request("GET", f"/api/appointments/patient/{self.patient_id}", role="patient")
        assert any(item["id"] == self.appointment_id for item in patient_appts)
        therapist_appts = self.request("GET", "/api/appointments/therapist/me", role="therapist")
        assert any(item["id"] == self.appointment_id for item in therapist_appts)
        notifications = self.request("GET", "/api/appointments/notifications/me", role="patient")
        assert notifications
        cancelled = self.request("PUT", f"/api/appointments/{self.appointment_id}", role="patient", json={"status": "Cancelled", "cancellation_reason": "Testing cancellation"})
        assert cancelled["status"] == "Cancelled"
        video = self.request("POST", "/api/video-consultations/", role="therapist", json={"patient_id": self.patient_id, "scheduled_start": start, "scheduled_end": (datetime.utcnow() + timedelta(days=2, hours=1)).isoformat(), "supervision_notes": "Observe squat pattern"})
        assert video["secure_session_url"]
        videos = self.request("GET", f"/api/video-consultations/patient/{self.patient_id}", role="patient")
        assert any(item["id"] == video["id"] for item in videos)
        scanned = self.request("POST", "/api/clinical-alerts/scan", role="therapist")
        assert "alerts_created" in scanned
        alerts = self.request("GET", "/api/clinical-alerts/", role="therapist")
        assert isinstance(alerts, list)
        pose = self.request("POST", "/api/pose-feedback/analyze", role="patient", json={"exercise": "Squat"})
        assert pose["feedback"]
        languages = self.request("GET", "/api/translations/languages")
        assert any(item["name"] == "English" for item in languages)
        translated = self.request("POST", "/api/translations/batch", json={"target_language": "Spanish", "source_language": "English", "texts": ["Patient Dashboard", "Login"]})
        assert "translations" in translated
        audit = self.request("GET", "/api/audit-logs/", role="therapist")
        assert isinstance(audit, list)
        summary = self.request("GET", "/api/admin-research/summary", role="admin")
        assert summary["total_patients"] >= 1
        workload = self.request("GET", "/api/admin-research/therapist-workload", role="admin")
        assert isinstance(workload, list)
        recovery = self.request("GET", "/api/admin-research/recovery-statistics", role="admin")
        assert "condition_statistics" in recovery
        export = self.request("GET", "/api/admin-research/deidentified-export", role="admin")
        assert isinstance(export, list)

    def run(self):
        checks = [
            ("auth register/login", self.register_and_login),
            ("patient onboarding, consents, therapist assignment", self.patient_setup_and_assignment),
            ("therapist plan builder, patient plan, session log, progress", self.plans_sessions_and_progress),
            ("messages, attachments, patient documents visible to therapist", self.communications_and_documents),
            ("clinical records, outcome interpretation, AI/RAG, discharge", self.clinical_records_ai_and_discharge),
            ("appointments, video consults, alerts, translation, audit, admin", self.appointments_alerts_video_and_admin),
        ]
        for label, fn in checks:
            fn()
            print(f"PASS: {label}", flush=True)
        print("ALL WORKFLOW CHECKS PASSED", flush=True)


if __name__ == "__main__":
    Workflow().run()
