# DiplomaConnect — Professional Networking & Career Platform for Diploma Students

DiplomaConnect is a full-stack web application tailored specifically for Diploma and Polytechnic engineering students. It unites student community networking, academic portfolio building, institution directories, career opportunities, event tracking, and rule-based AI guidance into a clean, modern SaaS platform.

---

## 🌟 Key Features

### 1. Student Authentication & Profiles
- **Comprehensive Registration:** Name, email, phone, DOB, gender, address, enrollment number, admission year, course, branch, college, university, semester, CGPA, and total credits.
- **Secure Password Hashing:** Powered by Werkzeug security (`generate_password_hash` and `check_password_hash`).
- **Profile Photo Upload:** With instant image replacement, format validation (`png`, `jpg`, `jpeg`, `webp`, `gif`), and fallback initials avatars.
- **Dynamic Profile Completion Meter:** Calculated automatically based on completed personal, academic, and portfolio sections.
- **Engineering Portfolio:** Manage technical skills, capstone projects (with live & GitHub links), certifications, and achievements.

### 2. Professional Community Feed
- **Create Posts:** Categorized by General, Project Showcase, Achievement, Certification, and Career Advice.
- **Likes & Comments:** Real-time persistence with duplicate like prevention and notification triggers.
- **Content Moderation:** In-place post editing, deletion, and safety reporting.

### 3. Student Discovery & Networking
- **Multi-Filter Search:** Filter students by name, skills, polytechnic college, branch, and semester.
- **Connection Pipeline:** Send Request → Pending → Accept/Reject → Connected → Message.
- **Safety & Privacy:** Built-in user blocking and reporting tools. Blocked users cannot view interactions, send connection requests, or message each other.

### 4. Direct 1-on-1 Messaging
- **Real Message Threads:** Persistent SQLite chat history between mutually connected students.
- **Unread Indicators:** Badges in top navigation and inbox thread views.
- **Instant Unread Reset:** Automatically marks messages as read when opening conversation threads.

### 5. In-App Notifications Center
- Real-time database alerts for connection requests, connection acceptances, post likes, comments, incoming messages, and application status updates.
- Filter, mark single as read, mark all as read, and delete notifications.

### 6. Bihar Polytechnic Directory
- Verified directory of state polytechnic institutions across Bihar (Patna, Barauni, Muzaffarpur, Bhagalpur, Siwan, Gaya, etc.).
- Search and filter by district and university affiliation (SBTE Bihar).
- College detail pages with direct links to enrolled students.

### 7. Opportunities & Applications
- Categorized listings: Internships, Entry-Level Jobs, NATS Apprenticeships, State Scholarships, Technical Training, and Competitions.
- Bookmark / Save listings for later review.
- Submit applications directly with resume statement notes.

### 8. Events & Technical Workshops
- Browse webinars, campus hackathons, CAD masterclasses, and JE preparation sessions.
- RSVP / Register toggle with live attendee counters and participant rosters.

### 9. AI Career Assistant
- Specialized offline career counselor tailored specifically for diploma students.
- Covers B.Tech Lateral Entry (BCECE LE / LEET), SSC JE & RRB JE exam strategies, CSE/IT roadmap, Mechanical CAD/CNC, Civil site engineering, and diploma fresher resumes.
- Operates resiliently with zero external API dependencies (optional API keys can be passed via environment variables without risk of crashes).

### 10. Administrator Panel & Moderation
- Platform metrics: Total students, colleges, opportunities, events, feed posts, and pending reports.
- User management: Search users, toggle account status (Active / Banned), toggle admin roles.
- College directory CRUD.
- Opportunity & Event management with applicant and attendee reviewers.
- Content safety moderation: Resolve reports, delete flagged posts, or suspend malicious accounts.

---

## 🛠️ Technology Stack

- **Backend:** Python 3, Flask 3.x, Werkzeug
- **Database:** SQLite3 with relational foreign keys and parameterized queries
- **Frontend:** HTML5, CSS3 (Custom Navy / Deep Blue / Indigo SaaS theme), JavaScript (ES6)
- **UI Framework:** Bootstrap 5.3 & Bootstrap Icons 1.11

---

## 📁 Project Structure

```
diploma-connect/
│
├── app.py                      # Flask routes, authentication, controllers, filters
├── database.py                 # SQLite schema initialization, safe migrations, seed data
├── database.db                 # SQLite database (Preserved user data)
├── requirements.txt            # Python dependencies
├── README.md                   # Documentation and deployment guide
│
├── templates/                  # Jinja2 HTML templates
│   ├── base.html               # Main responsive layout (navbar, sidebar, badges)
│   ├── index.html              # Dashboard with profile score, create post, live feed
│   ├── login.html              # Login page with validation and flash errors
│   ├── register.html           # Full diploma student registration form
│   ├── profile.html            # Profile page with skills, projects, certs, photo upload
│   ├── edit_profile.html       # Full profile edit form (personal + academic info)
│   ├── students.html           # Student discovery with multi-field search & filters
│   ├── student_profile.html    # Public profile view with Connect/Message/Report actions
│   ├── connections.html        # My Network: Connections, Incoming, Sent requests
│   ├── messages.html           # Conversations list with unread counters
│   ├── conversation.html       # Direct 1-on-1 chat interface
│   ├── notifications.html      # Notifications feed with read/delete actions
│   ├── colleges.html           # Polytechnic directory with district filter
│   ├── college_detail.html     # College profile with enrolled student list
│   ├── opportunities.html      # Opportunities with category filters & saved tab
│   ├── opportunity_detail.html # Opportunity detail with application modal
│   ├── events.html             # Events listing with mode/type filters
│   ├── event_detail.html       # Event detail with RSVP and attendee roster
│   ├── ai_assistant.html       # AI Career Assistant with offline knowledge engine
│   ├── admin.html              # Admin dashboard overview & statistics
│   ├── admin_users.html        # Admin user management (status, role, delete)
│   ├── admin_colleges.html     # Admin college CRUD
│   ├── admin_opportunities.html# Admin opportunity CRUD & applicant reviewer
│   ├── admin_opportunity_applicants.html # Opportunity applicants roster
│   ├── admin_events.html       # Admin event CRUD
│   └── admin_reports.html      # Content moderation for user/post reports
│
└── static/
    ├── css/
    │   ├── style.css           # Navy/Deep Blue/Indigo SaaS theme & responsive rules
    │   └── auth.css            # Auth pages layout
    ├── js/
    │   └── script.js           # Client-side validation, mobile drawer, photo submit
    ├── images/                 # Logo / assets
    └── uploads/                # User profile photos (profile_1.jpeg preserved)
```

---

## 🚀 How to Run Locally

### 1. Prerequisites
Ensure Python 3.8+ is installed on your system.

### 2. Clone / Open the Folder
```bash
cd diploma-connect
```

### 3. Create & Activate Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Run the Application
```bash
python app.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 🔑 Default Administrator Credentials

For administration and platform moderation testing, a default administrator account is seeded:

- **Email:** `admin@diplomaconnect.com`
- **Password:** `Admin@123`

---

## ⚙️ Environment Variables (Optional)

You can configure environment variables in a `.env` file or export them directly in your production shell:

| Variable | Description | Default |
| :--- | :--- | :--- |
| `SECRET_KEY` | Flask session encryption key | `diplomaconnect_secret_key_2026` |
| `PORT` | Web server listening port | `5000` |

---

## 🌐 Production Deployment

DiplomaConnect is deployment-ready for standard Python hosting services (Render, PythonAnywhere, Railway, Heroku, AWS EC2):

1. **WSGI Entry Point:** `app:app`
2. **Production Server:**
   ```bash
   pip install gunicorn
   gunicorn app:app --bind 0.0.0.0:$PORT
   ```
3. **Database:** SQLite is file-backed (`database.db`). Ensure persistent disk storage is enabled if hosting on containerized platforms like Render or Fly.io.

---

## ✏️ Student Modification Guide

If you want to edit parts of the application yourself:
- **Navbar & Navigation:** `templates/base.html`
- **Dashboard & Feed:** `templates/index.html`
- **Profile & Portfolio:** `templates/profile.html` and `templates/edit_profile.html`
- **Student Discovery:** `templates/students.html` and `templates/student_profile.html`
- **Direct Messaging:** `templates/messages.html` and `templates/conversation.html`
- **Colleges & Institutions:** `templates/colleges.html` and `templates/college_detail.html`
- **Opportunities & Jobs:** `templates/opportunities.html` and `templates/opportunity_detail.html`
- **Events & Webinars:** `templates/events.html` and `templates/event_detail.html`
- **AI Career Assistant:** `templates/ai_assistant.html` and rule engine in `app.py`
- **Admin Management:** `templates/admin*.html`
- **Main Styling & Palette:** `static/css/style.css`
- **Client JavaScript:** `static/js/script.js`
- **Backend Routes & Business Logic:** `app.py`
- **Database Schema & Tables:** `database.py` and `database.db`
- **Uploaded Photos:** `static/uploads/`
