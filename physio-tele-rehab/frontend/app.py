from datetime import date, datetime, time
from html import escape
import os

import pandas as pd
import requests
import streamlit as st
from streamlit.delta_generator import DeltaGenerator


def get_setting(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value:
        return value
    try:
        secret_value = st.secrets.get(name)
        if secret_value:
            return str(secret_value)
    except Exception:
        pass
    return default


API = get_setting("API_URL", "https://physiotelerehab.onrender.com/api")

LANGUAGES = [
    "English", "Afrikaans", "Albanian", "Amharic", "Arabic", "Armenian", "Assamese", "Aymara", "Azerbaijani",
    "Bambara", "Basque", "Belarusian", "Bengali", "Bhojpuri", "Bosnian", "Bulgarian", "Catalan", "Cebuano",
    "Chinese Simplified", "Chinese Traditional", "Corsican", "Croatian", "Czech", "Danish", "Dhivehi", "Dogri",
    "Dutch", "Esperanto", "Estonian", "Ewe", "Filipino", "Finnish", "French", "Frisian", "Galician", "Georgian",
    "German", "Greek", "Guarani", "Gujarati", "Haitian Creole", "Hausa", "Hawaiian", "Hebrew", "Hindi", "Hmong",
    "Hungarian", "Icelandic", "Igbo", "Ilocano", "Indonesian", "Irish", "Italian", "Japanese", "Javanese",
    "Kannada", "Kazakh", "Khmer", "Kinyarwanda", "Konkani", "Korean", "Krio", "Kurdish Kurmanji",
    "Kurdish Sorani", "Kyrgyz", "Lao", "Latin", "Latvian", "Lingala", "Lithuanian", "Luganda", "Luxembourgish",
    "Macedonian", "Maithili", "Malagasy", "Malay", "Malayalam", "Maltese", "Maori", "Marathi", "Meiteilon",
    "Mizo", "Mongolian", "Myanmar", "Nepali", "Norwegian", "Nyanja", "Odia", "Oromo", "Pashto", "Persian",
    "Polish", "Portuguese", "Punjabi", "Quechua", "Romanian", "Russian", "Samoan", "Sanskrit", "Scots Gaelic",
    "Sepedi", "Serbian", "Sesotho", "Shona", "Sindhi", "Sinhala", "Slovak", "Slovenian", "Somali", "Spanish",
    "Sundanese", "Swahili", "Swedish", "Tajik", "Tamil", "Tatar", "Telugu", "Thai", "Tigrinya", "Tsonga",
    "Turkish", "Turkmen", "Twi", "Ukrainian", "Urdu", "Uyghur", "Uzbek", "Vietnamese", "Welsh", "Xhosa",
    "Yiddish", "Yoruba", "Zulu",
]

TRANSLATIONS = {
    "Yoruba": {"Navigation": "Irinajo", "Language": "Ede", "Theme": "Akori", "Patient Dashboard": "Dasiboodu Alaisan", "Therapist Dashboard": "Dasiboodu Onise Itoju", "Appointments": "Ipade", "Logout": "Jade"},
    "Igbo": {"Navigation": "Ntughari", "Language": "Asusu", "Theme": "Agwa Ihu", "Patient Dashboard": "Dashboard Onye Oria", "Therapist Dashboard": "Dashboard Onye Na-Agwo Ahu", "Appointments": "Nhoputa", "Logout": "Puo"},
    "Hausa": {"Navigation": "Kewayawa", "Language": "Harshe", "Theme": "Jigo", "Patient Dashboard": "Allon Bayanin Mara Lafiya", "Therapist Dashboard": "Allon Bayanin Mai Jinya", "Appointments": "Alkawura", "Logout": "Fita"},
    "French": {"Navigation": "Navigation", "Language": "Langue", "Appointments": "Rendez-Vous", "Logout": "Deconnexion"},
    "Spanish": {"Navigation": "Navegacion", "Language": "Idioma", "Appointments": "Citas", "Logout": "Cerrar Sesion"},
}

CONSENT_ITEMS = [
    {
        "type": "Telehealth Consent",
        "title": "Telehealth Consent",
        "content": "Remote physiotherapy may use video, messages, images, documents, and exercise monitoring. Remote care has limits because the therapist cannot physically examine you. Emergencies require local emergency services. You may request in-person care when clinically needed.",
    },
    {
        "type": "Treatment Consent",
        "title": "Treatment Consent",
        "content": "You consent to physiotherapy assessment, exercise prescription, education, monitoring, and rehabilitation planning. Stop and report severe pain, dizziness, chest pain, shortness of breath, new weakness, swelling, or any concerning change.",
    },
    {
        "type": "Data Privacy Agreement",
        "title": "Data Privacy Agreement",
        "content": "You consent to secure storage and processing of your health information, uploaded documents, messages, exercise records, appointment history, outcome measures, and audit logs for clinical care and lawful record retention.",
    },
]


def t(label):
    if not isinstance(label, str):
        return label
    language = st.session_state.get("language", "English")
    if language == "English":
        return label
    cache = st.session_state.setdefault("translation_cache", {})
    cache_key = f"{language}::{label}"
    if cache_key in cache:
        return cache[cache_key]
    local_translation = TRANSLATIONS.get(language, {}).get(label)
    if local_translation:
        cache[cache_key] = local_translation
        return local_translation
    try:
        response = requests.post(
            f"{API}/translations/batch",
            json={"target_language": language, "source_language": "English", "texts": [label]},
            timeout=5,
        )
        if response.ok:
            translated = response.json().get("translations", {}).get(label, label)
            cache[cache_key] = translated
            return translated
    except Exception:
        pass
    cache[cache_key] = label
    return label


def already_translated(label):
    if not isinstance(label, str):
        return False
    language = st.session_state.get("language", "English")
    cached_values = {
        value
        for key, value in st.session_state.get("translation_cache", {}).items()
        if key.startswith(f"{language}::")
    }
    return label in set(TRANSLATIONS.get(language, {}).values()) or label in cached_values


def translate_ui_value(value):
    if isinstance(value, str):
        stripped = value.lstrip()
        if stripped.startswith("<style") or stripped.startswith("<script") or already_translated(value):
            return value
        return t(value)
    if isinstance(value, list):
        return [translate_ui_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(translate_ui_value(item) for item in value)
    return value


def should_translate_cell(value):
    if not isinstance(value, str):
        return False
    stripped = value.strip()
    if not stripped:
        return False
    if "@" in stripped or "://" in stripped or stripped.startswith("PT-"):
        return False
    if len(stripped) > 280:
        return False
    return any(char.isalpha() for char in stripped)


def translate_dataframe_value(value):
    if should_translate_cell(value):
        return t(value)
    return value


def translate_dataframe(data):
    try:
        if isinstance(data, pd.DataFrame):
            frame = data.copy()
        elif isinstance(data, list) and all(isinstance(item, dict) for item in data):
            frame = pd.DataFrame(data)
        else:
            return data
        frame.columns = [t(str(column).replace("_", " ").title()) for column in frame.columns]
        for column in frame.columns:
            if frame[column].dtype == "object":
                frame[column] = frame[column].map(translate_dataframe_value)
        return frame
    except Exception:
        return data


def make_i18n_wrapper(fn, has_self=False):
    def wrapper(*args, **kwargs):
        args = list(args)
        label_index = 1 if has_self else 0
        skip = kwargs.get("unsafe_allow_html")
        if not skip and len(args) > label_index:
            args[label_index] = translate_ui_value(args[label_index])
        elif not skip and "label" in kwargs:
            kwargs["label"] = translate_ui_value(kwargs["label"])
        return fn(*args, **kwargs)

    wrapper._physio_i18n_wrapped = True
    return wrapper


def make_dataframe_wrapper(fn, has_self=False):
    def wrapper(*args, **kwargs):
        args = list(args)
        data_index = 1 if has_self else 0
        if len(args) > data_index:
            args[data_index] = translate_dataframe(args[data_index])
        elif "data" in kwargs:
            kwargs["data"] = translate_dataframe(kwargs["data"])
        return fn(*args, **kwargs)

    wrapper._physio_i18n_wrapped = True
    return wrapper


def patch_streamlit_text():
    if getattr(st, "_physio_i18n_patch_version", 0) >= 2 and getattr(DeltaGenerator, "_physio_i18n_patch_version", 0) >= 2:
        return
    names = [
        "title", "header", "subheader", "caption", "info", "warning", "error", "success",
        "button", "text_input", "text_area", "selectbox", "checkbox", "radio", "date_input",
        "time_input", "number_input", "slider", "file_uploader", "form_submit_button", "tabs",
        "write", "markdown", "metric", "download_button", "expander", "link_button", "multiselect",
        "camera_input", "audio_input", "toggle", "select_slider",
    ]
    for name in names:
        original = getattr(st, name, None)
        if callable(original) and not getattr(original, "_physio_i18n_wrapped", False):
            setattr(st, name, make_i18n_wrapper(original))
        generator_original = getattr(DeltaGenerator, name, None)
        if callable(generator_original) and not getattr(generator_original, "_physio_i18n_wrapped", False):
            setattr(DeltaGenerator, name, make_i18n_wrapper(generator_original, has_self=True))
    for name in ["dataframe", "table"]:
        original = getattr(st, name, None)
        if callable(original) and not getattr(original, "_physio_i18n_wrapped", False):
            setattr(st, name, make_dataframe_wrapper(original))
        generator_original = getattr(DeltaGenerator, name, None)
        if callable(generator_original) and not getattr(generator_original, "_physio_i18n_wrapped", False):
            setattr(DeltaGenerator, name, make_dataframe_wrapper(generator_original, has_self=True))
    st._physio_i18n_patch_version = 2
    DeltaGenerator._physio_i18n_patch_version = 2


def headers():
    return {"Authorization": f"Bearer {st.session_state.token}"} if st.session_state.get("token") else {}


def api(method, path, **kwargs):
    try:
        response = requests.request(method, f"{API}{path}", headers={**headers(), **kwargs.pop("headers", {})}, timeout=20, **kwargs)
        try:
            payload = response.json() if response.text else {}
        except ValueError:
            payload = {"detail": response.text or f"HTTP {response.status_code}"}
        if response.ok:
            return payload
        detail = payload.get("detail", response.text or f"HTTP {response.status_code}")
        st.error(detail)
    except Exception as exc:
        st.error(f"Connection Error: {exc}")
    return None


def format_dt(value):
    if not value:
        return ""
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).strftime("%A, %d %B %Y At %I:%M %p")
    except ValueError:
        return str(value)


def attachment_bytes(message_id):
    try:
        response = requests.get(f"{API}/communications/attachment/{message_id}", headers=headers(), timeout=20)
        if response.ok:
            return response.content
    except Exception:
        return None
    return None


def medical_document_bytes(document_id):
    try:
        response = requests.get(f"{API}/clinical-records/documents/{document_id}/file", headers=headers(), timeout=20)
        if response.ok:
            return response.content
    except Exception:
        return None
    return None


def metadata_value(metadata, key):
    text_value = str(metadata or "")
    marker = f"'{key}':"
    if marker not in text_value:
        marker = f'"{key}":'
    if marker not in text_value:
        return None
    return text_value.split(marker, 1)[1].split(",", 1)[0].strip().strip("{}'\" ")


def message_sender_label(msg):
    if msg.get("sender_id") == st.session_state.get("user_id"):
        return "You"
    sender_name = msg.get("sender_name") or "Unknown"
    sender_role = str(msg.get("sender_role") or "").lower()
    if sender_role == "therapist":
        return f"Your therapist, {sender_name}"
    if sender_role == "patient":
        return f"Patient, {sender_name}"
    return sender_name


def render_document_file(document):
    blob = medical_document_bytes(document["id"])
    filename = metadata_value(document.get("file_metadata"), "filename") or document.get("title") or "medical-document"
    content_type = metadata_value(document.get("file_metadata"), "content_type") or ""
    if not blob:
        st.warning("Document file is not available on the server.")
        return
    if content_type.startswith("image/"):
        st.image(blob, caption=filename)
    elif content_type == "application/pdf" or filename.lower().endswith(".pdf"):
        st.download_button("Download PDF", blob, filename, mime="application/pdf", key=f"doc_pdf_{document['id']}")
    else:
        st.download_button("Download File", blob, filename, mime=content_type or "application/octet-stream", key=f"doc_file_{document['id']}")


def init_state():
    defaults = {"token": None, "role": None, "clinical_role": None, "route": "login", "language": "English", "theme": "Bright", "translation_cache": {}, "auth_mode": "login"}
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def go(route):
    st.session_state.route = route
    st.rerun()


def ui_text(value):
    return escape(str(t(value)))


def raw_text(value):
    return escape(str(value or ""))


def page_header(title, subtitle="", eyebrow="Physio Tele-Rehab"):
    st.markdown(
        f"""
        <section class="ptr-hero">
            <div>
                <div class="ptr-eyebrow">{ui_text(eyebrow)}</div>
                <h1>{ui_text(title)}</h1>
                <p>{ui_text(subtitle)}</p>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def stat_card(label, value, helper="", tone="teal"):
    st.markdown(
        f"""
        <div class="ptr-stat ptr-{tone}">
            <span>{ui_text(label)}</span>
            <strong>{raw_text(value)}</strong>
            <small>{ui_text(helper)}</small>
        </div>
        """,
        unsafe_allow_html=True,
    )


def info_card(title, body="", tone="neutral"):
    st.markdown(
        f"""
        <div class="ptr-card ptr-card-{tone}">
            <h3>{ui_text(title)}</h3>
            <p>{ui_text(body)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_pill(label, tone="teal"):
    st.markdown(f"<span class='ptr-pill ptr-pill-{tone}'>{ui_text(label)}</span>", unsafe_allow_html=True)


def login_page():
    page_header(
        "Remote rehabilitation that feels close",
        "Secure patient care, therapist workflows, outcome tracking, records, and textbook-grounded AI support.",
        "Physio Tele-Rehab",
    )
    auth_mode = st.session_state.get("auth_mode", "login")
    center, side = st.columns([0.92, 0.08])
    with center:
        if auth_mode == "login":
            st.subheader("Login")
            with st.form("login"):
                identifier = st.text_input("Email / Phone / Patient ID")
                password = st.text_input("Password", type="password")
                if st.form_submit_button("Login"):
                    result = api("POST", "/auth/login", json={"identifier": identifier, "password": password})
                    if result:
                        st.session_state.token = result["access_token"]
                        st.session_state.role = result["role"]
                        st.session_state.clinical_role = result.get("clinical_role")
                        st.session_state.user_id = result.get("user_id")
                        st.session_state.email_verified = result.get("email_verified", True)
                        if result["role"] == "patient" and not st.session_state.email_verified:
                            go("verify_email")
                        else:
                            go("patient" if result["role"] == "patient" else "therapist")

            st.markdown("<p class='ptr-auth-switch'>Do not have an account?</p>", unsafe_allow_html=True)
            if st.button("Create an account"):
                st.session_state.auth_mode = "signup"
                st.rerun()

            with st.expander("Forgot Password"):
                reset_identifier = st.text_input("Email / Phone Number", key="reset_identifier_input")
                if st.button("Send Reset Code"):
                    result = api("POST", "/auth/request-password-reset", json={"identifier": reset_identifier})
                    if result:
                        st.session_state.reset_identifier_value = reset_identifier
                        st.success(result.get("message", "Reset Code Sent."))
                        if result.get("delivery_status"):
                            st.info(f"{result.get('delivery_channel', '').title()} Delivery: {result.get('delivery_status')}")
                        if result.get("delivery_detail"):
                            st.caption(result.get("delivery_detail"))
                reset_code = st.text_input("Reset Code")
                new_password = st.text_input("New Password", type="password", key="reset_new_password")
                confirm_password = st.text_input("Confirm New Password", type="password")
                if st.button("Change Password"):
                    result = api("POST", "/auth/reset-password", json={"identifier": st.session_state.get("reset_identifier_value", reset_identifier), "code": reset_code, "new_password": new_password, "confirm_password": confirm_password})
                    if result:
                        st.success("Password Changed. You Can Login Now.")
        else:
            st.subheader("Create Account")
            st.caption("Create a patient account. Your email will be verified before onboarding.")
            with st.form("register"):
                full_name = st.text_input("Full Name")
                email = st.text_input("Email")
                phone = st.text_input("Phone Number")
                password = st.text_input("New Password", type="password")
                accepted = []
                with st.expander("Terms, consent, and privacy", expanded=True):
                    for item in CONSENT_ITEMS:
                        st.markdown(
                            f"""
                            <div class="ptr-consent-copy">
                                <strong>{raw_text(item['title'])}</strong>
                                <p>{raw_text(item['content'])}</p>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                        if st.checkbox(f"I agree to the {item['title']}"):
                            accepted.append(item["type"])
                if st.form_submit_button("Sign Up"):
                    result = api("POST", "/auth/register", json={"full_name": full_name, "email": email, "phone_number": phone, "role": "patient", "clinical_role": None, "password": password, "accepted_consents": accepted})
                    if result:
                        if result.get("invitation_email_status"):
                            st.info(f"Invitation Email: {result.get('invitation_email_status')}")
                        if result.get("verification_email_status"):
                            st.info(f"Verification Email: {result.get('verification_email_status')}")
                        st.session_state.last_verification_email_status = result.get("verification_email_status")
                        st.session_state.last_verification_email_detail = result.get("verification_email_detail")
                        st.session_state.token = result["access_token"]
                        st.session_state.role = result["role"]
                        st.session_state.clinical_role = result.get("clinical_role")
                        st.session_state.user_id = result.get("user_id")
                        st.session_state.email_verified = result.get("email_verified", False)
                        go("verify_email")
            if st.button("Back to login"):
                st.session_state.auth_mode = "login"
                st.rerun()


def verify_email_page():
    st.title("Verify Email")
    status = api("GET", "/auth/email-verification/status") or {}
    st.write(f"Email: {status.get('email') or ''}")
    if st.session_state.get("last_verification_email_status"):
        st.info(f"Verification Email Delivery: {st.session_state.last_verification_email_status}")
    if st.session_state.get("last_verification_email_detail"):
        st.caption(st.session_state.last_verification_email_detail)
    if status.get("email_verified"):
        st.success("Email Already Verified.")
        if st.button("Continue"):
            go("onboarding")
        return
    st.info("Enter The Verification Code Sent To Your Email Before Continuing To Onboarding.")
    code = st.text_input("Email Verification Code")
    col1, col2 = st.columns(2)
    if col1.button("Verify Email"):
        result = api("POST", "/auth/verify-email", json={"code": code})
        if result:
            st.session_state.email_verified = True
            st.success(result.get("message", "Email Verified."))
            go("onboarding")
    if col2.button("Resend Code"):
        result = api("POST", "/auth/resend-email-verification")
        if result:
            st.success(result.get("message", "Verification Code Sent."))
            if result.get("delivery_status"):
                st.info(f"Verification Email Delivery: {result.get('delivery_status')}")


def onboarding_page():
    st.title("Patient Onboarding")
    verification = api("GET", "/auth/email-verification/status") or {}
    if not verification.get("email_verified"):
        st.warning("Verify Your Email Before Onboarding.")
        go("verify_email")
        return
    today = date.today()
    oldest_birth_date = date(today.year - 120, today.month, today.day)
    with st.form("onboarding"):
        data = {
            "full_name": st.text_input("Full Name"),
            "date_of_birth": str(st.date_input("Date Of Birth", min_value=oldest_birth_date, max_value=today, value=date(today.year - 30, today.month, today.day))),
            "gender": st.selectbox("Gender", ["Female", "Male", "Other"]),
            "phone": st.text_input("Phone"),
            "email": st.text_input("Email"),
            "address": st.text_input("Address"),
            "city": st.text_input("City"),
            "state": st.text_input("State"),
            "country": st.text_input("Country"),
            "occupation": st.text_input("Occupation"),
            "language": st.selectbox("Preferred Language", LANGUAGES),
            "emergency_name": st.text_input("Emergency Contact Name"),
            "emergency_phone": st.text_input("Emergency Contact Phone"),
            "emergency_relation": st.text_input("Emergency Contact Relation"),
        }
        if st.form_submit_button("Complete Onboarding"):
            if api("POST", "/onboarding/", json=data):
                st.success("Onboarding Complete")
                go("patient")


def dashboard_notifications():
    notes = api("GET", "/appointments/notifications/me") or []
    if not notes:
        return
    urgent = [note for note in notes[:5] if note.get("channel") == "website"]
    if urgent:
        with st.expander("Dashboard Notifications", expanded=True):
            for note in urgent:
                st.info(f"{note.get('message')} ({format_dt(note.get('created_at'))})")


def contact_settings(profile):
    with st.expander("Contact Settings"):
        st.caption("Email changes require a verification code sent to the new email address.")
        current_email = profile.get("email") or ""
        current_phone = profile.get("phone") or ""
        st.write(f"Current Email: {current_email}")
        st.write(f"Current Phone: {current_phone}")
        new_email = st.text_input("New Email Address", value="", key="new_contact_email")
        if st.button("Send Email Verification Code"):
            result = api("POST", "/auth/request-email-change", json={"new_email": new_email})
            if result:
                st.session_state.pending_email_change = new_email
                st.success(result.get("message", "Verification Code Sent."))
        email_code = st.text_input("Email Verification Code")
        if st.button("Confirm Email Change"):
            target_email = st.session_state.get("pending_email_change", new_email)
            result = api("POST", "/auth/confirm-email-change", json={"new_email": target_email, "code": email_code})
            if result:
                st.success(result.get("message", "Email Updated."))
                st.rerun()
        with st.form("phone_update"):
            phone = st.text_input("New Phone Number", value=current_phone)
            if st.form_submit_button("Update Phone Number"):
                result = api("POST", "/auth/update-phone", json={"phone_number": phone})
                if result:
                    st.success(result.get("message", "Phone Updated."))
                    st.rerun()


def patient_dashboard():
    profile = api("GET", "/patients/me/profile")
    if not profile:
        page_header("Patient Onboarding", "Finish your profile so your therapist can personalize your rehab plan.")
        st.info("Complete Onboarding First.")
        if st.button("Go To Onboarding"):
            go("onboarding")
        return
    page_header(
        "Patient Dashboard",
        f"{profile.get('full_name') or 'Welcome back'} · {profile.get('patient_status') or 'Active rehab program'}",
        f"Patient ID: {profile.get('patient_identifier') or 'Pending'}",
    )
    dashboard_notifications()
    progress = api("GET", "/progress/me") or {}
    plans = api("GET", "/exercise-plans/my-plans") or []
    documents = api("GET", f"/clinical-records/documents/patient/{profile['id']}") or []
    outcomes = api("GET", f"/clinical-records/outcome-measures/patient/{profile['id']}") or []
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        stat_card("Total sessions", progress.get("total_sessions", 0), "Logged rehabilitation sessions", "blue")
    with c2:
        stat_card("Average pain change", progress.get("average_pain_change", 0), "Before versus after exercise", "green")
    with c3:
        stat_card("Active plans", len(plans), "Therapist-assigned plans", "teal")
    with c4:
        stat_card("Clinical documents", len(documents), "Shared with your therapist", "amber")
    tabs = st.tabs(["My Plan", "Session Log", "Progress", "Messages", "Appointments", "Clinical Records", "AI Pose Feedback", "Settings"])
    with tabs[0]:
        library = {item["id"]: item for item in (api("GET", "/exercises/") or [])}
        if not plans:
            info_card("No exercise plan assigned yet", "Your therapist will assign exercises, dosage, safety notes, and progression here.")
        for plan in plans:
            with st.expander(plan.get("title", "Exercise Plan"), expanded=True):
                c1, c2, c3 = st.columns(3)
                c1.metric("Frequency Per Week", plan.get("frequency_per_week"))
                c2.metric("Duration Weeks", plan.get("duration_weeks"))
                c3.metric("Assigned Exercises", len(str(plan.get("exercise_prescriptions") or "").split(",")) if plan.get("exercise_prescriptions") else 0)
                st.write(f"Clinical Notes: {plan.get('clinical_notes') or ''}")
                st.write(f"Progression: {plan.get('progression_notes') or ''}")
                prescriptions = str(plan.get("exercise_prescriptions") or "")
                selected_names = [exercise["name"] for exercise_id, exercise in library.items() if str(exercise_id) in prescriptions]
                if selected_names:
                    st.markdown("#### Assigned Exercises")
                    for name in selected_names:
                        status_pill(name, "teal")
    with tabs[1]:
        exercises = api("GET", "/exercises/") or []
        exercise_id = st.selectbox("Exercise", [x["id"] for x in exercises], format_func=lambda i: next((x["name"] for x in exercises if x["id"] == i), i)) if exercises else 1
        with st.form("session"):
            pain_before = st.slider("Pain Before", 0, 10, 0)
            pain_after = st.slider("Pain After", 0, 10, 0)
            adherence = st.slider("Adherence", 0, 100, 80) / 100
            notes = st.text_area("Notes")
            if st.form_submit_button("Save Session"):
                api("POST", "/session-logs/", json={"patient_id": profile["id"], "exercise_id": exercise_id, "pain_before": pain_before, "pain_after": pain_after, "adherence": adherence, "patient_feedback": notes})
    with tabs[2]:
        c1, c2 = st.columns(2)
        c1.metric("Total Sessions", progress.get("total_sessions", 0))
        c2.metric("Average Pain Change", progress.get("average_pain_change", 0))
        if progress.get("logs"):
            st.line_chart(pd.DataFrame(progress["logs"])[["pain_before", "pain_after", "adherence"]])
    with tabs[3]:
        message_box(profile["id"])
    with tabs[4]:
        appointments_page(profile)
    with tabs[5]:
        clinical_records(profile)
    with tabs[6]:
        pose_feedback()
    with tabs[7]:
        contact_settings(profile)


def therapist_dashboard():
    page_header("Therapist Dashboard", "Clinical review queue, patient monitoring, records, messaging, and evidence-supported decisions.", "Therapist workspace")
    dashboard_notifications()
    patients = api("GET", "/therapist/patients") or []
    unassigned = api("GET", "/therapist-assignments/unassigned-patients") or []
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        stat_card("Assigned Patients", len(patients), "Currently under your care", "teal")
    with c2:
        stat_card("Unassigned Queue", len(unassigned), "Patients waiting for therapist", "amber")
    with c3:
        stat_card("Clinical Alerts", "Scan", "Use the alerts tab to refresh", "red")
    with c4:
        stat_card("AI + RAG", "Ready", "Textbook evidence workflow", "blue")
    tabs = st.tabs(["Patients", "Queue", "Assessment", "Plan Builder", "Clinical Records", "Messages", "Appointments", "Exercise Library", "Coverage", "Video Consult", "Alerts", "Audit Logs", "Admin Research"])
    with tabs[0]:
        if patients:
            st.dataframe(pd.DataFrame(patients), use_container_width=True)
        else:
            info_card("No assigned patients yet", "Claim a patient from the queue or wait for assignment.")
    with tabs[1]:
        for patient in unassigned:
            with st.container(border=True):
                st.write(patient.get("full_name"))
                if st.button("Claim Patient", key=f"claim_{patient['id']}"):
                    api("POST", "/therapist-assignments/assign-therapist", json={"patient_id": patient["id"], "role": "primary"})
                    st.rerun()
    selected = select_patient(patients)
    if not selected:
        return
    with tabs[2]:
        assessment_form(selected)
    with tabs[3]:
        plan_builder(selected)
    with tabs[4]:
        clinical_records(selected)
    with tabs[5]:
        message_box(selected["id"])
    with tabs[6]:
        appointments_page(selected)
    with tabs[7]:
        exercise_library()
    with tabs[8]:
        coverage_panel(selected)
    with tabs[9]:
        video_consult_panel(selected)
    with tabs[10]:
        alerts_panel()
    with tabs[11]:
        audit_logs()
    with tabs[12]:
        admin_research()


def select_patient(patients):
    if not patients:
        return None
    patient_map = {p["id"]: p for p in patients}
    patient_id = st.selectbox("Selected Patient", list(patient_map), format_func=lambda i: patient_map[i].get("full_name", f"Patient {i}"))
    return patient_map[patient_id]


def assessment_form(patient):
    with st.form("assessment"):
        data = {"patient_id": patient["id"], "assessment_type": st.selectbox("Assessment Type", ["Initial", "Follow-Up", "Discharge"]), "subjective": st.text_area("Subjective History"), "objective": st.text_area("Objective Examination"), "range_of_motion": st.text_area("Range Of Motion"), "muscle_strength": st.text_area("Muscle Strength"), "balance": st.text_area("Balance"), "gait": st.text_area("Gait"), "functional_testing": st.text_area("Functional Testing"), "clinical_diagnosis": st.text_area("Clinical Diagnosis"), "assessment": st.text_area("Assessment"), "plan": st.text_area("Plan"), "outcome_measures": st.text_area("Outcome Measures"), "follow_up_recommendation": st.text_area("Follow-Up Recommendation"), "clinical_note": st.text_area("SOAP / Clinical Note")}
        if st.form_submit_button("Save Assessment"):
            api("POST", "/assessments/create", json=data)


def plan_builder(patient):
    exercises = api("GET", "/exercises/") or []
    selected = st.multiselect("Exercises", [x["id"] for x in exercises], format_func=lambda i: next((x["name"] for x in exercises if x["id"] == i), i))
    with st.form("plan"):
        title = st.text_input("Plan Title")
        goals = st.text_area("Goals")
        notes = st.text_area("Clinical Notes")
        progression = st.text_area("Progression Instructions")
        frequency = st.number_input("Frequency Per Week", 1, 14, 3)
        duration = st.number_input("Duration Weeks", 1, 52, 6)
        if st.form_submit_button("Create Plan"):
            api("POST", "/exercise-plans/create", json={"patient_id": patient["id"], "title": title, "clinical_notes": notes, "goals": [goals], "progression_notes": progression, "frequency_per_week": frequency, "duration_weeks": duration, "exercise_prescriptions": selected})


def appointments_page(patient):
    if st.session_state.role == "therapist":
        if st.button("Send Due Appointment Reminders"):
            result = api("POST", "/appointments/send-reminders")
            if result:
                st.success(f"Reminders Queued: {result.get('reminders_sent', 0)}")
        with st.form(f"appt_{patient['id']}"):
            appt_type = st.selectbox("Appointment Type", ["Tele-Rehabilitation", "Initial Assessment", "Follow-Up", "Discharge Review"])
            date = st.date_input("Appointment Date")
            appt_time = st.time_input("Appointment Time", value=time(10, 0))
            reason = st.text_area("Reason")
            if st.form_submit_button("Schedule Appointment"):
                scheduled_start = datetime.combine(date, appt_time).isoformat()
                appointment_key = f"{patient['id']}|{appt_type}|{scheduled_start}"
                if st.session_state.get("last_appointment_submit") == appointment_key:
                    st.warning("This Appointment Was Already Submitted.")
                else:
                    result = api("POST", "/appointments/", json={"patient_id": patient["id"], "appointment_type": appt_type, "scheduled_start": scheduled_start, "reason": reason})
                    if result:
                        st.session_state.last_appointment_submit = appointment_key
                        st.rerun()
    appointments = api("GET", f"/appointments/patient/{patient['id']}") or []
    notes = api("GET", "/appointments/notifications/me") or []
    if notes:
        with st.expander("Appointment Notifications"):
            for note in notes[:10]:
                st.write(f"{str(note.get('channel')).title()} - {note.get('status')}: {note.get('message')}")
    for appt in appointments:
        with st.expander(f"{appt.get('appointment_type')} - {format_dt(appt.get('scheduled_start'))}"):
            st.write(f"Status: {appt.get('status')}")
            st.write(f"Scheduled: {format_dt(appt.get('scheduled_start'))}")
            if appt.get("cancellation_reason"):
                st.write(f"Reason: {appt.get('cancellation_reason')}")
            reason = st.text_input("Cancellation / Deletion Reason", key=f"reason_{appt['id']}")
            if st.button("Cancel Appointment", key=f"cancel_{appt['id']}", disabled=appt.get("status") == "Cancelled"):
                if not reason.strip():
                    st.error("Enter A Cancellation Reason.")
                else:
                    api("PUT", f"/appointments/{appt['id']}", json={"status": "Cancelled", "cancellation_reason": reason})
                    st.rerun()
            if st.session_state.role == "therapist" and st.button("Delete Mistake", key=f"delete_{appt['id']}"):
                if not reason.strip():
                    st.error("Enter A Deletion Reason.")
                else:
                    api("DELETE", f"/appointments/{appt['id']}", params={"cancellation_reason": reason})
                    st.rerun()


def message_box(patient_id):
    st.markdown("#### Care Team Messages")
    col1, col2 = st.columns(2)
    if col1.button("Start Video Call", key=f"video_call_{patient_id}"):
        result = api("POST", "/communications/call", json={"patient_id": patient_id, "call_type": "video"})
        if result:
            st.rerun()
    if col2.button("Start Voice Call", key=f"voice_call_{patient_id}"):
        result = api("POST", "/communications/call", json={"patient_id": patient_id, "call_type": "voice"})
        if result:
            st.rerun()
    with st.form(f"msg_{patient_id}"):
        content = st.text_area("Message")
        if st.form_submit_button("Send Text"):
            if content.strip():
                api("POST", "/communications/", json={"patient_id": patient_id, "message_type": "text", "content": content})
                st.rerun()
            else:
                st.error("Type A Message First.")
    message_type = st.selectbox("Attachment Type", ["image", "document", "voice", "video"], key=f"attach_type_{patient_id}")
    upload = st.file_uploader("Optional Attachment", type=None)
    if message_type == "voice" and hasattr(st, "audio_input"):
        recorded = st.audio_input("Record Voice Note")
        if recorded is not None:
            upload = recorded
    if upload and st.button("Send Attachment"):
        files = {"file": (upload.name, upload.getvalue(), upload.type or "application/octet-stream")}
        result = api("POST", "/communications/upload", data={"patient_id": str(patient_id), "message_type": message_type, "content": ""}, files=files)
        if result:
            st.success("Attachment Sent.")
            st.rerun()
    messages = api("GET", f"/communications/patient/{patient_id}") or []
    for msg in messages:
        sender = message_sender_label(msg)
        mine = msg.get("sender_id") == st.session_state.get("user_id")
        bubble_class = "ptr-message mine" if mine else "ptr-message"
        st.markdown(
            f"""
            <div class="{bubble_class}">
                <div class="ptr-message-meta">{raw_text(sender)} · {raw_text(str(msg.get('message_type')).title())} · {raw_text(format_dt(msg.get('created_at')))}</div>
            """,
            unsafe_allow_html=True,
        )
        with st.container():
            content = msg.get("content") or ""
            call_url = metadata_value(msg.get("attachment_metadata"), "call_url")
            if call_url:
                st.write(content)
                st.link_button("Open Call", call_url)
            elif content:
                st.write(content)
            if msg.get("attachment_metadata"):
                blob = attachment_bytes(msg["id"])
                if blob:
                    kind = str(msg.get("message_type") or "")
                    if kind == "image":
                        st.image(blob)
                    elif kind == "video":
                        st.video(blob)
                    elif kind == "voice":
                        st.audio(blob)
                    else:
                        st.download_button("Download Attachment", blob, metadata_value(msg.get("attachment_metadata"), "filename") or "attachment")
        st.markdown("</div>", unsafe_allow_html=True)


def exercise_library():
    with st.form("exercise"):
        data = {"name": st.text_input("Exercise Name"), "description": st.text_area("Description"), "condition": st.text_input("Condition"), "body_region": st.text_input("Body Region"), "difficulty": st.selectbox("Difficulty", ["Easy", "Moderate", "Hard"]), "reps": st.text_input("Reps"), "sets": st.text_input("Sets"), "safety_precautions": st.text_area("Safety Precautions"), "video_url": st.text_input("Video URL"), "image_url": st.text_input("Image URL")}
        if st.form_submit_button("Add Exercise"):
            api("POST", "/exercises/", json=data)
    st.dataframe(pd.DataFrame(api("GET", "/exercises/") or []), use_container_width=True)


def coverage_panel(patient):
    st.subheader("Temporary Therapist Coverage")
    therapists = api("GET", "/therapist/all") or []
    options = [item["id"] for item in therapists if item["id"] != st.session_state.get("user_id")]
    if options:
        therapist_id = st.selectbox("Temporary Therapist", options, format_func=lambda i: next((x["full_name"] for x in therapists if x["id"] == i), i))
        start = st.date_input("Coverage Start")
        end = st.date_input("Coverage End")
        reason = st.text_area("Coverage Reason")
        if st.button("Assign Temporary Coverage"):
            api("POST", "/therapist-assignments/assign-therapist", json={"patient_id": patient["id"], "therapist_id": therapist_id, "role": "temporary", "coverage_start": str(start), "temporary_until": str(end), "coverage_reason": reason, "primary_therapist_id": patient.get("therapist_id")})
            st.rerun()
    if st.button("Expire Ended Temporary Coverage"):
        api("POST", "/therapist-assignments/expire-temporary")
        st.rerun()
    st.dataframe(pd.DataFrame(api("GET", f"/therapist-assignments/patient/{patient['id']}") or []), use_container_width=True)


def video_consult_panel(patient):
    st.subheader("Video Consultation")
    with st.form("video_consult"):
        date = st.date_input("Video Date")
        start_time = st.time_input("Video Time", value=time(12, 0))
        notes = st.text_area("Supervision Notes")
        if st.form_submit_button("Schedule Video Consultation"):
            api("POST", "/video-consultations/", json={"patient_id": patient["id"], "scheduled_start": datetime.combine(date, start_time).isoformat(), "supervision_notes": notes})
            st.rerun()
    consultations = api("GET", f"/video-consultations/patient/{patient['id']}") or []
    for consult in consultations:
        st.write(f"{consult.get('scheduled_start')} - {consult.get('status')}")
        url = consult.get("secure_session_url")
        if url:
            st.link_button("Open Secure Session", url)


def alerts_panel():
    if st.session_state.role in ["therapist", "admin"] and st.button("Scan Clinical Alerts"):
        api("POST", "/clinical-alerts/scan")
        st.rerun()
    alerts = api("GET", "/clinical-alerts/") or []
    if alerts:
        st.dataframe(pd.DataFrame(alerts), use_container_width=True)
    else:
        st.info("No Alerts Found.")


def audit_logs():
    logs = api("GET", "/audit-logs/") or []
    st.dataframe(pd.DataFrame(logs), use_container_width=True)


def pose_feedback():
    st.subheader("AI Pose Feedback")
    st.caption("Use a clear full-body camera view. The system gives exercise-form coaching from the live frame.")
    exercise = st.text_input("Exercise Being Performed", "Squat")
    camera_frame = st.camera_input("Live Exercise Camera")
    if camera_frame is not None and st.button("Analyze Live Frame"):
        files = {"file": (camera_frame.name or "pose-frame.jpg", camera_frame.getvalue(), camera_frame.type or "image/jpeg")}
        result = api("POST", "/pose-feedback/analyze-image", data={"exercise": exercise}, files=files) or {}
        st.metric("Form Score", result.get("score", 0))
        for item in result.get("feedback", []):
            st.write(item)
    elif camera_frame is None:
        st.info("Take A Live Camera Frame First.")


def clinical_records(patient):
    is_therapist = st.session_state.role in ["therapist", "admin"]
    st.markdown("#### Clinical Records")
    st.caption("Documents, outcome measures, objective progress, discharge summaries, and textbook-supported AI notes.")
    tab_names = ["Documents", "Outcome Measures", "Objective Progress", "AI Notes", "Discharge"]
    if is_therapist:
        tab_names.append("Permanent Record")
    tabs = st.tabs(tab_names)
    with tabs[0]:
        if st.session_state.role == "patient":
            with st.container(border=True):
                st.markdown("##### Upload document")
                c1, c2 = st.columns(2)
                with c1:
                    doc_type = st.selectbox("Document Type", ["MRI Report", "X-Ray", "CT Scan", "Referral Letter", "Laboratory Report", "Clinical Photograph", "Other"])
                    title = st.text_input("Document Title")
                with c2:
                    description = st.text_area("Document Description")
                    upload = st.file_uploader("Upload Medical Document")
                if upload and st.button("Save Medical Document"):
                    files = {"file": (upload.name, upload.getvalue(), upload.type or "application/octet-stream")}
                    result = api("POST", "/clinical-records/documents/upload", data={"patient_id": str(patient["id"]), "document_type": doc_type, "title": title or upload.name, "description": description or ""}, files=files)
                    if result:
                        st.success("Medical Document Uploaded.")
                        st.rerun()
        else:
            info_card("Patient-uploaded documents", "View and download MRI, CT, X-Ray, lab, referral, image, and other clinical files.")
        documents = api("GET", f"/clinical-records/documents/patient/{patient['id']}") or []
        if documents:
            for document in documents:
                title = document.get("title") or metadata_value(document.get("file_metadata"), "filename") or "Medical Document"
                with st.expander(f"{title} - {document.get('document_type', 'Document')}", expanded=True if is_therapist else False):
                    c1, c2, c3 = st.columns([1.2, 1, 1])
                    c1.metric("Document Type", document.get("document_type", "Document"))
                    c2.metric("Uploaded By", document.get("uploaded_by_name") or "Patient")
                    c3.metric("Uploaded", format_dt(document.get("created_at")) or "Unknown")
                    if document.get("description"):
                        st.write(document.get("description"))
                    render_document_file(document)
        else:
            st.info("No Medical Documents Uploaded Yet.")
    with tabs[1]:
        st.caption("Examples: Oswestry Disability Index, DASH, WOMAC, LEFS, Berg Balance Scale, TUG, 6 Minute Walk Test, VAS Pain, NPRS, KOOS, HOOS.")
        if is_therapist:
            with st.form("outcome"):
                name = st.text_input("Outcome Measure Used")
                score = st.number_input("Score", value=0.0)
                max_score = st.number_input("Max Score", value=100.0)
                interpretation = st.text_area("Interpretation")
                if st.form_submit_button("Save Outcome"):
                    api("POST", "/clinical-records/outcome-measures", json={"patient_id": patient["id"], "measure_name": name, "score": score, "max_score": max_score, "interpretation": interpretation})
        outcomes = api("GET", f"/clinical-records/outcome-measures/patient/{patient['id']}") or []
        if outcomes:
            for outcome in outcomes:
                with st.expander(f"{outcome.get('measure_name')} - {outcome.get('score')}/{outcome.get('max_score')}", expanded=True):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Score", outcome.get("score"))
                    c2.metric("Max Score", outcome.get("max_score"))
                    c3.metric("Measured", format_dt(outcome.get("measured_at")) or "")
                    if outcome.get("interpretation"):
                        info_card("Therapist interpretation", outcome.get("interpretation"), "teal")
        else:
            st.info("No Outcome Measures Recorded Yet.")
    with tabs[2]:
        st.caption("Examples: Range Of Motion, Strength, Functional Mobility, Balance, Gait, Pain, Adherence.")
        if is_therapist:
            with st.form("objective_progress"):
                metric_type = st.text_input("Progress Category")
                metric_name = st.text_input("Progress Measured")
                value = st.number_input("Value", value=0.0)
                unit = st.text_input("Unit")
                notes = st.text_area("Progress Notes")
                if st.form_submit_button("Save Objective Metric"):
                    api("POST", "/clinical-records/objective-progress", json={"patient_id": patient["id"], "metric_type": metric_type, "metric_name": metric_name, "value": value, "unit": unit, "notes": notes})
        metrics = api("GET", f"/clinical-records/objective-progress/patient/{patient['id']}") or []
        if metrics:
            frame = pd.DataFrame(metrics)
            st.dataframe(frame, use_container_width=True)
            st.line_chart(frame.set_index("measured_at")["value"])
    with tabs[3]:
        if is_therapist:
            rag = api("GET", "/clinical-records/textbook-rag/status") or {}
            c1, c2, c3 = st.columns(3)
            with c1:
                stat_card("Textbook RAG", "Available" if rag.get("available") else "Unavailable", "Evidence retrieval", "teal" if rag.get("available") else "amber")
            with c2:
                stat_card("Vectorstore Files", rag.get("documents_found", 0), "FAISS resources found", "blue")
            with c3:
                stat_card("Groq Key", "Loaded" if rag.get("groq_key_loaded") else "Missing", "LLM generation", "green" if rag.get("groq_key_loaded") else "red")
            source = st.text_area("Clinical Notes")
            if st.button("Search Textbook Evidence"):
                evidence = api("GET", "/clinical-records/textbook-rag/search", params={"q": source or patient.get("condition") or "rehabilitation precautions progression"}) or {}
                for item in evidence.get("results", []):
                    with st.expander(item.get("source", "Textbook Evidence"), expanded=False):
                        st.write(item.get("excerpt"))
            if st.button("Generate AI Suggestion"):
                result = api("POST", "/clinical-records/ai-suggestions", json={"patient_id": patient["id"], "request_type": "support", "source_text": source})
                if result:
                    st.success("AI suggestion generated.")
                    st.rerun()
        suggestions = api("GET", f"/clinical-records/ai-suggestions/patient/{patient['id']}") or []
        for item in suggestions:
            with st.expander(item.get("request_type", "AI Suggestion")):
                info_card("AI clinical suggestion", item.get("suggestion"), "blue")
                if is_therapist:
                    col1, col2 = st.columns(2)
                    if col1.button("Approve", key=f"approve_ai_{item['id']}"):
                        api("PUT", f"/clinical-records/ai-suggestions/{item['id']}/review", json={"approved": True})
                        st.rerun()
                    if col2.button("Reject", key=f"reject_ai_{item['id']}"):
                        api("PUT", f"/clinical-records/ai-suggestions/{item['id']}/review", json={"approved": False})
                        st.rerun()
    with tabs[4]:
        if is_therapist:
            with st.form("discharge"):
                final = st.text_area("Final Assessment")
                outcomes = st.text_area("Outcome Measures Summary")
                goals = st.text_area("Achieved Goals")
                hep = st.text_area("Home Exercise Program")
                summary = st.text_area("Discharge Summary")
                if st.form_submit_button("Discharge Patient"):
                    api("POST", "/clinical-records/discharge", json={"patient_id": patient["id"], "final_assessment": final, "outcome_measures_summary": outcomes, "achieved_goals": goals, "home_exercise_program": hep, "discharge_summary": summary})
                    st.rerun()
        st.dataframe(pd.DataFrame(api("GET", f"/clinical-records/discharge/patient/{patient['id']}") or []), use_container_width=True)
    if is_therapist:
        with tabs[5]:
            record = [
                ("Assessments", api("GET", f"/assessments/patient/{patient['id']}") or []),
                ("Outcome Measures", api("GET", f"/clinical-records/outcome-measures/patient/{patient['id']}") or []),
                ("Objective Progress", api("GET", f"/clinical-records/objective-progress/patient/{patient['id']}") or []),
                ("Medical Documents", api("GET", f"/clinical-records/documents/patient/{patient['id']}") or []),
                ("Discharge Summaries", api("GET", f"/clinical-records/discharge/patient/{patient['id']}") or []),
            ]
            cols = st.columns(len(record))
            for idx, (label, items) in enumerate(record):
                cols[idx].metric(label, len(items))
            for label, items in record:
                with st.expander(label, expanded=False):
                    if items:
                        st.dataframe(pd.DataFrame(items), use_container_width=True)
                    else:
                        st.info(f"No {label} Recorded Yet.")


def admin_research():
    if not (st.session_state.role == "admin" or st.session_state.clinical_role == "Clinic Administrator"):
        st.info("Clinic Administrator Access Required.")
        return
    summary = api("GET", "/admin-research/summary") or {}
    c1, c2, c3 = st.columns(3)
    c1.metric("Patients", summary.get("total_patients", 0))
    c2.metric("Therapists", summary.get("total_therapists", 0))
    c3.metric("Sessions", summary.get("total_sessions", 0))
    st.dataframe(pd.DataFrame(api("GET", "/admin-research/therapist-workload") or []), use_container_width=True)
    export = pd.DataFrame(api("GET", "/admin-research/deidentified-export") or [])
    st.dataframe(export, use_container_width=True)
    if not export.empty:
        st.download_button("Download De-Identified CSV", export.to_csv(index=False), "physio_research_export.csv")


def sidebar():
    with st.sidebar:
        st.markdown("<div class='ptr-sidebar-brand'>Physio Tele-Rehab</div>", unsafe_allow_html=True)
        current_language = st.session_state.get("language", "English")
        selected_language = st.selectbox("Language", LANGUAGES, index=LANGUAGES.index(current_language) if current_language in LANGUAGES else 0, key="language_picker")
        if selected_language != current_language:
            st.session_state.language = selected_language
            st.rerun()
        st.radio("Theme", ["Bright", "Dark"], key="theme", format_func=t)
        st.markdown("#### " + t("Navigation"))
        if st.session_state.token:
            if st.session_state.role == "patient" and st.button(t("Patient Dashboard")):
                go("patient")
            if st.session_state.role in ["therapist", "admin"] and st.button(t("Therapist Dashboard")):
                go("therapist")
            if st.button(t("Logout")):
                st.session_state.token = None
                st.session_state.role = None
                st.session_state.user_id = None
                go("login")


def apply_theme():
    base_css = """
        <style>
        :root {
            --ptr-navy:#07111f;
            --ptr-ink:#101828;
            --ptr-text:#101828;
            --ptr-muted:#667085;
            --ptr-bg:#f7f9fc;
            --ptr-surface:#ffffff;
            --ptr-elevated:#ffffff;
            --ptr-line:#e4e7ec;
            --ptr-primary:#175cd3;
            --ptr-primary-dark:#1849a9;
            --ptr-primary-soft:#eaf1ff;
            --ptr-teal:#0e9384;
            --ptr-teal-dark:#107569;
            --ptr-teal-soft:#e6f7f4;
            --ptr-blue:#175cd3;
            --ptr-blue-soft:#eaf1ff;
            --ptr-green:#079455;
            --ptr-green-soft:#ecfdf3;
            --ptr-amber:#dc6803;
            --ptr-amber-soft:#fffaeb;
            --ptr-red:#d92d20;
            --ptr-red-soft:#fef3f2;
            --ptr-lavender:#6938ef;
            --ptr-lavender-soft:#f4f3ff;
        }
        .block-container { padding-top: 1.4rem; max-width: 1440px; }
        html, body, .stApp, [data-testid="stAppViewContainer"] {
            overflow-x: hidden;
        }
        [data-testid="stSidebar"], [data-testid="stSidebarContent"] {
            background: linear-gradient(180deg, #07111f 0%, #0b1f36 58%, #102a43 100%)!important;
            border-right: 1px solid rgba(255,255,255,.08);
        }
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] h4,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] small {
            color: #e5edf7!important;
        }
        [data-testid="stSidebar"] [data-baseweb="select"] *,
        [data-testid="stSidebar"] input,
        [data-testid="stSidebar"] textarea {
            color: #101828!important;
        }
        [data-testid="stSidebar"] [role="radiogroup"] label span {
            color: #e5edf7!important;
        }
        .ptr-sidebar-brand {
            color:#ffffff!important;
            font-weight: 800;
            font-size: 1.15rem;
            line-height: 1.15;
            padding: .85rem .65rem 1.15rem;
            margin-bottom: .4rem;
            border-bottom: 1px solid rgba(255,255,255,.12);
        }
        .ptr-hero {
            background:
                radial-gradient(circle at 86% 18%, rgba(22, 163, 143, .25), transparent 28%),
                linear-gradient(135deg, #07111f 0%, #123b63 52%, #175cd3 100%);
            color: #fff;
            padding: 2rem 2.2rem;
            border-radius: 12px;
            margin: .25rem 0 1.25rem;
            box-shadow: 0 18px 42px rgba(16, 24, 40, .18);
        }
        .ptr-hero h1 {
            color: #fff!important;
            font-size: clamp(2rem, 4vw, 3.3rem);
            line-height: 1.05;
            margin: .25rem 0 .75rem;
            letter-spacing: 0;
        }
        .ptr-hero p {
            color: #d9e6f7!important;
            max-width: 820px;
            font-size: 1.03rem;
            margin: 0;
        }
        .ptr-eyebrow {
            color:#a7f3e7!important;
            text-transform: uppercase;
            font-size:.78rem;
            letter-spacing:.08em;
            font-weight:800;
        }
        .ptr-auth-switch {
            margin: 1rem 0 .25rem;
            color: var(--ptr-muted)!important;
            font-size: .95rem;
        }
        .ptr-consent-copy {
            border-top: 1px solid var(--ptr-line);
            padding: .65rem 0 .45rem;
        }
        .ptr-consent-copy:first-child {
            border-top: 0;
        }
        .ptr-consent-copy strong {
            display:block;
            color: var(--ptr-text)!important;
            font-size: .9rem;
            line-height: 1.35;
            margin-bottom: .2rem;
        }
        .ptr-consent-copy p {
            color: var(--ptr-muted)!important;
            font-size: .78rem;
            line-height: 1.45;
            margin: 0;
        }
        .ptr-stat {
            min-height: 132px;
            padding: 1rem;
            border-radius: 10px;
            background: var(--ptr-surface);
            border: 1px solid var(--ptr-line);
            box-shadow: 0 10px 26px rgba(16, 24, 40, .055);
            margin-bottom: 1rem;
        }
        .ptr-stat span, .ptr-card p, .ptr-stat small { color: var(--ptr-muted)!important; }
        .ptr-stat strong {
            display:block;
            color: var(--ptr-text)!important;
            font-size: 2rem;
            margin: .45rem 0 .2rem;
            line-height: 1.05;
        }
        .ptr-stat:before {
            content:"";
            display:block;
            width: 38px;
            height: 6px;
            border-radius: 999px;
            margin-bottom: .75rem;
            background: var(--ptr-teal);
        }
        .ptr-blue:before { background: var(--ptr-blue); }
        .ptr-green:before { background: var(--ptr-green); }
        .ptr-amber:before { background: var(--ptr-amber); }
        .ptr-red:before { background: var(--ptr-red); }
        .ptr-card {
            background: var(--ptr-surface);
            border: 1px solid var(--ptr-line);
            border-radius: 10px;
            padding: 1rem 1.1rem;
            margin: .65rem 0;
            box-shadow: 0 10px 26px rgba(16, 24, 40, .05);
        }
        .ptr-card h3 { font-size: 1rem; margin:0 0 .35rem; color:var(--ptr-text)!important; }
        .ptr-card-teal { border-left: 5px solid var(--ptr-teal); }
        .ptr-card-blue { border-left: 5px solid var(--ptr-blue); }
        .ptr-card-neutral { border-left: 5px solid var(--ptr-line); }
        .ptr-pill {
            display:inline-flex;
            align-items:center;
            min-height: 30px;
            padding:.35rem .7rem;
            border-radius:999px;
            font-weight:700;
            font-size:.82rem;
            margin:.25rem .35rem .25rem 0;
            border:1px solid transparent;
        }
        .ptr-pill-teal { background:var(--ptr-teal-soft); color:var(--ptr-teal-dark)!important; }
        .ptr-pill-blue { background:var(--ptr-blue-soft); color:var(--ptr-blue)!important; }
        .ptr-pill-green { background:var(--ptr-green-soft); color:var(--ptr-green)!important; }
        .ptr-pill-amber { background:var(--ptr-amber-soft); color:var(--ptr-amber)!important; }
        .ptr-pill-red { background:var(--ptr-red-soft); color:var(--ptr-red)!important; }
        .ptr-message {
            background: var(--ptr-surface);
            border: 1px solid var(--ptr-line);
            border-radius: 10px;
            padding: .8rem 1rem;
            margin: .7rem 0;
            box-shadow: 0 8px 20px rgba(15, 23, 42, .04);
        }
        .ptr-message.mine {
            background: var(--ptr-teal-soft);
            border-color: rgba(10,124,124,.22);
        }
        .ptr-message-meta {
            color: var(--ptr-muted)!important;
            font-size:.78rem;
            font-weight:800;
            margin-bottom:.35rem;
        }
        div[data-testid="stForm"], div[data-testid="stExpander"], div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 10px!important;
            border-color: var(--ptr-line)!important;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: .25rem;
            border-bottom: 1px solid var(--ptr-line);
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px 8px 0 0;
            padding: .65rem .95rem;
        }
        .stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] button {
            border-radius: 8px!important;
            border: 1px solid var(--ptr-primary)!important;
            background: var(--ptr-primary)!important;
            color: #fff!important;
            font-weight: 750!important;
        }
        .stButton > button:hover, .stDownloadButton > button:hover, [data-testid="stFormSubmitButton"] button:hover {
            background: var(--ptr-primary-dark)!important;
            border-color: var(--ptr-primary-dark)!important;
        }
        input, textarea, [data-baseweb="select"] > div {
            border-radius: 8px!important;
        }
        .ptr-hero .ptr-eyebrow,
        .ptr-hero h1,
        .ptr-hero p,
        section.ptr-hero h1,
        section.ptr-hero p {
            color: #ffffff!important;
            opacity: 1!important;
            filter: none!important;
        }
        .ptr-hero .ptr-eyebrow {
            color: #a7f3e7!important;
        }
        [data-testid="stSidebar"] [data-baseweb="select"] > div {
            background: #ffffff!important;
            border-color: #cbd5e1!important;
        }
        [data-testid="stSidebar"] [data-baseweb="select"] span,
        [data-testid="stSidebar"] [data-baseweb="select"] svg {
            color: #101828!important;
            fill: #101828!important;
        }
        [data-baseweb="popover"],
        [data-baseweb="popover"] * ,
        [role="listbox"],
        [role="listbox"] * {
            color: #101828!important;
        }
        [data-baseweb="popover"] {
            background: #ffffff!important;
        }
        [role="option"] {
            color: #101828!important;
            background: #ffffff!important;
        }
        [role="option"]:hover,
        [aria-selected="true"] {
            background: #eef4ff!important;
            color: #101828!important;
        }
        h1, h2, h3 { letter-spacing: 0!important; }
        @media (max-width: 768px) {
            .block-container {
                padding: .85rem .85rem 4rem!important;
                max-width: 100%!important;
            }
            .ptr-hero {
                padding: 1.15rem;
                border-radius: 10px;
                margin-top: .1rem;
            }
            .ptr-hero h1 {
                font-size: 2rem;
                line-height: 1.08;
            }
            .ptr-hero p {
                font-size: .95rem;
            }
            .ptr-stat {
                min-height: auto;
                padding: .9rem;
            }
            .ptr-stat strong {
                font-size: 1.65rem;
            }
            .ptr-card {
                padding: .9rem;
            }
            .ptr-message {
                padding: .75rem;
            }
            div[data-testid="column"] {
                width: 100%!important;
                flex: 1 1 100%!important;
                min-width: 100%!important;
                margin-bottom: .55rem;
            }
            .stTabs [data-baseweb="tab-list"] {
                overflow-x: auto;
                overflow-y: hidden;
                flex-wrap: nowrap;
                scrollbar-width: thin;
            }
            .stTabs [data-baseweb="tab"] {
                white-space: nowrap;
                min-width: max-content;
            }
            [data-testid="stDataFrame"], [data-testid="stTable"] {
                overflow-x: auto;
            }
            .stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] button {
                width: 100%;
                min-height: 42px;
            }
        }
        </style>
    """
    st.markdown(base_css, unsafe_allow_html=True)
    if st.session_state.theme == "Dark":
        st.markdown(
            """
            <style>
            :root { color-scheme: dark; }
            :root {
                --ptr-bg:#0f172a;
                --ptr-surface:#111827;
                --ptr-line:#334155;
                --ptr-text:#e5e7eb;
                --ptr-muted:#b6c2d1;
            }
            .stApp, [data-testid="stAppViewContainer"], [data-testid="stSidebar"], [data-testid="stHeader"] {
                background:#0f172a!important; color:#e5e7eb!important;
            }
            h1,h2,h3,h4,p,label,span,div,button,small,li,td,th {
                color:#e5e7eb!important;
            }
            input, textarea, select, [data-baseweb="select"] > div, [data-testid="stTextInput"] input {
                background:#111827!important; color:#f9fafb!important; border-color:#334155!important;
            }
            [data-testid="stMetric"], [data-testid="stExpander"], [data-testid="stDataFrame"], .stTabs [data-baseweb="tab-list"] {
                background:#111827!important; border-color:#334155!important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <style>
            :root { color-scheme: light; }
            .stApp, [data-testid="stAppViewContainer"], [data-testid="stSidebar"], [data-testid="stHeader"] {
                background:#f8fafc!important; color:#0f172a!important;
            }
            h1,h2,h3,h4,p,label,span,div,button,small,li,td,th {
                color:#0f172a!important;
            }
            input, textarea, select, [data-baseweb="select"] > div {
                background:#ffffff!important; color:#0f172a!important; border-color:#cbd5e1!important;
            }
            [data-testid="stMetric"], [data-testid="stExpander"], [data-testid="stDataFrame"], .stTabs [data-baseweb="tab-list"] {
                background:#ffffff!important; border-color:#cbd5e1!important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )


st.set_page_config(page_title="Physio Tele-Rehab", layout="wide")
init_state()
patch_streamlit_text()
apply_theme()
sidebar()

if st.session_state.get("token") and st.session_state.get("role") == "patient" and st.session_state.route in ["patient", "onboarding"]:
    verification = api("GET", "/auth/email-verification/status") or {}
    if not verification.get("email_verified"):
        st.session_state.email_verified = False
        st.session_state.route = "verify_email"

if st.session_state.route == "login":
    login_page()
elif st.session_state.route == "verify_email":
    verify_email_page()
elif st.session_state.route == "onboarding":
    onboarding_page()
elif st.session_state.route == "patient":
    patient_dashboard()
else:
    therapist_dashboard()
