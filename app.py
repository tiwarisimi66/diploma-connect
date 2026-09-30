"""
app.py - DiplomaConnect Main Application
A professional networking and career platform for Diploma/Polytechnic students.
Clean, readable, modular Flask backend.
"""

import os
import sqlite3
from functools import wraps
from datetime import datetime
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
    abort
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import database

# ---------------------------------------------------------
# APPLICATION SETUP
# ---------------------------------------------------------

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "diplomaconnect_secret_key_2026")

UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5MB maximum upload
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ---------------------------------------------------------
# DATABASE & CURRENT USER HELPERS
# ---------------------------------------------------------

def get_db():
    return database.get_db()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_current_user(conn=None):
    if "user_id" not in session:
        return None
    should_close = False
    if conn is None:
        conn = get_db()
        should_close = True
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    if should_close:
        conn.close()
    return user


# ---------------------------------------------------------
# AUTHENTICATION DECORATORS
# ---------------------------------------------------------

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login", next=request.url))
        
        # Verify account is active
        user = get_current_user()
        if not user or user["status"] == "banned":
            session.clear()
            flash("Your account has been suspended or is inactive.", "danger")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Administrator login required.", "warning")
            return redirect(url_for("login"))
        user = get_current_user()
        if not user or user["role"] != "admin":
            flash("Access denied: Administrator privileges required.", "danger")
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    return decorated_function


# ---------------------------------------------------------
# CONTEXT PROCESSOR & TEMPLATE FILTERS
# ---------------------------------------------------------

@app.context_processor
def inject_globals():
    user = get_current_user()
    unread_notifications = 0
    unread_messages = 0
    pending_connections = 0

    if user:
        conn = get_db()
        unread_notifications = conn.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0",
            (user["id"],)
        ).fetchone()[0]

        unread_messages = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE receiver_id = ? AND is_read = 0",
            (user["id"],)
        ).fetchone()[0]

        pending_connections = conn.execute(
            "SELECT COUNT(*) FROM connections WHERE receiver_id = ? AND status = 'pending'",
            (user["id"],)
        ).fetchone()[0]
        conn.close()

    return {
        "current_user": user,
        "unread_notifications_count": unread_notifications,
        "unread_messages_count": unread_messages,
        "pending_connections_count": pending_connections,
        "now_year": datetime.now().year
    }


# ---------------------------------------------------------
# AUTHENTICATION ROUTES
# ---------------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("home"))

    conn = get_db()
    colleges = conn.execute("SELECT name FROM colleges ORDER BY name").fetchall()
    conn.close()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        college = request.form.get("college", "").strip()
        branch = request.form.get("branch", "").strip()
        phone = request.form.get("phone", "").strip()

        # Backward compatibility / optional profile fields
        course = request.form.get("course", "").strip() or (f"Diploma in {branch}" if branch else "Diploma Engineering")
        if not branch and course:
            branch = course.replace("Diploma in ", "").strip()
        dob = request.form.get("dob", "")
        gender = request.form.get("gender", "")
        address = request.form.get("address", "").strip()
        enrollment_no = request.form.get("enrollment_no", "").strip()
        admission_year = request.form.get("admission_year", "").strip()
        university = request.form.get("university", "").strip() or "SBTE Bihar"
        semester = request.form.get("semester", "").strip()
        cgpa = request.form.get("cgpa", "").strip()
        total_credits = request.form.get("total_credits", "").strip()

        if not name or not email or not password:
            flash("Name, email, and password are required.", "danger")
            return render_template("register.html", colleges=colleges)

        if confirm_password and password != confirm_password:
            flash("Passwords do not match. Please re-enter.", "danger")
            return render_template("register.html", colleges=colleges)

        conn = get_db()
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            conn.close()
            flash("An account with this email address already exists.", "danger")
            return render_template("register.html", colleges=colleges)

        hashed_password = generate_password_hash(password)
        headline = f"Diploma Student in {branch or course or 'Engineering'} at {college or 'Polytechnic'}"
        about = f"Diploma student specializing in {branch or 'Engineering'}. Interested in technical projects, industry skills, and career opportunities."

        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (
                name, email, phone, password, dob, gender, address,
                enrollment_no, admission_year, course, branch, college,
                university, semester, cgpa, total_credits, headline, about, role, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'student', 'active')
        """, (
            name, email, phone, hashed_password, dob, gender, address,
            enrollment_no, admission_year, course, branch, college,
            university, semester, cgpa, total_credits, headline, about
        ))
        user_id = cursor.lastrowid

        # Send welcome notification
        cursor.execute("""
            INSERT INTO notifications (user_id, type, title, message, link)
            VALUES (?, 'welcome', 'Welcome to DiplomaConnect!', 'Complete your profile, add your technical skills, and discover fellow polytechnic students.', '/profile')
        """, (user_id,))

        conn.commit()
        conn.close()

        flash("Registration successful! Complete your profile to get personalized career and peer recommendations.", "success")
        return redirect(url_for("login"))

    return render_template("register.html", colleges=colleges)


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            if user["status"] == "banned":
                flash("Your account has been deactivated. Please contact support.", "danger")
                return render_template("login.html")

            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]

            flash(f"Welcome back, {user['name']}!", "success")
            next_url = request.args.get("next")
            return redirect(next_url or url_for("home"))

        flash("Invalid email or password. Please verify your credentials.", "danger")
        return render_template("login.html")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been securely logged out.", "info")
    return redirect(url_for("login"))


# ---------------------------------------------------------
# HOME / DASHBOARD & FEED
# ---------------------------------------------------------

@app.route("/")
@login_required
def home():
    uid = session["user_id"]
    conn = get_db()

    # User profile data & score
    user = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    skills_count = conn.execute("SELECT COUNT(*) FROM skills WHERE user_id = ?", (uid,)).fetchone()[0]
    projects_count = conn.execute("SELECT COUNT(*) FROM projects WHERE user_id = ?", (uid,)).fetchone()[0]
    profile_completion = database.calculate_profile_completion(user, skills_count, projects_count)

    # Fetch posts, excluding any from users that have a block with current user
    posts_raw = conn.execute("""
        SELECT p.*, u.name AS author_name, u.profile_photo AS author_photo,
               u.course AS author_course, u.college AS author_college,
               (SELECT COUNT(*) FROM post_likes WHERE post_id = p.id) AS like_count,
               (SELECT COUNT(*) FROM post_likes WHERE post_id = p.id AND user_id = ?) AS user_liked,
               (SELECT COUNT(*) FROM post_comments WHERE post_id = p.id) AS comment_count
        FROM posts p
        JOIN users u ON u.id = p.user_id
        WHERE p.user_id NOT IN (
            SELECT blocked_id FROM blocks WHERE blocker_id = ?
            UNION
            SELECT blocker_id FROM blocks WHERE blocked_id = ?
        )
        ORDER BY p.id DESC
        LIMIT 30
    """, (uid, uid, uid)).fetchall()

    posts = []
    for p in posts_raw:
        comments = conn.execute("""
            SELECT c.*, u.name AS author_name, u.profile_photo AS author_photo
            FROM post_comments c
            JOIN users u ON u.id = c.user_id
            WHERE c.post_id = ?
            ORDER BY c.id ASC
        """, (p["id"],)).fetchall()
        
        post_dict = dict(p)
        post_dict["comments"] = comments
        posts.append(post_dict)

    # Suggested students (not self, not already connected/pending, not blocked)
    suggested_students = conn.execute("""
        SELECT u.id, u.name, u.course, u.college, u.profile_photo, u.headline
        FROM users u
        WHERE u.id != ?
          AND u.status = 'active'
          AND u.id NOT IN (
              SELECT receiver_id FROM connections WHERE sender_id = ?
              UNION
              SELECT sender_id FROM connections WHERE receiver_id = ?
              UNION
              SELECT blocked_id FROM blocks WHERE blocker_id = ?
              UNION
              SELECT blocker_id FROM blocks WHERE blocked_id = ?
          )
        ORDER BY RANDOM()
        LIMIT 4
    """, (uid, uid, uid, uid, uid)).fetchall()

    # Recent opportunities
    recent_opportunities = conn.execute("""
        SELECT * FROM opportunities
        ORDER BY id DESC
        LIMIT 3
    """).fetchall()

    # Upcoming events
    upcoming_events = conn.execute("""
        SELECT * FROM events
        ORDER BY event_date ASC
        LIMIT 3
    """).fetchall()

    # Network summary
    connections_count = conn.execute("""
        SELECT COUNT(*) FROM connections
        WHERE (sender_id = ? OR receiver_id = ?) AND status = 'accepted'
    """, (uid, uid)).fetchone()[0]

    pending_received_count = conn.execute("""
        SELECT COUNT(*) FROM connections
        WHERE receiver_id = ? AND status = 'pending'
    """, (uid,)).fetchone()[0]

    # Real platform metrics (no invented numbers)
    total_students = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'student'").fetchone()[0]
    total_colleges = conn.execute("SELECT COUNT(*) FROM colleges").fetchone()[0]
    total_opportunities = conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0]
    total_events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]

    # Fetch user skills for skill builder & gap widget
    user_skills_rows = conn.execute("SELECT skill_name, category FROM skills WHERE user_id = ?", (uid,)).fetchall()
    user_skills = [s["skill_name"] for s in user_skills_rows]
    user_skills_lower = {s.lower() for s in user_skills}

    # Branch-specific recommended skills for polytechnic students
    course_str = ((user["course"] or "") + " " + (user["branch"] or "")).lower()
    if any(k in course_str for k in ["computer", "cse", "it", "software"]):
        recommended_skills = ["Python", "JavaScript", "SQL", "Git & GitHub", "HTML5 & CSS3", "Data Structures", "Linux"]
        branch_name = "Computer Science / IT"
    elif any(k in course_str for k in ["mech", "auto", "production"]):
        recommended_skills = ["AutoCAD 2D/3D", "SolidWorks", "CNC Programming", "Thermodynamics", "Industrial Safety", "GD&T"]
        branch_name = "Mechanical Engineering"
    elif any(k in course_str for k in ["civil", "construction"]):
        recommended_skills = ["AutoCAD Civil", "Total Station & Surveying", "STAAD.Pro", "Concrete Technology", "Quantity Estimation", "Site Supervision"]
        branch_name = "Civil Engineering"
    elif any(k in course_str for k in ["electr"]):
        recommended_skills = ["PLC & SCADA", "Substation Operations", "MATLAB", "Circuit Simulation", "Solar PV Design", "Electrical Wiring"]
        branch_name = "Electrical Engineering"
    elif any(k in course_str for k in ["ece", "electron", "telecom"]):
        recommended_skills = ["Embedded C / Arduino", "PCB Design", "IoT Protocols", "Microcontrollers", "Digital Signal Processing", "VLSI Basics"]
        branch_name = "Electronics Engineering"
    else:
        recommended_skills = ["Python", "AutoCAD", "Technical Communication", "MS Excel & Analytics", "Project Management", "Git & GitHub"]
        branch_name = "Polytechnic Engineering"

    missing_recommended = [sk for sk in recommended_skills if sk.lower() not in user_skills_lower]

    conn.close()

    return render_template(
        "index.html",
        user=user,
        posts=posts,
        profile_completion=profile_completion,
        suggested_students=suggested_students,
        recent_opportunities=recent_opportunities,
        upcoming_events=upcoming_events,
        connections_count=connections_count,
        pending_received_count=pending_received_count,
        total_students=total_students,
        total_colleges=total_colleges,
        total_opportunities=total_opportunities,
        total_events=total_events,
        user_skills=user_skills,
        recommended_skills=recommended_skills,
        missing_recommended=missing_recommended,
        branch_name=branch_name
    )


# ---------------------------------------------------------
# FEED ACTIONS: POSTS, LIKES, COMMENTS
# ---------------------------------------------------------

@app.route("/post/create", methods=["POST"])
@login_required
def create_post():
    content = request.form.get("content", "").strip()
    post_type = request.form.get("post_type", "general").strip()

    if not content:
        flash("Post content cannot be empty.", "warning")
        return redirect(request.referrer or url_for("home"))

    conn = get_db()
    conn.execute("""
        INSERT INTO posts (user_id, content, post_type)
        VALUES (?, ?, ?)
    """, (session["user_id"], content, post_type))
    conn.commit()
    conn.close()

    flash("Your post has been shared successfully!", "success")
    return redirect(request.referrer or url_for("home"))


@app.route("/post/<int:post_id>/edit", methods=["POST"])
@login_required
def edit_post(post_id):
    content = request.form.get("content", "").strip()
    if not content:
        flash("Post content cannot be empty.", "warning")
        return redirect(request.referrer or url_for("home"))

    conn = get_db()
    post = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    if not post:
        conn.close()
        flash("Post not found.", "danger")
        return redirect(request.referrer or url_for("home"))

    # Only author or admin can edit
    user = get_current_user()
    if post["user_id"] != user["id"] and user["role"] != "admin":
        conn.close()
        flash("Unauthorized action.", "danger")
        return redirect(request.referrer or url_for("home"))

    conn.execute("""
        UPDATE posts
        SET content = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (content, post_id))
    conn.commit()
    conn.close()

    flash("Post updated successfully.", "success")
    return redirect(request.referrer or url_for("home"))


@app.route("/post/<int:post_id>/delete", methods=["POST"])
@login_required
def delete_post(post_id):
    conn = get_db()
    post = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    if not post:
        conn.close()
        flash("Post not found.", "danger")
        return redirect(request.referrer or url_for("home"))

    user = get_current_user()
    if post["user_id"] != user["id"] and user["role"] != "admin":
        conn.close()
        flash("Unauthorized to delete this post.", "danger")
        return redirect(request.referrer or url_for("home"))

    conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()

    flash("Post removed successfully.", "info")
    return redirect(request.referrer or url_for("home"))


@app.route("/post/<int:post_id>/like", methods=["POST"])
@login_required
def like_post(post_id):
    uid = session["user_id"]
    conn = get_db()
    post = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    if not post:
        conn.close()
        return redirect(request.referrer or url_for("home"))

    existing = conn.execute(
        "SELECT id FROM post_likes WHERE post_id = ? AND user_id = ?",
        (post_id, uid)
    ).fetchone()

    if existing:
        conn.execute("DELETE FROM post_likes WHERE id = ?", (existing["id"],))
    else:
        conn.execute(
            "INSERT INTO post_likes (post_id, user_id) VALUES (?, ?)",
            (post_id, uid)
        )
        # Notify author if not self
        if post["user_id"] != uid:
            user = get_current_user(conn=conn)
            database.add_notification(
                post["user_id"],
                "like",
                "New Like",
                f"{user['name']} liked your post.",
                url_for("home"),
                conn=conn
            )

    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for("home"))


@app.route("/post/<int:post_id>/comment", methods=["POST"])
@login_required
def add_comment(post_id):
    content = request.form.get("content", "").strip()
    if not content:
        flash("Comment cannot be empty.", "warning")
        return redirect(request.referrer or url_for("home"))

    uid = session["user_id"]
    conn = get_db()
    post = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    if not post:
        conn.close()
        flash("Post not found.", "danger")
        return redirect(request.referrer or url_for("home"))

    conn.execute("""
        INSERT INTO post_comments (post_id, user_id, content)
        VALUES (?, ?, ?)
    """, (post_id, uid, content))

    if post["user_id"] != uid:
        user = get_current_user(conn=conn)
        database.add_notification(
            post["user_id"],
            "comment",
            "New Comment",
            f"{user['name']} commented on your post: \"{content[:40]}...\"",
            url_for("home"),
            conn=conn
        )

    conn.commit()
    conn.close()

    flash("Comment posted.", "success")
    return redirect(request.referrer or url_for("home"))


@app.route("/comment/<int:comment_id>/delete", methods=["POST"])
@login_required
def delete_comment(comment_id):
    uid = session["user_id"]
    conn = get_db()
    comment = conn.execute("""
        SELECT c.*, p.user_id AS post_author_id
        FROM post_comments c
        JOIN posts p ON p.id = c.post_id
        WHERE c.id = ?
    """, (comment_id,)).fetchone()

    if not comment:
        conn.close()
        flash("Comment not found.", "danger")
        return redirect(request.referrer or url_for("home"))

    user = get_current_user()
    if comment["user_id"] != uid and comment["post_author_id"] != uid and user["role"] != "admin":
        conn.close()
        flash("Unauthorized to delete this comment.", "danger")
        return redirect(request.referrer or url_for("home"))

    conn.execute("DELETE FROM post_comments WHERE id = ?", (comment_id,))
    conn.commit()
    conn.close()

    flash("Comment deleted.", "info")
    return redirect(request.referrer or url_for("home"))


# ---------------------------------------------------------
# PROFILE & EDIT PROFILE
# ---------------------------------------------------------

@app.route("/profile")
@login_required
def profile():
    uid = session["user_id"]
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    skills = conn.execute("SELECT * FROM skills WHERE user_id = ? ORDER BY id DESC", (uid,)).fetchall()
    projects = conn.execute("SELECT * FROM projects WHERE user_id = ? ORDER BY id DESC", (uid,)).fetchall()
    certifications = conn.execute("SELECT * FROM certifications WHERE user_id = ? ORDER BY id DESC", (uid,)).fetchall()
    achievements = conn.execute("SELECT * FROM achievements WHERE user_id = ? ORDER BY id DESC", (uid,)).fetchall()
    completion = database.calculate_profile_completion(user, len(skills), len(projects))
    conn.close()

    return render_template(
        "profile.html",
        user=user,
        skills=skills,
        projects=projects,
        certifications=certifications,
        achievements=achievements,
        completion=completion
    )


@app.route("/edit-profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    uid = session["user_id"]
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        dob = request.form.get("dob", "")
        gender = request.form.get("gender", "")
        address = request.form.get("address", "").strip()
        headline = request.form.get("headline", "").strip()
        about = request.form.get("about", "").strip()
        enrollment_no = request.form.get("enrollment_no", "").strip()
        admission_year = request.form.get("admission_year", "").strip()
        course = request.form.get("course", "").strip()
        branch = request.form.get("branch", "").strip() or course
        college = request.form.get("college", "").strip()
        university = request.form.get("university", "").strip()
        semester = request.form.get("semester", "").strip()
        cgpa = request.form.get("cgpa", "").strip()
        total_credits = request.form.get("total_credits", "").strip()

        # Check email uniqueness if modified
        if email != user["email"]:
            existing = conn.execute("SELECT id FROM users WHERE email = ? AND id != ?", (email, uid)).fetchone()
            if existing:
                conn.close()
                flash("This email address is already taken by another user.", "danger")
                return render_template("edit_profile.html", user=user)

        conn.execute("""
            UPDATE users SET
                name = ?, email = ?, phone = ?, dob = ?, gender = ?, address = ?,
                headline = ?, about = ?, enrollment_no = ?, admission_year = ?,
                course = ?, branch = ?, college = ?, university = ?, semester = ?,
                cgpa = ?, total_credits = ?
            WHERE id = ?
        """, (
            name, email, phone, dob, gender, address,
            headline, about, enrollment_no, admission_year,
            course, branch, college, university, semester,
            cgpa, total_credits, uid
        ))
        conn.commit()
        conn.close()

        session["name"] = name
        flash("Profile updated successfully!", "success")
        return redirect(url_for("profile"))

    conn.close()
    return render_template("edit_profile.html", user=user)


@app.route("/upload-photo", methods=["POST"])
@login_required
def upload_photo():
    if "profile_photo" not in request.files:
        flash("No photo file selected.", "warning")
        return redirect(url_for("profile"))

    file = request.files["profile_photo"]
    if file.filename == "":
        flash("No file selected.", "warning")
        return redirect(url_for("profile"))

    if not allowed_file(file.filename):
        flash("Invalid file format. Allowed extensions: png, jpg, jpeg, webp, gif.", "danger")
        return redirect(url_for("profile"))

    extension = file.filename.rsplit(".", 1)[1].lower()
    filename = f"profile_{session['user_id']}.{extension}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    # Clean older format versions
    for ext in ALLOWED_EXTENSIONS:
        old_file = os.path.join(UPLOAD_FOLDER, f"profile_{session['user_id']}.{ext}")
        if os.path.exists(old_file):
            try:
                os.remove(old_file)
            except Exception:
                pass

    file.save(filepath)

    conn = get_db()
    conn.execute("UPDATE users SET profile_photo = ? WHERE id = ?", (filename, session["user_id"]))
    conn.commit()
    conn.close()

    flash("Profile photo updated successfully!", "success")
    return redirect(url_for("profile"))


# ---------------------------------------------------------
# PORTFOLIO ITEMS (SKILLS, PROJECTS, CERTS, ACHIEVEMENTS)
# ---------------------------------------------------------

@app.route("/profile/skill/add", methods=["POST"])
@login_required
def add_skill():
    skill_name = request.form.get("skill_name", "").strip()
    category = request.form.get("category", "Technical").strip()
    redirect_to = request.form.get("redirect_to", "").strip()
    if skill_name:
        conn = get_db()
        conn.execute("""
            INSERT INTO skills (user_id, skill_name, category)
            VALUES (?, ?, ?)
        """, (session["user_id"], skill_name, category))
        conn.commit()
        conn.close()
        flash(f"Skill '{skill_name}' added!", "success")
    if redirect_to:
        return redirect(redirect_to)
    return redirect(url_for("profile"))


@app.route("/profile/skill/<int:skill_id>/delete", methods=["POST"])
@login_required
def delete_skill(skill_id):
    conn = get_db()
    conn.execute("DELETE FROM skills WHERE id = ? AND user_id = ?", (skill_id, session["user_id"]))
    conn.commit()
    conn.close()
    flash("Skill removed.", "info")
    return redirect(url_for("profile"))


@app.route("/profile/project/add", methods=["POST"])
@login_required
def add_project():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    tech_stack = request.form.get("tech_stack", "").strip()
    project_url = request.form.get("project_url", "").strip()
    github_url = request.form.get("github_url", "").strip()

    if title:
        conn = get_db()
        conn.execute("""
            INSERT INTO projects (user_id, title, description, tech_stack, project_url, github_url)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (session["user_id"], title, description, tech_stack, project_url, github_url))
        conn.commit()
        conn.close()
        flash("Project added to your portfolio!", "success")
    return redirect(url_for("profile"))


@app.route("/profile/project/<int:project_id>/delete", methods=["POST"])
@login_required
def delete_project(project_id):
    conn = get_db()
    conn.execute("DELETE FROM projects WHERE id = ? AND user_id = ?", (project_id, session["user_id"]))
    conn.commit()
    conn.close()
    flash("Project removed from your portfolio.", "info")
    return redirect(url_for("profile"))


@app.route("/profile/cert/add", methods=["POST"])
@login_required
def add_certification():
    title = request.form.get("title", "").strip()
    issuer = request.form.get("issuer", "").strip()
    issue_date = request.form.get("issue_date", "").strip()
    credential_url = request.form.get("credential_url", "").strip()

    if title and issuer:
        conn = get_db()
        conn.execute("""
            INSERT INTO certifications (user_id, title, issuer, issue_date, credential_url)
            VALUES (?, ?, ?, ?, ?)
        """, (session["user_id"], title, issuer, issue_date, credential_url))
        conn.commit()
        conn.close()
        flash("Certification added!", "success")
    return redirect(url_for("profile"))


@app.route("/profile/cert/<int:cert_id>/delete", methods=["POST"])
@login_required
def delete_certification(cert_id):
    conn = get_db()
    conn.execute("DELETE FROM certifications WHERE id = ? AND user_id = ?", (cert_id, session["user_id"]))
    conn.commit()
    conn.close()
    flash("Certification removed.", "info")
    return redirect(url_for("profile"))


@app.route("/profile/achievement/add", methods=["POST"])
@login_required
def add_achievement():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    year = request.form.get("year", "").strip()

    if title:
        conn = get_db()
        conn.execute("""
            INSERT INTO achievements (user_id, title, description, year)
            VALUES (?, ?, ?, ?)
        """, (session["user_id"], title, description, year))
        conn.commit()
        conn.close()
        flash("Achievement recorded!", "success")
    return redirect(url_for("profile"))


@app.route("/profile/achievement/<int:achievement_id>/delete", methods=["POST"])
@login_required
def delete_achievement(achievement_id):
    conn = get_db()
    conn.execute("DELETE FROM achievements WHERE id = ? AND user_id = ?", (achievement_id, session["user_id"]))
    conn.commit()
    conn.close()
    flash("Achievement removed.", "info")
    return redirect(url_for("profile"))


# ---------------------------------------------------------
# STUDENT DISCOVERY & PUBLIC PROFILES
# ---------------------------------------------------------

@app.route("/students")
@login_required
def discover_students():
    uid = session["user_id"]
    q = request.args.get("q", "").strip()
    college_filter = request.args.get("college", "").strip()
    course_filter = request.args.get("course", "").strip()
    semester_filter = request.args.get("semester", "").strip()

    conn = get_db()

    sql = """
        SELECT u.id, u.name, u.course, u.branch, u.college, u.university,
               u.semester, u.cgpa, u.profile_photo, u.headline,
               (SELECT GROUP_CONCAT(skill_name, ', ') FROM skills WHERE user_id = u.id) AS skills_list,
               (
                   SELECT status FROM connections
                   WHERE (sender_id = ? AND receiver_id = u.id)
                      OR (sender_id = u.id AND receiver_id = ?)
               ) AS connection_status,
               (
                   SELECT sender_id FROM connections
                   WHERE (sender_id = ? AND receiver_id = u.id)
                      OR (sender_id = u.id AND receiver_id = ?)
               ) AS connection_sender_id
        FROM users u
        WHERE u.id != ?
          AND u.status = 'active'
          AND u.id NOT IN (
              SELECT blocked_id FROM blocks WHERE blocker_id = ?
              UNION
              SELECT blocker_id FROM blocks WHERE blocked_id = ?
          )
    """
    params = [uid, uid, uid, uid, uid, uid, uid]

    if q:
        sql += """
            AND (
                u.name LIKE ?
                OR u.course LIKE ?
                OR u.college LIKE ?
                OR u.university LIKE ?
                OR u.headline LIKE ?
                OR u.id IN (SELECT user_id FROM skills WHERE skill_name LIKE ?)
            )
        """
        val = f"%{q}%"
        params.extend([val, val, val, val, val, val])

    if college_filter:
        sql += " AND u.college = ?"
        params.append(college_filter)

    if course_filter:
        sql += " AND (u.course = ? OR u.branch = ?)"
        params.extend([course_filter, course_filter])

    if semester_filter:
        sql += " AND u.semester = ?"
        params.append(semester_filter)

    sql += " ORDER BY u.name ASC"

    students = conn.execute(sql, params).fetchall()

    # Dropdown filters
    colleges = conn.execute("SELECT DISTINCT college FROM users WHERE college IS NOT NULL AND college != '' ORDER BY college").fetchall()
    courses = conn.execute("SELECT DISTINCT course FROM users WHERE course IS NOT NULL AND course != '' ORDER BY course").fetchall()
    semesters = conn.execute("SELECT DISTINCT semester FROM users WHERE semester IS NOT NULL AND semester != '' ORDER BY semester").fetchall()

    conn.close()

    return render_template(
        "students.html",
        students=students,
        q=q,
        colleges=colleges,
        courses=courses,
        semesters=semesters,
        selected_college=college_filter,
        selected_course=course_filter,
        selected_semester=semester_filter
    )


@app.route("/student/<int:user_id>")
@login_required
def student_profile(user_id):
    uid = session["user_id"]
    if user_id == uid:
        return redirect(url_for("profile"))

    conn = get_db()
    target_user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not target_user:
        conn.close()
        flash("Student profile not found.", "danger")
        return redirect(url_for("discover_students"))

    # Check block
    if database.is_blocked(uid, user_id):
        conn.close()
        flash("You cannot view this profile.", "warning")
        return redirect(url_for("discover_students"))

    skills = conn.execute("SELECT * FROM skills WHERE user_id = ?", (user_id,)).fetchall()
    projects = conn.execute("SELECT * FROM projects WHERE user_id = ?", (user_id,)).fetchall()
    certifications = conn.execute("SELECT * FROM certifications WHERE user_id = ?", (user_id,)).fetchall()
    achievements = conn.execute("SELECT * FROM achievements WHERE user_id = ?", (user_id,)).fetchall()

    connection = conn.execute("""
        SELECT * FROM connections
        WHERE (sender_id = ? AND receiver_id = ?)
           OR (sender_id = ? AND receiver_id = ?)
    """, (uid, user_id, user_id, uid)).fetchone()

    conn.close()

    return render_template(
        "student_profile.html",
        student=target_user,
        skills=skills,
        projects=projects,
        certifications=certifications,
        achievements=achievements,
        connection=connection
    )


# ---------------------------------------------------------
# CONNECTIONS & NETWORKING
# ---------------------------------------------------------

@app.route("/connections")
@login_required
def connections():
    uid = session["user_id"]
    conn = get_db()

    # Active Connections
    connected = conn.execute("""
        SELECT c.id AS connection_id, c.created_at AS connected_since,
               u.id AS user_id, u.name, u.course, u.college, u.profile_photo, u.headline
        FROM connections c
        JOIN users u ON u.id = (
            CASE WHEN c.sender_id = ? THEN c.receiver_id ELSE c.sender_id END
        )
        WHERE (c.sender_id = ? OR c.receiver_id = ?)
          AND c.status = 'accepted'
        ORDER BY c.id DESC
    """, (uid, uid, uid)).fetchall()

    # Incoming Requests (pending received)
    incoming = conn.execute("""
        SELECT c.id AS connection_id, c.created_at,
               u.id AS user_id, u.name, u.course, u.college, u.profile_photo, u.headline
        FROM connections c
        JOIN users u ON u.id = c.sender_id
        WHERE c.receiver_id = ? AND c.status = 'pending'
        ORDER BY c.id DESC
    """, (uid,)).fetchall()

    # Outgoing Requests (pending sent)
    outgoing = conn.execute("""
        SELECT c.id AS connection_id, c.created_at,
               u.id AS user_id, u.name, u.course, u.college, u.profile_photo, u.headline
        FROM connections c
        JOIN users u ON u.id = c.receiver_id
        WHERE c.sender_id = ? AND c.status = 'pending'
        ORDER BY c.id DESC
    """, (uid,)).fetchall()

    conn.close()

    return render_template(
        "connections.html",
        connected=connected,
        incoming=incoming,
        outgoing=outgoing
    )


@app.route("/connect/<int:user_id>", methods=["POST"])
@login_required
def send_connection(user_id):
    uid = session["user_id"]
    if user_id == uid:
        flash("You cannot connect with yourself.", "warning")
        return redirect(request.referrer or url_for("discover_students"))

    if database.is_blocked(uid, user_id):
        flash("Action unavailable.", "warning")
        return redirect(request.referrer or url_for("discover_students"))

    conn = get_db()
    existing = conn.execute("""
        SELECT * FROM connections
        WHERE (sender_id = ? AND receiver_id = ?)
           OR (sender_id = ? AND receiver_id = ?)
    """, (uid, user_id, user_id, uid)).fetchone()

    if not existing:
        conn.execute("""
            INSERT INTO connections (sender_id, receiver_id, status)
            VALUES (?, ?, 'pending')
        """, (uid, user_id))

        user = get_current_user(conn=conn)
        database.add_notification(
            user_id,
            "connection_request",
            "New Connection Request",
            f"{user['name']} sent you a connection request.",
            url_for("connections"),
            conn=conn
        )
        conn.commit()
        flash("Connection request sent!", "success")
    elif existing["status"] == "rejected":
        conn.execute("""
            UPDATE connections SET sender_id = ?, receiver_id = ?, status = 'pending', created_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (uid, user_id, existing["id"]))
        conn.commit()
        flash("Connection request re-sent!", "success")
    else:
        flash("Connection request already exists or pending.", "info")

    conn.close()
    return redirect(request.referrer or url_for("discover_students"))


@app.route("/connection/<int:connection_id>/accept", methods=["POST"])
@login_required
def accept_connection(connection_id):
    uid = session["user_id"]
    conn = get_db()
    c = conn.execute("SELECT * FROM connections WHERE id = ? AND receiver_id = ?", (connection_id, uid)).fetchone()
    if c:
        conn.execute("UPDATE connections SET status = 'accepted' WHERE id = ?", (connection_id,))
        user = get_current_user(conn=conn)
        database.add_notification(
            c["sender_id"],
            "connection_accepted",
            "Connection Accepted",
            f"{user['name']} accepted your connection request.",
            url_for("student_profile", user_id=uid),
            conn=conn
        )
        conn.commit()
        flash("Connection accepted! You can now exchange messages.", "success")
    conn.close()
    return redirect(request.referrer or url_for("connections"))


@app.route("/connection/<int:connection_id>/reject", methods=["POST"])
@login_required
def reject_connection(connection_id):
    uid = session["user_id"]
    conn = get_db()
    conn.execute("UPDATE connections SET status = 'rejected' WHERE id = ? AND receiver_id = ?", (connection_id, uid))
    conn.commit()
    conn.close()
    flash("Connection request declined.", "info")
    return redirect(request.referrer or url_for("connections"))


@app.route("/connection/<int:connection_id>/cancel", methods=["POST"])
@login_required
def cancel_connection(connection_id):
    uid = session["user_id"]
    conn = get_db()
    conn.execute("DELETE FROM connections WHERE id = ? AND sender_id = ?", (connection_id, uid))
    conn.commit()
    conn.close()
    flash("Connection request canceled.", "info")
    return redirect(request.referrer or url_for("connections"))


@app.route("/connection/<int:connection_id>/remove", methods=["POST"])
@login_required
def remove_connection(connection_id):
    uid = session["user_id"]
    conn = get_db()
    conn.execute("""
        DELETE FROM connections
        WHERE id = ? AND (sender_id = ? OR receiver_id = ?)
    """, (connection_id, uid, uid))
    conn.commit()
    conn.close()
    flash("Connection removed.", "info")
    return redirect(request.referrer or url_for("connections"))


# ---------------------------------------------------------
# MESSAGING SYSTEM
# ---------------------------------------------------------

@app.route("/messages")
@login_required
def messages_inbox():
    uid = session["user_id"]
    conn = get_db()

    # Fetch active conversations between connected users
    conversations = conn.execute("""
        SELECT u.id AS partner_id, u.name, u.course, u.college, u.profile_photo,
               m.content AS last_message, m.created_at AS last_time, m.sender_id AS last_sender_id,
               (
                   SELECT COUNT(*) FROM messages
                   WHERE sender_id = u.id AND receiver_id = ? AND is_read = 0
               ) AS unread_count
        FROM users u
        JOIN messages m ON m.id = (
            SELECT id FROM messages
            WHERE (sender_id = ? AND receiver_id = u.id)
               OR (sender_id = u.id AND receiver_id = ?)
            ORDER BY id DESC LIMIT 1
        )
        WHERE u.id NOT IN (
            SELECT blocked_id FROM blocks WHERE blocker_id = ?
            UNION
            SELECT blocker_id FROM blocks WHERE blocked_id = ?
        )
        ORDER BY m.id DESC
    """, (uid, uid, uid, uid, uid)).fetchall()

    # List of all accepted connections to easily start a new conversation
    all_connections = conn.execute("""
        SELECT u.id, u.name, u.course, u.college, u.profile_photo
        FROM connections c
        JOIN users u ON u.id = (
            CASE WHEN c.sender_id = ? THEN c.receiver_id ELSE c.sender_id END
        )
        WHERE (c.sender_id = ? OR c.receiver_id = ?) AND c.status = 'accepted'
        ORDER BY u.name ASC
    """, (uid, uid, uid)).fetchall()

    conn.close()

    return render_template(
        "messages.html",
        conversations=conversations,
        connections=all_connections
    )


@app.route("/messages/<int:recipient_id>")
@login_required
def conversation(recipient_id):
    uid = session["user_id"]
    if recipient_id == uid:
        flash("You cannot message yourself.", "warning")
        return redirect(url_for("messages_inbox"))

    if database.is_blocked(uid, recipient_id):
        flash("Messaging is blocked with this user.", "warning")
        return redirect(url_for("messages_inbox"))

    conn = get_db()
    recipient = conn.execute("SELECT * FROM users WHERE id = ?", (recipient_id,)).fetchone()
    if not recipient:
        conn.close()
        flash("User not found.", "danger")
        return redirect(url_for("messages_inbox"))

    # Check connection
    conn_check = conn.execute("""
        SELECT id FROM connections
        WHERE ((sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?))
          AND status = 'accepted'
    """, (uid, recipient_id, recipient_id, uid)).fetchone()

    # Mark incoming messages as read
    conn.execute("""
        UPDATE messages SET is_read = 1
        WHERE sender_id = ? AND receiver_id = ? AND is_read = 0
    """, (recipient_id, uid))
    conn.commit()

    # Message history
    chat_history = conn.execute("""
        SELECT * FROM messages
        WHERE (sender_id = ? AND receiver_id = ?)
           OR (sender_id = ? AND receiver_id = ?)
        ORDER BY id ASC
    """, (uid, recipient_id, recipient_id, uid)).fetchall()

    conn.close()

    return render_template(
        "conversation.html",
        recipient=recipient,
        messages=chat_history,
        is_connected=bool(conn_check)
    )


@app.route("/messages/<int:recipient_id>/send", methods=["POST"])
@login_required
def send_message(recipient_id):
    uid = session["user_id"]
    content = request.form.get("content", "").strip()

    if not content:
        return redirect(url_for("conversation", recipient_id=recipient_id))

    if database.is_blocked(uid, recipient_id):
        flash("Cannot send message to this user.", "warning")
        return redirect(url_for("messages_inbox"))

    conn = get_db()
    conn.execute("""
        INSERT INTO messages (sender_id, receiver_id, content)
        VALUES (?, ?, ?)
    """, (uid, recipient_id, content))

    user = get_current_user(conn=conn)
    database.add_notification(
        recipient_id,
        "message",
        "New Message",
        f"{user['name']} sent you a message: \"{content[:30]}...\"",
        url_for("conversation", recipient_id=uid),
        conn=conn
    )

    conn.commit()
    conn.close()

    return redirect(url_for("conversation", recipient_id=recipient_id))


# ---------------------------------------------------------
# NOTIFICATIONS
# ---------------------------------------------------------

@app.route("/notifications")
@login_required
def notifications_view():
    uid = session["user_id"]
    conn = get_db()
    notifs = conn.execute("""
        SELECT * FROM notifications
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 50
    """, (uid,)).fetchall()
    conn.close()

    return render_template("notifications.html", notifications=notifs)


@app.route("/notification/<int:notification_id>/read", methods=["POST"])
@login_required
def mark_notification_read(notification_id):
    uid = session["user_id"]
    conn = get_db()
    conn.execute("UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?", (notification_id, uid))
    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for("notifications_view"))


@app.route("/notifications/mark-all-read", methods=["POST"])
@login_required
def mark_all_notifications_read():
    uid = session["user_id"]
    conn = get_db()
    conn.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (uid,))
    conn.commit()
    conn.close()
    flash("All notifications marked as read.", "success")
    return redirect(url_for("notifications_view"))


@app.route("/notification/<int:notification_id>/delete", methods=["POST"])
@login_required
def delete_notification(notification_id):
    uid = session["user_id"]
    conn = get_db()
    conn.execute("DELETE FROM notifications WHERE id = ? AND user_id = ?", (notification_id, uid))
    conn.commit()
    conn.close()
    flash("Notification deleted.", "info")
    return redirect(url_for("notifications_view"))


# ---------------------------------------------------------
# COLLEGE DIRECTORY
# ---------------------------------------------------------

@app.route("/colleges")
@login_required
def college_directory():
    q = request.args.get("q", "").strip()
    district = request.args.get("district", "").strip()

    conn = get_db()
    sql = "SELECT * FROM colleges WHERE 1=1"
    params = []

    if q:
        sql += " AND (name LIKE ? OR district LIKE ? OR university LIKE ?)"
        val = f"%{q}%"
        params.extend([val, val, val])

    if district:
        sql += " AND district = ?"
        params.append(district)

    sql += " ORDER BY name ASC"
    colleges = conn.execute(sql, params).fetchall()

    districts = conn.execute("""
        SELECT DISTINCT district FROM colleges
        WHERE district IS NOT NULL AND district != ''
        ORDER BY district ASC
    """).fetchall()

    conn.close()

    return render_template(
        "colleges.html",
        colleges=colleges,
        districts=districts,
        q=q,
        selected_district=district
    )


@app.route("/college/<int:college_id>")
@login_required
def college_detail(college_id):
    conn = get_db()
    college = conn.execute("SELECT * FROM colleges WHERE id = ?", (college_id,)).fetchone()
    if not college:
        conn.close()
        flash("College not found.", "danger")
        return redirect(url_for("college_directory"))

    students = conn.execute("""
        SELECT id, name, course, branch, college, profile_photo, semester, headline
        FROM users
        WHERE college = ? AND status = 'active'
        ORDER BY name ASC
    """, (college["name"],)).fetchall()

    conn.close()

    return render_template(
        "college_detail.html",
        college=college,
        students=students
    )


# ---------------------------------------------------------
# OPPORTUNITIES & APPLICATIONS
# ---------------------------------------------------------

@app.route("/opportunities")
@login_required
def opportunities_list():
    uid = session["user_id"]
    category = request.args.get("category", "").strip().lower()
    q = request.args.get("q", "").strip()
    tab = request.args.get("tab", "all").strip().lower()

    conn = get_db()
    params = []

    if tab == "saved":
        sql = """
            SELECT o.*, 1 AS is_saved,
                   (SELECT COUNT(*) FROM applications WHERE opportunity_id = o.id AND user_id = ?) AS has_applied
            FROM opportunities o
            JOIN saved_opportunities s ON s.opportunity_id = o.id
            WHERE s.user_id = ?
        """
        params.extend([uid, uid])
    elif tab == "applied":
        sql = """
            SELECT o.*, a.status AS application_status, a.created_at AS applied_date,
                   (SELECT COUNT(*) FROM saved_opportunities WHERE opportunity_id = o.id AND user_id = ?) AS is_saved,
                   1 AS has_applied
            FROM opportunities o
            JOIN applications a ON a.opportunity_id = o.id
            WHERE a.user_id = ?
        """
        params.extend([uid, uid])
    else:
        sql = """
            SELECT o.*,
                   (SELECT COUNT(*) FROM saved_opportunities WHERE opportunity_id = o.id AND user_id = ?) AS is_saved,
                   (SELECT COUNT(*) FROM applications WHERE opportunity_id = o.id AND user_id = ?) AS has_applied
            FROM opportunities o
            WHERE 1=1
        """
        params.extend([uid, uid])

    if category:
        sql += " AND o.category = ?"
        params.append(category)

    if q:
        sql += " AND (o.title LIKE ? OR o.organization LIKE ? OR o.skills_required LIKE ? OR o.location LIKE ?)"
        val = f"%{q}%"
        params.extend([val, val, val, val])

    sql += " ORDER BY o.id DESC"
    opportunities = conn.execute(sql, params).fetchall()

    # Counts for badge tabs
    all_count = conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0]
    saved_count = conn.execute("SELECT COUNT(*) FROM saved_opportunities WHERE user_id = ?", (uid,)).fetchone()[0]
    applied_count = conn.execute("SELECT COUNT(*) FROM applications WHERE user_id = ?", (uid,)).fetchone()[0]

    conn.close()

    return render_template(
        "opportunities.html",
        opportunities=opportunities,
        category=category,
        q=q,
        tab=tab,
        all_count=all_count,
        saved_count=saved_count,
        applied_count=applied_count
    )


@app.route("/opportunity/<int:opportunity_id>")
@login_required
def opportunity_detail(opportunity_id):
    uid = session["user_id"]
    conn = get_db()
    opp = conn.execute("SELECT * FROM opportunities WHERE id = ?", (opportunity_id,)).fetchone()
    if not opp:
        conn.close()
        flash("Opportunity not found.", "danger")
        return redirect(url_for("opportunities_list"))

    is_saved = bool(conn.execute(
        "SELECT id FROM saved_opportunities WHERE user_id = ? AND opportunity_id = ?",
        (uid, opportunity_id)
    ).fetchone())

    application = conn.execute(
        "SELECT * FROM applications WHERE user_id = ? AND opportunity_id = ?",
        (uid, opportunity_id)
    ).fetchone()

    conn.close()

    return render_template(
        "opportunity_detail.html",
        opportunity=opp,
        is_saved=is_saved,
        application=application
    )


@app.route("/opportunity/<int:opportunity_id>/save", methods=["POST"])
@login_required
def toggle_save_opportunity(opportunity_id):
    uid = session["user_id"]
    conn = get_db()
    saved = conn.execute(
        "SELECT id FROM saved_opportunities WHERE user_id = ? AND opportunity_id = ?",
        (uid, opportunity_id)
    ).fetchone()

    if saved:
        conn.execute("DELETE FROM saved_opportunities WHERE id = ?", (saved["id"],))
        flash("Removed from saved opportunities.", "info")
    else:
        conn.execute(
            "INSERT INTO saved_opportunities (user_id, opportunity_id) VALUES (?, ?)",
            (uid, opportunity_id)
        )
        flash("Opportunity bookmarked!", "success")

    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for("opportunity_detail", opportunity_id=opportunity_id))


@app.route("/opportunity/<int:opportunity_id>/apply", methods=["POST"])
@login_required
def apply_opportunity(opportunity_id):
    uid = session["user_id"]
    resume_note = request.form.get("resume_note", "").strip()

    conn = get_db()
    existing = conn.execute(
        "SELECT id FROM applications WHERE user_id = ? AND opportunity_id = ?",
        (uid, opportunity_id)
    ).fetchone()

    if existing:
        flash("You have already submitted an application for this opportunity.", "info")
    else:
        conn.execute("""
            INSERT INTO applications (user_id, opportunity_id, resume_note, status)
            VALUES (?, ?, ?, 'applied')
        """, (uid, opportunity_id, resume_note))

        opp = conn.execute("SELECT title, organization FROM opportunities WHERE id = ?", (opportunity_id,)).fetchone()
        database.add_notification(
            uid,
            "application",
            "Application Submitted",
            f"Your application for '{opp['title']}' at {opp['organization']} has been recorded.",
            url_for("opportunity_detail", opportunity_id=opportunity_id),
            conn=conn
        )

        conn.commit()
        flash("Application submitted successfully!", "success")

    conn.close()
    return redirect(url_for("opportunity_detail", opportunity_id=opportunity_id))


# ---------------------------------------------------------
# EVENTS & REGISTRATION
# ---------------------------------------------------------

@app.route("/events")
@login_required
def events_list():
    uid = session["user_id"]
    q = request.args.get("q", "").strip()
    event_type = request.args.get("type", "").strip().lower()

    conn = get_db()
    sql = """
        SELECT e.*,
               (SELECT COUNT(*) FROM event_registrations WHERE event_id = e.id) AS attendee_count,
               (SELECT status FROM event_registrations WHERE event_id = e.id AND user_id = ?) AS user_registration_status
        FROM events e
        WHERE 1=1
    """
    params = [uid]

    if event_type:
        sql += " AND e.event_type = ?"
        params.append(event_type)

    if q:
        sql += " AND (e.title LIKE ? OR e.organizer LIKE ? OR e.location LIKE ?)"
        val = f"%{q}%"
        params.extend([val, val, val])

    sql += " ORDER BY e.event_date ASC"
    events = conn.execute(sql, params).fetchall()
    conn.close()

    return render_template(
        "events.html",
        events=events,
        q=q,
        selected_type=event_type
    )


@app.route("/event/<int:event_id>")
@login_required
def event_detail(event_id):
    uid = session["user_id"]
    conn = get_db()
    event = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    if not event:
        conn.close()
        flash("Event not found.", "danger")
        return redirect(url_for("events_list"))

    registration = conn.execute(
        "SELECT * FROM event_registrations WHERE user_id = ? AND event_id = ?",
        (uid, event_id)
    ).fetchone()

    attendees = conn.execute("""
        SELECT u.id, u.name, u.course, u.college, u.profile_photo, er.status, er.created_at
        FROM event_registrations er
        JOIN users u ON u.id = er.user_id
        WHERE er.event_id = ?
        ORDER BY er.id DESC
    """, (event_id,)).fetchall()

    conn.close()

    return render_template(
        "event_detail.html",
        event=event,
        registration=registration,
        attendees=attendees
    )


@app.route("/event/<int:event_id>/register", methods=["POST"])
@login_required
def toggle_event_registration(event_id):
    uid = session["user_id"]
    status_choice = request.form.get("status", "registered")

    conn = get_db()
    existing = conn.execute(
        "SELECT id FROM event_registrations WHERE user_id = ? AND event_id = ?",
        (uid, event_id)
    ).fetchone()

    if existing:
        conn.execute("DELETE FROM event_registrations WHERE id = ?", (existing["id"],))
        flash("Registration canceled.", "info")
    else:
        conn.execute("""
            INSERT INTO event_registrations (user_id, event_id, status)
            VALUES (?, ?, ?)
        """, (uid, event_id, status_choice))

        event = conn.execute("SELECT title FROM events WHERE id = ?", (event_id,)).fetchone()
        database.add_notification(
            uid,
            "event",
            "Event Registration Confirmed",
            f"You have registered for '{event['title']}'. Check event details for timings.",
            url_for("event_detail", event_id=event_id),
            conn=conn
        )
        flash("You are registered for this event!", "success")

    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for("event_detail", event_id=event_id))


# ---------------------------------------------------------
# AI CAREER ASSISTANT
# ---------------------------------------------------------

@app.route("/ai-assistant", methods=["GET", "POST"])
@login_required
def ai_assistant():
    answer = None
    question = ""
    topic_tag = None
    uid = session["user_id"]

    conn = get_db()
    user = conn.execute("SELECT name, course, branch, college, semester, cgpa FROM users WHERE id = ?", (uid,)).fetchone()
    conn.close()

    if request.method == "POST":
        question = request.form.get("question", "").strip()

        if question:
            q_lower = question.lower()

            # Rule-based intelligent offline career counselor for diploma students
            if any(k in q_lower for k in ["leet", "lateral", "b.tech", "btech", "degree", "bcece", "engineering after diploma"]):
                topic_tag = "Lateral Entry & Higher Studies"
                answer = (
                    "**Lateral Entry to B.Tech (Direct 2nd Year / 3rd Semester):**\n\n"
                    "1. **Eligibility:** Complete your 3-year Diploma with minimum 45% (40% for reserved categories) recognized by AICTE / SBTE.\n"
                    "2. **State LEET Entrance Exams:** In Bihar, prepare for **BCECE (LE)**. In UP, **UPTAC LEET**; in West Bengal, **JELET**.\n"
                    "3. **Syllabus Focus:** Engineering Mathematics (Calculus, Differential Equations, Matrices), Basic Electrical/Mechanical Concepts, and Technical English.\n"
                    "4. **Top Colleges for LEET:** MIT Muzaffarpur, BCE Bhagalpur, Bakhtiyarpur College of Engineering, and state government engineering colleges.\n"
                    "5. **Alternative Path:** You can also pursue Part-Time / Evening B.Tech or AMIE while working in an industry role."
                )
            elif any(k in q_lower for k in ["government", "govt", "ssc je", "rrb je", "psu", "railway", "isro", "drdo", "bhel"]):
                topic_tag = "Government Jobs & Public Sector"
                answer = (
                    "**Government Opportunities for Diploma Holders:**\n\n"
                    "1. **SSC JE (Junior Engineer):** Premier central exam recruiting for CPWD, MES, CWC, and Border Roads. High vacancy for Civil, Electrical, and Mechanical.\n"
                    "2. **RRB JE (Railway Recruitment Board):** Excellent payscale and career growth in Indian Railways technical divisions.\n"
                    "3. **State JE Examinations:** State department recruitment (Bihar Water Resources, Road Construction, Building Construction, BSPHCL for Electrical).\n"
                    "4. **PSU Recruitments:** IOCL, ONGC, NTPC, SAIL, and BHEL hire Diploma Trainees through written test & trade tests.\n"
                    "5. **Preparation Strategy:** Start technical subject revisions from 5th semester, solve previous 10 years' SSC JE objective papers, and practice non-tech reasoning and general awareness."
                )
            elif any(k in q_lower for k in ["computer science", "cse", "it", "software", "web dev", "python", "programming", "coding"]):
                topic_tag = "Computer Science & IT Career Path"
                answer = (
                    "**Roadmap for Diploma CSE / IT Students:**\n\n"
                    "1. **Foundation:** Master one core programming language thoroughly (Python or Java/C++).\n"
                    "2. **Web Development Stack:** Learn HTML5, CSS3, modern JavaScript, and Flask/Django for backend integration with SQLite/PostgreSQL.\n"
                    "3. **Projects:** Build 2-3 genuine full-stack applications (e.g., student management, inventory system, portfolio network) and host code on GitHub.\n"
                    "4. **Certifications:** Pursue free certifications from freeCodeCamp, CS50, or Cisco Networking Academy.\n"
                    "5. **Entry Roles:** Junior Python Developer, Web Developer, QA/Testing Engineer, Technical Support Specialist. Apply to startups and IT service firms."
                )
            elif any(k in q_lower for k in ["mechanical", "mech", "cad", "autocad", "automobile", "production"]):
                topic_tag = "Mechanical Engineering Career Path"
                answer = (
                    "**Roadmap for Diploma Mechanical Students:**\n\n"
                    "1. **Essential Software Skills:** AutoCAD 2D/3D drafting, SolidWorks, or CATIA. High industry demand for design drafters.\n"
                    "2. **Core Domain Focus:** Thermodynamics, Manufacturing Processes, Fluid Mechanics, Strength of Materials.\n"
                    "3. **Industrial Training:** Undergo training in CNC operations, quality control (QA/QC), or HVAC systems.\n"
                    "4. **Target Employers:** Automotive manufacturers (Tata Motors, Hero, Maruti vendors), Indian Railways, BHEL, and engineering fabrication plants.\n"
                    "5. **Key Tip:** Maintain a digital portfolio of your AutoCAD design drawings and 3D models."
                )
            elif any(k in q_lower for k in ["civil", "construction", "site engineer", "surveying"]):
                topic_tag = "Civil Engineering Career Path"
                answer = (
                    "**Roadmap for Diploma Civil Engineering Students:**\n\n"
                    "1. **Core Practical Skills:** Total Station surveying, GPS leveling, Site measurement books, Concrete technology tests.\n"
                    "2. **Software Tools:** AutoCAD Civil, Revit, and basic structural estimation spreadsheets.\n"
                    "3. **Target Roles:** Junior Site Engineer, Quality Inspector, Quantity Surveyor, Billing Engineer, Draftsman.\n"
                    "4. **Top Recruiters:** L&T Construction, NBCC, Bihar Rajya Pul Nirman Nigam, and regional infrastructure contractors.\n"
                    "5. **Govt Opportunities:** State PWD, Irrigation departments, and SSC JE Civil have the largest number of seats."
                )
            elif any(k in q_lower for k in ["electrical", "electronics", "eee", "ece", "plc", "scada", "iot"]):
                topic_tag = "Electrical & Electronics Career Path"
                answer = (
                    "**Roadmap for Diploma Electrical / Electronics Students:**\n\n"
                    "1. **Practical Industry Skills:** Substation maintenance, PLC & SCADA programming, MATLAB/Simulink, PCB designing.\n"
                    "2. **Certifications:** Industrial Automation training (MSME centers), Solar PV technician certification.\n"
                    "3. **Job Roles:** Substation Operator, Maintenance Engineer, PLC Programmer, Service Technician, Telecommunications Field Engineer.\n"
                    "4. **Key Sectors:** State Power Distribution Companies (BSPHCL), Solar Energy EPC firms, Indian Railways (Loco Maintenance), and consumer electronics manufacturing."
                )
            elif any(k in q_lower for k in ["resume", "cv", "portfolio", "interview"]):
                topic_tag = "Resume & Interview Strategy"
                answer = (
                    "**Diploma Resume & Interview Checklist:**\n\n"
                    "1. **Structure:** Header (Name, Phone, Email, LinkedIn/DiplomaConnect profile) -> Objective -> Education (Diploma first with CGPA, 10th details) -> Technical Skills -> Projects -> Certifications -> Achievements.\n"
                    "2. **Projects Matter Most:** Clearly state the project title, tools used, and your individual contribution (e.g., 'Implemented SQLite database and authentication in Flask').\n"
                    "3. **Keep it 1 Page:** Recruiters spend less than 10 seconds reviewing fresher resumes.\n"
                    "4. **Interview Preparation:** Be ready to draw circuit diagrams or explain block diagrams of your final year diploma project on a whiteboard.\n"
                    "5. **Soft Skills:** Practice a clear 60-second introduction explaining your technical background and eagerness to learn on the job."
                )
            elif any(k in q_lower for k in ["internship", "apprentice", "apprenticeship", "nats", "stipend"]):
                topic_tag = "Internships & NATS Apprenticeship"
                answer = (
                    "**Internship & Apprenticeship Guide:**\n\n"
                    "1. **NATS Portal:** Register on the National Apprenticeship Training Scheme (portal.mhrdnats.gov.in) with your diploma enrollment number.\n"
                    "2. **Stipend:** Diploma apprentices receive a government-guaranteed monthly stipend ranging between ₹8,000 - ₹12,000.\n"
                    "3. **Internship Season:** Apply 2-3 months before your 5th/6th semester breaks.\n"
                    "4. **Check Opportunities:** Browse the DiplomaConnect Opportunities tab for vetted polytechnic internships and apprentice drives.\n"
                    "5. **Documentation:** Keep your semester marksheets, Bonafide certificate from college principal, and Aadhaar card ready."
                )
            else:
                topic_tag = "General Career Advisory"
                answer = (
                    "**General Advice for Your Diploma Journey:**\n\n"
                    f"Hello {user['name'] if user else 'student'}! For diploma students in {user['course'] if user and user['course'] else 'engineering'}:\n\n"
                    "1. **Academics:** Maintain a CGPA above 7.5 to meet cutoff criteria for B.Tech lateral entry and PSU recruitment.\n"
                    "2. **Hands-on Skills:** Employers value practical lab and software competence over pure theory.\n"
                    "3. **Professional Network:** Connect with alumni and seniors on DiplomaConnect who have cleared exams or landed placements.\n"
                    "4. **Final Year Project:** Pick an impactful real-world problem rather than copying ready-made kits.\n\n"
                    "*You can ask specific questions like: 'How to prepare for SSC JE?', 'Career paths for Civil diploma', 'Resume tips', or 'Best Python projects'.*"
                )

    return render_template(
        "ai_assistant.html",
        answer=answer,
        question=question,
        topic_tag=topic_tag,
        user=user
    )


# ---------------------------------------------------------
# CAREER ROADMAPS & LEARNING RESOURCES
# ---------------------------------------------------------

@app.route("/roadmap")
@login_required
def roadmap():
    uid = session["user_id"]
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    user_skills_rows = conn.execute("SELECT skill_name FROM skills WHERE user_id = ?", (uid,)).fetchall()
    user_skills = [s["skill_name"] for s in user_skills_rows]
    user_skills_lower = {s.lower() for s in user_skills}
    conn.close()

    branch_param = request.args.get("branch", "").lower()
    user_course = ((user["course"] or "") + " " + (user["branch"] or "")).lower()

    if not branch_param:
        if any(b in user_course for b in ["computer", "cse", "it", "software"]):
            active_branch = "cse"
        elif any(b in user_course for b in ["mech", "auto", "production"]):
            active_branch = "mechanical"
        elif any(b in user_course for b in ["civil", "construction"]):
            active_branch = "civil"
        elif any(b in user_course for b in ["electr"]):
            active_branch = "electrical"
        elif any(b in user_course for b in ["ece", "electron", "telecom"]):
            active_branch = "electronics"
        else:
            active_branch = "cse"
    else:
        active_branch = branch_param

    return render_template(
        "roadmap.html",
        user=user,
        user_skills=user_skills,
        user_skills_lower=user_skills_lower,
        active_branch=active_branch
    )


@app.route("/resources")
@login_required
def resources():
    uid = session["user_id"]
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    conn.close()

    category = request.args.get("category", "all")
    return render_template(
        "resources.html",
        user=user,
        category=category
    )


# ---------------------------------------------------------
# SAFETY & PRIVACY: REPORTING & BLOCKING
# ---------------------------------------------------------

@app.route("/report", methods=["POST"])
@login_required
def report_content():
    reporter_id = session["user_id"]
    reported_user_id = request.form.get("reported_user_id")
    reported_post_id = request.form.get("reported_post_id")
    reason = request.form.get("reason", "").strip()

    if not reason:
        flash("Please provide a reason for the report.", "warning")
        return redirect(request.referrer or url_for("home"))

    conn = get_db()
    conn.execute("""
        INSERT INTO reports (reporter_id, reported_user_id, reported_post_id, reason, status)
        VALUES (?, ?, ?, ?, 'pending')
    """, (reporter_id, reported_user_id or None, reported_post_id or None, reason))
    conn.commit()
    conn.close()

    flash("Thank you for your report. Our administration will review it promptly.", "success")
    return redirect(request.referrer or url_for("home"))


@app.route("/block/<int:user_id>", methods=["POST"])
@login_required
def block_user(user_id):
    uid = session["user_id"]
    if user_id == uid:
        flash("You cannot block yourself.", "warning")
        return redirect(request.referrer or url_for("home"))

    conn = get_db()
    # Insert block
    conn.execute("""
        INSERT OR IGNORE INTO blocks (blocker_id, blocked_id)
        VALUES (?, ?)
    """, (uid, user_id))

    # Remove any existing connection
    conn.execute("""
        DELETE FROM connections
        WHERE (sender_id = ? AND receiver_id = ?)
           OR (sender_id = ? AND receiver_id = ?)
    """, (uid, user_id, user_id, uid))

    conn.commit()
    conn.close()

    flash("User has been blocked. They can no longer connect or interact with you.", "info")
    return redirect(url_for("home"))


@app.route("/unblock/<int:user_id>", methods=["POST"])
@login_required
def unblock_user(user_id):
    uid = session["user_id"]
    conn = get_db()
    conn.execute("DELETE FROM blocks WHERE blocker_id = ? AND blocked_id = ?", (uid, user_id))
    conn.commit()
    conn.close()

    flash("User has been unblocked.", "info")
    return redirect(request.referrer or url_for("home"))


# ---------------------------------------------------------
# ADMIN MANAGEMENT SYSTEM
# ---------------------------------------------------------

@app.route("/admin")
@admin_required
def admin_dashboard():
    conn = get_db()
    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_students = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'student'").fetchone()[0]
    total_colleges = conn.execute("SELECT COUNT(*) FROM colleges").fetchone()[0]
    total_opportunities = conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0]
    total_events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    total_posts = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    pending_reports = conn.execute("SELECT COUNT(*) FROM reports WHERE status = 'pending'").fetchone()[0]

    recent_users = conn.execute("SELECT * FROM users ORDER BY id DESC LIMIT 5").fetchall()
    recent_reports = conn.execute("""
        SELECT r.*, u.name AS reporter_name
        FROM reports r
        JOIN users u ON u.id = r.reporter_id
        WHERE r.status = 'pending'
        ORDER BY r.id DESC LIMIT 5
    """).fetchall()

    conn.close()

    return render_template(
        "admin.html",
        total_users=total_users,
        total_students=total_students,
        total_colleges=total_colleges,
        total_opportunities=total_opportunities,
        total_events=total_events,
        total_posts=total_posts,
        pending_reports=pending_reports,
        recent_users=recent_users,
        recent_reports=recent_reports
    )


@app.route("/admin/users")
@admin_required
def admin_users():
    q = request.args.get("q", "").strip()
    role_filter = request.args.get("role", "").strip()

    conn = get_db()
    sql = "SELECT * FROM users WHERE 1=1"
    params = []

    if q:
        sql += " AND (name LIKE ? OR email LIKE ? OR college LIKE ? OR course LIKE ?)"
        val = f"%{q}%"
        params.extend([val, val, val, val])

    if role_filter:
        sql += " AND role = ?"
        params.append(role_filter)

    sql += " ORDER BY id DESC"
    users = conn.execute(sql, params).fetchall()
    conn.close()

    return render_template("admin_users.html", users=users, q=q, selected_role=role_filter)


@app.route("/admin/user/<int:user_id>/toggle-status", methods=["POST"])
@admin_required
def admin_toggle_user_status(user_id):
    conn = get_db()
    user = conn.execute("SELECT status, role FROM users WHERE id = ?", (user_id,)).fetchone()
    if user:
        if user_id == session["user_id"]:
            flash("You cannot deactivate your own admin account.", "warning")
        else:
            new_status = "banned" if user["status"] == "active" else "active"
            conn.execute("UPDATE users SET status = ? WHERE id = ?", (new_status, user_id))
            conn.commit()
            flash(f"User account status changed to '{new_status}'.", "info")
    conn.close()
    return redirect(request.referrer or url_for("admin_users"))


@app.route("/admin/user/<int:user_id>/toggle-role", methods=["POST"])
@admin_required
def admin_toggle_user_role(user_id):
    conn = get_db()
    user = conn.execute("SELECT role FROM users WHERE id = ?", (user_id,)).fetchone()
    if user:
        if user_id == session["user_id"]:
            flash("You cannot demote yourself.", "warning")
        else:
            new_role = "admin" if user["role"] == "student" else "student"
            conn.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
            conn.commit()
            flash(f"User role changed to '{new_role}'.", "success")
    conn.close()
    return redirect(request.referrer or url_for("admin_users"))


@app.route("/admin/colleges")
@admin_required
def admin_colleges():
    q = request.args.get("q", "").strip()
    conn = get_db()
    sql = "SELECT * FROM colleges WHERE 1=1"
    params = []
    if q:
        sql += " AND (name LIKE ? OR district LIKE ?)"
        val = f"%{q}%"
        params.extend([val, val])
    sql += " ORDER BY id DESC"
    colleges = conn.execute(sql, params).fetchall()
    conn.close()
    return render_template("admin_colleges.html", colleges=colleges, q=q)


@app.route("/admin/college/add", methods=["POST"])
@admin_required
def admin_add_college():
    name = request.form.get("name", "").strip()
    district = request.form.get("district", "").strip()
    university = request.form.get("university", "SBTE Bihar").strip()
    college_type = request.form.get("type", "Government Polytechnic").strip()
    website = request.form.get("website", "").strip()
    description = request.form.get("description", "").strip()

    if name:
        conn = get_db()
        try:
            conn.execute("""
                INSERT INTO colleges (name, district, university, type, website, description, verified)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (name, district, university, college_type, website, description))
            conn.commit()
            flash(f"College '{name}' added successfully!", "success")
        except sqlite3.IntegrityError:
            flash(f"A college with name '{name}' already exists.", "danger")
        conn.close()

    return redirect(url_for("admin_colleges"))


@app.route("/admin/college/<int:college_id>/edit", methods=["POST"])
@admin_required
def admin_edit_college(college_id):
    name = request.form.get("name", "").strip()
    district = request.form.get("district", "").strip()
    university = request.form.get("university", "").strip()
    college_type = request.form.get("type", "").strip()
    website = request.form.get("website", "").strip()
    description = request.form.get("description", "").strip()

    if name:
        conn = get_db()
        conn.execute("""
            UPDATE colleges SET
                name = ?, district = ?, university = ?, type = ?,
                website = ?, description = ?
            WHERE id = ?
        """, (name, district, university, college_type, website, description, college_id))
        conn.commit()
        conn.close()
        flash("College updated successfully.", "success")
    return redirect(url_for("admin_colleges"))


@app.route("/admin/college/<int:college_id>/delete", methods=["POST"])
@admin_required
def admin_delete_college(college_id):
    conn = get_db()
    conn.execute("DELETE FROM colleges WHERE id = ?", (college_id,))
    conn.commit()
    conn.close()
    flash("College removed from directory.", "info")
    return redirect(url_for("admin_colleges"))


@app.route("/admin/opportunities")
@admin_required
def admin_opportunities():
    conn = get_db()
    opps = conn.execute("""
        SELECT o.*,
               (SELECT COUNT(*) FROM applications WHERE opportunity_id = o.id) AS applicants_count
        FROM opportunities o
        ORDER BY o.id DESC
    """).fetchall()
    conn.close()
    return render_template("admin_opportunities.html", opportunities=opps)


@app.route("/admin/opportunity/add", methods=["POST"])
@admin_required
def admin_add_opportunity():
    title = request.form.get("title", "").strip()
    org = request.form.get("organization", "").strip()
    category = request.form.get("category", "internship").strip()
    description = request.form.get("description", "").strip()
    location = request.form.get("location", "").strip()
    eligibility = request.form.get("eligibility", "").strip()
    skills = request.form.get("skills_required", "").strip()
    deadline = request.form.get("deadline", "").strip()
    application_url = request.form.get("application_url", "").strip()

    if title and org and description:
        conn = get_db()
        conn.execute("""
            INSERT INTO opportunities (
                title, organization, category, description, location,
                eligibility, skills_required, deadline, application_url, posted_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, org, category, description, location, eligibility, skills, deadline, application_url, session["user_id"]))
        conn.commit()
        conn.close()
        flash("Opportunity listed successfully!", "success")

    return redirect(url_for("admin_opportunities"))


@app.route("/admin/opportunity/<int:opportunity_id>/edit", methods=["POST"])
@admin_required
def admin_edit_opportunity(opportunity_id):
    title = request.form.get("title", "").strip()
    org = request.form.get("organization", "").strip()
    category = request.form.get("category", "").strip()
    description = request.form.get("description", "").strip()
    location = request.form.get("location", "").strip()
    eligibility = request.form.get("eligibility", "").strip()
    skills = request.form.get("skills_required", "").strip()
    deadline = request.form.get("deadline", "").strip()
    application_url = request.form.get("application_url", "").strip()

    if title and org and description:
        conn = get_db()
        conn.execute("""
            UPDATE opportunities SET
                title = ?, organization = ?, category = ?, description = ?, location = ?,
                eligibility = ?, skills_required = ?, deadline = ?, application_url = ?
            WHERE id = ?
        """, (title, org, category, description, location, eligibility, skills, deadline, application_url, opportunity_id))
        conn.commit()
        conn.close()
        flash("Opportunity updated.", "success")
    return redirect(url_for("admin_opportunities"))


@app.route("/admin/opportunity/<int:opportunity_id>/delete", methods=["POST"])
@admin_required
def admin_delete_opportunity(opportunity_id):
    conn = get_db()
    conn.execute("DELETE FROM opportunities WHERE id = ?", (opportunity_id,))
    conn.commit()
    conn.close()
    flash("Opportunity deleted.", "info")
    return redirect(url_for("admin_opportunities"))


@app.route("/admin/opportunity/<int:opportunity_id>/applicants")
@admin_required
def admin_opportunity_applicants(opportunity_id):
    conn = get_db()
    opp = conn.execute("SELECT * FROM opportunities WHERE id = ?", (opportunity_id,)).fetchone()
    if not opp:
        conn.close()
        flash("Opportunity not found.", "danger")
        return redirect(url_for("admin_opportunities"))

    applicants = conn.execute("""
        SELECT a.*, u.name, u.email, u.phone, u.course, u.college, u.cgpa, u.profile_photo
        FROM applications a
        JOIN users u ON u.id = a.user_id
        WHERE a.opportunity_id = ?
        ORDER BY a.id DESC
    """, (opportunity_id,)).fetchall()
    conn.close()

    return render_template("admin_opportunity_applicants.html", opportunity=opp, applicants=applicants)


@app.route("/admin/events")
@admin_required
def admin_events():
    conn = get_db()
    events = conn.execute("""
        SELECT e.*,
               (SELECT COUNT(*) FROM event_registrations WHERE event_id = e.id) AS registrations_count
        FROM events e
        ORDER BY e.event_date DESC
    """).fetchall()
    conn.close()
    return render_template("admin_events.html", events=events)


@app.route("/admin/event/add", methods=["POST"])
@admin_required
def admin_add_event():
    title = request.form.get("title", "").strip()
    organizer = request.form.get("organizer", "").strip()
    description = request.form.get("description", "").strip()
    event_date = request.form.get("event_date", "").strip()
    event_time = request.form.get("event_time", "").strip()
    location = request.form.get("location", "").strip()
    event_type = request.form.get("event_type", "online").strip()
    reg_link = request.form.get("registration_link", "").strip()

    if title and organizer and event_date:
        conn = get_db()
        conn.execute("""
            INSERT INTO events (
                title, organizer, description, event_date, event_time,
                location, event_type, registration_link, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, organizer, description, event_date, event_time, location, event_type, reg_link, session["user_id"]))
        conn.commit()
        conn.close()
        flash("Event added to calendar.", "success")

    return redirect(url_for("admin_events"))


@app.route("/admin/event/<int:event_id>/edit", methods=["POST"])
@admin_required
def admin_edit_event(event_id):
    title = request.form.get("title", "").strip()
    organizer = request.form.get("organizer", "").strip()
    description = request.form.get("description", "").strip()
    event_date = request.form.get("event_date", "").strip()
    event_time = request.form.get("event_time", "").strip()
    location = request.form.get("location", "").strip()
    event_type = request.form.get("event_type", "").strip()
    reg_link = request.form.get("registration_link", "").strip()

    if title and event_date:
        conn = get_db()
        conn.execute("""
            UPDATE events SET
                title = ?, organizer = ?, description = ?, event_date = ?,
                event_time = ?, location = ?, event_type = ?, registration_link = ?
            WHERE id = ?
        """, (title, organizer, description, event_date, event_time, location, event_type, reg_link, event_id))
        conn.commit()
        conn.close()
        flash("Event updated.", "success")
    return redirect(url_for("admin_events"))


@app.route("/admin/event/<int:event_id>/delete", methods=["POST"])
@admin_required
def admin_delete_event(event_id):
    conn = get_db()
    conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
    conn.commit()
    conn.close()
    flash("Event removed.", "info")
    return redirect(url_for("admin_events"))


@app.route("/admin/reports")
@admin_required
def admin_reports():
    conn = get_db()
    reports = conn.execute("""
        SELECT r.*,
               u_rep.name AS reporter_name,
               u_rep.email AS reporter_email,
               u_tar.name AS reported_user_name,
               p.content AS reported_post_content
        FROM reports r
        JOIN users u_rep ON u_rep.id = r.reporter_id
        LEFT JOIN users u_tar ON u_tar.id = r.reported_user_id
        LEFT JOIN posts p ON p.id = r.reported_post_id
        ORDER BY r.id DESC
    """).fetchall()
    conn.close()
    return render_template("admin_reports.html", reports=reports)


@app.route("/admin/report/<int:report_id>/resolve", methods=["POST"])
@admin_required
def admin_resolve_report(report_id):
    action = request.form.get("action", "dismiss")
    conn = get_db()
    report = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()

    if report:
        if action == "delete_post" and report["reported_post_id"]:
            conn.execute("DELETE FROM posts WHERE id = ?", (report["reported_post_id"],))
            flash("Reported post deleted.", "info")
        elif action == "ban_user" and report["reported_user_id"]:
            conn.execute("UPDATE users SET status = 'banned' WHERE id = ?", (report["reported_user_id"],))
            flash("Reported user has been banned.", "warning")

        conn.execute("UPDATE reports SET status = 'resolved' WHERE id = ?", (report_id,))
        conn.commit()
        flash("Report marked as resolved.", "success")

    conn.close()
    return redirect(url_for("admin_reports"))


# ---------------------------------------------------------
# APPLICATION ENTRY POINT
# ---------------------------------------------------------

# Ensure tables are initialized when starting app
database.init_db()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
