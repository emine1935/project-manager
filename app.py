import streamlit as st
import sqlite3
import plotly.express as px

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="Project Manager", layout="wide", page_icon="📊")

# ---------------- USERS ----------------
users = {
    "emine": "1253"
}

# ---------------- SESSION ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user" not in st.session_state:
    st.session_state.user = None

# ---------------- LOGIN ----------------
def login():
    st.title("🔐 Giriş Paneli")

    username = st.text_input("Kullanıcı Adı").strip()
    password = st.text_input("Şifre", type="password").strip()

    if st.button("Giriş Yap"):
        if username == "" or password == "":
            st.error("Boş bırakma")
        elif username in users and users[username] == password:
            st.session_state.logged_in = True
            st.session_state.user = username
            st.rerun()
        else:
            st.error("Hatalı giriş")

if not st.session_state.logged_in:
    login()
    st.stop()

# ---------------- DB ----------------
conn = sqlite3.connect("project.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    status TEXT,
    owner TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_name TEXT,
    status TEXT,
    project_id INTEGER,
    owner TEXT
)
""")

conn.commit()

# ---------------- MENU ----------------
st.title("📊 Proje Yönetim Sistemi")

st.sidebar.title("📌 Menü")
menu = st.sidebar.radio("Seç", ["Dashboard", "Projects", "Tasks"])

# =====================================================
# DASHBOARD
# =====================================================
if menu == "Dashboard":

    st.header("📊 Genel Durum")

    c.execute("SELECT COUNT(*) FROM projects WHERE owner=?", (st.session_state.user,))
    project_count = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM tasks WHERE owner=?", (st.session_state.user,))
    task_count = c.fetchone()[0]

    c.execute("""
        SELECT COUNT(*) FROM tasks
        WHERE owner=? AND status='Tamamlandı'
    """, (st.session_state.user,))
    done_count = c.fetchone()[0]

    c.execute("""
        SELECT COUNT(*) FROM tasks
        WHERE owner=? AND status!='Tamamlandı'
    """, (st.session_state.user,))
    pending_count = c.fetchone()[0]

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("📁 Projeler", project_count)
    col2.metric("📋 Görevler", task_count)
    col3.metric("✅ Tamamlanan", done_count)
    col4.metric("⏳ Bekleyen", pending_count)

    st.divider()

    if task_count > 0:
        st.progress(done_count / task_count)
    else:
        st.info("Henüz görev yok")

    st.divider()

    # PIE CHART
    c.execute("""
        SELECT status, COUNT(*)
        FROM tasks
        WHERE owner=?
        GROUP BY status
    """, (st.session_state.user,))

    data = c.fetchall()

    if data:
        fig = px.pie(
            names=[d[0] for d in data],
            values=[d[1] for d in data],
            title="Görev Dağılımı"
        )
        st.plotly_chart(fig, use_container_width=True)

# =====================================================
# PROJECTS
# =====================================================
elif menu == "Projects":

    st.header("📁 Projeler")

    new_project = st.text_input("Yeni Proje Adı")
    status_options = ["Planlanıyor", "Devam Ediyor", "Tamamlandı"]
    status = st.selectbox("Durum", status_options)

    if st.button("➕ Ekle"):
        if new_project == "":
            st.warning("Boş olamaz")
        else:
            c.execute(
                "INSERT INTO projects (name, status, owner) VALUES (?, ?, ?)",
                (new_project, status, st.session_state.user)
            )
            conn.commit()
            st.success("Eklendi!")
            st.rerun()

    st.divider()

    c.execute("SELECT * FROM projects WHERE owner=?", (st.session_state.user,))
    projects = c.fetchall()

    for p in projects:

        col1, col2, col3 = st.columns([4,2,2])

        with col1:
            st.markdown(f"### 📁 {p[1]}")

        with col2:
            new_status = st.selectbox(
                "Durum",
                status_options,
                index=status_options.index(p[2]),
                key=f"pstatus_{p[0]}"
            )

            if new_status != p[2]:
                c.execute(
                    "UPDATE projects SET status=? WHERE id=?",
                    (new_status, p[0])
                )
                conn.commit()
                st.rerun()

        with col3:
            if st.button("🗑️ Sil", key=f"p_{p[0]}"):
                c.execute("DELETE FROM projects WHERE id=?", (p[0],))
                conn.commit()
                st.rerun()

        with st.expander("📂 Görevleri Gör"):
            c.execute("""
                SELECT task_name, status
                FROM tasks
                WHERE project_id=? AND owner=?
            """, (p[0], st.session_state.user))

            tasks = c.fetchall()

            if not tasks:
                st.info("Görev yok")
            else:
                for t in tasks:
                    st.write(f"📌 {t[0]} — {t[1]}")

# =====================================================
# TASKS
# =====================================================
elif menu == "Tasks":

    st.header("📋 Görev Yönetimi")

    c.execute("SELECT id, name FROM projects WHERE owner=?", (st.session_state.user,))
    projects = c.fetchall()

    project_dict = {name: pid for pid, name in projects}

    if not project_dict:
        st.warning("Önce proje ekle!")
        st.stop()

    selected_project = st.selectbox("Proje Seç", list(project_dict.keys()))
    selected_project_id = project_dict[selected_project]

    st.divider()

    task_name = st.text_input("Görev Adı")

    task_status = st.selectbox(
        "Durum",
        ["Bekliyor", "Devam Ediyor", "Tamamlandı"]
    )

    if st.button("➕ Görev Ekle"):
        if task_name == "":
            st.warning("Boş olamaz")
        else:
            c.execute(
                "INSERT INTO tasks (task_name, status, project_id, owner) VALUES (?, ?, ?, ?)",
                (task_name, task_status, selected_project_id, st.session_state.user)
            )
            conn.commit()
            st.success("Eklendi!")
            st.rerun()

    st.divider()

    st.subheader("📋 Görevler")

    c.execute("""
        SELECT id, task_name, status
        FROM tasks
        WHERE owner=? AND project_id=?
    """, (st.session_state.user, selected_project_id))

    tasks = c.fetchall()

    for t in tasks:

        col1, col2, col3 = st.columns([4,2,1])

        with col1:
            st.write(f"📌 {t[1]}")

        with col2:
            new_status = st.selectbox(
                "Durum",
                ["Bekliyor", "Devam Ediyor", "Tamamlandı"],
                index=["Bekliyor", "Devam Ediyor", "Tamamlandı"].index(t[2]),
                key=f"tstatus_{t[0]}"
            )

            if new_status != t[2]:
                c.execute(
                    "UPDATE tasks SET status=? WHERE id=?",
                    (new_status, t[0])
                )
                conn.commit()
                st.rerun()

        with col3:
            if st.button("🗑️", key=f"t_{t[0]}"):
                c.execute("DELETE FROM tasks WHERE id=?", (t[0],))
                conn.commit()
                st.rerun()