"""
database.py - Database connection, safe schema migrations, and helper functions for DiplomaConnect.
Designed to be beginner-friendly, clean, and easily editable by students.
"""

import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")


def get_db():
    """
    Returns an open SQLite database connection with row factory configured to Row.
    """
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """
    Safely initializes all database tables, columns, and seed data.
    Preserves existing tables and records without dropping or resetting database.db.
    """
    conn = get_db()
    cursor = conn.cursor()

    # 1. USERS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            password TEXT NOT NULL,
            dob TEXT,
            gender TEXT,
            address TEXT,
            enrollment_no TEXT,
            admission_year TEXT,
            course TEXT,
            branch TEXT,
            college TEXT,
            university TEXT,
            semester TEXT,
            cgpa TEXT,
            total_credits TEXT,
            profile_photo TEXT,
            role TEXT DEFAULT 'student',
            headline TEXT,
            about TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Safe column additions to 'users' if created previously with fewer columns
    existing_user_cols = [
        row["name"] for row in cursor.execute("PRAGMA table_info(users)").fetchall()
    ]
    user_cols_to_add = [
        ("branch", "TEXT"),
        ("role", "TEXT DEFAULT 'student'"),
        ("headline", "TEXT"),
        ("about", "TEXT"),
        ("status", "TEXT DEFAULT 'active'"),
        ("created_at", "TEXT"),
    ]
    for col_name, col_def in user_cols_to_add:
        if col_name not in existing_user_cols:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}")

    # 2. SKILLS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            skill_name TEXT NOT NULL,
            category TEXT DEFAULT 'Technical',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    # 3. PROJECTS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            tech_stack TEXT,
            project_url TEXT,
            github_url TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    # 4. CERTIFICATIONS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS certifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            issuer TEXT NOT NULL,
            issue_date TEXT,
            credential_url TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    # 5. ACHIEVEMENTS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            year TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    # 6. POSTS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            post_type TEXT DEFAULT 'general',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    # 7. POST LIKES TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS post_likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(post_id, user_id),
            FOREIGN KEY (post_id) REFERENCES posts (id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    # 8. POST COMMENTS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS post_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES posts (id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    # 9. CONNECTIONS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(sender_id, receiver_id),
            FOREIGN KEY (sender_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (receiver_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    # 10. MESSAGES TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sender_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (receiver_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    # 11. NOTIFICATIONS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            link TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    # 12. COLLEGES TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS colleges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            district TEXT,
            university TEXT,
            type TEXT,
            website TEXT,
            description TEXT,
            verified INTEGER DEFAULT 1
        )
    """)
    existing_college_cols = [
        row["name"] for row in cursor.execute("PRAGMA table_info(colleges)").fetchall()
    ]
    for col_name, col_def in [("website", "TEXT"), ("description", "TEXT")]:
        if col_name not in existing_college_cols:
            cursor.execute(f"ALTER TABLE colleges ADD COLUMN {col_name} {col_def}")

    # 13. OPPORTUNITIES TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            organization TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            location TEXT,
            eligibility TEXT,
            skills_required TEXT,
            deadline TEXT,
            application_url TEXT,
            posted_by INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (posted_by) REFERENCES users (id) ON DELETE SET NULL
        )
    """)

    # 14. SAVED OPPORTUNITIES TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS saved_opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            opportunity_id INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, opportunity_id),
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (opportunity_id) REFERENCES opportunities (id) ON DELETE CASCADE
        )
    """)

    # 15. APPLICATIONS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            opportunity_id INTEGER NOT NULL,
            resume_note TEXT,
            status TEXT DEFAULT 'applied',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, opportunity_id),
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (opportunity_id) REFERENCES opportunities (id) ON DELETE CASCADE
        )
    """)

    # 16. EVENTS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            organizer TEXT NOT NULL,
            description TEXT NOT NULL,
            event_date TEXT NOT NULL,
            event_time TEXT,
            location TEXT,
            event_type TEXT DEFAULT 'online',
            registration_link TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE SET NULL
        )
    """)

    # 17. EVENT REGISTRATIONS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS event_registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            event_id INTEGER NOT NULL,
            status TEXT DEFAULT 'registered',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, event_id),
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE
        )
    """)

    # 18. REPORTS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_id INTEGER NOT NULL,
            reported_user_id INTEGER,
            reported_post_id INTEGER,
            reason TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (reporter_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (reported_user_id) REFERENCES users (id) ON DELETE SET NULL,
            FOREIGN KEY (reported_post_id) REFERENCES posts (id) ON DELETE SET NULL
        )
    """)

    # 19. BLOCKS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS blocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            blocker_id INTEGER NOT NULL,
            blocked_id INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(blocker_id, blocked_id),
            FOREIGN KEY (blocker_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (blocked_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    # Commit structural changes
    conn.commit()

    # ---------------- SEED ESSENTIAL & SAMPLE DATA ----------------

    # A. Default Admin Account
    admin = cursor.execute(
        "SELECT id FROM users WHERE email = ?", ("admin@diplomaconnect.com",)
    ).fetchone()
    if not admin:
        admin_pass_hash = generate_password_hash("Admin@123")
        cursor.execute("""
            INSERT INTO users (
                name, email, phone, password, role, headline, about,
                course, college, university, semester, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "DiplomaConnect Admin",
            "admin@diplomaconnect.com",
            "+91 9876543210",
            admin_pass_hash,
            "admin",
            "Platform Administrator & Student Coordinator",
            "Dedicated to empowering diploma and polytechnic students across India with opportunities, networking, and career roadmaps.",
            "Administration",
            "DiplomaConnect Central Hub",
            "SBTE Bihar",
            "Faculty/Admin",
            "active"
        ))

    # B. Verified Bihar Polytechnic Colleges (if count is low)
    college_count = cursor.execute("SELECT COUNT(*) FROM colleges").fetchone()[0]
    if college_count == 0:
        bihar_colleges = [
            ("Government Polytechnic Barauni", "Begusarai", "SBTE Bihar", "Government Polytechnic", "https://gpba.org.in", "Established government polytechnic offering diploma courses in Civil, Mechanical, Electrical, and Chemical engineering."),
            ("Government Polytechnic Bhagalpur", "Bhagalpur", "SBTE Bihar", "Government Polytechnic", "https://gpbgp.ac.in", "Premier technical diploma institute in eastern Bihar offering core diploma branches."),
            ("Government Polytechnic Chapra", "Saran", "SBTE Bihar", "Government Polytechnic", "https://gpchapra.org.in", "Pioneering technical polytechnic in Saran division with modern labs."),
            ("Government Polytechnic Gaya", "Gaya", "SBTE Bihar", "Government Polytechnic", "https://gpgaya.ac.in", "Prominent polytechnic offering Electrical, Mechanical, Civil, and CSE diplomas."),
            ("Government Polytechnic Muzaffarpur", "Muzaffarpur", "SBTE Bihar", "Government Polytechnic", "https://gpmuzaffarpur.org.in", "One of North Bihar's oldest polytechnics with extensive industry workshops."),
            ("Government Polytechnic Patna-7", "Patna", "SBTE Bihar", "Government Polytechnic", "https://gpp7.org.in", "Flagship government polytechnic in Patna with state-of-the-art computer science and IT facilities."),
            ("Government Polytechnic Purnea", "Purnea", "SBTE Bihar", "Government Polytechnic", "https://gppurnea.org.in", "Leading polytechnic institute in Seemanchal region offering engineering diplomas."),
            ("Government Polytechnic Vaishali", "Vaishali", "SBTE Bihar", "Government Polytechnic", "https://gpvaishali.org.in", "Technical institution dedicated to high-standard polytechnic engineering education."),
            ("Government Polytechnic Siwan", "Siwan", "SBTE Bihar", "Government Polytechnic", "https://gpsiwan.org.in", "Well-equipped government polytechnic providing diplomas in Civil, Mechanical, and Electrical."),
            ("Government Polytechnic Madhubani", "Madhubani", "SBTE Bihar", "Government Polytechnic", "https://gpmadhubani.org.in", "Modern government polytechnic college established under State Govt initiatives."),
            ("Government Polytechnic Nalanda", "Nalanda", "SBTE Bihar", "Government Polytechnic", "https://gpnalanda.org.in", "Academic hub for technical diploma students in Nalanda and South Bihar."),
            ("Government Polytechnic Nawada", "Nawada", "SBTE Bihar", "Government Polytechnic", "https://gpnawada.org.in", "State polytechnic providing hands-on vocational engineering curriculum."),
            ("Government Polytechnic Rohtas", "Rohtas", "SBTE Bihar", "Government Polytechnic", "https://gprohtas.org.in", "Technical diploma college serving Western Bihar with active workshops."),
            ("Government Polytechnic Saharsa", "Saharsa", "SBTE Bihar", "Government Polytechnic", "https://gpsaharsa.org.in", "Offering diploma certifications in technical and computational trades."),
            ("Government Polytechnic Supaul", "Supaul", "SBTE Bihar", "Government Polytechnic", "https://gpsupaul.org.in", "Polytechnic institute with contemporary engineering laboratories."),
            ("Government Polytechnic Sitamarhi", "Sitamarhi", "SBTE Bihar", "Government Polytechnic", "https://gpsitamarhi.org.in", "Government polytechnic imparting quality technical skills to students."),
            ("Government Polytechnic Jehanabad", "Jehanabad", "SBTE Bihar", "Government Polytechnic", "https://gpjehanabad.org.in", "Well-connected diploma institute focusing on practical training."),
            ("Government Polytechnic Khagaria", "Khagaria", "SBTE Bihar", "Government Polytechnic", "https://gpkhagaria.org.in", "Established to provide accessible technical engineering education.")
        ]
        for col in bihar_colleges:
            cursor.execute("""
                INSERT OR IGNORE INTO colleges (name, district, university, type, website, description, verified)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, col)

    # C. Realistic Sample Opportunities tailored for Diploma Students
    opp_count = cursor.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0]
    if opp_count == 0:
        sample_opportunities = [
            (
                "Junior Web Developer Intern",
                "Bihar State Electronic Development Corp (BELTRON)",
                "internship",
                "BELTRON is inviting applications from Diploma Computer Science and IT students for a 6-month hands-on web development internship. Interns will work with Flask, Python, SQLite, and frontend frameworks on state e-governance portals.",
                "Patna, Bihar (Hybrid)",
                "Diploma in Computer Science, IT or related branch (3rd - 6th Semester)",
                "Python, HTML, CSS, JavaScript, SQLite",
                "2026-10-30",
                "https://bsedc.bihar.gov.in"
            ),
            (
                "Junior Engineer / Technician Apprentice",
                "Bharat Heavy Electricals Limited (BHEL)",
                "apprenticeship",
                "Apprenticeship training program for Diploma holders in Electrical, Mechanical, and Electronics Engineering under the National Apprenticeship Training Scheme (NATS). Monthly stipend provided as per government norms.",
                "Barauni / Patna",
                "Diploma in Electrical / Mechanical / Electronics Engineering",
                "Circuit Analysis, Machine Maintenance, Electrical Safety, CAD",
                "2026-11-15",
                "https://www.bhel.com"
            ),
            (
                "Junior Site Supervisor (Civil)",
                "Bihar Rajya Pul Nirman Nigam Ltd",
                "job",
                "Full-time entry-level position for fresh Diploma in Civil Engineering pass-outs. Responsibilities include site quality inspection, surveying, measurement book entries, and safety supervision.",
                "Muzaffarpur & Patna, Bihar",
                "3-Year Diploma in Civil Engineering from SBTE recognized institute",
                "AutoCAD, Site Surveying, Concrete Technology, Estimation",
                "2026-10-25",
                "https://brpnnl.bihar.gov.in"
            ),
            (
                "SBTE Merit-cum-Means Polytechnic Scholarship",
                "Department of Science & Technology, Govt. of Bihar",
                "scholarship",
                "Annual scholarship grant of ₹12,000 for deserving polytechnic students pursuing regular diploma programs in government polytechnics with CGPA >= 7.5.",
                "All Bihar Districts",
                "Enrolled in 1st, 2nd, or 3rd year in any Government Polytechnic in Bihar",
                "Consistent Academic Record (CGPA 7.5+)",
                "2026-11-30",
                "https://dst.bihar.gov.in"
            ),
            (
                "State Polytechnic Innovation & Hackathon Challenge",
                "State Council for Technical Education (SBTE)",
                "competition",
                "Annual state-level project design competition for polytechnic students. Pitch practical solutions for rural infrastructure, smart irrigation, renewable energy, or digital literacy. Cash prizes up to ₹50,000.",
                "Patna Science Centre / Online",
                "Open to all registered diploma engineering students in Bihar",
                "Hardware/Software prototyping, Presentation, Problem Solving",
                "2026-10-20",
                "https://sbte.bihar.gov.in"
            ),
            (
                "Industrial Automation & PLC/SCADA Training",
                "MSME Technology Centre, Patna",
                "training",
                "Government-subsidized 4-week certification program in PLC programming, SCADA interfaces, and industrial robotics for Electrical, Electronics, and Mechanical diploma students.",
                "Patna, Bihar (Offline)",
                "Diploma 4th to 6th semester students",
                "Basics of Digital Electronics and Control Systems",
                "2026-11-05",
                "https://msme.gov.in"
            )
        ]
        for opp in sample_opportunities:
            cursor.execute("""
                INSERT INTO opportunities (
                    title, organization, category, description, location,
                    eligibility, skills_required, deadline, application_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, opp)

    # D. Realistic Upcoming Events
    event_count = cursor.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    if event_count == 0:
        sample_events = [
            (
                "Bihar Diploma Career Conclave 2026",
                "State Council for Technical Education & Industry Partners",
                "A full-day summit featuring talks from industry leaders, lateral entry (B.Tech LEET) toppers, and PSU recruitment officers guiding diploma students on career paths.",
                "2026-10-15",
                "10:00 AM - 04:30 PM",
                "SK Memorial Hall, Patna (and Live Streamed)",
                "online",
                "https://diplomaconnect.com/conclave"
            ),
            (
                "Python & Web Development Bootcamp for Diploma Students",
                "DiplomaConnect Developer Community",
                "Interactive hands-on workshop covering backend programming with Flask, SQLite database modeling, and building real-world projects to showcase on resume.",
                "2026-10-22",
                "06:00 PM - 08:30 PM",
                "Google Meet / Online Workshop",
                "online",
                "https://diplomaconnect.com/bootcamp"
            ),
            (
                "AutoCAD & 3D Modeling Masterclass",
                "Mechanical & Civil Engineering Guild",
                "Practical workshop for Civil and Mechanical students on drafting structural plans, mechanical assemblies, and standard industrial drawing conventions.",
                "2026-11-02",
                "11:00 AM - 02:00 PM",
                "GP Patna-7 Auditorium & Virtual",
                "offline",
                "https://diplomaconnect.com/autocad"
            ),
            (
                "SSC JE & State JE Examination Strategy Session",
                "Polytechnic Alumni Network",
                "Top rankers from recent Junior Engineer examinations share their preparation strategy, subject weightage, recommended resources, and time management tips.",
                "2026-11-10",
                "07:00 PM - 09:00 PM",
                "Online Webinar",
                "online",
                "https://diplomaconnect.com/je-prep"
            )
        ]
        for ev in sample_events:
            cursor.execute("""
                INSERT INTO events (
                    title, organizer, description, event_date, event_time,
                    location, event_type, registration_link
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, ev)

    # E. Seed initial post if feed is completely empty
    post_count = cursor.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    if post_count == 0:
        user1 = cursor.execute("SELECT id FROM users WHERE id = 1").fetchone()
        author_id = user1["id"] if user1 else 1
        cursor.execute("""
            INSERT INTO posts (user_id, content, post_type)
            VALUES (?, ?, ?)
        """, (
            author_id,
            "Welcome to DiplomaConnect! Excited to connect with fellow diploma and polytechnic students across departments. Feel free to connect and share your latest projects, skills, and questions!",
            "general"
        ))

    conn.commit()
    conn.close()


def add_notification(user_id, notif_type, title, message, link=None, conn=None):
    """Utility to generate an in-app notification for a user."""
    should_close = False
    if conn is None:
        conn = get_db()
        should_close = True
    conn.execute("""
        INSERT INTO notifications (user_id, type, title, message, link)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, notif_type, title, message, link))
    if should_close:
        conn.commit()
        conn.close()


def is_blocked(user1_id, user2_id, conn=None):
    """Returns True if user1 has blocked user2 or user2 has blocked user1."""
    if not user1_id or not user2_id:
        return False
    should_close = False
    if conn is None:
        conn = get_db()
        should_close = True
    res = conn.execute("""
        SELECT id FROM blocks
        WHERE (blocker_id = ? AND blocked_id = ?)
           OR (blocker_id = ? AND blocked_id = ?)
    """, (user1_id, user2_id, user2_id, user1_id)).fetchone()
    if should_close:
        conn.close()
    return bool(res)


def calculate_profile_completion(user, skills_count=0, projects_count=0):
    """
    Calculates profile completion percentage (0 - 100) based on fields populated.
    """
    if not user:
        return 0

    score = 0

    # Core basics (30 pts)
    if user["name"]: score += 5
    if user["email"]: score += 5
    if user["phone"]: score += 5
    if user["dob"]: score += 5
    if user["gender"]: score += 5
    if user["address"]: score += 5

    # Academic details (30 pts)
    if user["college"]: score += 6
    if user["university"]: score += 6
    if user["course"]: score += 6
    if user["semester"]: score += 6
    if user["cgpa"]: score += 6

    # Professional portfolio (40 pts)
    if user["profile_photo"]: score += 10
    if user["headline"]: score += 10
    if user["about"]: score += 10
    if skills_count > 0: score += 5
    if projects_count > 0: score += 5

    return min(100, score)
