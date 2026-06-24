"""Initial Physio Tele-Rehab schema.

Revision ID: 20260624_0001
Revises:
Create Date: 2026-06-24
"""

from __future__ import annotations

from alembic import op

revision = "20260624_0001"
down_revision = None
branch_labels = None
depends_on = None


TABLES_SQL = [
    """CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY,email VARCHAR UNIQUE,hashed_password VARCHAR NOT NULL,full_name VARCHAR,role VARCHAR NOT NULL,is_active BOOLEAN DEFAULT TRUE,phone_number VARCHAR,created_at VARCHAR,clinical_role VARCHAR,email_verified BOOLEAN DEFAULT FALSE)""",
    """CREATE TABLE IF NOT EXISTS patient_profiles (id SERIAL PRIMARY KEY,user_id INTEGER UNIQUE REFERENCES users(id) ON DELETE CASCADE,full_name VARCHAR NOT NULL,date_of_birth VARCHAR,gender VARCHAR,phone VARCHAR,email VARCHAR,address VARCHAR,city VARCHAR,state VARCHAR,country VARCHAR,occupation VARCHAR,language VARCHAR,emergency_name VARCHAR,emergency_phone VARCHAR,emergency_relation VARCHAR,condition VARCHAR,severity VARCHAR,age INTEGER,weight_kg FLOAT,height_cm FLOAT,notes TEXT,therapist_id INTEGER REFERENCES users(id),is_onboarded BOOLEAN DEFAULT FALSE,patient_identifier VARCHAR UNIQUE,created_at TIMESTAMP,patient_status VARCHAR DEFAULT 'registered')""",
    """CREATE TABLE IF NOT EXISTS audit_logs (id SERIAL PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),user_email VARCHAR,action_type VARCHAR NOT NULL,resource_type VARCHAR NOT NULL,resource_id INTEGER,patient_id INTEGER REFERENCES patient_profiles(id),therapist_id INTEGER REFERENCES users(id),assignment_role VARCHAR,description TEXT,changes_detail JSON,timestamp TIMESTAMP,ip_address VARCHAR)""",
    """CREATE TABLE IF NOT EXISTS password_reset_tokens (id SERIAL PRIMARY KEY,identifier VARCHAR NOT NULL,code_hash VARCHAR NOT NULL,expires_at TIMESTAMP NOT NULL,used BOOLEAN DEFAULT FALSE,created_at TIMESTAMP)""",
    """CREATE TABLE IF NOT EXISTS email_verification_tokens (id SERIAL PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,email VARCHAR NOT NULL,code_hash VARCHAR NOT NULL,expires_at TIMESTAMP NOT NULL,used BOOLEAN DEFAULT FALSE,created_at TIMESTAMP)""",
    """CREATE TABLE IF NOT EXISTS email_change_tokens (id SERIAL PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,new_email VARCHAR NOT NULL,code_hash VARCHAR NOT NULL,expires_at TIMESTAMP NOT NULL,used BOOLEAN DEFAULT FALSE,created_at TIMESTAMP)""",
    """CREATE TABLE IF NOT EXISTS therapist_assignments (id SERIAL PRIMARY KEY,patient_id INTEGER NOT NULL REFERENCES patient_profiles(id) ON DELETE CASCADE,therapist_id INTEGER NOT NULL REFERENCES users(id),role VARCHAR NOT NULL,assigned_at TIMESTAMP,assigned_by_id INTEGER NOT NULL REFERENCES users(id),temporary_until TIMESTAMP,is_active BOOLEAN DEFAULT TRUE,deactivated_at TIMESTAMP,deactivation_reason VARCHAR,created_at TIMESTAMP,updated_at TIMESTAMP,primary_therapist_id INTEGER REFERENCES users(id),coverage_start TIMESTAMP,coverage_reason TEXT)""",
    """CREATE TABLE IF NOT EXISTS exercises (id SERIAL PRIMARY KEY,name VARCHAR NOT NULL,description TEXT NOT NULL,condition VARCHAR NOT NULL,target_muscles JSON,body_region VARCHAR,difficulty VARCHAR,is_progression BOOLEAN DEFAULT FALSE,prerequisite_exercise_id INTEGER,equipment_needed JSON,setup_instructions TEXT,reps VARCHAR,sets VARCHAR,duration_seconds INTEGER,rest_seconds INTEGER,frequency_per_week VARCHAR,safety_precautions TEXT,contraindications JSON,video_url VARCHAR,image_url VARCHAR,demonstration_notes TEXT,is_active BOOLEAN DEFAULT TRUE,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
    """CREATE TABLE IF NOT EXISTS clinician_assessments (id SERIAL PRIMARY KEY,patient_id INTEGER REFERENCES patient_profiles(id) ON DELETE CASCADE,therapist_id INTEGER REFERENCES users(id),assessment_type VARCHAR,clinical_note TEXT,subjective TEXT,objective TEXT,assessment TEXT,plan TEXT,created_by VARCHAR,created_at TIMESTAMP,range_of_motion TEXT,muscle_strength TEXT,balance TEXT,gait TEXT,functional_testing TEXT,clinical_diagnosis TEXT,outcome_measures TEXT,follow_up_recommendation TEXT)""",
    """CREATE TABLE IF NOT EXISTS exercise_plans (id SERIAL PRIMARY KEY,patient_id INTEGER NOT NULL REFERENCES patient_profiles(id) ON DELETE CASCADE,therapist_id INTEGER NOT NULL REFERENCES users(id),assessment_id INTEGER REFERENCES clinician_assessments(id),title VARCHAR NOT NULL,diagnosis_summary TEXT,clinical_notes TEXT,plan_notes TEXT,frequency_per_week INTEGER,duration_weeks INTEGER,sessions_per_day INTEGER,start_date TIMESTAMP,end_date TIMESTAMP,progression_notes TEXT,progression_criteria TEXT,patient_specific_modifications JSON,goals JSON,is_active BOOLEAN DEFAULT TRUE,is_completed BOOLEAN DEFAULT FALSE,completion_date TIMESTAMP,precautions TEXT,contraindications JSON,created_at TIMESTAMP,updated_at TIMESTAMP,exercise_prescriptions JSON,daily_schedule JSON)""",
    """CREATE TABLE IF NOT EXISTS session_logs (id SERIAL PRIMARY KEY,patient_id INTEGER NOT NULL REFERENCES patient_profiles(id) ON DELETE CASCADE,exercise_id INTEGER NOT NULL REFERENCES exercises(id),exercise_plan_id INTEGER REFERENCES exercise_plans(id) ON DELETE SET NULL,therapist_id INTEGER REFERENCES users(id),observed_by_therapist BOOLEAN DEFAULT FALSE,assignment_role VARCHAR,session_date TIMESTAMP,session_start_time TIMESTAMP,session_end_time TIMESTAMP,target_reps INTEGER,actual_reps INTEGER,repetition_adherence FLOAT,form_score FLOAT DEFAULT 0,form_quality VARCHAR,pain_before INTEGER,pain_after INTEGER,pain_change INTEGER,adherence FLOAT,exercise_completed BOOLEAN DEFAULT TRUE,therapist_notes TEXT,patient_feedback TEXT,ai_observations TEXT,any_adverse_events BOOLEAN DEFAULT FALSE,adverse_event_notes TEXT,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,duration_minutes FLOAT,difficulty VARCHAR)""",
    """CREATE TABLE IF NOT EXISTS appointments (id SERIAL PRIMARY KEY,patient_id INTEGER NOT NULL REFERENCES patient_profiles(id) ON DELETE CASCADE,therapist_id INTEGER NOT NULL REFERENCES users(id),appointment_type VARCHAR DEFAULT 'Tele-Rehabilitation',scheduled_start TIMESTAMP NOT NULL,scheduled_end TIMESTAMP,status VARCHAR DEFAULT 'Pending Approval',reason TEXT,location VARCHAR DEFAULT 'Secure Video',reminder_status VARCHAR DEFAULT 'Pending',waitlist_status VARCHAR DEFAULT 'Not Waitlisted',cancellation_reason TEXT,created_by_user_id INTEGER NOT NULL REFERENCES users(id),created_at TIMESTAMP,updated_at TIMESTAMP)""",
    """CREATE TABLE IF NOT EXISTS appointment_notifications (id SERIAL PRIMARY KEY,appointment_id INTEGER NOT NULL REFERENCES appointments(id) ON DELETE CASCADE,user_id INTEGER NOT NULL REFERENCES users(id),channel VARCHAR NOT NULL,message TEXT NOT NULL,status VARCHAR DEFAULT 'Pending',created_at TIMESTAMP,sent_at TIMESTAMP)""",
    """CREATE TABLE IF NOT EXISTS communication_messages (id SERIAL PRIMARY KEY,patient_id INTEGER NOT NULL REFERENCES patient_profiles(id) ON DELETE CASCADE,sender_id INTEGER NOT NULL REFERENCES users(id),recipient_id INTEGER REFERENCES users(id),message_type VARCHAR DEFAULT 'text',content TEXT,attachment_metadata JSON,created_at TIMESTAMP)""",
    """CREATE TABLE IF NOT EXISTS consent_records (id SERIAL PRIMARY KEY,patient_id INTEGER NOT NULL REFERENCES patient_profiles(id) ON DELETE CASCADE,consent_type VARCHAR NOT NULL,consent_text TEXT NOT NULL,signature TEXT NOT NULL,accepted BOOLEAN DEFAULT TRUE,signed_at TIMESTAMP,ip_address VARCHAR)""",
    """CREATE TABLE IF NOT EXISTS video_consultations (id SERIAL PRIMARY KEY,patient_id INTEGER NOT NULL REFERENCES patient_profiles(id) ON DELETE CASCADE,therapist_id INTEGER NOT NULL REFERENCES users(id),scheduled_start TIMESTAMP NOT NULL,scheduled_end TIMESTAMP,status VARCHAR DEFAULT 'Scheduled',secure_session_url VARCHAR,supervision_notes TEXT,movement_correction_notes TEXT,created_at TIMESTAMP)""",
    """CREATE TABLE IF NOT EXISTS clinical_alerts (id SERIAL PRIMARY KEY,patient_id INTEGER NOT NULL REFERENCES patient_profiles(id) ON DELETE CASCADE,therapist_id INTEGER REFERENCES users(id),alert_type VARCHAR NOT NULL,severity VARCHAR,message TEXT NOT NULL,source VARCHAR,is_resolved BOOLEAN DEFAULT FALSE,resolved_at TIMESTAMP,created_at TIMESTAMP)""",
    """CREATE TABLE IF NOT EXISTS medical_documents (id SERIAL PRIMARY KEY,patient_id INTEGER NOT NULL REFERENCES patient_profiles(id) ON DELETE CASCADE,uploaded_by_user_id INTEGER NOT NULL REFERENCES users(id),document_type VARCHAR NOT NULL,title VARCHAR NOT NULL,description TEXT,file_metadata JSON NOT NULL,created_at TIMESTAMP)""",
    """CREATE TABLE IF NOT EXISTS outcome_measures (id SERIAL PRIMARY KEY,patient_id INTEGER NOT NULL REFERENCES patient_profiles(id) ON DELETE CASCADE,therapist_id INTEGER NOT NULL REFERENCES users(id),measure_name VARCHAR NOT NULL,score FLOAT NOT NULL,max_score FLOAT,interpretation TEXT,measured_at TIMESTAMP,created_at TIMESTAMP)""",
    """CREATE TABLE IF NOT EXISTS objective_progress_metrics (id SERIAL PRIMARY KEY,patient_id INTEGER NOT NULL REFERENCES patient_profiles(id) ON DELETE CASCADE,therapist_id INTEGER NOT NULL REFERENCES users(id),metric_type VARCHAR NOT NULL,metric_name VARCHAR NOT NULL,value FLOAT NOT NULL,unit VARCHAR,notes TEXT,measured_at TIMESTAMP,created_at TIMESTAMP)""",
    """CREATE TABLE IF NOT EXISTS rehabilitation_goals (id SERIAL PRIMARY KEY,patient_id INTEGER NOT NULL REFERENCES patient_profiles(id) ON DELETE CASCADE,therapist_id INTEGER NOT NULL REFERENCES users(id),description TEXT NOT NULL,target_date TIMESTAMP,completion_percentage FLOAT DEFAULT 0,status VARCHAR DEFAULT 'not_started',created_at TIMESTAMP,updated_at TIMESTAMP)""",
    """CREATE TABLE IF NOT EXISTS ai_clinical_suggestions (id SERIAL PRIMARY KEY,patient_id INTEGER NOT NULL REFERENCES patient_profiles(id) ON DELETE CASCADE,therapist_id INTEGER NOT NULL REFERENCES users(id),request_type VARCHAR NOT NULL,source_text TEXT,suggestion TEXT NOT NULL,reviewed_by_therapist BOOLEAN DEFAULT FALSE,approved BOOLEAN DEFAULT FALSE,created_at TIMESTAMP)""",
    """CREATE TABLE IF NOT EXISTS discharge_summaries (id SERIAL PRIMARY KEY,patient_id INTEGER NOT NULL REFERENCES patient_profiles(id) ON DELETE CASCADE,therapist_id INTEGER NOT NULL REFERENCES users(id),final_assessment TEXT NOT NULL,outcome_measures_summary TEXT,achieved_goals TEXT,home_exercise_program TEXT,discharge_summary TEXT NOT NULL,discharged_at TIMESTAMP,created_at TIMESTAMP)""",
    """CREATE TABLE IF NOT EXISTS translation_cache (id SERIAL PRIMARY KEY,source_language VARCHAR NOT NULL,target_language VARCHAR NOT NULL,source_text TEXT NOT NULL,translated_text TEXT NOT NULL,provider VARCHAR NOT NULL,created_at TIMESTAMP,UNIQUE(source_language,target_language,source_text))""",
]

INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS ix_patient_profiles_user_id ON patient_profiles(user_id)",
    "CREATE INDEX IF NOT EXISTS ix_patient_profiles_therapist_id ON patient_profiles(therapist_id)",
    "CREATE INDEX IF NOT EXISTS ix_exercise_plans_patient_id ON exercise_plans(patient_id)",
    "CREATE INDEX IF NOT EXISTS ix_session_logs_patient_id ON session_logs(patient_id)",
    "CREATE INDEX IF NOT EXISTS ix_session_logs_exercise_plan_id ON session_logs(exercise_plan_id)",
    "CREATE INDEX IF NOT EXISTS ix_appointments_patient_id ON appointments(patient_id)",
    "CREATE INDEX IF NOT EXISTS ix_communication_messages_patient_id ON communication_messages(patient_id)",
]

DROP_TABLES = [
    "translation_cache",
    "discharge_summaries",
    "ai_clinical_suggestions",
    "rehabilitation_goals",
    "objective_progress_metrics",
    "outcome_measures",
    "medical_documents",
    "clinical_alerts",
    "video_consultations",
    "consent_records",
    "communication_messages",
    "appointment_notifications",
    "appointments",
    "session_logs",
    "exercise_plans",
    "clinician_assessments",
    "exercises",
    "therapist_assignments",
    "email_change_tokens",
    "email_verification_tokens",
    "password_reset_tokens",
    "audit_logs",
    "patient_profiles",
    "users",
]


def upgrade() -> None:
    for statement in TABLES_SQL:
        op.execute(statement)
    for statement in INDEXES_SQL:
        op.execute(statement)


def downgrade() -> None:
    for table in DROP_TABLES:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
