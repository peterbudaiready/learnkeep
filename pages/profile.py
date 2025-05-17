# pages/profile.py  •  extended with password / email / phone dialogs
from __future__ import annotations
import base64, datetime
import streamlit as st
from postgrest.exceptions import APIError
from supabase import create_client, Client
from login_popup import display_login_popup

# Add custom CSS to ensure elements are visible
st.markdown("""
    <style>
    .stButton > button, .stToggle {
        visibility: visible !important;
        display: block !important;
        width: 100% !important;
        margin: 5px 0 !important;
    }
    </style>
""", unsafe_allow_html=True)

# ─── Streamlit bootstrap ─────────────────────────────────────────────────
display_login_popup()                      # stores logged‑in user in Session

# Initialize Supabase client
SUPABASE_URL = "https://fcyutudqmkhrywffsjky.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZjeXV0dWRxbWtocnl3ZmZzamt5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDI0MjQ3OTAsImV4cCI6MjA1ODAwMDc5MH0.IucZQwgH1CFYFCgb9E3-TV7I-NOnPq9-3lmrWc4ZE7I"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ─── helpers ────────────────────────────────────────────────────────────
def get_auth_user() -> dict:
    if "user" not in st.session_state:
        st.session_state["user"] = supabase.auth.get_user().user or {}
    return st.session_state["user"]

def get_user_profile(uid: str) -> dict:
    try:
        data = (
            supabase.table("user_profile")
            .select("*")
            .eq("user_id", uid)
            .maybe_single()
            .execute()
            .data
        )
        return data or {}
    except AttributeError:                        # supabase‑py <2.3
        r = supabase.table("user_profile").select("*").eq("user_id", uid).limit(1).execute()
        return r.data[0] if r.data else {}
    except APIError as e:
        st.error(f"Supabase error: {e.message}")
        return {}

def hex_encode(b: bytes) -> str: return "\\x" + b.hex()
def hex_decode(s: str) -> bytes: return bytes.fromhex(s[2:]) if s.startswith("\\x") else bytes.fromhex(s)
def bytes_to_data_uri(b: bytes, mime="image/png") -> str: return f"data:{mime};base64," + base64.b64encode(b).decode()

def upsert_user_profile(uid: str, profile_name: str, bio: str, pic: bytes | None):
    payload = {
        "user_id": uid,
        "profile_name": profile_name,
        "bio": bio,
        "updated_at": datetime.datetime.utcnow().isoformat(),
    }
    if pic is not None:
        payload["profile_pic"] = hex_encode(pic)
    supabase.table("user_profile").upsert(payload, on_conflict="user_id").execute()

# ─── load current data ──────────────────────────────────────────────────
auth_user = get_auth_user()
if not auth_user: st.stop()

uid   = auth_user["id"]
meta  = auth_user.get("user_metadata", {})
prof  = get_user_profile(uid)

# ─── generic function to call update_user safely ────────────────────────
def safe_update_user(payload: dict):
    try:
        res = supabase.auth.update_user(payload)
    except Exception as exc:
        st.error(f"Supabase error: {exc}")
        return False

    if getattr(res, "error", None):
        st.error(f"Auth update failed: {res.error.message}")
        return False

    # adopt new session (email / password change)
    if getattr(res, "session", None):
        supabase.auth.set_session(res.session.access_token, res.session.refresh_token)

    # refresh cached user
    if getattr(res, "user", None):
        st.session_state["user"] = res.user
    return True

# ─── dialogs ------------------------------------------------------------
try: dialog = st.dialog
except AttributeError: dialog = st.experimental_dialog

@dialog("Edit profile", width="large")
def dlg_edit_profile():
    with st.form("profile_form"):
        email        = st.text_input("Email",        auth_user.get("email", ""))
        display_name = st.text_input("Display name", prof.get("profile_name", ""))
        new_pwd      = st.text_input("New password", type="password")
        bio          = st.text_area("Short bio",     prof.get("bio", ""))
        upload       = st.file_uploader("Profile picture (png/jpg)", type=["png","jpg","jpeg"])
        if upload: st.image(upload, caption="Preview", width=160)
        submitted = st.form_submit_button("Save changes")

    if not submitted: return

    # 1. update auth.users metadata / email / password
    payload = {"data": {"name": display_name}}
    if email and email != auth_user.get("email"): payload["email"] = email
    if new_pwd:                                   payload["password"] = new_pwd
    if len(payload) > 1 and not safe_update_user(payload): return

    # 2. upsert extended profile
    upsert_user_profile(uid, display_name, bio, upload.read() if upload else None)

    st.success("Profile updated!")
    st.rerun()

@dialog("Change password", width="small")
def dlg_change_pwd():
    with st.form("pwd_form"):
        new1 = st.text_input("New password", type="password")
        new2 = st.text_input("Confirm password", type="password")
        ok = st.form_submit_button("Update")
    if not ok: return
    if new1 != new2:
        st.error("Passwords do not match.")
        return
    if safe_update_user({"password": new1}):
        st.success("Password updated!") ; st.rerun()

@dialog("Change email", width="small")
def dlg_change_email():
    with st.form("email_form"):
        new_email = st.text_input("New email")
        ok = st.form_submit_button("Update")
    if not ok: return
    if safe_update_user({"email": new_email}):
        st.success("Email updated! Check your inbox for confirmation.") ; st.rerun()

@dialog("Add / change phone number", width="small")
def dlg_change_phone():
    with st.form("phone_form"):
        phone = st.text_input("Phone (+123...)")
        ok = st.form_submit_button("Update")
    if not ok: return
    if safe_update_user({"phone": phone}):
        st.success("Phone number updated!") ; st.rerun()

# ─── display card UI ────────────────────────────────────────────────────
st.header("👤 Profile")


def current_pic_uri() -> str:
    v = prof.get("profile_pic")
    if isinstance(v, (bytes, bytearray)): return bytes_to_data_uri(v)
    if isinstance(v, str) and v.startswith("\\x"):
        try: return bytes_to_data_uri(hex_decode(v))
        except Exception: pass
    return "https://via.placeholder.com/160"

left, right = st.columns([1, 3], gap="large", border=True, vertical_alignment="center")
with left:
    st.image(current_pic_uri(), width=160, use_container_width=True)

with right:
    st.subheader(prof.get("profile_name") or "Unnamed user")
    st.write(f"**Email:** {auth_user.get('email', '—')}")
    st.write(f"**Phone:** {auth_user.get('phone', '—')}")
    st.write(f"**Bio:**  {prof.get('bio', 'Not provided')}")
    
    st.divider()
    
    # Profile management buttons
    col1, col2, col3, col4 = st.columns([1,1,1,1,], gap="small")
    
    with col1:
        if st.button("✏️ Edit Info", use_container_width=True): dlg_edit_profile()
    with col2:
        if st.button("🔑 Change Password", use_container_width=True): dlg_change_pwd()
    with col3:
        if st.button("📧 Change Email", use_container_width=True): dlg_change_email()
    with col4:
        if st.button("📱 Add/Change Phone No.", use_container_width=True): dlg_change_phone()