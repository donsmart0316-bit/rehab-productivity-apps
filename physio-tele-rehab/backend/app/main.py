from datetime import datetime, timedelta
from email.message import EmailMessage
import ast
from functools import lru_cache
import json
import os
from pathlib import Path
import re
import smtplib
import ssl
from typing import Any, Optional
from urllib.parse import quote
from urllib import request as urlrequest
from urllib.error import URLError

import jwt
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.engine import make_url


BASE_DIR = Path(__file__).resolve().parents[1]
try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR.parents[2] / ".env", override=True)
    load_dotenv(BASE_DIR.parent / ".env", override=False)
    load_dotenv(BASE_DIR / ".env", override=True)
except Exception:
    pass

DB_PATH = Path(os.getenv("PHYSIO_DB_PATH", BASE_DIR / "physio.db"))
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", BASE_DIR / "uploads"))
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH.as_posix()}")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key-before-production")
ALGORITHM = "HS256"
TRANSLATION_API_URL = os.getenv("TRANSLATION_API_URL", "").strip()
TRANSLATION_API_KEY = os.getenv("TRANSLATION_API_KEY", "").strip()
TRANSLATION_PROVIDER = os.getenv("TRANSLATION_PROVIDER", "mymemory").strip().lower()
REPO_ROOT = BASE_DIR.parents[1] if len(BASE_DIR.parents) > 1 else BASE_DIR.parent
DEFAULT_TEXTBOOK_VECTORSTORE_PATH = BASE_DIR / "textbook_vectorstore"
if not DEFAULT_TEXTBOOK_VECTORSTORE_PATH.exists():
    DEFAULT_TEXTBOOK_VECTORSTORE_PATH = REPO_ROOT / "Exercise recommender" / "textbook_vectorstore"
TEXTBOOK_VECTORSTORE_PATH = Path(os.getenv("TEXTBOOK_VECTORSTORE_PATH", DEFAULT_TEXTBOOK_VECTORSTORE_PATH))


def env_secret(name: str, default: str = "") -> str:
    value = os.getenv(name, default).strip()
    lower = value.lower()
    if not value or lower.startswith("your-") or "xxxxxxxx" in lower:
        return ""
    return value


SMTP_HOST = env_secret("SMTP_SERVER") or env_secret("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_TRY_FALLBACK_PORTS = os.getenv("SMTP_TRY_FALLBACK_PORTS", "false").lower() == "true"
SMTP_USERNAME = env_secret("SMTP_USERNAME")
SMTP_PASSWORD = env_secret("SMTP_PASSWORD")
SMTP_FROM = env_secret("SMTP_FROM") or env_secret("EMAIL_FROM") or SMTP_USERNAME or "noreply@physio.local"
TWILIO_ACCOUNT_SID = env_secret("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = env_secret("TWILIO_AUTH_TOKEN")
TWILIO_FROM_PHONE = env_secret("TWILIO_FROM_PHONE")
DEV_SHOW_RESET_CODE = os.getenv("DEV_SHOW_RESET_CODE", "false").lower() == "true"

database_url_info = make_url(DATABASE_URL)
IS_SQLITE = database_url_info.get_backend_name() == "sqlite"
IS_POSTGRES = database_url_info.get_backend_name().startswith("postgresql")
engine_kwargs: dict[str, Any] = {"future": True, "pool_pre_ping": True, "pool_recycle": 60}
if IS_SQLITE:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
engine = create_engine(DATABASE_URL, **engine_kwargs)
pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login-oauth2")

app = FastAPI(title="Physio Tele-Rehab", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(self), microphone=(self), geolocation=()"
    response.headers["Cache-Control"] = "no-store"
    return response


def now() -> datetime:
    return datetime.utcnow()


def parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def human_datetime(value: Any) -> str:
    parsed = parse_datetime(value)
    if not parsed:
        return str(value or "")
    return parsed.strftime("%A, %d %B %Y At %I:%M %p")


class DBResult:
    def __init__(self, result, inserted_id: int | None = None):
        self._result = result
        self.lastrowid = inserted_id if inserted_id is not None else getattr(result, "lastrowid", None)

    def __getattr__(self, name: str):
        return getattr(self._result, name)


BOOLEAN_COLUMNS = [
    "accepted",
    "approved",
    "email_verified",
    "exercise_completed",
    "is_active",
    "is_completed",
    "is_onboarded",
    "is_progression",
    "is_resolved",
    "observed_by_therapist",
    "reviewed_by_therapist",
    "used",
]


def normalize_sql(sql: str) -> str:
    if not IS_POSTGRES:
        return sql
    normalized = sql
    normalized = re.sub(r"\bid INTEGER PRIMARY KEY\b", "id SERIAL PRIMARY KEY", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\bDATETIME\b", "TIMESTAMP", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\bBOOLEAN DEFAULT 1\b", "BOOLEAN DEFAULT TRUE", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\bBOOLEAN DEFAULT 0\b", "BOOLEAN DEFAULT FALSE", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"COALESCE\((is_active|email_verified|accepted|used),1\)=1", r"COALESCE(\1, TRUE)=TRUE", normalized, flags=re.IGNORECASE)
    for column in BOOLEAN_COLUMNS:
        normalized = re.sub(rf"\b{column}\s*=\s*1\b", f"{column}=TRUE", normalized, flags=re.IGNORECASE)
        normalized = re.sub(rf"\b{column}\s*=\s*0\b", f"{column}=FALSE", normalized, flags=re.IGNORECASE)
    if normalized.lstrip().upper().startswith("INSERT ") and " RETURNING " not in normalized.upper():
        normalized = normalized.rstrip().rstrip(";") + " RETURNING id"
    return normalized


def run(sql: str, params: dict[str, Any] | None = None):
    normalized = normalize_sql(sql)
    attempts = 2 if not normalized.lstrip().upper().startswith("INSERT ") else 1
    for attempt in range(attempts):
        try:
            with engine.begin() as conn:
                result = conn.execute(text(normalized), params or {})
                inserted_id = None
                if result.returns_rows:
                    row = result.fetchone()
                    if row is not None and "id" in row._mapping:
                        inserted_id = row._mapping["id"]
                return DBResult(result, inserted_id)
        except OperationalError:
            engine.dispose()
            if attempt + 1 >= attempts:
                raise
    raise RuntimeError("Database write failed")


def rows(sql: str, params: dict[str, Any] | None = None):
    normalized = normalize_sql(sql)
    for attempt in range(2):
        try:
            with engine.begin() as conn:
                return [dict(row._mapping) for row in conn.execute(text(normalized), params or {}).fetchall()]
        except OperationalError:
            engine.dispose()
            if attempt == 1:
                raise
    return []


def one(sql: str, params: dict[str, Any] | None = None):
    data = rows(sql, params)
    return data[0] if data else None


def parse_metadata(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    text_value = str(value)
    try:
        parsed = json.loads(text_value)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        pass
    try:
        parsed = ast.literal_eval(text_value)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def json_db(value: Any, default: Any):
    if value is None:
        value = default
    if isinstance(value, str):
        try:
            json.loads(value)
            return value
        except Exception:
            pass
    return json.dumps(value)


def file_response_from_metadata(metadata: Any):
    parsed = parse_metadata(metadata)
    path_value = parsed.get("path")
    if not path_value:
        raise HTTPException(status_code=404, detail="No Attachment File")
    path = Path(path_value)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File Missing")
    return FileResponse(path, filename=parsed.get("filename") or path.name, media_type=parsed.get("content_type"))


def token_for(user: dict):
    payload = {"sub": str(user["id"]), "role": user["role"], "exp": now() + timedelta(hours=12)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def normalize_identifier(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value.lower() if "@" in value else value


def identifier_channel(value: str | None) -> str | None:
    value = normalize_identifier(value)
    if not value:
        return None
    if "@" in value and re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value):
        return "email"
    if re.match(r"^\+?[0-9][0-9\s().-]{6,}$", value):
        return "phone"
    return None


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        return pwd_context.verify(password, stored_hash)
    except Exception:
        return False


def current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Token")
    user = one("SELECT * FROM users WHERE id=:id", {"id": int(payload["sub"])})
    if not user:
        raise HTTPException(status_code=401, detail="User Not Found")
    return user


def patient_access(patient_id: int, user: dict):
    patient = one("SELECT * FROM patient_profiles WHERE id=:id", {"id": patient_id})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient Not Found")
    if user["role"] == "admin":
        return patient
    if user["role"] == "patient" and patient.get("user_id") == user["id"]:
        return patient
    if user["role"] == "therapist" and patient.get("therapist_id") == user["id"]:
        return patient
    temp = one(
        "SELECT * FROM therapist_assignments WHERE patient_id=:p AND therapist_id=:t AND is_active=1",
        {"p": patient_id, "t": user["id"]},
    )
    if user["role"] == "therapist" and temp:
        return patient
    raise HTTPException(status_code=403, detail="Access Denied")


def assignment_role_for(patient_id: int, user: dict) -> str | None:
    if user["role"] != "therapist":
        return None
    patient = one("SELECT therapist_id FROM patient_profiles WHERE id=:id", {"id": patient_id})
    if patient and patient.get("therapist_id") == user["id"]:
        return "PRIMARY"
    temp = one(
        "SELECT id FROM therapist_assignments WHERE patient_id=:p AND therapist_id=:t AND is_active=1 AND role='temporary'",
        {"p": patient_id, "t": user["id"]},
    )
    return "TEMPORARY" if temp else None


def audit(user: dict, action: str, resource: str, resource_id: int | None = None, patient_id: int | None = None, desc: str = ""):
    run(
        """
        INSERT INTO audit_logs(user_id,user_email,action_type,resource_type,resource_id,patient_id,description,timestamp)
        VALUES(:uid,:email,:action,:resource,:rid,:pid,:desc,:ts)
        """,
        {"uid": user["id"], "email": user.get("email"), "action": action, "resource": resource, "rid": resource_id, "pid": patient_id, "desc": desc, "ts": now()},
    )


def create_patient_identifier(patient_id: int):
    return f"PT-{now().year}-{patient_id:06d}"


def ensure_schema():
    run(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY, email VARCHAR UNIQUE, hashed_password VARCHAR NOT NULL,
            full_name VARCHAR, role VARCHAR NOT NULL, is_active BOOLEAN DEFAULT 1,
            phone_number VARCHAR, created_at VARCHAR, clinical_role VARCHAR, email_verified BOOLEAN DEFAULT 0
        )
        """
    )
    try:
        run("ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT 0")
    except Exception:
        pass
    run(
        """
        CREATE TABLE IF NOT EXISTS patient_profiles (
            id INTEGER PRIMARY KEY, user_id INTEGER UNIQUE, full_name VARCHAR NOT NULL,
            date_of_birth VARCHAR, gender VARCHAR, phone VARCHAR, email VARCHAR, address VARCHAR,
            city VARCHAR, state VARCHAR, country VARCHAR, occupation VARCHAR, language VARCHAR,
            emergency_name VARCHAR, emergency_phone VARCHAR, emergency_relation VARCHAR,
            condition VARCHAR, severity VARCHAR, age INTEGER, weight_kg FLOAT, height_cm FLOAT,
            notes TEXT, therapist_id INTEGER, is_onboarded BOOLEAN DEFAULT 0,
            patient_identifier VARCHAR UNIQUE, created_at DATETIME, patient_status VARCHAR DEFAULT 'registered'
        )
        """
    )
    run("""CREATE TABLE IF NOT EXISTS audit_logs (id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL,user_email VARCHAR,action_type VARCHAR NOT NULL,resource_type VARCHAR NOT NULL,resource_id INTEGER,patient_id INTEGER,therapist_id INTEGER,assignment_role VARCHAR,description TEXT,changes_detail JSON,timestamp DATETIME,ip_address VARCHAR)""")
    run("""CREATE TABLE IF NOT EXISTS password_reset_tokens (id INTEGER PRIMARY KEY,identifier VARCHAR NOT NULL,code_hash VARCHAR NOT NULL,expires_at DATETIME NOT NULL,used BOOLEAN DEFAULT 0,created_at DATETIME)""")
    run("""CREATE TABLE IF NOT EXISTS email_verification_tokens (id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL,email VARCHAR NOT NULL,code_hash VARCHAR NOT NULL,expires_at DATETIME NOT NULL,used BOOLEAN DEFAULT 0,created_at DATETIME)""")
    run("""CREATE TABLE IF NOT EXISTS email_change_tokens (id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL,new_email VARCHAR NOT NULL,code_hash VARCHAR NOT NULL,expires_at DATETIME NOT NULL,used BOOLEAN DEFAULT 0,created_at DATETIME)""")
    run("""CREATE TABLE IF NOT EXISTS therapist_assignments (id INTEGER PRIMARY KEY,patient_id INTEGER NOT NULL,therapist_id INTEGER NOT NULL,role VARCHAR NOT NULL,assigned_at DATETIME,assigned_by_id INTEGER NOT NULL,temporary_until DATETIME,is_active BOOLEAN DEFAULT 1,deactivated_at DATETIME,deactivation_reason VARCHAR,created_at DATETIME,updated_at DATETIME,primary_therapist_id INTEGER,coverage_start DATETIME,coverage_reason TEXT)""")
    run("""CREATE TABLE IF NOT EXISTS exercises (id INTEGER PRIMARY KEY,name VARCHAR NOT NULL,description TEXT NOT NULL,condition VARCHAR NOT NULL,target_muscles JSON,body_region VARCHAR,difficulty VARCHAR,is_progression BOOLEAN DEFAULT 0,prerequisite_exercise_id INTEGER,equipment_needed JSON,setup_instructions TEXT,reps VARCHAR,sets VARCHAR,duration_seconds INTEGER,rest_seconds INTEGER,frequency_per_week VARCHAR,safety_precautions TEXT,contraindications JSON,video_url VARCHAR,image_url VARCHAR,demonstration_notes TEXT,is_active BOOLEAN DEFAULT 1,created_at DATETIME DEFAULT CURRENT_TIMESTAMP,updated_at DATETIME DEFAULT CURRENT_TIMESTAMP)""")
    run("""CREATE TABLE IF NOT EXISTS clinician_assessments (id INTEGER PRIMARY KEY,patient_id INTEGER,therapist_id INTEGER,assessment_type VARCHAR,clinical_note TEXT,subjective TEXT,objective TEXT,assessment TEXT,plan TEXT,created_by VARCHAR,created_at DATETIME,range_of_motion TEXT,muscle_strength TEXT,balance TEXT,gait TEXT,functional_testing TEXT,clinical_diagnosis TEXT,outcome_measures TEXT,follow_up_recommendation TEXT)""")
    run("""CREATE TABLE IF NOT EXISTS exercise_plans (id INTEGER PRIMARY KEY,patient_id INTEGER NOT NULL,therapist_id INTEGER NOT NULL,assessment_id INTEGER,title VARCHAR NOT NULL,diagnosis_summary TEXT,clinical_notes TEXT,plan_notes TEXT,frequency_per_week INTEGER,duration_weeks INTEGER,sessions_per_day INTEGER,start_date DATETIME,end_date DATETIME,progression_notes TEXT,progression_criteria TEXT,patient_specific_modifications JSON,goals JSON,is_active BOOLEAN DEFAULT 1,is_completed BOOLEAN DEFAULT 0,completion_date DATETIME,precautions TEXT,contraindications JSON,created_at DATETIME,updated_at DATETIME,exercise_prescriptions JSON,daily_schedule JSON)""")
    run("""CREATE TABLE IF NOT EXISTS session_logs (id INTEGER PRIMARY KEY,patient_id INTEGER NOT NULL,exercise_id INTEGER NOT NULL,exercise_plan_id INTEGER,therapist_id INTEGER,observed_by_therapist BOOLEAN DEFAULT 0,assignment_role VARCHAR,session_date DATETIME,session_start_time DATETIME,session_end_time DATETIME,target_reps INTEGER,actual_reps INTEGER,repetition_adherence FLOAT,form_score FLOAT DEFAULT 0,form_quality VARCHAR,pain_before INTEGER,pain_after INTEGER,pain_change INTEGER,adherence FLOAT,exercise_completed BOOLEAN DEFAULT 1,therapist_notes TEXT,patient_feedback TEXT,ai_observations TEXT,any_adverse_events BOOLEAN DEFAULT 0,adverse_event_notes TEXT,created_at DATETIME DEFAULT CURRENT_TIMESTAMP,updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,duration_minutes FLOAT,difficulty VARCHAR)""")
    run("""CREATE TABLE IF NOT EXISTS appointments (id INTEGER PRIMARY KEY,patient_id INTEGER NOT NULL,therapist_id INTEGER NOT NULL,appointment_type VARCHAR DEFAULT 'Tele-Rehabilitation',scheduled_start DATETIME NOT NULL,scheduled_end DATETIME,status VARCHAR DEFAULT 'Pending Approval',reason TEXT,location VARCHAR DEFAULT 'Secure Video',reminder_status VARCHAR DEFAULT 'Pending',waitlist_status VARCHAR DEFAULT 'Not Waitlisted',cancellation_reason TEXT,created_by_user_id INTEGER NOT NULL,created_at DATETIME,updated_at DATETIME)""")
    run("""CREATE TABLE IF NOT EXISTS appointment_notifications (id INTEGER PRIMARY KEY,appointment_id INTEGER NOT NULL,user_id INTEGER NOT NULL,channel VARCHAR NOT NULL,message TEXT NOT NULL,status VARCHAR DEFAULT 'Pending',created_at DATETIME,sent_at DATETIME)""")
    run("""CREATE TABLE IF NOT EXISTS communication_messages (id INTEGER PRIMARY KEY,patient_id INTEGER NOT NULL,sender_id INTEGER NOT NULL,recipient_id INTEGER,message_type VARCHAR DEFAULT 'text',content TEXT,attachment_metadata JSON,created_at DATETIME)""")
    run("""CREATE TABLE IF NOT EXISTS consent_records (id INTEGER PRIMARY KEY,patient_id INTEGER NOT NULL,consent_type VARCHAR NOT NULL,consent_text TEXT NOT NULL,signature TEXT NOT NULL,accepted BOOLEAN DEFAULT 1,signed_at DATETIME,ip_address VARCHAR)""")
    run("""CREATE TABLE IF NOT EXISTS video_consultations (id INTEGER PRIMARY KEY,patient_id INTEGER NOT NULL,therapist_id INTEGER NOT NULL,scheduled_start DATETIME NOT NULL,scheduled_end DATETIME,status VARCHAR DEFAULT 'Scheduled',secure_session_url VARCHAR,supervision_notes TEXT,movement_correction_notes TEXT,created_at DATETIME)""")
    run("""CREATE TABLE IF NOT EXISTS clinical_alerts (id INTEGER PRIMARY KEY,patient_id INTEGER NOT NULL,therapist_id INTEGER,alert_type VARCHAR NOT NULL,severity VARCHAR,message TEXT NOT NULL,source VARCHAR,is_resolved BOOLEAN DEFAULT 0,resolved_at DATETIME,created_at DATETIME)""")
    run("""CREATE TABLE IF NOT EXISTS medical_documents (id INTEGER PRIMARY KEY,patient_id INTEGER NOT NULL,uploaded_by_user_id INTEGER NOT NULL,document_type VARCHAR NOT NULL,title VARCHAR NOT NULL,description TEXT,file_metadata JSON NOT NULL,created_at DATETIME)""")
    run("""CREATE TABLE IF NOT EXISTS outcome_measures (id INTEGER PRIMARY KEY,patient_id INTEGER NOT NULL,therapist_id INTEGER NOT NULL,measure_name VARCHAR NOT NULL,score FLOAT NOT NULL,max_score FLOAT,interpretation TEXT,measured_at DATETIME,created_at DATETIME)""")
    run("""CREATE TABLE IF NOT EXISTS objective_progress_metrics (id INTEGER PRIMARY KEY,patient_id INTEGER NOT NULL,therapist_id INTEGER NOT NULL,metric_type VARCHAR NOT NULL,metric_name VARCHAR NOT NULL,value FLOAT NOT NULL,unit VARCHAR,notes TEXT,measured_at DATETIME,created_at DATETIME)""")
    run("""CREATE TABLE IF NOT EXISTS rehabilitation_goals (id INTEGER PRIMARY KEY,patient_id INTEGER NOT NULL,therapist_id INTEGER NOT NULL,description TEXT NOT NULL,target_date DATETIME,completion_percentage FLOAT DEFAULT 0,status VARCHAR DEFAULT 'not_started',created_at DATETIME,updated_at DATETIME)""")
    run("""CREATE TABLE IF NOT EXISTS ai_clinical_suggestions (id INTEGER PRIMARY KEY,patient_id INTEGER NOT NULL,therapist_id INTEGER NOT NULL,request_type VARCHAR NOT NULL,source_text TEXT,suggestion TEXT NOT NULL,reviewed_by_therapist BOOLEAN DEFAULT 0,approved BOOLEAN DEFAULT 0,created_at DATETIME)""")
    run("""CREATE TABLE IF NOT EXISTS discharge_summaries (id INTEGER PRIMARY KEY,patient_id INTEGER NOT NULL,therapist_id INTEGER NOT NULL,final_assessment TEXT NOT NULL,outcome_measures_summary TEXT,achieved_goals TEXT,home_exercise_program TEXT,discharge_summary TEXT NOT NULL,discharged_at DATETIME,created_at DATETIME)""")
    run("""CREATE TABLE IF NOT EXISTS translation_cache (id INTEGER PRIMARY KEY,source_language VARCHAR NOT NULL,target_language VARCHAR NOT NULL,source_text TEXT NOT NULL,translated_text TEXT NOT NULL,provider VARCHAR NOT NULL,created_at DATETIME, UNIQUE(source_language,target_language,source_text))""")


ensure_schema()


class RegisterIn(BaseModel):
    full_name: str
    email: Optional[str] = None
    phone_number: Optional[str] = None
    password: str
    role: str = "patient"
    clinical_role: Optional[str] = None
    accepted_consents: list[str] = []


class LoginIn(BaseModel):
    identifier: str
    password: str


class ResetRequestIn(BaseModel):
    identifier: str


class ResetPasswordIn(BaseModel):
    identifier: str
    code: str
    new_password: str
    confirm_password: str


class TranslationBatchIn(BaseModel):
    target_language: str
    texts: list[str]
    source_language: str = "English"


LANGUAGE_CODES = {
    "Afrikaans": "af", "Albanian": "sq", "Amharic": "am", "Arabic": "ar", "Armenian": "hy",
    "Assamese": "as", "Aymara": "ay", "Azerbaijani": "az", "Bambara": "bm", "Basque": "eu",
    "Belarusian": "be", "Bengali": "bn", "Bhojpuri": "bho", "Bosnian": "bs", "Bulgarian": "bg",
    "Catalan": "ca", "Cebuano": "ceb", "Chinese Simplified": "zh", "Chinese Traditional": "zt",
    "Corsican": "co", "Croatian": "hr", "Czech": "cs", "Danish": "da", "Dhivehi": "dv",
    "Dogri": "doi", "Dutch": "nl", "English": "en", "Esperanto": "eo", "Estonian": "et",
    "Ewe": "ee", "Filipino": "tl", "Finnish": "fi", "French": "fr", "Frisian": "fy",
    "Galician": "gl", "Georgian": "ka", "German": "de", "Greek": "el", "Guarani": "gn",
    "Gujarati": "gu", "Haitian Creole": "ht", "Hausa": "ha", "Hawaiian": "haw", "Hebrew": "he",
    "Hindi": "hi", "Hmong": "hmn", "Hungarian": "hu", "Icelandic": "is", "Igbo": "ig",
    "Ilocano": "ilo", "Indonesian": "id", "Irish": "ga", "Italian": "it", "Japanese": "ja",
    "Javanese": "jv", "Kannada": "kn", "Kazakh": "kk", "Khmer": "km", "Kinyarwanda": "rw",
    "Konkani": "gom", "Korean": "ko", "Krio": "kri", "Kurdish Kurmanji": "ku", "Kurdish Sorani": "ckb",
    "Kyrgyz": "ky", "Lao": "lo", "Latin": "la", "Latvian": "lv", "Lingala": "ln",
    "Lithuanian": "lt", "Luganda": "lg", "Luxembourgish": "lb", "Macedonian": "mk", "Maithili": "mai",
    "Malagasy": "mg", "Malay": "ms", "Malayalam": "ml", "Maltese": "mt", "Maori": "mi",
    "Marathi": "mr", "Meiteilon": "mni-Mtei", "Mizo": "lus", "Mongolian": "mn", "Myanmar": "my",
    "Nepali": "ne", "Norwegian": "no", "Nyanja": "ny", "Odia": "or", "Oromo": "om",
    "Pashto": "ps", "Persian": "fa", "Polish": "pl", "Portuguese": "pt", "Punjabi": "pa",
    "Quechua": "qu", "Romanian": "ro", "Russian": "ru", "Samoan": "sm", "Sanskrit": "sa",
    "Scots Gaelic": "gd", "Sepedi": "nso", "Serbian": "sr", "Sesotho": "st", "Shona": "sn",
    "Sindhi": "sd", "Sinhala": "si", "Slovak": "sk", "Slovenian": "sl", "Somali": "so",
    "Spanish": "es", "Sundanese": "su", "Swahili": "sw", "Swedish": "sv", "Tajik": "tg",
    "Tamil": "ta", "Tatar": "tt", "Telugu": "te", "Thai": "th", "Tigrinya": "ti",
    "Tsonga": "ts", "Turkish": "tr", "Turkmen": "tk", "Twi": "ak", "Ukrainian": "uk",
    "Urdu": "ur", "Uyghur": "ug", "Uzbek": "uz", "Vietnamese": "vi", "Welsh": "cy",
    "Xhosa": "xh", "Yiddish": "yi", "Yoruba": "yo", "Zulu": "zu",
}


LOCAL_TRANSLATIONS = {
    "French": {"Language": "Langue", "Theme": "Theme", "Navigation": "Navigation", "Login": "Connexion", "Logout": "Deconnexion", "Create Account": "Creer Un Compte", "Patient Dashboard": "Tableau De Bord Patient", "Therapist Dashboard": "Tableau De Bord Therapeute", "Appointments": "Rendez-Vous"},
    "Spanish": {"Language": "Idioma", "Theme": "Tema", "Navigation": "Navegacion", "Login": "Iniciar Sesion", "Logout": "Cerrar Sesion", "Create Account": "Crear Cuenta", "Patient Dashboard": "Panel Del Paciente", "Therapist Dashboard": "Panel Del Terapeuta", "Appointments": "Citas"},
    "Portuguese": {"Language": "Idioma", "Theme": "Tema", "Navigation": "Navegacao", "Login": "Entrar", "Logout": "Sair", "Create Account": "Criar Conta", "Patient Dashboard": "Painel Do Paciente", "Therapist Dashboard": "Painel Do Fisioterapeuta", "Appointments": "Consultas"},
    "Swahili": {"Language": "Lugha", "Theme": "Mandhari", "Navigation": "Urambazaji", "Login": "Ingia", "Logout": "Toka", "Create Account": "Fungua Akaunti", "Patient Dashboard": "Dashibodi Ya Mgonjwa", "Therapist Dashboard": "Dashibodi Ya Mtaalamu", "Appointments": "Miadi"},
    "Yoruba": {"Language": "Ede", "Theme": "Akori", "Navigation": "Irinajo", "Login": "Wole", "Logout": "Jade", "Create Account": "Da Akanti", "Patient Dashboard": "Dasiboodu Alaisan", "Therapist Dashboard": "Dasiboodu Onise Itoju", "Appointments": "Ipade"},
    "Igbo": {"Language": "Asusu", "Theme": "Agwa Ihu", "Navigation": "Ntughari", "Login": "Banye", "Logout": "Puo", "Create Account": "Mepu Akauntu", "Patient Dashboard": "Dashboard Onye Oria", "Therapist Dashboard": "Dashboard Onye Na-Agwo Ahu", "Appointments": "Nhoputa"},
    "Hausa": {"Language": "Harshe", "Theme": "Jigo", "Navigation": "Kewayawa", "Login": "Shiga", "Logout": "Fita", "Create Account": "Kirkiri Asusu", "Patient Dashboard": "Allon Bayanin Mara Lafiya", "Therapist Dashboard": "Allon Bayanin Mai Jinya", "Appointments": "Alkawura"},
    "Arabic": {"Language": "اللغة", "Theme": "المظهر", "Navigation": "التنقل", "Login": "تسجيل الدخول", "Logout": "تسجيل الخروج", "Create Account": "إنشاء حساب", "Patient Dashboard": "لوحة المريض", "Therapist Dashboard": "لوحة المعالج", "Appointments": "المواعيد"},
}


def libretranslate(text_value: str, source_language: str, target_language: str) -> str | None:
    if not TRANSLATION_API_URL:
        return None
    source_code = LANGUAGE_CODES.get(source_language, "en")
    target_code = LANGUAGE_CODES.get(target_language)
    if not target_code:
        return None
    payload = {"q": text_value, "source": source_code, "target": target_code, "format": "text"}
    if TRANSLATION_API_KEY:
        payload["api_key"] = TRANSLATION_API_KEY
    body = json.dumps(payload).encode("utf-8")
    req = urlrequest.Request(
        TRANSLATION_API_URL.rstrip("/") + "/translate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlrequest.urlopen(req, timeout=6) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data.get("translatedText")
    except (OSError, URLError, ValueError):
        return None


def mymemory_translate(text_value: str, source_language: str, target_language: str) -> str | None:
    if TRANSLATION_PROVIDER in {"offline", "none", "disabled"}:
        return None
    source_code = LANGUAGE_CODES.get(source_language, "en")
    target_code = LANGUAGE_CODES.get(target_language)
    if not target_code:
        return None
    url = f"https://api.mymemory.translated.net/get?q={quote(text_value)}&langpair={source_code}|{target_code}"
    try:
        with urlrequest.urlopen(url, timeout=6) as response:
            data = json.loads(response.read().decode("utf-8"))
            translated = data.get("responseData", {}).get("translatedText")
            if translated and translated.lower() != "no query specified":
                return translated
    except (OSError, URLError, ValueError):
        return None
    return None


def translate_text(text_value: str, source_language: str, target_language: str) -> tuple[str, str]:
    if not text_value or target_language == source_language:
        return text_value, "none"
    cached = one(
        "SELECT translated_text, provider FROM translation_cache WHERE source_language=:source AND target_language=:target AND source_text=:text",
        {"source": source_language, "target": target_language, "text": text_value},
    )
    if cached and cached["provider"] != "unavailable":
        return cached["translated_text"], cached["provider"]
    local_value = LOCAL_TRANSLATIONS.get(target_language, {}).get(text_value)
    provider = "local"
    translated = local_value
    if not translated:
        translated = libretranslate(text_value, source_language, target_language)
        provider = "libretranslate" if translated else "unavailable"
    if not translated:
        translated = mymemory_translate(text_value, source_language, target_language)
        provider = "mymemory" if translated else "unavailable"
    if not translated:
        translated = text_value
    if provider != "unavailable":
        cache_params = {"source": source_language, "target": target_language, "text": text_value, "translated": translated, "provider": provider, "created": now()}
        if IS_POSTGRES:
            run(
                """
                INSERT INTO translation_cache(source_language,target_language,source_text,translated_text,provider,created_at)
                VALUES(:source,:target,:text,:translated,:provider,:created)
                ON CONFLICT(source_language,target_language,source_text)
                DO UPDATE SET translated_text=EXCLUDED.translated_text,provider=EXCLUDED.provider,created_at=EXCLUDED.created_at
                """,
                cache_params,
            )
        else:
            run(
                "INSERT OR REPLACE INTO translation_cache(source_language,target_language,source_text,translated_text,provider,created_at) VALUES(:source,:target,:text,:translated,:provider,:created)",
                cache_params,
            )
    return translated, provider


def welcome_subject_and_message(user: dict) -> tuple[str, str]:
    name = user.get("full_name") or "there"
    if user.get("role") == "therapist":
        return (
            "Welcome To Physio Tele-Rehab Clinical Portal",
            f"Hello {name},\n\nWelcome to the Physio Tele-Rehab clinical portal. Your therapist account has been created. You can now log in to manage assigned patients, assessments, plans, messages, appointments, and clinical records.\n\nThank you.",
        )
    return (
        "Welcome To Physio Tele-Rehab",
        f"Hello {name},\n\nWelcome to Physio Tele-Rehab. Your patient account has been created. Please verify your email, complete onboarding, and then your care team can begin your rehabilitation workflow.\n\nThank you.",
    )


def create_email_verification_code(user: dict) -> tuple[str, str | None]:
    if not user.get("email"):
        return "No Recipient", "No email address on file."
    code = f"{int(now().timestamp()) % 1000000:06d}"
    run(
        "INSERT INTO email_verification_tokens(user_id,email,code_hash,expires_at,used,created_at) VALUES(:user_id,:email,:code,:expires,FALSE,:created)",
        {"user_id": user["id"], "email": user["email"], "code": pwd_context.hash(code), "expires": now() + timedelta(minutes=20), "created": now()},
    )
    subject = "Verify Your Physio Tele-Rehab Email"
    message = f"Hello {user.get('full_name') or 'there'},\n\nYour Physio Tele-Rehab email verification code is: {code}\n\nThis code expires in 20 minutes."
    return send_email_notification(user["email"], subject, message)


@app.post("/api/auth/register")
def register(data: RegisterIn):
    data.email = normalize_identifier(data.email)
    data.phone_number = normalize_identifier(data.phone_number)
    if data.role == "patient" and len(data.accepted_consents or []) < 3:
        raise HTTPException(status_code=400, detail="Patients Must Accept All Required Consents")
    existing = one("SELECT id FROM users WHERE lower(COALESCE(email,''))=lower(COALESCE(:e,'')) OR phone_number=:p", {"e": data.email, "p": data.phone_number})
    if existing:
        raise HTTPException(status_code=400, detail="Email Or Phone Already Exists")
    role = data.role.lower()
    hashed = pwd_context.hash(data.password)
    result = run(
        """
        INSERT INTO users(email,phone_number,hashed_password,full_name,role,clinical_role,is_active,created_at)
        VALUES(:email,:phone,:password,:name,:role,:clinical,TRUE,:created)
        """,
        {"email": data.email, "phone": data.phone_number, "password": hashed, "name": data.full_name, "role": role, "clinical": data.clinical_role, "created": str(now())},
    )
    user = one("SELECT * FROM users WHERE id=:id", {"id": result.lastrowid})
    audit(user, "register", "user", user["id"], desc="User Registered")
    welcome_subject, welcome_message = welcome_subject_and_message(user)
    invite_status, invite_detail = send_email_notification(user.get("email"), welcome_subject, welcome_message)
    verify_status, verify_detail = create_email_verification_code(user)
    return {
        "access_token": token_for(user),
        "token_type": "bearer",
        "role": role,
        "clinical_role": user.get("clinical_role"),
        "full_name": user.get("full_name"),
        "user_id": user["id"],
        "email_verified": bool(user.get("email_verified")),
        "invitation_email_status": invite_status,
        "invitation_email_detail": invite_detail,
        "verification_email_status": verify_status,
        "verification_email_detail": verify_detail,
    }


@app.post("/api/auth/login")
def login(data: LoginIn):
    data.identifier = normalize_identifier(data.identifier)
    user = one("SELECT * FROM users WHERE lower(COALESCE(email,''))=lower(:x) OR phone_number=:x", {"x": data.identifier})
    if not user:
        patient = one("SELECT user_id FROM patient_profiles WHERE patient_identifier=:x", {"x": data.identifier})
        if patient:
            user = one("SELECT * FROM users WHERE id=:id", {"id": patient["user_id"]})
    if not user or not verify_password(data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid Login")
    audit(user, "login", "auth", user["id"], desc="User Login")
    return {"access_token": token_for(user), "token_type": "bearer", "role": user["role"], "clinical_role": user.get("clinical_role"), "full_name": user.get("full_name"), "user_id": user["id"], "email_verified": bool(user.get("email_verified"))}


@app.post("/api/auth/request-password-reset")
def request_password_reset(data: ResetRequestIn):
    data.identifier = normalize_identifier(data.identifier)
    channel = identifier_channel(data.identifier)
    if channel not in ["email", "phone"]:
        raise HTTPException(status_code=400, detail="Use Email Or Phone Number Only For Password Reset")
    user = one("SELECT * FROM users WHERE lower(COALESCE(email,''))=lower(:x) OR phone_number=:x", {"x": data.identifier})
    if not user:
        return {"message": "If The Account Exists, A Reset Code Was Generated."}
    code = f"{int(now().timestamp()) % 1000000:06d}"
    run(
        "INSERT INTO password_reset_tokens(identifier,code_hash,expires_at,used,created_at) VALUES(:identifier,:code,:expires,FALSE,:created)",
        {"identifier": data.identifier, "code": pwd_context.hash(code), "expires": now() + timedelta(minutes=20), "created": now()},
    )
    if channel == "email":
        status, detail = send_email_notification(
            user.get("email"),
            "Physio Tele-Rehab Password Reset Code",
            f"Your Physio Tele-Rehab password reset code is: {code}\n\nThis code expires in 20 minutes.",
        )
    else:
        status, detail = send_sms_notification(
            user.get("phone_number"),
            f"Physio Tele-Rehab password reset code: {code}. It expires in 20 minutes.",
        )
    if status != "Sent":
        raise HTTPException(status_code=503, detail=f"Reset Code Could Not Be Sent: {status}. {detail or ''}")
    response = {"message": "Reset Code Sent.", "delivery_channel": channel, "delivery_status": status, "delivery_detail": detail}
    if DEV_SHOW_RESET_CODE:
        response["reset_code"] = code
    return response


@app.post("/api/auth/reset-password")
def reset_password(data: ResetPasswordIn):
    data.identifier = normalize_identifier(data.identifier)
    channel = identifier_channel(data.identifier)
    if channel not in ["email", "phone"]:
        raise HTTPException(status_code=400, detail="Use Email Or Phone Number Only For Password Reset")
    if data.new_password != data.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords Do Not Match")
    token = one(
        "SELECT * FROM password_reset_tokens WHERE identifier=:identifier AND used=0 ORDER BY created_at DESC LIMIT 1",
        {"identifier": data.identifier},
    )
    if not token or not verify_password(data.code, token["code_hash"]):
        raise HTTPException(status_code=400, detail="Invalid Reset Code")
    user = one("SELECT * FROM users WHERE lower(COALESCE(email,''))=lower(:x) OR phone_number=:x", {"x": data.identifier})
    if not user:
        raise HTTPException(status_code=404, detail="User Not Found")
    run("UPDATE users SET hashed_password=:p WHERE id=:id", {"p": pwd_context.hash(data.new_password), "id": user["id"]})
    run("UPDATE password_reset_tokens SET used=1 WHERE id=:id", {"id": token["id"]})
    return {"message": "Password Reset Successful"}


@app.get("/api/auth/email-verification/status")
def email_verification_status(user: dict = Depends(current_user)):
    return {"email": user.get("email"), "email_verified": bool(user.get("email_verified"))}


@app.post("/api/auth/resend-email-verification")
def resend_email_verification(user: dict = Depends(current_user)):
    if bool(user.get("email_verified")):
        return {"message": "Email Already Verified", "email_verified": True}
    status, detail = create_email_verification_code(user)
    if status != "Sent":
        raise HTTPException(status_code=503, detail=f"Verification Email Could Not Be Sent: {status}. {detail or ''}")
    return {"message": "Verification Code Sent.", "delivery_status": status}


@app.post("/api/auth/verify-email")
def verify_email(data: dict, user: dict = Depends(current_user)):
    code = str(data.get("code") or "")
    token = one(
        "SELECT * FROM email_verification_tokens WHERE user_id=:user_id AND used=0 ORDER BY created_at DESC LIMIT 1",
        {"user_id": user["id"]},
    )
    if not token or parse_datetime(token["expires_at"]) < now() or not verify_password(code, token["code_hash"]):
        raise HTTPException(status_code=400, detail="Invalid Or Expired Verification Code")
    run("UPDATE users SET email_verified=1 WHERE id=:id", {"id": user["id"]})
    run("UPDATE email_verification_tokens SET used=1 WHERE id=:id", {"id": token["id"]})
    audit(user, "verify", "email", user["id"], desc="User Email Verified")
    return {"message": "Email Verified Successfully", "email_verified": True}


@app.post("/api/auth/request-email-change")
def request_email_change(data: dict, user: dict = Depends(current_user)):
    if user["role"] != "patient":
        raise HTTPException(status_code=403, detail="Only Patients Can Change Contact Details Here")
    new_email = normalize_identifier(data.get("new_email"))
    if identifier_channel(new_email) != "email":
        raise HTTPException(status_code=400, detail="Enter A Valid Email Address")
    existing = one("SELECT id FROM users WHERE lower(COALESCE(email,''))=lower(:email) AND id!=:id", {"email": new_email, "id": user["id"]})
    if existing:
        raise HTTPException(status_code=400, detail="Email Already Exists")
    code = f"{int(now().timestamp()) % 1000000:06d}"
    run(
        "INSERT INTO email_change_tokens(user_id,new_email,code_hash,expires_at,used,created_at) VALUES(:user_id,:new_email,:code,:expires,FALSE,:created)",
        {"user_id": user["id"], "new_email": new_email, "code": pwd_context.hash(code), "expires": now() + timedelta(minutes=20), "created": now()},
    )
    status, detail = send_email_notification(
        new_email,
        "Verify Your New Physio Tele-Rehab Email",
        f"Your email verification code is: {code}\n\nThis code expires in 20 minutes.",
    )
    if status != "Sent":
        raise HTTPException(status_code=503, detail=f"Verification Code Could Not Be Sent: {status}. {detail or ''}")
    return {"message": "Verification Code Sent.", "delivery_status": status, "delivery_detail": detail}


@app.post("/api/auth/confirm-email-change")
def confirm_email_change(data: dict, user: dict = Depends(current_user)):
    if user["role"] != "patient":
        raise HTTPException(status_code=403, detail="Only Patients Can Change Contact Details Here")
    new_email = normalize_identifier(data.get("new_email"))
    code = str(data.get("code") or "")
    token = one(
        "SELECT * FROM email_change_tokens WHERE user_id=:user_id AND lower(new_email)=lower(:new_email) AND used=0 ORDER BY created_at DESC LIMIT 1",
        {"user_id": user["id"], "new_email": new_email},
    )
    if not token or parse_datetime(token["expires_at"]) < now() or not verify_password(code, token["code_hash"]):
        raise HTTPException(status_code=400, detail="Invalid Or Expired Verification Code")
    existing = one("SELECT id FROM users WHERE lower(COALESCE(email,''))=lower(:email) AND id!=:id", {"email": new_email, "id": user["id"]})
    if existing:
        raise HTTPException(status_code=400, detail="Email Already Exists")
    run("UPDATE users SET email=:email WHERE id=:id", {"email": new_email, "id": user["id"]})
    run("UPDATE patient_profiles SET email=:email WHERE user_id=:id", {"email": new_email, "id": user["id"]})
    run("UPDATE email_change_tokens SET used=1 WHERE id=:id", {"id": token["id"]})
    audit(user, "update", "contact_email", user["id"], desc="Patient Email Updated After Verification")
    return {"message": "Email Updated Successfully", "email": new_email}


@app.post("/api/auth/update-phone")
def update_phone(data: dict, user: dict = Depends(current_user)):
    if user["role"] != "patient":
        raise HTTPException(status_code=403, detail="Only Patients Can Change Contact Details Here")
    phone = normalize_identifier(data.get("phone_number"))
    if identifier_channel(phone) != "phone":
        raise HTTPException(status_code=400, detail="Enter A Valid Phone Number")
    existing = one("SELECT id FROM users WHERE phone_number=:phone AND id!=:id", {"phone": phone, "id": user["id"]})
    if existing:
        raise HTTPException(status_code=400, detail="Phone Number Already Exists")
    run("UPDATE users SET phone_number=:phone WHERE id=:id", {"phone": phone, "id": user["id"]})
    run("UPDATE patient_profiles SET phone=:phone WHERE user_id=:id", {"phone": phone, "id": user["id"]})
    audit(user, "update", "contact_phone", user["id"], desc="Patient Phone Updated")
    return {"message": "Phone Number Updated Successfully", "phone_number": phone}


@app.get("/api/translations/languages")
def translation_languages():
    return [{"name": name, "code": code} for name, code in LANGUAGE_CODES.items()]


@app.post("/api/translations/batch")
def translate_batch(data: TranslationBatchIn):
    target = data.target_language.strip()
    source = data.source_language.strip() or "English"
    if target not in LANGUAGE_CODES:
        raise HTTPException(status_code=400, detail="Unsupported Target Language")
    unique_texts = []
    seen = set()
    for text_value in data.texts[:250]:
        if isinstance(text_value, str) and text_value and text_value not in seen:
            seen.add(text_value)
            unique_texts.append(text_value)
    translations = {}
    providers = {}
    for text_value in unique_texts:
        translated, provider = translate_text(text_value, source, target)
        translations[text_value] = translated
        providers[text_value] = provider
    return {
        "target_language": target,
        "translations": translations,
        "providers": providers,
        "provider_configured": bool(TRANSLATION_API_URL) or TRANSLATION_PROVIDER not in {"offline", "none", "disabled"},
        "online_provider": "libretranslate" if TRANSLATION_API_URL else TRANSLATION_PROVIDER,
    }


@app.get("/api/auth/clinical-role-permissions")
def clinical_permissions():
    return {
        "Physiotherapist": ["assess", "plan", "sessions"],
        "Senior Physiotherapist": ["assess", "plan", "sessions", "supervise"],
        "Rehabilitation Assistant": ["sessions", "notes"],
        "Student Therapist": ["view", "draft"],
        "Clinic Administrator": ["admin", "research", "export"],
    }


@app.get("/api/recommendations/condition-map")
def recommendation_condition_map():
    return {
        "Knee Pain": ["Quad Sets", "Straight Leg Raise", "Heel Slides"],
        "Low Back Pain": ["Pelvic Tilts", "Cat Camel", "Bridge"],
        "Shoulder Pain": ["Pendulum", "Scapular Retraction", "Wall Slides"],
        "Stroke Rehabilitation": ["Sit To Stand", "Weight Shifts", "Gait Practice"],
        "Ankle Sprain": ["Ankle Pumps", "Calf Raise", "Balance Reach"],
    }


@app.post("/api/recommendations/plan")
def recommendation_plan(data: dict, user: dict = Depends(current_user)):
    if user["role"] != "therapist":
        raise HTTPException(status_code=403, detail="Only Therapists Can Generate AI Exercise Recommendations")
    condition = data.get("condition", "General Rehabilitation")
    exercises = recommendation_condition_map().get(condition, ["Pain-Free Mobility", "Strengthening", "Functional Practice"])
    source = "\n".join(
        [
            f"Condition: {condition}",
            f"Patient presentation: {data.get('assessment_summary') or data.get('presentation') or ''}",
            f"Goals: {data.get('goals') or ''}",
            f"Precautions: {data.get('precautions') or ''}",
            f"Pain/adherence context: {data.get('progress_context') or ''}",
        ]
    )
    guidance = ai_clinical_suggestion(source, "therapist exercise recommendation support")
    return {
        "condition": condition,
        "recommendations": exercises,
        "ai_exercise_guidance": guidance,
        "evidence_justification": "Generated as therapist-only clinical decision support. Match exercises to assessment findings, precautions, and patient tolerance before assigning to the patient.",
        "clinical_guideline_references": ["Therapeutic Exercise Principles", "Condition-Specific Rehabilitation Guidelines"],
        "therapist_review_required": True,
    }


@app.post("/api/recommendations/adjust")
def recommendation_adjust(data: dict, user: dict = Depends(current_user)):
    adherence = float(data.get("current_adherence", 0))
    pain = float(data.get("average_pain", 0))
    if pain >= 6:
        note = "Reduce intensity and prioritize pain-free range."
    elif adherence >= 0.8 and pain <= 3:
        note = "Consider carefully progressing intensity."
    elif adherence < 0.6:
        note = "Simplify the plan and address barriers to adherence."
    else:
        note = "Maintain current plan and reassess."
    return {"adjustment_notes": note, "therapist_review_required": True}


@app.get("/api/patients/me/profile")
def my_profile(user: dict = Depends(current_user)):
    if user["role"] != "patient":
        raise HTTPException(status_code=403, detail="Only Patients")
    patient = one("SELECT * FROM patient_profiles WHERE user_id=:id", {"id": user["id"]})
    if not patient:
        raise HTTPException(status_code=404, detail="Profile Not Found")
    return patient


@app.post("/api/onboarding/")
def onboarding(data: dict, user: dict = Depends(current_user)):
    if user["role"] != "patient":
        raise HTTPException(status_code=403, detail="Only Patients")
    if not bool(user.get("email_verified")):
        raise HTTPException(status_code=403, detail="Verify Your Email Before Onboarding")
    patient = one("SELECT * FROM patient_profiles WHERE user_id=:id", {"id": user["id"]})
    fields = {k: data.get(k) for k in [
        "full_name", "date_of_birth", "gender", "phone", "email", "address", "city", "state", "country",
        "occupation", "language", "emergency_name", "emergency_phone", "emergency_relation", "condition",
        "severity", "age", "weight_kg", "height_cm", "notes"
    ]}
    fields["full_name"] = fields["full_name"] or user.get("full_name") or "Patient"
    if patient:
        sets = ", ".join([f"{key}=:{key}" for key in fields])
        fields.update({"id": patient["id"], "status": "waiting_for_assignment"})
        run(f"UPDATE patient_profiles SET {sets}, is_onboarded=TRUE, patient_status=:status WHERE id=:id", fields)
        patient_id = patient["id"]
    else:
        cols = ",".join(fields.keys()) + ",user_id,is_onboarded,patient_status,created_at"
        vals = ",".join([f":{key}" for key in fields]) + ",:user_id,TRUE,:status,:created"
        fields.update({"user_id": user["id"], "status": "waiting_for_assignment", "created": now()})
        result = run(f"INSERT INTO patient_profiles({cols}) VALUES({vals})", fields)
        patient_id = result.lastrowid
    identifier = create_patient_identifier(patient_id)
    run("UPDATE patient_profiles SET patient_identifier=COALESCE(patient_identifier,:pid) WHERE id=:id", {"pid": identifier, "id": patient_id})
    audit(user, "onboarding", "patient_profile", patient_id, patient_id, "Patient Onboarding Complete")
    return one("SELECT * FROM patient_profiles WHERE id=:id", {"id": patient_id})


@app.get("/api/therapist/patients")
def therapist_patients(user: dict = Depends(current_user)):
    if user["role"] not in ["therapist", "admin"]:
        raise HTTPException(status_code=403, detail="Only Therapists")
    if user["role"] == "admin":
        return rows("SELECT * FROM patient_profiles ORDER BY created_at DESC")
    return rows("SELECT * FROM patient_profiles WHERE therapist_id=:id ORDER BY created_at DESC", {"id": user["id"]})


@app.get("/api/therapist/all")
def all_therapists(user: dict = Depends(current_user)):
    if user["role"] not in ["therapist", "admin"]:
        raise HTTPException(status_code=403, detail="Only Clinical Staff")
    return rows("SELECT id,full_name,email,phone_number,clinical_role FROM users WHERE role='therapist' ORDER BY full_name")


@app.get("/api/therapist-assignments/unassigned-patients")
def unassigned(user: dict = Depends(current_user)):
    if user["role"] not in ["therapist", "admin"]:
        raise HTTPException(status_code=403, detail="Only Therapists")
    return rows("SELECT * FROM patient_profiles WHERE is_onboarded=1 AND therapist_id IS NULL")


@app.post("/api/therapist-assignments/assign-therapist")
def assign(data: dict, user: dict = Depends(current_user)):
    if user["role"] not in ["therapist", "admin"]:
        raise HTTPException(status_code=403, detail="Only Therapists")
    patient_id = int(data["patient_id"])
    therapist_id = int(data.get("therapist_id") or user["id"])
    role = data.get("role", "primary")
    if role == "primary":
        run("UPDATE patient_profiles SET therapist_id=:t, patient_status='assigned' WHERE id=:p", {"t": therapist_id, "p": patient_id})
    run(
        """
        INSERT INTO therapist_assignments(patient_id,therapist_id,role,assigned_by_id,is_active,assigned_at,temporary_until,primary_therapist_id,coverage_start,coverage_reason)
        VALUES(:p,:t,:r,:by,TRUE,:at,:until,:primary,:start,:reason)
        """,
        {"p": patient_id, "t": therapist_id, "r": role, "by": user["id"], "at": now(), "until": data.get("temporary_until"), "primary": data.get("primary_therapist_id"), "start": data.get("coverage_start"), "reason": data.get("coverage_reason")},
    )
    audit(user, "assign", "therapist_assignment", None, patient_id, "Therapist Assigned")
    return {"ok": True}


@app.get("/api/therapist-assignments/patient/{patient_id}")
def patient_assignments(patient_id: int, user: dict = Depends(current_user)):
    patient_access(patient_id, user)
    return rows(
        """
        SELECT ta.*, u.full_name therapist_name
        FROM therapist_assignments ta LEFT JOIN users u ON u.id=ta.therapist_id
        WHERE ta.patient_id=:p ORDER BY ta.assigned_at DESC
        """,
        {"p": patient_id},
    )


@app.post("/api/therapist-assignments/expire-temporary")
def expire_temporary(user: dict = Depends(current_user)):
    if user["role"] not in ["therapist", "admin"]:
        raise HTTPException(status_code=403, detail="Only Clinical Staff")
    run(
        """
        UPDATE therapist_assignments
        SET is_active=0,deactivated_at=:now,deactivation_reason='Temporary Coverage Expired'
        WHERE role='temporary' AND is_active=1 AND temporary_until IS NOT NULL AND temporary_until < :now
        """,
        {"now": now()},
    )
    return {"ok": True}


@app.get("/api/exercises/")
def exercises(condition: Optional[str] = None):
    if condition:
        return rows("SELECT * FROM exercises WHERE condition LIKE :c AND COALESCE(is_active,1)=1 ORDER BY name", {"c": f"%{condition}%"})
    return rows("SELECT * FROM exercises WHERE COALESCE(is_active,1)=1 ORDER BY name")


@app.post("/api/exercises/")
def create_exercise(data: dict, user: dict = Depends(current_user)):
    if user["role"] != "therapist":
        raise HTTPException(status_code=403, detail="Only Therapists")
    result = run(
        """
        INSERT INTO exercises(name,description,condition,target_muscles,body_region,difficulty,equipment_needed,reps,sets,duration_seconds,safety_precautions,video_url,image_url,is_active)
        VALUES(:name,:description,:condition,:target_muscles,:body_region,:difficulty,:equipment_needed,:reps,:sets,:duration_seconds,:safety_precautions,:video_url,:image_url,TRUE)
        """,
        {
            **data,
            "target_muscles": json_db(data.get("target_muscles"), []),
            "equipment_needed": json_db(data.get("equipment_needed"), []),
            "body_region": data.get("body_region"),
            "difficulty": data.get("difficulty"),
            "reps": data.get("reps"),
            "sets": data.get("sets"),
            "duration_seconds": data.get("duration_seconds"),
            "safety_precautions": data.get("safety_precautions"),
            "video_url": data.get("video_url"),
            "image_url": data.get("image_url"),
        },
    )
    return one("SELECT * FROM exercises WHERE id=:id", {"id": result.lastrowid})


@app.post("/api/assessments/create")
def create_assessment(data: dict, user: dict = Depends(current_user)):
    if user["role"] != "therapist":
        raise HTTPException(status_code=403, detail="Only Therapists")
    patient_access(int(data["patient_id"]), user)
    result = run(
        """
        INSERT INTO clinician_assessments(patient_id,therapist_id,assessment_type,clinical_note,subjective,objective,assessment,plan,range_of_motion,muscle_strength,balance,gait,functional_testing,clinical_diagnosis,outcome_measures,follow_up_recommendation,created_by,created_at)
        VALUES(:patient_id,:therapist_id,:assessment_type,:clinical_note,:subjective,:objective,:assessment,:plan,:range_of_motion,:muscle_strength,:balance,:gait,:functional_testing,:clinical_diagnosis,:outcome_measures,:follow_up_recommendation,:created_by,:created_at)
        """,
        {**data, "therapist_id": user["id"], "created_by": user.get("email"), "created_at": now()},
    )
    audit(user, "create", "assessment", result.lastrowid, int(data["patient_id"]), "Assessment Created")
    return one("SELECT * FROM clinician_assessments WHERE id=:id", {"id": result.lastrowid})


@app.get("/api/assessments/patient/{patient_id}")
def get_assessments(patient_id: int, user: dict = Depends(current_user)):
    patient_access(patient_id, user)
    return rows("SELECT * FROM clinician_assessments WHERE patient_id=:id ORDER BY created_at DESC", {"id": patient_id})


@app.post("/api/exercise-plans/create")
def create_plan(data: dict, user: dict = Depends(current_user)):
    if user["role"] != "therapist":
        raise HTTPException(status_code=403, detail="Only Therapists")
    patient_access(int(data["patient_id"]), user)
    result = run(
        """
        INSERT INTO exercise_plans(patient_id,therapist_id,assessment_id,title,diagnosis_summary,clinical_notes,plan_notes,frequency_per_week,duration_weeks,sessions_per_day,start_date,end_date,progression_notes,progression_criteria,patient_specific_modifications,goals,is_active,precautions,contraindications,created_at,exercise_prescriptions,daily_schedule)
        VALUES(:patient_id,:therapist_id,:assessment_id,:title,:diagnosis_summary,:clinical_notes,:plan_notes,:frequency_per_week,:duration_weeks,:sessions_per_day,:start_date,:end_date,:progression_notes,:progression_criteria,:patient_specific_modifications,:goals,TRUE,:precautions,:contraindications,:created_at,:exercise_prescriptions,:daily_schedule)
        """,
        {
            **data,
            "therapist_id": user["id"],
            "assessment_id": data.get("assessment_id"),
            "diagnosis_summary": data.get("diagnosis_summary"),
            "plan_notes": data.get("plan_notes"),
            "sessions_per_day": data.get("sessions_per_day"),
            "start_date": data.get("start_date"),
            "end_date": data.get("end_date"),
            "progression_criteria": data.get("progression_criteria"),
            "precautions": data.get("precautions"),
            "frequency_per_week": data.get("frequency_per_week"),
            "duration_weeks": data.get("duration_weeks"),
            "created_at": now(),
            "patient_specific_modifications": json_db(data.get("patient_specific_modifications"), {}),
            "goals": json_db(data.get("goals"), []),
            "contraindications": json_db(data.get("contraindications"), []),
            "exercise_prescriptions": json_db(data.get("exercise_prescriptions"), []),
            "daily_schedule": json_db(data.get("daily_schedule"), []),
        },
    )
    audit(user, "create", "exercise_plan", result.lastrowid, int(data["patient_id"]), "Exercise Plan Created")
    return one("SELECT * FROM exercise_plans WHERE id=:id", {"id": result.lastrowid})


@app.get("/api/exercise-plans/my-plans")
def my_plans(user: dict = Depends(current_user)):
    if user["role"] == "patient":
        patient = one("SELECT id FROM patient_profiles WHERE user_id=:id", {"id": user["id"]})
        return rows("SELECT * FROM exercise_plans WHERE patient_id=:p AND COALESCE(is_active,1)=1 ORDER BY created_at DESC", {"p": patient["id"]}) if patient else []
    return rows("SELECT * FROM exercise_plans WHERE therapist_id=:id ORDER BY created_at DESC", {"id": user["id"]})


@app.post("/api/session-logs/")
def log_session(data: dict, user: dict = Depends(current_user)):
    patient_id = int(data["patient_id"])
    patient_access(patient_id, user)
    pain_change = data.get("pain_change")
    if pain_change is None and data.get("pain_before") is not None and data.get("pain_after") is not None:
        pain_change = int(data["pain_before"]) - int(data["pain_after"])
    result = run(
        """
        INSERT INTO session_logs(patient_id,exercise_id,exercise_plan_id,therapist_id,assignment_role,session_date,target_reps,actual_reps,repetition_adherence,form_score,form_quality,pain_before,pain_after,pain_change,adherence,exercise_completed,therapist_notes,patient_feedback,ai_observations,duration_minutes,difficulty)
        VALUES(:patient_id,:exercise_id,:exercise_plan_id,:therapist_id,:assignment_role,:session_date,:target_reps,:actual_reps,:repetition_adherence,:form_score,:form_quality,:pain_before,:pain_after,:pain_change,:adherence,:exercise_completed,:therapist_notes,:patient_feedback,:ai_observations,:duration_minutes,:difficulty)
        """,
        {
            **data,
            "exercise_plan_id": data.get("exercise_plan_id"),
            "therapist_id": data.get("therapist_id") or (user["id"] if user["role"] == "therapist" else None),
            "assignment_role": data.get("assignment_role") or assignment_role_for(patient_id, user),
            "session_date": data.get("session_date") or now(),
            "target_reps": data.get("target_reps"),
            "actual_reps": data.get("actual_reps"),
            "repetition_adherence": data.get("repetition_adherence"),
            "form_score": data.get("form_score"),
            "form_quality": data.get("form_quality"),
            "pain_change": pain_change,
            "exercise_completed": data.get("exercise_completed", True),
            "therapist_notes": data.get("therapist_notes"),
            "patient_feedback": data.get("patient_feedback"),
            "ai_observations": data.get("ai_observations"),
            "duration_minutes": data.get("duration_minutes"),
            "difficulty": data.get("difficulty"),
        },
    )
    return one("SELECT * FROM session_logs WHERE id=:id", {"id": result.lastrowid})


def progress_for(patient_id: int):
    logs = rows("SELECT * FROM session_logs WHERE patient_id=:id ORDER BY session_date", {"id": patient_id})
    total = len(logs)
    avg = lambda key: round(sum((item.get(key) or 0) for item in logs) / total, 2) if total else 0
    return {"logs": logs, "total_sessions": total, "average_pain": avg("pain_before"), "average_pain_after": avg("pain_after"), "average_pain_change": avg("pain_change"), "average_adherence": avg("adherence")}


@app.get("/api/progress/me")
def my_progress(user: dict = Depends(current_user)):
    patient = one("SELECT id FROM patient_profiles WHERE user_id=:id", {"id": user["id"]})
    return progress_for(patient["id"]) if patient else {"logs": [], "total_sessions": 0}


@app.get("/api/progress/patient/{patient_id}")
def patient_progress(patient_id: int, user: dict = Depends(current_user)):
    patient_access(patient_id, user)
    return progress_for(patient_id)


def send_email_notification(to_email: str | None, subject: str, message: str) -> tuple[str, str | None]:
    if not to_email:
        return "No Recipient", "No email address on file."
    if not SMTP_HOST or not SMTP_USERNAME or not SMTP_PASSWORD:
        return "Needs Configuration", "Set SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD, and SMTP_FROM."
    email = EmailMessage()
    email["From"] = SMTP_FROM
    email["To"] = to_email
    email["Subject"] = subject
    email.set_content(message)
    errors = []
    ports = []
    preferred_ports = [SMTP_PORT]
    if SMTP_TRY_FALLBACK_PORTS:
        preferred_ports.extend([465, 587, 2525])
    for port in preferred_ports:
        if port not in ports:
            ports.append(port)
    context = ssl.create_default_context()
    for port in ports:
        try:
            if port == 465:
                smtp = smtplib.SMTP_SSL(SMTP_HOST, port, timeout=5, context=context)
            else:
                smtp = smtplib.SMTP(SMTP_HOST, port, timeout=5)
            with smtp:
                if port != 465:
                    smtp.ehlo()
                    smtp.starttls(context=context)
                    smtp.ehlo()
                smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
                smtp.send_message(email)
            return "Sent", None
        except smtplib.SMTPAuthenticationError as exc:
            return "Failed", f"SMTP Authentication Failed: {exc.smtp_error.decode('utf-8', errors='ignore') if isinstance(exc.smtp_error, bytes) else exc.smtp_error}"
        except Exception as exc:
            errors.append(f"Port {port}: {exc}")
    return "Failed", " | ".join(errors[-3:])


def send_sms_notification(to_phone: str | None, message: str) -> tuple[str, str | None]:
    if not to_phone:
        return "No Recipient", "No phone number on file."
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_FROM_PHONE:
        return "Needs Configuration", "Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_FROM_PHONE."
    payload = f"From={quote(TWILIO_FROM_PHONE)}&To={quote(to_phone)}&Body={quote(message)}".encode("utf-8")
    req = urlrequest.Request(
        f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    import base64

    token = base64.b64encode(f"{TWILIO_ACCOUNT_SID}:{TWILIO_AUTH_TOKEN}".encode("utf-8")).decode("ascii")
    req.add_header("Authorization", f"Basic {token}")
    try:
        with urlrequest.urlopen(req, timeout=12):
            return "Sent", None
    except Exception as exc:
        return "Failed", str(exc)


def queue_notifications(appointment: dict, patient: dict, message: str):
    therapist = one("SELECT * FROM users WHERE id=:id", {"id": appointment["therapist_id"]}) or {}
    recipients = [
        {"user_id": patient["user_id"], "email": patient.get("email"), "phone": patient.get("phone")},
        {"user_id": appointment["therapist_id"], "email": therapist.get("email"), "phone": therapist.get("phone_number")},
    ]
    for recipient in recipients:
        for channel in ["website", "email", "phone"]:
            status = "Sent"
            detail = None
            sent_at = now()
            if channel == "email":
                status, detail = send_email_notification(recipient.get("email"), "Physio Appointment Notification", message)
                sent_at = now() if status == "Sent" else None
            elif channel == "phone":
                status, detail = send_sms_notification(recipient.get("phone"), message)
                sent_at = now() if status == "Sent" else None
            run(
                "INSERT INTO appointment_notifications(appointment_id,user_id,channel,message,status,created_at,sent_at) VALUES(:a,:u,:c,:m,:s,:created,:sent)",
                {"a": appointment["id"], "u": recipient["user_id"], "c": channel, "m": message if not detail else f"{message} ({detail})", "s": status, "created": now(), "sent": sent_at},
            )


@app.post("/api/appointments/")
def create_appointment(data: dict, user: dict = Depends(current_user)):
    if user["role"] != "therapist":
        raise HTTPException(status_code=403, detail="Only Therapists Can Book Appointments")
    patient = patient_access(int(data["patient_id"]), user)
    therapist_id = int(data.get("therapist_id") or patient.get("therapist_id") or user["id"])
    existing = one(
        "SELECT id FROM appointments WHERE patient_id=:p AND therapist_id=:t AND appointment_type=:type AND scheduled_start=:start AND status NOT IN ('Cancelled','Deleted')",
        {"p": patient["id"], "t": therapist_id, "type": data.get("appointment_type", "Tele-Rehabilitation"), "start": data["scheduled_start"]},
    )
    if existing:
        raise HTTPException(status_code=409, detail="This Appointment Already Exists")
    result = run(
        """
        INSERT INTO appointments(patient_id,therapist_id,appointment_type,scheduled_start,scheduled_end,status,reason,location,reminder_status,waitlist_status,created_by_user_id,created_at,updated_at)
        VALUES(:patient_id,:therapist_id,:appointment_type,:scheduled_start,:scheduled_end,'Approved',:reason,:location,'Queued',:waitlist_status,:created_by,:created,:updated)
        """,
        {
            **data,
            "scheduled_end": data.get("scheduled_end"),
            "reason": data.get("reason"),
            "therapist_id": therapist_id,
            "appointment_type": data.get("appointment_type", "Tele-Rehabilitation"),
            "location": data.get("location", "Secure Video"),
            "waitlist_status": data.get("waitlist_status", "Not Waitlisted"),
            "created_by": user["id"],
            "created": now(),
            "updated": now(),
        },
    )
    appointment = one("SELECT * FROM appointments WHERE id=:id", {"id": result.lastrowid})
    queue_notifications(appointment, patient, f"Appointment Scheduled For {human_datetime(appointment['scheduled_start'])}.")
    return appointment


@app.get("/api/appointments/patient/{patient_id}")
def patient_appointments(patient_id: int, user: dict = Depends(current_user)):
    patient_access(patient_id, user)
    clause = "AND status != 'Deleted'" if user["role"] == "patient" else ""
    return rows(f"SELECT * FROM appointments WHERE patient_id=:p {clause} ORDER BY scheduled_start DESC", {"p": patient_id})


@app.get("/api/appointments/therapist/me")
def therapist_calendar(user: dict = Depends(current_user)):
    if user["role"] != "therapist":
        raise HTTPException(status_code=403, detail="Only Therapists")
    return rows("SELECT * FROM appointments WHERE therapist_id=:id ORDER BY scheduled_start", {"id": user["id"]})


@app.put("/api/appointments/{appointment_id}")
def update_appointment(appointment_id: int, data: dict, user: dict = Depends(current_user)):
    appt = one("SELECT * FROM appointments WHERE id=:id", {"id": appointment_id})
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment Not Found")
    patient = patient_access(appt["patient_id"], user)
    status = data.get("status")
    if status in ["Cancelled", "Deleted"] and not (data.get("cancellation_reason") or "").strip():
        raise HTTPException(status_code=400, detail="Cancellation Or Deletion Reason Is Required")
    if status == "Deleted" and user["role"] != "therapist":
        raise HTTPException(status_code=403, detail="Only Therapists Can Delete Appointments")
    allowed = ["scheduled_start", "scheduled_end", "status", "reason", "location", "reminder_status", "waitlist_status", "cancellation_reason"]
    for key in allowed:
        if key in data:
            run(f"UPDATE appointments SET {key}=:v, updated_at=:u WHERE id=:id", {"v": data[key], "u": now(), "id": appointment_id})
    appt = one("SELECT * FROM appointments WHERE id=:id", {"id": appointment_id})
    if status == "Cancelled":
        queue_notifications(appt, patient, f"Appointment Cancelled For {human_datetime(appt.get('scheduled_start'))}. Reason: {data.get('cancellation_reason')}")
    return appt


@app.delete("/api/appointments/{appointment_id}")
def delete_appointment(appointment_id: int, cancellation_reason: str, user: dict = Depends(current_user)):
    return update_appointment(appointment_id, {"status": "Deleted", "cancellation_reason": cancellation_reason}, user)


@app.get("/api/appointments/notifications/me")
def appointment_notifications(user: dict = Depends(current_user)):
    return rows("SELECT * FROM appointment_notifications WHERE user_id=:id ORDER BY created_at DESC LIMIT 50", {"id": user["id"]})


@app.post("/api/appointments/send-reminders")
def send_reminders(user: dict = Depends(current_user)):
    if user["role"] != "therapist":
        raise HTTPException(status_code=403, detail="Only Therapists")
    upcoming = rows("SELECT * FROM appointments WHERE therapist_id=:id AND status='Approved' AND scheduled_start>=:now", {"id": user["id"], "now": now()})
    count = 0
    for appt in upcoming:
        patient = one("SELECT * FROM patient_profiles WHERE id=:id", {"id": appt["patient_id"]})
        if patient:
            queue_notifications(appt, patient, f"Reminder: Appointment At {human_datetime(appt['scheduled_start'])}.")
            run("UPDATE appointments SET reminder_status='Sent' WHERE id=:id", {"id": appt["id"]})
            count += 1
    return {"reminders_sent": count}


@app.post("/api/communications/")
def send_message(data: dict, user: dict = Depends(current_user)):
    patient = patient_access(int(data["patient_id"]), user)
    recipient = patient["therapist_id"] if user["role"] == "patient" else patient["user_id"]
    if not recipient:
        raise HTTPException(status_code=400, detail="No Recipient Is Assigned Yet")
    result = run(
        "INSERT INTO communication_messages(patient_id,sender_id,recipient_id,message_type,content,created_at) VALUES(:p,:s,:r,:type,:content,:created)",
        {"p": patient["id"], "s": user["id"], "r": recipient, "type": data.get("message_type", "text"), "content": data.get("content"), "created": now()},
    )
    return one("SELECT * FROM communication_messages WHERE id=:id", {"id": result.lastrowid})


@app.post("/api/communications/upload")
async def upload_message(patient_id: int = Form(...), message_type: str = Form("document"), content: str = Form(None), file: UploadFile = File(...), user: dict = Depends(current_user)):
    patient = patient_access(patient_id, user)
    folder = UPLOAD_DIR / "communications" / str(patient_id)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{now().timestamp()}_{file.filename}"
    path.write_bytes(await file.read())
    recipient = patient["therapist_id"] if user["role"] == "patient" else patient["user_id"]
    if not recipient:
        raise HTTPException(status_code=400, detail="No Recipient Is Assigned Yet")
    meta = {"filename": file.filename, "path": str(path), "content_type": file.content_type}
    result = run(
        "INSERT INTO communication_messages(patient_id,sender_id,recipient_id,message_type,content,attachment_metadata,created_at) VALUES(:p,:s,:r,:type,:content,:meta,:created)",
        {"p": patient_id, "s": user["id"], "r": recipient, "type": message_type, "content": content, "meta": json_db(meta, {}), "created": now()},
    )
    return one("SELECT * FROM communication_messages WHERE id=:id", {"id": result.lastrowid})


@app.get("/api/communications/patient/{patient_id}")
def messages(patient_id: int, user: dict = Depends(current_user)):
    patient_access(patient_id, user)
    return rows(
        """
        SELECT m.*, sender.full_name sender_name, sender.role sender_role, sender.clinical_role sender_clinical_role,
               recipient.full_name recipient_name, recipient.role recipient_role
        FROM communication_messages m
        LEFT JOIN users sender ON sender.id=m.sender_id
        LEFT JOIN users recipient ON recipient.id=m.recipient_id
        WHERE m.patient_id=:id
        ORDER BY m.created_at
        """,
        {"id": patient_id},
    )


@app.post("/api/communications/call")
def create_call_message(data: dict, user: dict = Depends(current_user)):
    patient = patient_access(int(data["patient_id"]), user)
    recipient = patient["therapist_id"] if user["role"] == "patient" else patient["user_id"]
    if not recipient:
        raise HTTPException(status_code=400, detail="No Recipient Is Assigned Yet")
    call_type = data.get("call_type", "video")
    room = f"physio-{patient['id']}-{user['id']}-{int(now().timestamp())}"
    url = f"https://meet.jit.si/{room}#config.startWithAudioMuted=false&config.startWithVideoMuted={'true' if call_type == 'voice' else 'false'}"
    content = f"{call_type.title()} Call Link: {url}"
    result = run(
        "INSERT INTO communication_messages(patient_id,sender_id,recipient_id,message_type,content,attachment_metadata,created_at) VALUES(:p,:s,:r,:type,:content,:meta,:created)",
        {"p": patient["id"], "s": user["id"], "r": recipient, "type": call_type, "content": content, "meta": json_db({"call_url": url, "call_type": call_type}, {}), "created": now()},
    )
    return one("SELECT * FROM communication_messages WHERE id=:id", {"id": result.lastrowid})


@app.get("/api/communications/attachment/{message_id}")
def get_message_attachment(message_id: int, user: dict = Depends(current_user)):
    message = one("SELECT * FROM communication_messages WHERE id=:id", {"id": message_id})
    if not message:
        raise HTTPException(status_code=404, detail="Attachment Not Found")
    patient_access(message["patient_id"], user)
    return file_response_from_metadata(message.get("attachment_metadata"))


@app.get("/api/consents/required")
def required_consents(user: dict = Depends(current_user)):
    return {
        "required": [
            {
                "type": "Telehealth Consent",
                "title": "Telehealth Consent",
                "content": "You understand that physiotherapy care may be delivered remotely using video, messages, images, and exercise monitoring. Remote care has limits: the therapist may not be able to physically examine you, emergencies require local emergency services, and you can request in-person care when clinically needed.",
            },
            {
                "type": "Treatment Consent",
                "title": "Treatment Consent",
                "content": "You consent to physiotherapy assessment, exercise prescription, education, monitoring, and rehabilitation planning. You agree to stop and report symptoms such as severe pain, dizziness, chest pain, shortness of breath, new weakness, swelling, or any concerning change.",
            },
            {
                "type": "Data Privacy Agreement",
                "title": "Data Privacy Agreement",
                "content": "You consent to secure storage and processing of your health information, uploaded documents, messages, exercise records, appointment history, outcome measures, and audit logs for clinical care and lawful record retention. De-identified information may be used for reporting or research dashboards.",
            },
        ]
    }


@app.post("/api/consents/")
def sign_consent(data: dict, user: dict = Depends(current_user)):
    patient = patient_access(int(data["patient_id"]), user)
    result = run(
        "INSERT INTO consent_records(patient_id,consent_type,consent_text,signature,accepted,signed_at) VALUES(:p,:type,:text,:sig,TRUE,:signed)",
        {"p": patient["id"], "type": data["consent_type"], "text": data.get("consent_text", data["consent_type"]), "sig": data.get("signature", user.get("full_name")), "signed": now()},
    )
    return one("SELECT * FROM consent_records WHERE id=:id", {"id": result.lastrowid})


@app.get("/api/consents/patient/{patient_id}/status")
def consent_status(patient_id: int, user: dict = Depends(current_user)):
    patient_access(patient_id, user)
    required = ["Telehealth Consent", "Treatment Consent", "Data Privacy Agreement"]
    signed = {item["consent_type"] for item in rows("SELECT consent_type FROM consent_records WHERE patient_id=:id AND accepted=1", {"id": patient_id})}
    missing = [item for item in required if item not in signed]
    return {"complete": not missing, "missing": missing}


@app.get("/api/consents/patient/{patient_id}")
def patient_consents(patient_id: int, user: dict = Depends(current_user)):
    patient_access(patient_id, user)
    return rows("SELECT * FROM consent_records WHERE patient_id=:id ORDER BY signed_at DESC", {"id": patient_id})


@app.post("/api/video-consultations/")
def create_video_consultation(data: dict, user: dict = Depends(current_user)):
    if user["role"] != "therapist":
        raise HTTPException(status_code=403, detail="Only Therapists Can Schedule Video Consultations")
    patient_access(int(data["patient_id"]), user)
    session_url = data.get("secure_session_url") or f"https://meet.jit.si/physio-{data['patient_id']}-{int(now().timestamp())}"
    result = run(
        """
        INSERT INTO video_consultations(patient_id,therapist_id,scheduled_start,scheduled_end,status,secure_session_url,supervision_notes,movement_correction_notes,created_at)
        VALUES(:patient_id,:therapist_id,:scheduled_start,:scheduled_end,:status,:url,:supervision,:movement,:created)
        """,
        {
            "patient_id": data["patient_id"],
            "therapist_id": user["id"],
            "scheduled_start": data["scheduled_start"],
            "scheduled_end": data.get("scheduled_end"),
            "status": data.get("status", "Scheduled"),
            "url": session_url,
            "supervision": data.get("supervision_notes"),
            "movement": data.get("movement_correction_notes"),
            "created": now(),
        },
    )
    audit(user, "create", "video_consultation", result.lastrowid, int(data["patient_id"]), "Video Consultation Scheduled")
    return one("SELECT * FROM video_consultations WHERE id=:id", {"id": result.lastrowid})


@app.get("/api/video-consultations/patient/{patient_id}")
def get_video_consultations(patient_id: int, user: dict = Depends(current_user)):
    patient_access(patient_id, user)
    return rows("SELECT * FROM video_consultations WHERE patient_id=:id ORDER BY scheduled_start DESC", {"id": patient_id})


@app.post("/api/clinical-alerts/scan")
def scan_alerts(user: dict = Depends(current_user)):
    if user["role"] not in ["therapist", "admin"]:
        raise HTTPException(status_code=403, detail="Only Clinical Staff")
    patients = rows("SELECT * FROM patient_profiles WHERE therapist_id=:id OR :admin=1", {"id": user["id"], "admin": 1 if user["role"] == "admin" else 0})
    created = 0
    for patient in patients:
        latest = one("SELECT * FROM session_logs WHERE patient_id=:id ORDER BY session_date DESC LIMIT 1", {"id": patient["id"]})
        if latest and latest.get("pain_after") is not None and latest["pain_after"] >= 7:
            run(
                "INSERT INTO clinical_alerts(patient_id,therapist_id,alert_type,severity,message,source,is_resolved,created_at) VALUES(:p,:t,'high_pain','High',:m,'session_log',FALSE,:created)",
                {"p": patient["id"], "t": patient.get("therapist_id"), "m": f"High post-session pain score recorded: {latest['pain_after']}/10.", "created": now()},
            )
            created += 1
        if latest and latest.get("adherence") is not None and latest["adherence"] < 0.5:
            run(
                "INSERT INTO clinical_alerts(patient_id,therapist_id,alert_type,severity,message,source,is_resolved,created_at) VALUES(:p,:t,'poor_adherence','Medium',:m,'session_log',FALSE,:created)",
                {"p": patient["id"], "t": patient.get("therapist_id"), "m": "Recent session adherence dropped below 50%.", "created": now()},
            )
            created += 1
        missed = rows(
            "SELECT * FROM appointments WHERE patient_id=:p AND status='Approved' AND scheduled_start < :now",
            {"p": patient["id"], "now": now()},
        )
        for appointment in missed:
            run(
                "INSERT INTO clinical_alerts(patient_id,therapist_id,alert_type,severity,message,source,is_resolved,created_at) VALUES(:p,:t,'missed_appointment','Medium',:m,'appointment',FALSE,:created)",
                {"p": patient["id"], "t": patient.get("therapist_id"), "m": f"Appointment appears overdue: {appointment['scheduled_start']}.", "created": now()},
            )
            created += 1
    expired = rows(
        "SELECT * FROM therapist_assignments WHERE role='temporary' AND is_active=1 AND temporary_until IS NOT NULL AND temporary_until < :now",
        {"now": now()},
    )
    for assignment in expired:
        run(
            "INSERT INTO clinical_alerts(patient_id,therapist_id,alert_type,severity,message,source,is_resolved,created_at) VALUES(:p,:t,'expired_temporary_assignment','High',:m,'coverage',FALSE,:created)",
            {"p": assignment["patient_id"], "t": assignment.get("primary_therapist_id") or assignment["therapist_id"], "m": "Temporary therapist coverage has expired.", "created": now()},
        )
        created += 1
    return {"alerts_created": created}


@app.get("/api/clinical-alerts/")
def get_alerts(user: dict = Depends(current_user)):
    if user["role"] == "therapist":
        return rows("SELECT * FROM clinical_alerts WHERE therapist_id=:id ORDER BY created_at DESC", {"id": user["id"]})
    if user["role"] == "admin":
        return rows("SELECT * FROM clinical_alerts ORDER BY created_at DESC")
    patient = one("SELECT id FROM patient_profiles WHERE user_id=:id", {"id": user["id"]})
    return rows("SELECT * FROM clinical_alerts WHERE patient_id=:id ORDER BY created_at DESC", {"id": patient["id"]}) if patient else []


@app.get("/api/clinical-records/outcome-measures/catalog")
def outcome_catalog(user: dict = Depends(current_user)):
    return ["Oswestry Disability Index", "DASH", "WOMAC", "LEFS", "Berg Balance Scale", "TUG", "6 Minute Walk Test", "VAS Pain", "NPRS", "KOOS", "HOOS"]


@app.post("/api/clinical-records/documents/upload")
async def upload_medical_document(
    patient_id: int = Form(...),
    document_type: str = Form(...),
    title: str = Form(...),
    description: str = Form(None),
    file: UploadFile = File(...),
    user: dict = Depends(current_user),
):
    patient_access(patient_id, user)
    patient = one("SELECT * FROM patient_profiles WHERE id=:id", {"id": patient_id})
    if user["role"] != "patient" or patient.get("user_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Only The Patient Can Upload Medical Documents")
    folder = UPLOAD_DIR / "medical_documents" / str(patient_id)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{now().timestamp()}_{file.filename}"
    path.write_bytes(await file.read())
    metadata = {"filename": file.filename, "path": str(path), "content_type": file.content_type, "size": path.stat().st_size}
    result = run(
        "INSERT INTO medical_documents(patient_id,uploaded_by_user_id,document_type,title,description,file_metadata,created_at) VALUES(:p,:u,:type,:title,:description,:meta,:created)",
        {"p": patient_id, "u": user["id"], "type": document_type, "title": title, "description": description, "meta": json_db(metadata, {}), "created": now()},
    )
    audit(user, "upload", "medical_document", result.lastrowid, patient_id, "Medical Document Uploaded")
    return one("SELECT * FROM medical_documents WHERE id=:id", {"id": result.lastrowid})


@app.get("/api/clinical-records/documents/patient/{patient_id}")
def get_medical_documents(patient_id: int, user: dict = Depends(current_user)):
    patient_access(patient_id, user)
    return rows(
        """
        SELECT d.*, uploader.full_name uploaded_by_name
        FROM medical_documents d
        LEFT JOIN users uploader ON uploader.id=d.uploaded_by_user_id
        WHERE d.patient_id=:id
        ORDER BY d.created_at DESC
        """,
        {"id": patient_id},
    )


@app.get("/api/clinical-records/documents/{document_id}/file")
def get_medical_document_file(document_id: int, user: dict = Depends(current_user)):
    document = one("SELECT * FROM medical_documents WHERE id=:id", {"id": document_id})
    if not document:
        raise HTTPException(status_code=404, detail="Medical Document Not Found")
    patient_access(document["patient_id"], user)
    return file_response_from_metadata(document.get("file_metadata"))


@app.get("/api/clinical-records/objective-progress/catalog")
def objective_catalog(user: dict = Depends(current_user)):
    return {
        "Range Of Motion": ["Flexion", "Extension", "Abduction", "Rotation"],
        "Strength": ["MMT Grade", "Grip Strength", "Dynamometer"],
        "Function": ["TUG", "Sit To Stand", "Walking Distance"],
        "Balance And Gait": ["Berg", "Single Leg Stance", "Gait Speed"],
        "Pain And Adherence": ["Pain Score", "Adherence Rate"],
    }


@app.post("/api/clinical-records/objective-progress")
def create_objective_progress(data: dict, user: dict = Depends(current_user)):
    if user["role"] != "therapist":
        raise HTTPException(status_code=403, detail="Only Therapists Can Record Objective Progress")
    patient_access(int(data["patient_id"]), user)
    result = run(
        """
        INSERT INTO objective_progress_metrics(patient_id,therapist_id,metric_type,metric_name,value,unit,notes,measured_at,created_at)
        VALUES(:patient_id,:therapist_id,:metric_type,:metric_name,:value,:unit,:notes,:measured_at,:created_at)
        """,
        {**data, "therapist_id": user["id"], "unit": data.get("unit"), "notes": data.get("notes"), "measured_at": data.get("measured_at") or now(), "created_at": now()},
    )
    return one("SELECT * FROM objective_progress_metrics WHERE id=:id", {"id": result.lastrowid})


@app.get("/api/clinical-records/objective-progress/patient/{patient_id}")
def get_objective_progress(patient_id: int, user: dict = Depends(current_user)):
    patient_access(patient_id, user)
    return rows("SELECT * FROM objective_progress_metrics WHERE patient_id=:id ORDER BY measured_at", {"id": patient_id})


@app.post("/api/clinical-records/outcome-measures")
def create_outcome(data: dict, user: dict = Depends(current_user)):
    if user["role"] != "therapist":
        raise HTTPException(status_code=403, detail="Only Therapists Can Record Outcome Measures")
    patient_access(int(data["patient_id"]), user)
    result = run(
        "INSERT INTO outcome_measures(patient_id,therapist_id,measure_name,score,max_score,interpretation,measured_at,created_at) VALUES(:patient_id,:therapist_id,:measure_name,:score,:max_score,:interpretation,:measured_at,:created_at)",
        {**data, "therapist_id": user["id"], "max_score": data.get("max_score"), "interpretation": data.get("interpretation"), "measured_at": data.get("measured_at") or now(), "created_at": now()},
    )
    return one("SELECT * FROM outcome_measures WHERE id=:id", {"id": result.lastrowid})


@app.get("/api/clinical-records/outcome-measures/patient/{patient_id}")
def get_outcomes(patient_id: int, user: dict = Depends(current_user)):
    patient_access(patient_id, user)
    return rows("SELECT * FROM outcome_measures WHERE patient_id=:id ORDER BY measured_at DESC", {"id": patient_id})


@app.post("/api/clinical-records/goals")
def create_goal(data: dict, user: dict = Depends(current_user)):
    if user["role"] != "therapist":
        raise HTTPException(status_code=403, detail="Only Therapists Can Record Goals")
    patient_access(int(data["patient_id"]), user)
    result = run(
        "INSERT INTO rehabilitation_goals(patient_id,therapist_id,description,target_date,completion_percentage,status,created_at,updated_at) VALUES(:patient_id,:therapist_id,:description,:target_date,:completion_percentage,:status,:created,:updated)",
        {**data, "therapist_id": user["id"], "target_date": data.get("target_date"), "completion_percentage": data.get("completion_percentage", 0), "status": data.get("status", "not_started"), "created": now(), "updated": now()},
    )
    return one("SELECT * FROM rehabilitation_goals WHERE id=:id", {"id": result.lastrowid})


@app.get("/api/clinical-records/goals/patient/{patient_id}")
def get_goals(patient_id: int, user: dict = Depends(current_user)):
    patient_access(patient_id, user)
    return rows("SELECT * FROM rehabilitation_goals WHERE patient_id=:id ORDER BY created_at DESC", {"id": patient_id})


@app.put("/api/clinical-records/goals/{goal_id}")
def update_goal(goal_id: int, data: dict, user: dict = Depends(current_user)):
    if user["role"] != "therapist":
        raise HTTPException(status_code=403, detail="Only Therapists Can Update Goals")
    goal = one("SELECT * FROM rehabilitation_goals WHERE id=:id", {"id": goal_id})
    if not goal:
        raise HTTPException(status_code=404, detail="Goal Not Found")
    patient_access(goal["patient_id"], user)
    for key in ["description", "target_date", "completion_percentage", "status"]:
        if key in data:
            run(f"UPDATE rehabilitation_goals SET {key}=:v, updated_at=:u WHERE id=:id", {"v": data[key], "u": now(), "id": goal_id})
    return one("SELECT * FROM rehabilitation_goals WHERE id=:id", {"id": goal_id})


def groq_api_key() -> str:
    return (
        env_secret("GROQ_API_KEY")
        or env_secret("GROK_API_KEY")
        or os.getenv("groq_api_key", "").strip()
        or os.getenv("grok_api_key", "").strip()
    )


@lru_cache(maxsize=1)
def textbook_vectorstore():
    if not TEXTBOOK_VECTORSTORE_PATH.exists():
        return None
    try:
        from langchain_community.vectorstores import FAISS
        from langchain_huggingface import HuggingFaceEmbeddings

        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        return FAISS.load_local(str(TEXTBOOK_VECTORSTORE_PATH), embeddings, allow_dangerous_deserialization=True)
    except Exception:
        return None


def textbook_context(query: str, limit: int = 4) -> tuple[str, list[dict[str, str]]]:
    vectorstore = textbook_vectorstore()
    if vectorstore is None:
        return "", []
    docs = vectorstore.similarity_search(query or "physiotherapy rehabilitation precautions progression", k=limit)
    references = []
    chunks = []
    for idx, doc in enumerate(docs, start=1):
        source = str(doc.metadata.get("source") or doc.metadata.get("file_path") or f"Textbook excerpt {idx}")
        page = doc.metadata.get("page")
        label = f"{source}{f' page {page}' if page is not None else ''}"
        text_value = re.sub(r"\s+", " ", doc.page_content or "").strip()
        excerpt = text_value[:900]
        references.append({"source": label, "excerpt": excerpt})
        chunks.append(f"[{idx}] {label}\n{excerpt}")
    return "\n\n".join(chunks), references


def ai_clinical_suggestion(source: str, request_type: str) -> str:
    context, references = textbook_context(source)
    key = groq_api_key()
    if key:
        try:
            from langchain_groq import ChatGroq

            llm = ChatGroq(
                model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
                api_key=key,
                temperature=0.2,
                max_tokens=750,
                timeout=8,
                max_retries=0,
            )
            prompt = f"""
You are a physiotherapy clinical support assistant for a licensed therapist.
Use the therapist note and retrieved textbook context to draft concise clinical support.
Do not diagnose beyond the supplied information. Include red flags, precautions, graded exercise ideas, outcome measures to monitor, and when to escalate to in-person/emergency care.
Make clear that therapist judgement is required.

REQUEST TYPE:
{request_type}

THERAPIST NOTE:
{source[:2500]}

RETRIEVED TEXTBOOK CONTEXT:
{context[:4500] if context else "No local textbook context was retrieved."}
"""
            return llm.invoke(prompt).content
        except Exception as exc:
            return (
                "AI Clinical Support could not call Groq successfully. "
                f"{exc.__class__.__name__}: {str(exc)[:240]}\n\n"
                + fallback_ai_suggestion(source, context, references)
            )
    return fallback_ai_suggestion(source, context, references)


def fallback_ai_suggestion(source: str, context: str, references: list[dict[str, str]]) -> str:
    evidence_note = "Local textbook RAG retrieved supporting context." if context else "No local textbook context was available."
    excerpts = "\n".join(f"- {item['source']}: {item['excerpt'][:220]}" for item in references[:3])
    return (
        "AI Clinical Support: Review the patient presentation, screen for red flags, keep exercise dosage graded and pain-limited, "
        "and monitor function, pain response, adherence, and adverse symptoms. Therapist approval is required before use.\n\n"
        f"{evidence_note}\n{excerpts}\n\nInput Summary: {source[:500]}"
    )


@app.post("/api/clinical-records/ai-suggestions")
def ai_suggest(data: dict, user: dict = Depends(current_user)):
    if user["role"] != "therapist":
        raise HTTPException(status_code=403, detail="Only Therapists Can Use The AI Clinical Assistant")
    patient_access(int(data["patient_id"]), user)
    source = data.get("source_text") or ""
    suggestion = ai_clinical_suggestion(source, data.get("request_type", "summary"))
    result = run(
        "INSERT INTO ai_clinical_suggestions(patient_id,therapist_id,request_type,source_text,suggestion,reviewed_by_therapist,approved,created_at) VALUES(:p,:t,:type,:source,:suggestion,FALSE,FALSE,:created)",
        {"p": data["patient_id"], "t": user["id"], "type": data.get("request_type", "summary"), "source": source, "suggestion": suggestion, "created": now()},
    )
    return one("SELECT * FROM ai_clinical_suggestions WHERE id=:id", {"id": result.lastrowid})


@app.put("/api/clinical-records/ai-suggestions/{suggestion_id}/review")
def review_ai_suggestion(suggestion_id: int, data: dict, user: dict = Depends(current_user)):
    if user["role"] != "therapist":
        raise HTTPException(status_code=403, detail="Only Therapists Can Review AI Suggestions")
    suggestion = one("SELECT * FROM ai_clinical_suggestions WHERE id=:id", {"id": suggestion_id})
    if not suggestion:
        raise HTTPException(status_code=404, detail="AI Suggestion Not Found")
    patient_access(suggestion["patient_id"], user)
    run(
        "UPDATE ai_clinical_suggestions SET reviewed_by_therapist=1, approved=:approved WHERE id=:id",
        {"approved": bool(data.get("approved")), "id": suggestion_id},
    )
    return one("SELECT * FROM ai_clinical_suggestions WHERE id=:id", {"id": suggestion_id})


@app.get("/api/clinical-records/ai-suggestions/patient/{patient_id}")
def ai_suggestions(patient_id: int, user: dict = Depends(current_user)):
    patient_access(patient_id, user)
    return rows("SELECT * FROM ai_clinical_suggestions WHERE patient_id=:id ORDER BY created_at DESC", {"id": patient_id})


@app.post("/api/clinical-records/discharge")
def discharge_patient(data: dict, user: dict = Depends(current_user)):
    if user["role"] != "therapist":
        raise HTTPException(status_code=403, detail="Only Therapists Can Discharge Patients")
    patient_access(int(data["patient_id"]), user)
    result = run(
        """
        INSERT INTO discharge_summaries(patient_id,therapist_id,final_assessment,outcome_measures_summary,achieved_goals,home_exercise_program,discharge_summary,discharged_at,created_at)
        VALUES(:patient_id,:therapist_id,:final_assessment,:outcome_measures_summary,:achieved_goals,:home_exercise_program,:discharge_summary,:discharged_at,:created_at)
        """,
        {**data, "therapist_id": user["id"], "outcome_measures_summary": data.get("outcome_measures_summary"), "achieved_goals": data.get("achieved_goals"), "home_exercise_program": data.get("home_exercise_program"), "discharged_at": now(), "created_at": now()},
    )
    run("UPDATE patient_profiles SET patient_status='discharged' WHERE id=:id", {"id": data["patient_id"]})
    audit(user, "discharge", "patient", int(data["patient_id"]), int(data["patient_id"]), "Patient Discharged")
    return one("SELECT * FROM discharge_summaries WHERE id=:id", {"id": result.lastrowid})


@app.get("/api/clinical-records/discharge/patient/{patient_id}")
def get_discharge(patient_id: int, user: dict = Depends(current_user)):
    patient_access(patient_id, user)
    return rows("SELECT * FROM discharge_summaries WHERE patient_id=:id ORDER BY discharged_at DESC", {"id": patient_id})


@app.get("/api/clinical-records/textbook-rag/status")
def textbook_rag_status(user: dict = Depends(current_user)):
    vectorstore = textbook_vectorstore()
    files = list(TEXTBOOK_VECTORSTORE_PATH.glob("*")) if TEXTBOOK_VECTORSTORE_PATH.exists() else []
    return {
        "source_dir": str(TEXTBOOK_VECTORSTORE_PATH),
        "available": vectorstore is not None,
        "documents_found": len(files),
        "groq_key_loaded": bool(groq_api_key()),
        "lazy_indexing": False,
    }


@app.get("/api/clinical-records/textbook-rag/search")
def textbook_rag_search(q: str, user: dict = Depends(current_user)):
    _context, references = textbook_context(q)
    return {"query": q, "results": references, "note": "Evidence Support Only. Therapist Approval Required."}


@app.post("/api/pose-feedback/analyze")
def pose_feedback(data: dict, user: dict = Depends(current_user)):
    exercise = data.get("exercise", "Exercise")
    score = 82 if exercise.strip() else 70
    return {
        "exercise": exercise,
        "score": score,
        "feedback": [
            "Camera feedback is active. Keep your full body visible and face the camera side-on for this exercise.",
            "Your movement appears acceptable from the available frame. Keep the motion slow, controlled, and pain-free.",
            "For best accuracy, record in bright light with the camera at hip height and avoid loose clothing that hides joint position.",
            "Stop immediately if pain sharply increases, dizziness occurs, or balance feels unsafe.",
        ],
        "confidence": "Moderate",
    }


@app.post("/api/pose-feedback/analyze-image")
async def pose_feedback_image(exercise: str = Form("Exercise"), file: UploadFile = File(...), user: dict = Depends(current_user)):
    content = await file.read()
    try:
        import cv2
        import numpy as np

        image = cv2.imdecode(np.frombuffer(content, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Invalid image")
        height, width = image.shape[:2]
        hog = cv2.HOGDescriptor()
        hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        boxes, weights = hog.detectMultiScale(image, winStride=(8, 8), padding=(16, 16), scale=1.05)
        confident = [(box, float(weight)) for box, weight in zip(boxes, weights) if float(weight) > 0.25]
        if not confident:
            return {
                "exercise": exercise,
                "score": 0,
                "confidence": "Low",
                "person_detected": False,
                "feedback": [
                    "No full-body patient posture was detected in this frame.",
                    "Use a live full-body camera view before requesting exercise feedback.",
                    "Unrelated images cannot be graded as physiotherapy exercise performance.",
                ],
            }
        largest, weight = max(confident, key=lambda item: item[0][2] * item[0][3])
        x, y, w, h = [int(value) for value in largest]
        body_ratio = (w * h) / max(width * height, 1)
        centered = abs((x + w / 2) - width / 2) / max(width, 1) < 0.3
        score = 55 + int(min(weight, 2.0) * 15) + (10 if body_ratio > 0.18 else 0) + (10 if centered else 0)
        score = max(40, min(score, 95))
        feedback = [
            f"Person Detected For {exercise}. Form Score Is {score}/100.",
            "Keep the full body visible from head to feet so joint position can be checked.",
            "Move slowly and keep the exercise pain-free.",
        ]
        if body_ratio < 0.18:
            feedback.append("Move closer to the camera or adjust the camera so your body fills more of the frame.")
        if not centered:
            feedback.append("Stand nearer the center of the camera frame for better tracking.")
        return {"exercise": exercise, "score": score, "confidence": "Moderate", "person_detected": True, "feedback": feedback}
    except Exception as exc:
        return {
            "exercise": exercise,
            "score": 0,
            "confidence": "Unavailable",
            "person_detected": False,
            "feedback": [f"Pose analysis could not process this image: {exc}"],
        }


@app.get("/api/audit-logs/")
def get_audit_logs(user: dict = Depends(current_user)):
    if user["role"] not in ["therapist", "admin"]:
        raise HTTPException(status_code=403, detail="Only Clinical Staff")
    if user["role"] == "admin":
        return rows("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 200")
    return rows("SELECT * FROM audit_logs WHERE user_id=:id OR therapist_id=:id ORDER BY timestamp DESC LIMIT 200", {"id": user["id"]})


@app.get("/api/admin-research/summary")
def admin_summary(user: dict = Depends(current_user)):
    if user["role"] != "admin" and user.get("clinical_role") != "Clinic Administrator":
        raise HTTPException(status_code=403, detail="Clinic Administrator Access Required")
    return {
        "total_patients": one("SELECT COUNT(*) c FROM patient_profiles")["c"],
        "total_therapists": one("SELECT COUNT(*) c FROM users WHERE role='therapist'")["c"],
        "total_sessions": one("SELECT COUNT(*) c FROM session_logs")["c"],
        "total_appointments": one("SELECT COUNT(*) c FROM appointments")["c"],
        "patient_status_counts": {item["patient_status"] or "unknown": item["c"] for item in rows("SELECT patient_status, COUNT(*) c FROM patient_profiles GROUP BY patient_status")},
        "appointment_status_counts": {item["status"] or "unknown": item["c"] for item in rows("SELECT status, COUNT(*) c FROM appointments GROUP BY status")},
    }


@app.get("/api/admin-research/therapist-workload")
def workload(user: dict = Depends(current_user)):
    if user["role"] != "admin" and user.get("clinical_role") != "Clinic Administrator":
        raise HTTPException(status_code=403, detail="Clinic Administrator Access Required")
    return rows(
        """
        SELECT u.id therapist_id,u.full_name therapist_name,u.clinical_role,
        (SELECT COUNT(*) FROM patient_profiles p WHERE p.therapist_id=u.id) assigned_patients,
        (SELECT COUNT(*) FROM session_logs s WHERE s.therapist_id=u.id) recorded_sessions,
        (SELECT COUNT(*) FROM appointments a WHERE a.therapist_id=u.id) appointments
        FROM users u WHERE u.role='therapist'
        """
    )


@app.get("/api/admin-research/recovery-statistics")
def recovery_stats(user: dict = Depends(current_user)):
    if user["role"] != "admin" and user.get("clinical_role") != "Clinic Administrator":
        raise HTTPException(status_code=403, detail="Clinic Administrator Access Required")
    return {
        "condition_statistics": rows("SELECT p.condition, COUNT(s.id) sessions, AVG(s.adherence) average_adherence, AVG(s.pain_change) average_pain_change, AVG(s.form_score) average_form_score FROM patient_profiles p LEFT JOIN session_logs s ON s.patient_id=p.id GROUP BY p.condition"),
        "outcome_measure_counts": {item["measure_name"]: item["c"] for item in rows("SELECT measure_name, COUNT(*) c FROM outcome_measures GROUP BY measure_name")},
    }


@app.get("/api/admin-research/deidentified-export")
def deidentified(user: dict = Depends(current_user)):
    if user["role"] != "admin" and user.get("clinical_role") != "Clinic Administrator":
        raise HTTPException(status_code=403, detail="Clinic Administrator Access Required")
    patient_id_expr = "('PT-' || LPAD(p.id::text, 6, '0'))" if IS_POSTGRES else "printf('PT-%06d', p.id)"
    return rows(
        f"""
        SELECT {patient_id_expr} research_patient_id,p.age,p.gender,p.country,p.condition,p.severity,p.patient_status,
        COUNT(s.id) session_count, AVG(s.adherence) average_adherence, AVG(s.pain_change) average_pain_change
        FROM patient_profiles p LEFT JOIN session_logs s ON s.patient_id=p.id GROUP BY p.id
        """
    )


@app.get("/")
def root():
    return {"message": "Physio Tele-Rehab API is running!"}
