import json
import os
import re
import threading
import traceback
import unicodedata
from datetime import datetime
from html import escape
from urllib.parse import quote_plus

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from fpdf import FPDF
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


st.set_page_config(page_title="Personalized Rehab Exercise Recommender", layout="wide")

st.markdown(
    """
<style>
    .main {background-color: #cbd3da;}
    .stButton>button {background-color: #2E8B57; color: white; border-radius: 10px;}
    .card {background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); margin-bottom: 20px;}
    h1, h2, h3 {color: #1f4d3d;}
    .exercise-card {
        background: #ffffff;
        border: 1px solid #dce5df;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 3px 14px rgba(31,77,61,0.10);
        margin-bottom: 18px;
    }
    .exercise-visual {
        min-height: 138px;
        padding: 18px;
        background: linear-gradient(135deg, #1f4d3d 0%, #2E8B57 55%, #dcefe5 100%);
        color: #ffffff;
        display: flex;
        align-items: end;
    }
    .exercise-visual h3 {
        color: #ffffff;
        margin: 0;
        font-size: 1.25rem;
        line-height: 1.25;
    }
    .exercise-body {padding: 16px 18px;}
    .exercise-body ul {margin-top: 6px;}
    .exercise-meta {
        display: inline-block;
        margin: 4px 8px 8px 0;
        padding: 4px 8px;
        border-radius: 999px;
        background: #eef6f1;
        color: #1f4d3d;
        font-size: 0.82rem;
        font-weight: 600;
    }
    .video-link {
        display: inline-block;
        margin-top: 8px;
        padding: 8px 11px;
        border-radius: 8px;
        background: #1f4d3d;
        color: #ffffff !important;
        text-decoration: none;
        font-weight: 700;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.title("Personalized Rehab Exercise Recommender")
st.markdown("**Safe | Personalized | Expert-Guided**")


# ---------------- LOAD DATA ----------------
@st.cache_data(show_spinner=False)
def load_core_data():
    df = pd.read_excel("rehab_recommender.xlsx")
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    return df.fillna("")


core_df = load_core_data()


# ---------------- MODELS ----------------
@st.cache_resource(show_spinner=False)
def load_embedding_model():
    return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")


load_dotenv()


def get_secret(name):
    value = os.getenv(name)
    if value:
        return value
    try:
        value = st.secrets.get(name)
        if value:
            return value
        for section in ("general", "secrets"):
            scoped = st.secrets.get(section, {})
            if hasattr(scoped, "get"):
                value = scoped.get(name)
                if value:
                    return value
    except Exception:
        return None
    return None


def visible_secret_keys():
    try:
        keys = []
        for key, value in st.secrets.items():
            keys.append(str(key))
            if hasattr(value, "keys"):
                keys.extend(f"{key}.{nested}" for nested in value.keys())
        return sorted(keys)
    except Exception:
        return []


GROQ_API_KEY = get_secret("GROQ_API_KEY") or get_secret("GROK_API_KEY")
if not GROQ_API_KEY:
    st.error("Groq API key not found. Set GROQ_API_KEY in your environment or Streamlit secrets.")
    keys = visible_secret_keys()
    if keys:
        st.caption(f"Visible Streamlit secret names: {', '.join(keys)}")
    else:
        st.caption("No Streamlit secret names are visible to this app. Save secrets for this exact app, then reboot.")
    st.stop()


@st.cache_resource(show_spinner=False)
def load_llm(max_tokens=950):
    return ChatGroq(
        model="llama-3.1-8b-instant",
        api_key=GROQ_API_KEY,
        temperature=0.2,
        max_tokens=max_tokens,
        max_retries=3,
        timeout=45,
    )


@st.cache_data(show_spinner=False, ttl=3600)
def cached_llm_response(prompt, max_tokens=950):
    return load_llm(max_tokens=max_tokens).invoke(prompt).content


def describe_groq_error(exc):
    message = str(exc)
    if "getaddrinfo failed" in message or "ConnectError" in message:
        return (
            "Groq could not be reached because DNS/network resolution failed. "
            "Your API key may still be valid; check internet/DNS/firewall/VPN and retry."
        )
    if "401" in message or "invalid_api_key" in message.lower() or "Unauthorized" in message:
        return "Groq rejected the API key. Check GROQ_API_KEY in .env or Streamlit secrets."
    if "403" in message or "permissiondenied" in message.lower() or "access denied" in message.lower():
        return (
            "Groq refused the request with 403 Access denied. Your API key was loaded, but Groq is rejecting "
            "this network/account context. Check VPN/proxy/firewall, Groq account access, organization/project "
            "permissions, billing/usage status, and whether your current network is allowed to reach Groq."
        )
    if "429" in message or "rate" in message.lower():
        return "Groq rate limit was reached. Wait briefly and retry."
    if "timeout" in message.lower():
        return "Groq request timed out. Retry, or use Balanced evidence for a shorter request."
    return f"Groq request failed: {exc.__class__.__name__}. {message[:300]}"


BALANCED_RAG_SEARCH_K = 6
BALANCED_RAG_FETCH_K = 18
BALANCED_RAG_CHARS_PER_CHUNK = 700
BALANCED_MAX_RAG_CONTEXT_CHARS = 5200

DEEP_RAG_SEARCH_K = 12
DEEP_RAG_FETCH_K = 40
DEEP_RAG_CHARS_PER_CHUNK = 950
DEEP_MAX_RAG_CONTEXT_CHARS = 9500


# ====================== RAG (Textbooks) ======================
@st.cache_resource(show_spinner=False)
def load_rag_vectorstore():
    embedder = load_embedding_model()
    vectorstore_path = "textbook_vectorstore"
    if os.path.exists(vectorstore_path):
        return FAISS.load_local(vectorstore_path, embedder, allow_dangerous_deserialization=True)

    textbook_folder = "textbooks"
    if not os.path.isdir(textbook_folder):
        st.error("Textbook folder not found and no prebuilt vectorstore is available.")
        st.stop()

    st.info("Building textbook vector database. This can take several minutes on first run.")
    documents = []
    for filename in os.listdir(textbook_folder):
        if not filename.lower().endswith(".pdf"):
            continue
        try:
            loader = PyMuPDFLoader(os.path.join(textbook_folder, filename))
            docs = loader.load()
            for doc in docs:
                doc.metadata["source"] = filename
            documents.extend(docs)
        except Exception as exc:
            st.warning(f"Failed to load {filename}: {exc}")

    if not documents:
        st.error("No textbook documents could be loaded.")
        st.stop()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=250,
        separators=["\n\n", "\n", ".", " ", ""],
    )
    chunks = splitter.split_documents(documents)
    vectorstore = FAISS.from_documents(chunks, embedder)
    vectorstore.save_local(vectorstore_path)
    st.success(f"Processed {len(chunks)} textbook chunks.")
    return vectorstore


@st.cache_data(show_spinner=False, ttl=3600)
def retrieve_textbook_context(query, mode="Balanced evidence"):
    vectorstore = load_rag_vectorstore()
    search_k = DEEP_RAG_SEARCH_K if mode == "Deep evidence" else BALANCED_RAG_SEARCH_K
    fetch_k = DEEP_RAG_FETCH_K if mode == "Deep evidence" else BALANCED_RAG_FETCH_K
    retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={"k": search_k, "fetch_k": fetch_k, "lambda_mult": 0.45 if mode == "Deep evidence" else 0.65},
    )
    return build_textbook_context(retriever.invoke(query), mode)


def warm_rag_in_background():
    if st.session_state.get("rag_warm_started"):
        return

    def _warm():
        try:
            load_rag_vectorstore()
        except Exception:
            pass

    threading.Thread(target=_warm, daemon=True).start()
    st.session_state.rag_warm_started = True


# ====================== SMART QUERY BUILDER ======================
def build_rag_query(condition, goal, symptoms):
    condition_lower = condition.lower()
    enriched_condition = condition

    if "headache" in condition_lower:
        enriched_condition += """
        cervicogenic headache tension headache cervical spine dysfunction
        neck posture upper trapezius tightness deep neck flexors
        headache physiotherapy posture correction
        """
    elif "knee" in condition_lower:
        enriched_condition += """
        knee rehabilitation quadriceps strengthening patellofemoral pain
        ACL rehab meniscus rehab proprioception gait retraining
        """
    elif "stroke" in condition_lower:
        enriched_condition += """
        neurological rehabilitation gait training balance training
        coordination exercises neuroplasticity stroke physiotherapy mobility recovery
        """
    elif "shoulder" in condition_lower:
        enriched_condition += """
        rotator cuff rehabilitation scapular stabilization shoulder mobility
        impingement syndrome shoulder physiotherapy
        """
    elif "low back" in condition_lower or "back pain" in condition_lower:
        enriched_condition += """
        lumbar stabilization core strengthening lumbar mobility posture correction
        low back rehabilitation spine physiotherapy
        """
    elif "ankle" in condition_lower:
        enriched_condition += """
        ankle sprain rehabilitation balance training proprioception
        ankle strengthening gait mechanics
        """
    elif "neck" in condition_lower:
        enriched_condition += """
        cervical rehabilitation posture correction neck mobility
        deep neck flexor training cervical stabilization
        """

    return f"""
    {enriched_condition}

    Symptoms:
    {symptoms}

    Rehabilitation goal:
    {goal}

    therapeutic exercise progression precautions contraindications
    pain management strengthening stretching mobility training functional recovery
    home exercise program safety guidelines
    """


# ====================== SIDEBAR & INPUTS ======================
st.subheader("Your Information")

col1, col2 = st.columns([2, 1])
with col1:
    condition = st.text_input("**Main Condition**", placeholder="Knee Osteoarthritis")
    goal = st.selectbox("**Your Main Goal**", ["Pain relief", "Mobility", "Strength", "Balance", "Return to sport"])
    other_goals = st.text_area(
        "**Other Goals (Optional)**",
        placeholder="e.g. walk for 30 minutes, climb stairs, return to work, sleep without pain...",
    )
    specific_symptoms = st.text_area("**Specific Symptoms**", placeholder="Swelling, stiffness, instability, numbness...")

with col2:
    age = st.number_input("**Age**", 18, 90, 45)
    gender = st.selectbox("**Gender**", ["Male", "Female"])
    pain_level = st.slider("**Pain Level (1-10)**", 1, 10, 5)

st.subheader("Important History & Details")
col_a, col_b = st.columns(2)
with col_a:
    time_since_injury = st.selectbox("Time Since Injury/Onset", ["Acute (<2 weeks)", "Subacute (2-6 weeks)", "Chronic (>6 weeks)"])
    bmi = st.number_input("**BMI**", 15.0, 45.0, 25.0)
    condition_duration = st.selectbox("**Condition Duration**", ["First episode", "Recurrent", "Long-term (>1 year)"])
    daily_activity = st.selectbox("**Daily Activity Level**", ["Sedentary", "Light", "Moderate", "Active"])

with col_b:
    recent_surgery = st.selectbox("Recent Surgery?", ["No", "Yes - Within 3 months", "Yes - Older"])
    high_bp = st.selectbox("High Blood Pressure?", ["No", "Yes - Controlled", "Yes - Uncontrolled"])
    dizziness = st.selectbox("Dizziness / Balance Issues?", ["No", "Occasional", "Frequent"])
    diabetes = st.selectbox("Diabetes?", ["No", "Yes - Controlled", "Yes - Uncontrolled"])

equipment = st.multiselect(
    "**Equipment Available at Home**",
    [
        "None",
        "Chair",
        "Resistance Band",
        "Towel",
        "Dumbbells",
        "Mat",
        "Wall",
        "Hot Water (Heating)",
        "Ice Pack / Cold Compress (Cooling)",
        "Heating Pad",
        "Foam Roller",
    ],
)

previous_response = st.text_area(
    "Previous Exercises Tried & Response",
    placeholder="e.g. Straight leg raise helped, squats increased pain...",
)

with st.expander("Generation Options"):
    generation_mode = st.radio(
        "Evidence mode",
        ["Balanced evidence", "Deep evidence"],
        index=0,
        help=(
            "Both modes use textbook retrieval. Balanced is faster; Deep retrieves a little more context "
            "for complex cases."
        ),
        horizontal=True,
    )

def valid_conditions(text):
    if not text:
        st.warning("Please enter a valid condition.")
        return False
    if len(text) < 3:
        st.warning("Condition must be at least 3 characters long.")
        return False
    if sum(c.isalpha() or c.isspace() for c in text) / len(text) < 0.7:
        st.warning("Condition must contain mostly letters and spaces.")
        return False
    junk_text = ["asdf", "qwer", "zxcv", "lorem", "ipsum", "test", "1234"]
    if text.lower() in junk_text:
        st.warning("Please enter a valid condition.")
        return False
    return True


def build_patient_profile():
    return {
        "age": age,
        "gender": gender,
        "bmi": bmi,
        "condition": condition.strip(),
        "condition_duration": condition_duration,
        "time_since_injury": time_since_injury,
        "pain_level": pain_level,
        "symptoms": specific_symptoms.strip(),
        "goal": goal,
        "other_goals": other_goals.strip() or "None provided",
        "daily_activity": daily_activity,
        "recent_surgery": recent_surgery,
        "high_blood_pressure": high_bp,
        "dizziness_balance": dizziness,
        "diabetes": diabetes,
        "equipment": equipment or ["None"],
        "previous_exercise_response": previous_response.strip(),
    }


def format_patient_profile(profile_data):
    return "\n".join(f"- {key.replace('_', ' ').title()}: {value}" for key, value in profile_data.items())


def screen_red_flags(profile_data):
    text = " ".join(
        [
            profile_data["condition"],
            profile_data["symptoms"],
            profile_data["previous_exercise_response"],
        ]
    ).lower()
    blocking = []
    cautions = []

    emergency_patterns = {
        "Possible stroke or acute facial nerve emergency": [
            r"\bfacial droop\b",
            r"\bfacial deviation\b",
            r"\bone side of (the )?face\b",
            r"\bslurred speech\b",
            r"\bsudden weakness\b",
        ],
        "Possible cauda equina or serious spinal nerve compression": [
            r"\bsaddle anesthesia\b",
            r"\bloss of bladder\b",
            r"\bloss of bowel\b",
            r"\burinary retention\b",
            r"\bcauda equina\b",
        ],
        "Possible DVT or pulmonary/cardiac emergency": [
            r"\bcalf swelling\b",
            r"\bcalf pain\b",
            r"\bshortness of breath\b",
            r"\bchest pain\b",
            r"\bdvt\b",
        ],
        "Possible fracture, infection, or systemic illness": [
            r"\bfracture\b",
            r"\bfever\b",
            r"\bunexplained weight loss\b",
            r"\bnight pain\b",
            r"\bcancer\b",
        ],
    }

    for issue, patterns in emergency_patterns.items():
        if any(re.search(pattern, text) for pattern in patterns):
            blocking.append(issue)

    if profile_data["high_blood_pressure"] == "Yes - Uncontrolled":
        blocking.append("Uncontrolled high blood pressure needs medical clearance before exercise.")
    if profile_data["diabetes"] == "Yes - Uncontrolled":
        cautions.append("Uncontrolled diabetes requires extra monitoring and medical clearance for exercise intensity.")
    if profile_data["dizziness_balance"] == "Frequent":
        cautions.append("Frequent dizziness or balance issues require guarded, supported exercise only.")
    if profile_data["recent_surgery"] == "Yes - Within 3 months":
        cautions.append("Recent surgery requires protocol-specific restrictions and surgeon/physiotherapist clearance.")
    if profile_data["pain_level"] >= 8:
        cautions.append("Severe pain suggests a highly irritable condition; recommendations must remain gentle.")

    return blocking, cautions


def match_condition_rows(condition_text):
    condition_text = condition_text.strip().lower()
    return core_df[core_df["condition"].str.lower().str.contains(re.escape(condition_text), na=False)]


def rank_dataset_candidates(rows, profile_data, limit=8):
    candidates = rows.copy()

    if profile_data["pain_level"] >= 7 and "difficulty" in candidates:
        beginner = candidates["difficulty"].str.contains("Beginner", case=False, na=False)
        if beginner.any():
            candidates = candidates[beginner]

    if "rehab_stage" in candidates:
        if profile_data["time_since_injury"].startswith("Acute"):
            stage_match = candidates["rehab_stage"].eq("") | candidates["rehab_stage"].str.contains(r"\bacute\b", case=False, na=False)
        elif profile_data["time_since_injury"].startswith("Subacute"):
            stage_match = candidates["rehab_stage"].eq("") | candidates["rehab_stage"].str.contains("subacute", case=False, na=False)
        else:
            stage_match = candidates["rehab_stage"].eq("") | candidates["rehab_stage"].str.contains("chronic|strengthening|advanced", case=False, na=False)
        if stage_match.any():
            candidates = candidates[stage_match]

    if "equipment" in candidates and profile_data["equipment"] and "None" not in profile_data["equipment"]:
        equipment_terms = "|".join(re.escape(item) for item in profile_data["equipment"])
        no_equipment = candidates["equipment"].eq("")
        matching_equipment = candidates["equipment"].str.contains(equipment_terms, case=False, na=False)
        if (no_equipment | matching_equipment).any():
            candidates = candidates[no_equipment | matching_equipment]

    difficulty_order = {"Beginner": 0, "Intermediate": 1, "Advanced": 2}
    if "difficulty" in candidates:
        candidates = candidates.assign(
            _difficulty_rank=candidates["difficulty"].map(difficulty_order).fillna(3)
        ).sort_values(["_difficulty_rank", "exercise_name"])

    return candidates.head(limit)


def format_dataset_exercises(rows):
    if rows.empty:
        return (
            "No direct condition match was found in the structured exercise dataset. "
            "Use the patient profile and internal textbook evidence to generate a clinically appropriate plan."
        )

    fields = [
        "exercise_name",
        "condition",
        "body_part",
        "difficulty",
        "equipment",
        "reps_sets",
        "video_url",
        "benefits",
        "precautions",
        "contraindications",
        "progression_notes",
        "rehab_stage",
        "pain_severity_suitability",
        "mobility_level_suitability",
        "recovery_goals",
    ]
    lines = []
    for _, row in rows.iterrows():
        parts = []
        for field in fields:
            value = str(row.get(field, "")).strip()
            if value:
                parts.append(f"{field.replace('_', ' ')}: {value}")
        lines.append("- " + " | ".join(parts))
    return "\n".join(lines)


def build_fallback_plan(profile_data, rows, cautions, reason=None):
    selected = rows.head(5)
    lines = [
        "Safety Summary:",
        "This plan uses the structured exercise dataset because the AI service was unavailable or slow. "
        "Keep all exercises gentle, controlled, and pain-limited.",
    ]
    if reason:
        lines.append(f"Service note: {reason}")
    if cautions:
        lines.extend([f"- {caution}" for caution in cautions])
    lines.append(
        "- Stop and seek medical advice if you develop worsening pain, new numbness or weakness, dizziness, "
        "chest pain, shortness of breath, marked swelling, fever, or any neurological change."
    )

    lines.append("\nTop Recommended Exercises:")
    if selected.empty:
        lines.extend(
            [
                "No structured dataset exercise matched your condition closely enough for an automatic exercise list.",
                "Please use the safety rules below and consult a qualified physiotherapist for a condition-specific prescription.",
                "\nEquipment-Based Modifications:",
                f"Available equipment: {', '.join(profile_data['equipment'])}.",
                "\nWeekly Progression:",
                "Week 1-2: Gentle, pain-free mobility only.",
                "Week 3-4: Progress only after clinician review or if symptoms clearly improve.",
                "Week 5+: Build activity gradually with professional guidance.",
                "\nWhen To Seek Medical Care:",
                "Seek medical care for severe or worsening symptoms, neurological signs, chest pain, shortness of breath, swelling, fever, or uncertainty about exercise safety.",
            ]
        )
        return "\n".join(lines)

    for index, (_, row) in enumerate(selected.iterrows(), start=1):
        name = str(row.get("exercise_name", "Exercise")).strip() or "Exercise"
        reps = str(row.get("reps_sets", "Start with 1-2 gentle sets as tolerated.")).strip()
        benefits = str(row.get("benefits", "Supports your rehabilitation goal.")).strip()
        precautions = str(row.get("precautions", "Do not push into pain.")).strip()
        contraindications = str(row.get("contraindications", "")).strip()
        equipment_needed = str(row.get("equipment", "")).strip() or "No equipment"
        progression = str(row.get("progression_notes", "Progress only if symptoms remain settled.")).strip()

        lines.extend(
            [
                f"{index}. {name}",
                f"- Purpose: {benefits}",
                "- How to do it:",
                "  - Step 1: Set up in a comfortable, supported position.",
                "  - Step 2: Perform the movement slowly and within a comfortable range.",
                "  - Step 3: Return to the starting position with control.",
                f"- Dosage: {reps}",
                "- Frequency: Start 3-4 days per week unless symptoms increase.",
                f"- Equipment: {equipment_needed}",
                f"- Stop or modify if: {precautions}",
            ]
        )
        if contraindications:
            lines.append(f"- Avoid or get clinician review if present: {contraindications}")
        lines.append(f"- Progression: {progression}")

    lines.extend(
        [
            "\nEquipment-Based Modifications:",
            f"Use only available equipment: {', '.join(profile_data['equipment'])}. If an exercise needs equipment you do not have, choose the no-equipment option or ask a clinician for a substitute.",
            "\nWeekly Progression:",
            "Week 1-2: Use the easiest version and keep pain at or below 3/10 during and after exercise.",
            "Week 3-4: Add small increases in repetitions or range only if symptoms settle within 24 hours.",
            "Week 5+: Progress resistance, balance challenge, or function gradually, one variable at a time.",
            "\nWhen To Seek Medical Care:",
            "Seek medical care for severe or worsening symptoms, neurological signs, chest pain, shortness of breath, unexplained swelling, fever, or if you are unsure whether exercise is safe.",
        ]
    )
    return "\n".join(lines)


def build_textbook_context(docs, mode="Balanced evidence"):
    chars_per_chunk = DEEP_RAG_CHARS_PER_CHUNK if mode == "Deep evidence" else BALANCED_RAG_CHARS_PER_CHUNK
    max_context_chars = DEEP_MAX_RAG_CONTEXT_CHARS if mode == "Deep evidence" else BALANCED_MAX_RAG_CONTEXT_CHARS
    chunks = []
    seen = set()
    for index, doc in enumerate(docs, start=1):
        source = doc.metadata.get("source", "Unknown source")
        page = doc.metadata.get("page", "")
        page_label = f", page {page + 1}" if isinstance(page, int) else ""
        clean_text = " ".join(doc.page_content.split())
        fingerprint = clean_text[:220].lower()
        if not clean_text or fingerprint in seen:
            continue
        seen.add(fingerprint)
        chunks.append(f"[Internal evidence {index}: {source}{page_label}]\n{clean_text[:chars_per_chunk]}")

    context = "\n\n".join(chunks)
    return context[:max_context_chars]


def make_pdf_bytes(condition_text, plan_text, profile_data):
    pdf_text = unicodedata.normalize("NFKD", plan_text).encode("latin-1", "ignore").decode("latin-1")
    safe_condition = unicodedata.normalize("NFKD", condition_text).encode("latin-1", "ignore").decode("latin-1")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Physiotherapy Home Exercise Prescription", ln=True, align="C")
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 7, f"Date: {datetime.now().strftime('%Y-%m-%d')}", ln=True)
    pdf.cell(0, 7, f"Condition: {safe_condition}", ln=True)
    pdf.cell(0, 7, f"Age: {profile_data['age']} | Gender: {profile_data['gender']} | Pain: {profile_data['pain_level']}/10", ln=True)
    pdf.cell(0, 7, f"Goal: {profile_data['goal']} | Onset: {profile_data['time_since_injury']}", ln=True)
    if profile_data.get("other_goals") and profile_data["other_goals"] != "None provided":
        other_goals_text = unicodedata.normalize("NFKD", profile_data["other_goals"]).encode("latin-1", "ignore").decode("latin-1")
        pdf.multi_cell(0, 7, f"Other goals: {other_goals_text}")
    pdf.ln(3)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, "Prescription", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 6, pdf_text)
    pdf.ln(3)
    pdf.set_font("Arial", "I", 9)
    pdf.multi_cell(
        0,
        5,
        "Educational support only. Follow the stop rules in this prescription and consult a qualified physiotherapist for individualized supervision.",
    )
    return pdf.output(dest="S").encode("latin-1")


def youtube_search_url(exercise_name, condition_text):
    query = quote_plus(f"{exercise_name} physiotherapy exercise {condition_text}")
    return f"https://www.youtube.com/results?search_query={query}"


def build_video_lookup(rows, condition_text):
    lookup = {}
    if rows.empty:
        return lookup
    for _, row in rows.iterrows():
        name = str(row.get("exercise_name", "")).strip()
        if not name:
            continue
        url = str(row.get("video_url", "")).strip() or youtube_search_url(name, condition_text)
        lookup[name.lower()] = url
    return lookup


def get_video_url(exercise_name, video_lookup, condition_text):
    key = exercise_name.lower().strip()
    if key in video_lookup:
        return video_lookup[key]
    for known_name, url in video_lookup.items():
        if known_name in key or key in known_name:
            return url
    return youtube_search_url(exercise_name, condition_text)


def parse_exercise_cards(plan_text):
    exercise_start = re.compile(r"^\s*(\d+)[\.\)]\s+(.+?)\s*$")
    section_start = re.compile(r"^\s*(Consultant Summary|Exercise Prescription|Equipment Modifications|Weekly Progression|When To Seek Medical Care):\s*$", re.I)
    cards = []
    current = None

    for raw_line in plan_text.splitlines():
        line = raw_line.rstrip()
        match = exercise_start.match(line)
        if match:
            if current:
                cards.append(current)
            title = re.sub(r"[*_`#]", "", match.group(2)).strip()
            current = {"title": title, "lines": []}
            continue
        if current:
            if section_start.match(line) and "exercise prescription" not in line.lower():
                cards.append(current)
                current = None
                continue
            if line.strip():
                current["lines"].append(line)

    if current:
        cards.append(current)
    return cards


def render_exercise_cards(plan_text, video_lookup, condition_text):
    cards = parse_exercise_cards(plan_text)
    if not cards:
        st.markdown(plan_text)
        return

    st.subheader("Exercise Prescription")
    for card in cards:
        title = card["title"]
        video_url = get_video_url(title, video_lookup, condition_text)
        image_query = quote_plus(f"physiotherapy exercise {title}")
        image_url = f"https://source.unsplash.com/900x420/?{image_query}"
        body = "\n".join(card["lines"])
        body_html = escape(body).replace("\n", "<br>")
        st.markdown(
            f"""
<div class="exercise-card">
    <div class="exercise-visual" style="background-image: linear-gradient(135deg, rgba(31,77,61,0.92), rgba(46,139,87,0.70)), url('{image_url}'); background-size: cover; background-position: center;">
        <h3>{escape(title)}</h3>
    </div>
    <div class="exercise-body">
        <span class="exercise-meta">Home exercise</span>
        <span class="exercise-meta">Personalized</span>
        <div>{body_html}</div>
        <a class="video-link" href="{escape(video_url)}" target="_blank" rel="noopener noreferrer">Watch video guide</a>
    </div>
</div>
""",
            unsafe_allow_html=True,
        )


# ====================== CLINICAL VETTING ENGINE ======================
def clinical_vet(profile, dataset_ex, textbook_context, cautions, mode):
    if mode == "Deep evidence":
        mode_instruction = """
Mode: Deep evidence.
- Provide a more detailed plan with explicit clinical reasoning for each exercise.
- Include stage-specific progression criteria, regression options, and monitoring rules.
- Use 4-5 exercises if safe and relevant.
"""
        max_tokens = 1450
    else:
        mode_instruction = """
Mode: Balanced evidence.
- Provide a concise, practical plan.
- Include the strongest 3-4 exercises only.
"""
        max_tokens = 950

    prompt = f"""
You are an expert consultant physiotherapist writing a personalized home-exercise prescription.
Speak directly to the patient as "you" and "your".
This is an educational home-exercise support tool, not a diagnosis or a replacement for in-person care.
Use expert clinical judgment: be specific, confident, and practical, while escalating unsafe or unclear presentations to medical/physiotherapy review.

{mode_instruction}

PATIENT PROFILE:
{profile}

DATASET EXERCISE CANDIDATES:
{dataset_ex}

INTERNAL TEXTBOOK EVIDENCE:
{textbook_context}

ADDITIONAL SAFETY CAUTIONS:
{chr(10).join(f"- {item}" for item in cautions) if cautions else "- None reported."}

Rules:
- Use every patient profile item when tailoring the prescription: age, gender, BMI, condition, duration, onset stage, pain level, symptoms, main goal, other goals, activity level, surgery history, blood pressure, dizziness/balance, diabetes, equipment, and previous exercise response.
- Prefer structured dataset exercises when they match the condition and profile.
- If the structured dataset has no direct condition match, use internal textbook evidence and expert physiotherapy reasoning from the full patient profile to generate the plan.
- If both dataset and textbook evidence are sparse, still provide a safe, practical consultant prescription using general physiotherapy principles, but make it cautious and advise in-person review when needed.
- Use textbook context to refine exercise choice, dosage, precautions, and progression; do not override contraindications.
- Do not mention textbooks, sources, source labels, retrieval, internal evidence, dataset, or AI process to the patient.
- Do not recommend exercises that conflict with listed contraindications, severe pain, surgery status, dizziness, uncontrolled conditions, or equipment availability.
- Keep intensity low for severe pain, acute onset, post-surgical status, frequent dizziness, or uncontrolled diabetes.
- Include clear stop rules: worsening pain, numbness, weakness, dizziness, chest pain, shortness of breath, swelling, fever, or neurological change.
- Do not mention internal chain-of-thought or hidden reasoning.
- Use clear bullets and short lines. Do not write exercise instructions as dense paragraphs.
- Each exercise must have the exact sub-bullets shown below.
- Each exercise must include a Video line. If a dataset video_url is available, use it. If not, write "Video: Provided in the exercise card".

Output Format:
Consultant Summary:
- 2-4 short bullet points.

Exercise Prescription:

1. Exercise name
   - Purpose:
   - How to do it:
     - Step 1:
     - Step 2:
     - Step 3:
   - Dosage:
   - Frequency:
   - Progress when:
   - Stop or modify if:
   - Video:

Equipment Modifications:
- Bullet points only.

Weekly Progression:
- Week 1-2:
- Week 3-4:
- Week 5+:

When To Seek Medical Care:
- Bullet points only.
"""
    return cached_llm_response(prompt, max_tokens=max_tokens)


# ====================== GENERATE PLAN ======================
save_plan_locally = st.checkbox(
    "Save this plan locally on this device",
    value=False,
    help="For privacy, plans are not saved unless you choose this option.",
)

if st.button("Generate Personalized Plan", type="primary", use_container_width=True, key="generate_btn"):
    if not valid_conditions(condition):
        st.error("Please enter a valid condition to generate a plan.")
        st.stop()

    profile_data = build_patient_profile()
    blocking_red_flags, safety_cautions = screen_red_flags(profile_data)

    if blocking_red_flags:
        st.error("This presentation needs medical review before exercise recommendations.")
        for item in blocking_red_flags:
            st.warning(item)
        st.info("Please seek urgent medical care or contact a qualified clinician before starting exercises.")
        st.stop()

    with st.spinner("Creating your plan..."):
        try:
            matched_rows = match_condition_rows(condition)

            candidate_limit = 12 if generation_mode == "Deep evidence" else 8
            if matched_rows.empty:
                candidate_rows = matched_rows
            else:
                candidate_rows = rank_dataset_candidates(matched_rows, profile_data, limit=candidate_limit)

            combined_goals = f"{goal}. {other_goals.strip()}" if other_goals.strip() else goal
            rag_query = build_rag_query(condition, combined_goals, specific_symptoms)
            if generation_mode == "Deep evidence":
                rag_query += """
                clinical reasoning exercise dosage adverse events differential precautions
                progression criteria regression criteria monitoring response to pain
                condition-specific contraindications functional outcomes
                """
            textbook_context = retrieve_textbook_context(rag_query, generation_mode)

            dataset_exercises = format_dataset_exercises(candidate_rows)
            profile = format_patient_profile(profile_data)

            try:
                final_plan = clinical_vet(profile, dataset_exercises, textbook_context, safety_cautions, generation_mode)
            except Exception as llm_error:
                st.error(describe_groq_error(llm_error))
                st.info("The plan was not generated because Groq rejected the request. Fix the Groq/network issue, then click Generate again.")
                st.stop()

            st.session_state.final_plan = final_plan
            st.session_state.condition = condition
            st.session_state.profile = profile_data
            st.session_state.textbook_context = textbook_context
            st.session_state.dataset_exercises = dataset_exercises
            st.session_state.video_lookup = build_video_lookup(candidate_rows, condition)

            st.success("Plan generated successfully.")
            render_exercise_cards(final_plan, st.session_state.video_lookup, condition)
            with st.expander("View full prescription text"):
                st.markdown(final_plan)

            if save_plan_locally:
                plan_data = {
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "condition": condition,
                    "age": age,
                    "pain_level": pain_level,
                    "plan": final_plan,
                }
                save_path = "saved_plans.json"
                if os.path.exists(save_path):
                    with open(save_path, "r", encoding="utf-8") as f:
                        all_plans = json.load(f)
                else:
                    all_plans = []
                all_plans.append(plan_data)
                with open(save_path, "w", encoding="utf-8") as f:
                    json.dump(all_plans, f, indent=2)
                st.caption("Saved locally to saved_plans.json.")

            pdf_bytes = make_pdf_bytes(condition, final_plan, profile_data)
            safe_filename_condition = re.sub(r"[^A-Za-z0-9_-]+", "_", condition.strip()).strip("_")
            st.download_button(
                label="Download Exercise Prescription PDF",
                key="download_pdf",
                data=pdf_bytes,
                file_name=f"Exercise_Prescription_{safe_filename_condition or 'plan'}.pdf",
                mime="application/pdf",
            )
        except Exception:
            st.error("Error generating plan. Please try again.")
            with st.expander("Technical details"):
                st.code(traceback.format_exc())


# ====================== CHAT INTERFACE ======================
if "final_plan" in st.session_state:
    st.subheader("Ask Questions About Your Plan")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_question = st.chat_input("Ask about modifications, progression, pain concerns, or equipment options...")
    if user_question:
        st.session_state.chat_history.append({"role": "user", "content": user_question})

        with st.chat_message("user"):
            st.markdown(user_question)

        chat_profile = format_patient_profile(st.session_state.get("profile", {}))
        question_profile = {
            "condition": st.session_state.get("condition", ""),
            "symptoms": user_question,
            "previous_exercise_response": "",
            "high_blood_pressure": high_bp,
            "diabetes": diabetes,
            "dizziness_balance": dizziness,
            "recent_surgery": recent_surgery,
            "pain_level": pain_level,
            "other_goals": other_goals.strip() or "None provided",
        }
        blocking_red_flags, _ = screen_red_flags(question_profile)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                if blocking_red_flags:
                    answer = (
                        "That symptom could be a red flag. Please pause exercise and seek medical review before "
                        "continuing. If symptoms are sudden, severe, or worsening, seek urgent care."
                    )
                else:
                    stored_textbook_context = st.session_state.get("textbook_context", "")
                    stored_dataset_exercises = st.session_state.get("dataset_exercises", "")
                    try:
                        question_context = retrieve_textbook_context(
                            f"{st.session_state.get('condition', '')}\n{user_question}\nprecautions contraindications progression",
                            "Balanced evidence",
                        )
                    except Exception:
                        question_context = ""
                    chat_prompt = f"""
Patient profile:
{chat_profile}

Current rehab plan:
{st.session_state.final_plan[:3500]}

Dataset exercise candidates used for the plan:
{stored_dataset_exercises[:2200]}

Internal textbook evidence used for the plan:
{stored_textbook_context[:3000]}

Additional internal textbook evidence for this question:
{question_context[:1800]}

Patient question:
{user_question}

Answer as an expert consultant physiotherapist. Stay within the generated plan, exercise candidates,
and internal textbook evidence. Do not mention textbooks, source labels, retrieval, internal evidence,
dataset, or AI process to the patient. If the question asks for something unsupported or unsafe, say so
and give a safer alternative. Include stop rules when pain, dizziness, numbness, weakness, chest pain,
or shortness of breath is mentioned. Do not diagnose new conditions.
"""
                    try:
                        answer = cached_llm_response(chat_prompt, max_tokens=950)
                    except Exception as chat_error:
                        answer = f"Groq could not answer this chat message. {describe_groq_error(chat_error)}"
                st.markdown(answer)
                st.session_state.chat_history.append({"role": "assistant", "content": answer})


st.markdown("---")
st.markdown("**Dr Obasi Kizito (BPT, MRTB)**")
st.markdown("Email: Donsmart0316@gmail.com")
st.markdown("Need a consultation? Feel free to reach out directly.")
st.caption("Educational tool only | Always consult a qualified physiotherapist | Stop if pain increases")
warm_rag_in_background()
