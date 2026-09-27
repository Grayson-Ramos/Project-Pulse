"""
app.py
------
Stage 1 (barebone) MBA Student Lifecycle Dashboard.

Implements the Sprint 1 backlog (US-01 through US-16) using mock in-memory
data. Real authentication, a live SQL Server connection, and richer styling
are deliberately deferred to later stages -- this stage focuses on
structure, navigation, and correct behavior against the acceptance
criteria.

Run with:
    streamlit run app.py
"""

from datetime import datetime

import pandas as pd
import streamlit as st
import streamlit as st
from supabase import create_client, Client

# 1. Initialize the connection
@st.cache_resource
def init_connection() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# 2. Fetch data (Cached to prevent hitting the DB on every button click)
@st.cache_data(ttl=600) # Caches results for 10 minutes
def get_enrollments():
    # Because you set up Foreign Keys, you can select (*) from enrollments 
    # and nest the linked records from students, programs, and advisers.
    response = supabase.table("enrollments").select(
        "*, students(*), programs(*), advisers(*)"
    ).execute()
    
    return response.data

# 3. Display in Streamlit
st.title("OBE Pilot Database")

data = get_enrollments()

if data:
    st.dataframe(data)
else:
    st.warning("No data found or connection failed.")


)

# ---------------------------------------------------------------------------
# Page config & light styling
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="MBA Student Lifecycle Dashboard",
    page_icon="🎓",
    layout="wide",
)

st.markdown(
    """
    <style>
        .main-header {
            padding: 1.1rem 1.6rem;
            background: linear-gradient(90deg, #1e293b 0%, #334155 100%);
            border-radius: 14px;
            color: #f8fafc;
            margin-bottom: 1.4rem;
        }
        .main-header h1 { margin: 0; font-size: 1.4rem; }
        .main-header p { margin: 0; opacity: 0.75; font-size: 0.85rem; }
        .stat-card {
            padding: 1.1rem 1.2rem;
            border-radius: 14px;
            color: white;
            height: 100%;
        }
        .stat-card .label { font-size: 0.8rem; opacity: 0.9; }
        .stat-card .value { font-size: 1.9rem; font-weight: 700; line-height: 1.2; }
        .stat-card .sub { font-size: 0.75rem; opacity: 0.85; margin-top: 0.2rem; }
        .status-pill {
            padding: 0.15rem 0.55rem;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 600;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ROLES = ["Dean", "Program Chair", "Faculty/Advisor", "IT/Admin"]

# Which nav sections each role is allowed to see (US-01: role-based menus)
ROLE_MENUS = {
    "Dean": ["Executive KPIs"],
    "Program Chair": ["Student List"],
    "Faculty/Advisor": ["Student List", "Student Profile"],
    "IT/Admin": [
        "Program Configuration",
        "Field Mapping",
        "Data Connection",
        "Permissions",
        "Sync Log",
        "Access Log",
    ],
}

COURSEWORK_COLOR = {"Completed": "🟢", "Pending": "🟡", "Cancelled": "🔴"}
COMP_EXAM_COLOR = {"Passed": "🟢", "In-Progress": "🟡", "Incomplete": "🔴"}
CAPSTONE_COLOR = {"Defended for Completion": "🟢", "In-Progress": "🟡"}

CARD_COLORS = {"green": "#16a34a", "yellow": "#d97706", "red": "#dc2626", "slate": "#334155"}


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
def init_state():
    defaults = {
        "role": "Dean",
        "program": PROGRAMS[0],
        "selected_student_id": None,
        "access_log": [],
        "last_updated": datetime.now(),
        "nav_section": ROLE_MENUS["Dean"][0],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_state()


def log_access(role: str, program: str):
    """US-01: record each simulated login so IT/Admin can audit access."""
    st.session_state.access_log.insert(
        0,
        {
            "Timestamp": datetime.now(),
            "Role": role,
            "Program": program,
            "Event": "Login (role switched)",
        },
    )
    st.session_state.access_log = st.session_state.access_log[:50]


# ---------------------------------------------------------------------------
# Data loading (cached mock layer -- swap for a live query in a later stage)
# ---------------------------------------------------------------------------
@st.cache_data
def load_students(program: str) -> pd.DataFrame:
    return generate_student_data(program)


# ---------------------------------------------------------------------------
# Small UI helpers
# ---------------------------------------------------------------------------
def stat_card(column, label, value, sub, color_key="slate"):
    column.markdown(
        f"""
        <div class="stat-card" style="background-color:{CARD_COLORS[color_key]};">
            <div class="label">{label}</div>
            <div class="value">{value}</div>
            <div class="sub">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def dominant_color(counts: pd.Series, order: list) -> str:
    """Pick the color of whichever status has the most students, used to
    color a summary card. `order` maps status -> color key."""
    if counts.empty:
        return "slate"
    top_status = counts.idxmax()
    return order.get(top_status, "slate")


def render_sidebar():
    with st.sidebar:
        st.markdown("### 🎓 Dashboard Access")
        st.caption("Stage 1 uses a simulated login. Real authentication "
                    "(US-01) will replace this control in a later stage.")

        role = st.selectbox("Role", ROLES, index=ROLES.index(st.session_state.role))
        if role != st.session_state.role:
            st.session_state.role = role
            st.session_state.nav_section = ROLE_MENUS[role][0]
            st.session_state.selected_student_id = None
            log_access(role, st.session_state.program)

        st.markdown("---")
        st.markdown("### 🏫 Active Program")
        st.caption("Set by IT/Admin (US-02). All views below filter to this program.")
        program = st.selectbox("Program", PROGRAMS, index=PROGRAMS.index(st.session_state.program))
        if program != st.session_state.program:
            st.session_state.program = program
            st.session_state.selected_student_id = None
            st.session_state.last_updated = datetime.now()

        st.markdown("---")
        st.caption(f"📅 Data last updated: **{st.session_state.last_updated.strftime('%b %d, %Y · %I:%M %p')}**")
        if st.button("🔄 Simulate data refresh", use_container_width=True):
            st.cache_data.clear()
            st.session_state.last_updated = datetime.now()
            st.rerun()

        st.markdown("---")
        st.caption(f"Logged in as **{st.session_state.role}**")


def render_header():
    st.markdown(
        f"""
        <div class="main-header">
            <h1>MBA Student Lifecycle Dashboard</h1>
            <p>{st.session_state.program} · Viewing as {st.session_state.role}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_nav():
    options = ROLE_MENUS[st.session_state.role]
    if st.session_state.nav_section not in options:
        st.session_state.nav_section = options[0]
    selected = st.radio("Section", options, horizontal=True, label_visibility="collapsed",
                         index=options.index(st.session_state.nav_section))
    st.session_state.nav_section = selected
    st.markdown("")


# ---------------------------------------------------------------------------
# Role views
# ---------------------------------------------------------------------------
def view_executive_kpis(df: pd.DataFrame):
    """Dean: US-05 (headcount) + US-14 (RAG status per lifecycle stage)."""
    active_df = df[df["Enrollment Status"] == "Active"]
    current_cohort = COHORT_LABELS[max(INTAKE_YEARS)]

    c1, c2, c3, c4 = st.columns(4)
    stat_card(c1, "TOTAL ENROLLED", len(active_df), f"Active · {current_cohort} term", "slate")

    coursework_counts = active_df["Coursework Status"].value_counts()
    exam_counts = active_df["Comprehensive Exam Status"].value_counts()
    capstone_counts = active_df["Capstone Status"].value_counts()

    stat_card(
        c2, "COURSEWORK",
        f"{coursework_counts.get('Completed', 0)}/{len(active_df)}",
        "Completed",
        dominant_color(coursework_counts, {"Completed": "green", "Pending": "yellow", "Cancelled": "red"}),
    )
    stat_card(
        c3, "COMPREHENSIVE EXAM",
        f"{exam_counts.get('Passed', 0)}/{len(active_df)}",
        "Passed",
        dominant_color(exam_counts, {"Passed": "green", "In-Progress": "yellow", "Incomplete": "red"}),
    )
    stat_card(
        c4, "CAPSTONE",
        f"{capstone_counts.get('Defended for Completion', 0)}/{len(active_df)}",
        "Defended",
        dominant_color(capstone_counts, {"Defended for Completion": "green", "In-Progress": "yellow"}),
    )

    st.markdown("#### Lifecycle stage breakdown")
    st.caption("Colorblind-safe: every status is shown as color + label, never color alone.")

    b1, b2, b3 = st.columns(3)
    with b1:
        st.markdown("**Coursework**")
        for status, icon in COURSEWORK_COLOR.items():
            st.write(f"{icon} {status}: **{coursework_counts.get(status, 0)}**")
    with b2:
        st.markdown("**Comprehensive Exam**")
        for status, icon in COMP_EXAM_COLOR.items():
            st.write(f"{icon} {status}: **{exam_counts.get(status, 0)}**")
    with b3:
        st.markdown("**Capstone**")
        for status, icon in CAPSTONE_COLOR.items():
            st.write(f"{icon} {status}: **{capstone_counts.get(status, 0)}**")


def filter_students(df: pd.DataFrame, search: str, cohort: str) -> pd.DataFrame:
    result = df.copy()
    if cohort != "All cohorts":
        result = result[result["Cohort"] == cohort]
    if search:
        s = search.strip().lower()
        result = result[
            result["Name"].str.lower().str.contains(s)
            | result["Student ID"].str.lower().str.contains(s)
        ]
    return result


def view_student_list(df: pd.DataFrame, allow_profile_link: bool):
    """Program Chair (US-03, US-06, US-12, US-15) and, for Faculty/Advisor,
    the entry point into the single-student profile (US-04)."""
    st.caption(f"📅 Data last updated: **{st.session_state.last_updated.strftime('%b %d, %Y · %I:%M %p')}**")

    col_a, col_b = st.columns([2, 1])
    with col_a:
        search = st.text_input("🔎 Search by name or student ID", placeholder="e.g. Maria or MBA-1007")
    with col_b:
        cohort = st.selectbox("Cohort / intake year", ["All cohorts"] + list(COHORT_LABELS.values()))

    filtered = filter_students(df, search, cohort)

    if filtered.empty:
        st.warning("No results found. Try a different name, ID, or cohort.")
        return

    display_cols = [
        "Student ID", "Name", "Cohort", "Enrollment Status",
        "Coursework Status", "Comprehensive Exam Status", "Capstone Status",
    ]

    if allow_profile_link:
        st.caption("Select a row to open that student's full profile.")
        event = st.dataframe(
            filtered[display_cols],
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
        )
        rows = event.selection.rows if event is not None and event.selection else []
        if rows:
            st.session_state.selected_student_id = filtered.iloc[rows[0]]["Student ID"]
            st.session_state.nav_section = "Student Profile"
            st.rerun()
    else:
        st.dataframe(filtered[display_cols], use_container_width=True, hide_index=True)

    st.caption(f"Showing {len(filtered)} of {len(df)} students. Click any column header to sort.")


def view_student_profile(df: pd.DataFrame):
    """Faculty/Advisor: US-04, US-07, US-08, US-09."""
    ids = df["Student ID"] + " — " + df["Name"]
    default_idx = 0
    if st.session_state.selected_student_id:
        matches = df.index[df["Student ID"] == st.session_state.selected_student_id].tolist()
        if matches:
            default_idx = df.index.get_loc(matches[0])

    choice = st.selectbox("Student", ids, index=default_idx)
    student_id = choice.split(" — ")[0]
    student = df[df["Student ID"] == student_id].iloc[0]
    st.session_state.selected_student_id = student_id

    st.markdown(f"### {student['Name']}  ·  `{student['Student ID']}`")
    st.caption(f"{student['Program']} · {student['Cohort']} · Enrollment: {student['Enrollment Status']}")

    p1, p2, p3 = st.columns(3)
    last_updated_str = student["Last Updated"].strftime("%b %d, %Y")

    with p1:
        st.markdown("#### 📘 Coursework")
        icon = COURSEWORK_COLOR.get(student["Coursework Status"], "⚪")
        st.markdown(f"## {icon} {student['Coursework Status']}")
        st.caption(f"Last updated {last_updated_str}")
    with p2:
        st.markdown("#### 📝 Comprehensive Exam")
        icon = COMP_EXAM_COLOR.get(student["Comprehensive Exam Status"], "⚪")
        st.markdown(f"## {icon} {student['Comprehensive Exam Status']}")
        st.caption(f"Last updated {last_updated_str}")
    with p3:
        st.markdown("#### 🎓 Capstone")
        icon = CAPSTONE_COLOR.get(student["Capstone Status"], "⚪")
        st.markdown(f"## {icon} {student['Capstone Status']}")
        st.caption(f"Last updated {last_updated_str}")

    if st.button("← Back to student list"):
        st.session_state.nav_section = "Student List"
        st.rerun()


def view_program_configuration():
    """IT/Admin: US-02."""
    st.markdown("#### Active program")
    st.caption("Admin selects or creates the Program record that drives every other view.")
    st.selectbox("Current program record", PROGRAMS, index=PROGRAMS.index(st.session_state.program), disabled=True,
                 help="Change the active program from the sidebar.")
    with st.form("new_program_form"):
        new_program = st.text_input("Create a new program record", placeholder="e.g. MS Finance")
        submitted = st.form_submit_button("Create program")
        if submitted and new_program.strip():
            st.success(f"Mock: '{new_program.strip()}' would be created and become selectable in the sidebar.")


def view_field_mapping():
    """IT/Admin: US-10."""
    st.markdown("#### Dashboard field → database column mapping")
    st.caption("Editing here does not require a code deployment. Invalid/missing mappings would be flagged before go-live.")
    st.data_editor(default_field_mapping(), use_container_width=True, hide_index=True, num_rows="dynamic")


def view_data_connection():
    """IT/Admin: US-11."""
    st.markdown("#### SQL Server connection")
    st.success("🟢 Connected (mock) — using a read-only service account.")
    st.caption("Credentials are stored securely, never in plain text. A failed connection surfaces a visible error, never a silent blank dashboard.")
    st.text_input("Connection string", value="Driver={ODBC Driver 18};Server=•••;Database=•••;", disabled=True)
    st.button("Test connection (mock)")


def view_permissions():
    """IT/Admin: US-13."""
    st.markdown("#### Role permission levels")
    st.caption("Only IT/Admin can change permission levels. View-only roles cannot trigger write actions.")
    st.data_editor(default_permissions(), use_container_width=True, hide_index=True)


def view_sync_log():
    """IT/Admin: US-16."""
    st.markdown("#### Failed data-sync attempts")
    log_df = generate_sync_log()
    if len(log_df) >= 3:
        st.error("⚠️ Repeated sync failures detected — investigate the connection.")
    st.dataframe(log_df, use_container_width=True, hide_index=True)


def view_access_log():
    """IT/Admin: supports US-01's 'unauthorized access attempts are logged'."""
    st.markdown("#### Access log")
    st.caption("Every simulated login (role switch) is recorded here.")
    if not st.session_state.access_log:
        st.info("No access events yet in this session.")
    else:
        st.dataframe(pd.DataFrame(st.session_state.access_log), use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    render_sidebar()
    render_header()
    render_nav()

    df = load_students(st.session_state.program)
    section = st.session_state.nav_section

    if section == "Executive KPIs":
        view_executive_kpis(df)
    elif section == "Student List":
        allow_link = st.session_state.role == "Faculty/Advisor"
        view_student_list(df, allow_profile_link=allow_link)
    elif section == "Student Profile":
        view_student_profile(df)
    elif section == "Program Configuration":
        view_program_configuration()
    elif section == "Field Mapping":
        view_field_mapping()
    elif section == "Data Connection":
        view_data_connection()
    elif section == "Permissions":
        view_permissions()
    elif section == "Sync Log":
        view_sync_log()
    elif section == "Access Log":
        view_access_log()


if __name__ == "__main__":
    main()
    
