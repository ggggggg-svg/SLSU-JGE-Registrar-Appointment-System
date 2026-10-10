import calendar
import os
import re
import uuid
from datetime import datetime, date, timedelta

from flask import (Flask, render_template_string, request, session, redirect,
                   flash, jsonify)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'slsu-jge-tagkawayan-2026-change-me')
app.permanent_session_lifetime = timedelta(days=14)
app.config['MAX_CONTENT_LENGTH'] = 3 * 1024 * 1024      # profile photo upload limit (3 MB)

# ========== CONFIG ==========
LOGO_URL = "/static/JGE_LOGO.png"          # put your logo at static/JGE.jpg
BACKGROUND_URL = "/static/Office.jpg" # login page background photo: static/Office.jpg
BANNER_URL = "/static/bannerjge.png"  # rectangular photo on the home page (falls back to Office.jpg)
ABOUT_BANNER_URL = "/static/Fronts.jpg" # rectangular photo on top of About Us (falls back to Banner.jpg, then Office.jpg)
AVATAR_DIR = os.path.join(app.static_folder, 'avatars')   # uploaded profile pictures
os.makedirs(AVATAR_DIR, exist_ok=True)
FLASH_MS = 2500                        # notifications disappear after this many milliseconds
ADMIN_EMAIL = 'admin@slsu.edu.ph'
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')   # change in production
SLOT_CAPACITY = 50                      # max bookings per date + time slot
COURSES = [
    "BS Industrial Technology major in Computer Technology",
    "BS Industrial Technology major in Food and Beverages Technology",
    "Bachelor of Industrial Technology (BINDTECH)",
    "BS Business Administration major in Marketing Management",
    "BS Business Administration major in Financial Management",
    "Bachelor of Science in Public Administration",
    "Bachelor of Elementary Education",
    "Bachelor of Secondary Education major in English",
    "Bachelor of Secondary Education major in Mathematics",
    "Bachelor of Secondary Education major in Science",
    "Bachelor of Secondary Education major in Filipino",
    "Bachelor of Science in Fisheries and Aquatic Science",
]
YEARS = ["1st Year", "2nd Year", "3rd Year", "4th Year", "5th Year", "Graduated / Alumni"]
PAYMENTS = ["SLSU JGE Campus Cashier"]
LHS = "Laboratory High School"           # students of the campus Laboratory High School can also use the portal
GRADES = ["Grade 7", "Grade 8", "Grade 9", "Grade 10", "Grade 11", "Grade 12"]
# Documents & services, grouped. The booking dropdown uses the same list.
SERVICES = {
    "Academic Records": ["Transcript of Records (TOR)", "Diploma / Graduation Certificate",
                         "Summary of Grades", "True Copy of Grades",
                         "Certificate of Academic Standing"],
    "Transfer & Clearance": ["Honorable Dismissal / Transfer Credentials", "Cross-Enrollment Permit",
                             "Subject Equivalency & Credit", "Graduation Clearance", "Graduation Eligibility", "Medium of Instruction", "Good Moral Character Certificate"],
    "Verification & Authentication": ["Certification, Authentication & Verification (CAV)",
                                      "Notarization of Documents", "Certified True Copy of COR", "Duplicate / Replacement Diploma & TOR"],
    "Administrative": ["Correction of Name / Records", "Change of Matriculation",
                       "Leave of Absence", "Curriculum / Program of Study"],
}
DOCS = [d for items in SERVICES.values() for d in items]
TIMES = ["09:00 AM – 10:00 AM", "10:00 AM – 11:00 AM", "11:00 AM – 12:00 NN",
         "01:00 PM – 02:00 PM", "02:00 PM – 03:00 PM"]
# Requirements reminder shown when booking (and in Help). Strings = one item; dict = item with sub-items.
REQUIREMENTS = [
    "Valid school ID / Government ID",
    "Request Form (get from Registrar's Office or school website)",
    "Processing fee",
    dict(title="Clearance:", sub=[
        "Library clearance",
        "Department/Campus clearance",
        "Finance/Accounting clearance (no unpaid balances)",
        "ID/library card return (if graduating/transferring)"]),
    "1×1 or 2×2 ID photos (as required)",
]
# IMPORTANT requirements per document (shown highlighted when a student picks that document).
# DRAFT: please edit to match the Registrar's Office official requirements. A document without an entry
# only shows the general list above.
DOC_REQUIREMENTS = {
    "Transcript of Records (TOR)": [
        "Fully signed clearance (library, department/campus, finance/accounting)",
        "Official receipt of the processing fee",
        "Purpose of the request (employment, transfer, board exam, etc.) - write it in the comments"],
    "Diploma / Graduation Certificate": [
        "Fully signed graduation clearance",
        "ID and library card returned",
        "Official receipt of the diploma fee"],
    "Summary of Grades": [
        "Valid school ID (you can only request your own record)",
        "Official receipt of the processing fee"],
    "True Copy of Grades": [
        "Valid school ID",
        "Official receipt of the processing fee",
        "Semester / school year needed - write it in the comments"],
    "Certificate of Academic Standing": [
        "Valid school ID",
        "Purpose of the request - write it in the comments"],
    "Honorable Dismissal / Transfer Credentials": [
        "Fully signed clearance with no unpaid balance",
        "Letter or proof of acceptance from the school you are transferring to",
        "ID and library card returned"],
    "Cross-Enrollment Permit": [
        "Approval letter from your Dean / Department head",
        "Name of the host school and the subjects to cross-enroll",
        "Official receipt of the fee"],
    "Subject Equivalency & Credit": [
        "Copy of your grades / TOR from your previous school",
        "Subject descriptions or syllabi (as required)",
        "Approval of your Department head"],
    "Graduation Clearance": [
        "Clearance form signed by the Library, Department/Campus and Finance/Accounting",
        "No unpaid balance and no unreturned items"],
    "Graduation Eligibility": [
        "Academic requirements completed and checked by your Department",
        "Valid school ID"],
    "Medium of Instruction": [
        "Valid school ID",
        "Purpose of the request (abroad, scholarship, etc.) - write it in the comments"],
    "Good Moral Character Certificate": [
        "Valid school ID",
        "Clearance from the Student Affairs / Discipline office (if required)",
        "Purpose of the request - write it in the comments"],
    "Certification, Authentication & Verification (CAV)": [
        "Certified True Copy (CTC) signed by the University Registrar or authorized signatory",
        "Clear PDF scan of each CTC document (for the CHED eCAV portal)",
        "Official receipt of the CAV fee"],
    "Notarization of Documents": [
        "Original document and the photocopies to be notarized",
        "Valid government ID"],
    "Certified True Copy of COR": [
        "Valid school ID",
        "Semester / school year of the COR - write it in the comments",
        "Official receipt of the fee"],
    "Duplicate / Replacement Diploma & TOR": [
        "Notarized affidavit of loss",
        "Valid government ID",
        "Official receipt of the replacement fee"],
    "Correction of Name / Records": [
        "PSA birth certificate (or marriage certificate for a change of surname)",
        "Valid government ID",
        "Supporting documents that show the correct entry"],
    "Change of Matriculation": [
        "Approval from your Dean / Department head",
        "Copy of your current Certificate of Registration (COR)"],
    "Leave of Absence": [
        "Approved leave of absence form / letter signed by your Dean",
        "Clearance from the Finance/Accounting office"],
    "Curriculum / Program of Study": [
        "Valid school ID",
        "Program and curriculum year - write them in the comments"],
}
# Attendance policy: a Pending appointment whose date has passed becomes "Missed" (removed from active lists).
MISS_LIMIT = 3                 # missed appointments before the account is restricted
RESTRICT_MONTHS = 3            # how long booking is locked
MIN_AGE_COLLEGE, MIN_AGE_LHS = 16, 11
CONTACT_EMAIL = "registrar.jge@slsu.edu.ph"      # registrar email, e.g. "registrar.jge@slsu.edu.ph"  (fill in)
CONTACT_FACEBOOK = "https://www.facebook.com/registrar.slsujge"   # full link of the registrar Facebook page, e.g. "https://www.facebook.com/registrar.slsujge"  (fill in)
CONTACT_ADDRESS = "Brgy. Rizal, Tagkawayan, Quezon"
CONTACT_PHONE = "09123456789"      # optional
OFFICE_DAYS = "Monday to Friday, 9:00 AM – 3:00 PM (closed 12:00 – 1:00 PM). Closed on weekends and holidays."

# Home page: Office of the University Registrar
UNIV = dict(
    intro=("The Office of the University Registrar is a service unit under the Office of the Vice President "
           "for Academic Affairs with the following functions:"),
    functions=[
        "Provides services in the following areas: admission, enrolment, load requirements, scholarships, course "
        "adjustments (withdrawal, dropping, changing/adding of courses, overload, substitution), shifting, cross "
        "enrolment, transfer, records evaluation and graduation in accordance with policies of the university and "
        "the Commission on Higher Education (CHED)",
        "Manages the registration of students and processes applications for scholarships/discounts/grants in close "
        "coordination with the various colleges, Accounting Office and the Information Communication Technology "
        "Department.",
        "Assists the academic departments in the approval of new programs and revision of curricula.",
        "Liaises with various government agencies such as the Commission on Higher Education (CHED), Department of "
        "Education, Department of Foreign Affairs, Bureau of Immigration, Professional Regulation Commission, Civil "
        "Service Commission.",
        "Serves as custodian of academic records and is responsible for the proper maintenance, preparation and "
        "disposition of such records, ensuring integrity, accuracy and confidentiality.",
    ],
    docs=[
        "Adding of Subjects",
        "Application for Cross Enrolment",
        "Application for Overload",
        "Application for Substitution of Subjects",
        "Application for Scholarship/Grant",
        "Application for Sibling Discount",
        dict(title="Certification for the following:", sub=[
            "Candidacy for Graduation", "Course Description", "Eligibility to Take Up Law (CEL)", "Enrolment",
            "Grade Point Average (GPA)", "Graduation", "Scholarship",
            "Units Earned, English as Medium of Instruction"]),
        "Certified True Copy of Diploma (requesting party should present the original copy)",
        "Certified True Copy of Form 137/Form 138",
        "Correction or Change of Name/Date of Place of Birth",
        "Correction of Grade",
        "Changing of Subject (for dissolved classes only)",
        "Completion of Subject",
        "Diploma",
        "Dropping of Subjects",
        dict(title="Government Electronics Certification, Authentication and Verification (E-CAV) of Diploma and/or "
                   "Transcript of Records",
             steps=[
                 "The applicant will submit a request for Certified True Copy (CTC) of the required academic "
                 "documents from window 11 (e.g., Transcript of Records, Diploma, Certificate of Graduation, RLE, "
                 "etc., as applicable). Note: Ensure that the Certified True Copy is signed by the current "
                 "University Registrar or the authorized signatory.",
                 "The applicant will scan the Certified True Copy documents in clear PDF format.",
                 "The applicant will create an account through the CHED eCAV Portal.",
                 "Complete the online eCAV application, upload the required PDF documents, and submit the "
                 "application and follow additional procedures required by CHED from the ECAV portal.  "
                 "CHED eCAV | Electronic Certification, Authentication, and Verification",
             ]),
        "Request for Late Encoding of Grades",
        "Shifting of Course/Program",
        "Transcript of Records",
        "Transfer Credential/Honorable Dismissal",
        "True Copy of Grades",
        "Withdrawal of Enrollment",
    ],
)

# About Us content - DRAFT text, please replace with the office's official statements.
ABOUT = dict(
    mission=("To provide accurate, secure and timely management of student academic records, and to deliver "
             "courteous, efficient and transparent registrar services to students, alumni and the university community."),
    vision=("A trusted, technology-driven Office of the Registrar that sets the standard for dependable records "
            "management and student-centered service at SLSU – JGE Tagkawayan Campus."),
    goals=["Safeguard the integrity, confidentiality and accuracy of official student records.",
           "Process document requests quickly and transparently, with minimal waiting time.",
           "Offer accessible online services such as appointment scheduling and request tracking.",
           "Comply with university policies and the Data Privacy Act of 2012 (RA 10173).",
           "Keep improving registrar services through student feedback."],
    history=["Southern Luzon State University – JGE Tagkawayan Campus is one of the campuses of Southern Luzon "
             "State University in the province of Quezon. As the campus grew, so did the need for one office to keep "
             "and issue official academic records, from enrollment and grades to transcripts and diplomas. That office "
             "is the Office of the Registrar.",
             "To make requesting documents more orderly, the SLSU-JGE Tagkawayan ICT Student Government developed this "
             "online appointment system. Students can now choose a schedule, state their request and track its status "
             "from a phone or computer, while registrar staff see who is coming, when and for what."],
)
# ============================

# In-memory databases (reset on restart)
pending_accounts, approved_users, appointments_db = {}, {}, {}
rejected_accounts = set()
feedback_db = []


# ========== HELPERS ==========
def calculate_age(s):
    try:
        b = datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return 0
    t = date.today()
    return t.year - b.year - ((t.month, t.day) < (b.month, b.day))


def is_password_valid(pw):
    if len(pw) < 8:
        return False, "Password must be at least 8 characters"
    if not re.search(r'[A-Z]', pw):
        return False, "Must include at least one UPPERCASE letter (A-Z)"
    if not re.search(r'[0-9]', pw):
        return False, "Must include at least one number (0-9)"
    if not re.search(r'[^A-Za-z0-9]', pw):
        return False, "Must include at least one special symbol (!@#$%^&* etc.)"
    return True, "OK"


def is_gmail_valid(e):
    return bool(re.fullmatch(r'[a-z0-9._%+\-]+@gmail\.com', e.lower()))


def find_user(key):
    """Accept the Gmail address or the Student ID."""
    if key in approved_users:
        return key
    for e, u in approved_users.items():
        if u['studentid'].strip().lower() == key:
            return e
    return None


def compose_name(ln, fn, mn):
    """'Last, First Middle' (middle omitted when N/A)."""
    mn = (mn or '').strip()
    return f"{ln}, {fn}" if mn.upper() in ('', 'N/A') else f"{ln}, {fn} {mn}"


def split_name(full):
    """Best-effort split of 'Last, First M.' (fallback for records without separate name fields)."""
    full = (full or '').strip()
    ln = fn = mn = ''
    if ',' in full:
        ln, rest = [x.strip() for x in full.split(',', 1)]
        parts = rest.split()
        if len(parts) >= 2 and len(parts[-1].strip('.')) <= 2:
            mn, fn = parts[-1], ' '.join(parts[:-1])
        else:
            fn = rest
    else:
        parts = full.split()
        if len(parts) >= 2:
            ln, fn = parts[-1], ' '.join(parts[:-1])
        else:
            fn = full
    return dict(ln=ln, fn=fn, mn=mn)


def name_parts(u):
    if u.get('ln') or u.get('fn'):
        return dict(ln=u.get('ln', ''), fn=u.get('fn', ''), mn=u.get('mn', ''))
    return split_name(u.get('fullname', ''))


def greeting_name(u):
    """'Mr. Santos' / 'Ms. Santos' (last name only). No title if gender is not given."""
    ln = name_parts(u)['ln'] or u.get('fullname', '')
    title = {'Male': 'Mr.', 'Female': 'Ms.'}.get(u.get('gender'), '')
    return f"{title} {ln}".strip()


def slot_key(a):
    return (a['sched_date'], TIMES.index(a['sched_time']) if a['sched_time'] in TIMES else 0)


def add_months(d, n):
    y, m = d.year + (d.month - 1 + n) // 12, (d.month - 1 + n) % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def fmt_date(iso):
    try:
        return datetime.strptime(iso, '%Y-%m-%d').strftime('%b %d, %Y')
    except ValueError:
        return ''


def is_restricted(u):
    return (u or {}).get('restricted_until', '') > date.today().isoformat()


def sweep_missed():
    """Pending appointments whose day has passed become Missed; MISS_LIMIT misses lock booking."""
    today = date.today()
    for email, lst in appointments_db.items():
        for a in lst:
            if a['status'] == 'Pending' and not a.get('exempt') and a['sched_date'] < today.isoformat():
                a.update(status='Missed', missed_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'), counted=True)
                u = approved_users.get(email)
                if u is not None:
                    u['strikes'] = u.get('strikes', 0) + 1
                    if u['strikes'] >= MISS_LIMIT:
                        u['restricted_until'] = add_months(today, RESTRICT_MONTHS).isoformat()
                        u['strikes'] = 0


def refund_strike(a):
    if a.get('counted'):
        a['counted'] = False
        u = approved_users.get(a.get('email'))
        if u and u.get('strikes', 0) > 0:
            u['strikes'] -= 1


def group_cy(items):
    """Group records by program, then year level (college) or grade level + section (Laboratory HS)
    -> [(program, count, [(label, [rows])])]."""
    NS = 'Not specified'
    known = COURSES + [LHS]
    out = []
    names = [c for c in known if any(i.get('course') == c for i in items)]
    if any(i.get('course') not in known for i in items):
        names.append(NS)
    for c in names:
        pool = [i for i in items if i.get('course') == c or (c == NS and i.get('course') not in known)]
        sub = []
        if c == LHS:
            for gname in GRADES + [NS]:
                in_g = [i for i in pool if i.get('year_level') == gname or (gname == NS and i.get('year_level') not in GRADES)]
                secs = sorted({(i.get('section') or '').strip() for i in in_g}, key=lambda x: (x == '', x.lower()))
                for sec in secs:
                    rows = [i for i in in_g if (i.get('section') or '').strip() == sec]
                    sub.append((f"{gname} · Section {sec}" if sec else f"{gname} · No section", rows))
        else:
            for y in YEARS + [NS]:
                rows = [i for i in pool if i.get('year_level') == y or (y == NS and i.get('year_level') not in YEARS)]
                if rows:
                    sub.append((y, rows))
        out.append((c, len(pool), sub))
    return out


def detect_image(data):
    """Return an extension if the bytes look like a supported image, else None."""
    if data[:3] == b'\xff\xd8\xff':
        return 'jpg'
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return 'png'
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return 'webp'
    if data[:4] == b'GIF8':
        return 'gif'
    return None


def delete_avatar(url):
    if url and url.startswith('/static/avatars/'):
        try:
            os.remove(os.path.join(AVATAR_DIR, os.path.basename(url)))
        except OSError:
            pass


def render(tpl, **kw):
    return render_template_string(tpl, css=CSS, logo=LOGO_URL, bg=BACKGROUND_URL, banner=BANNER_URL,
                                  about_banner=ABOUT_BANNER_URL, about=ABOUT, univ=UNIV, cemail=CONTACT_EMAIL,
                                  cfb=CONTACT_FACEBOOK, caddr=CONTACT_ADDRESS, cdays=OFFICE_DAYS,
                                  cphone=CONTACT_PHONE, flash_ms=FLASH_MS, courses=COURSES, years=YEARS,
                                  payments=PAYMENTS, times=TIMES, docs=DOCS, services=SERVICES, grades=GRADES, lhs=LHS,
                                  reqs=REQUIREMENTS, doc_reqs=DOC_REQUIREMENTS, **kw)


# ========== SHARED CSS (deep green theme, light + dark) ==========
CSS = """
*{margin:0;padding:0;box-sizing:border-box}
html{scroll-behavior:smooth}
:root{--pri:#003d1f;--dark:#00240f;--hover:#005a2d;--acc:#003d1f;--soft:#e3f0e8;--bg:#f3f6f4;--card:#fff;--inp:#fff;
 --tx:#1b2620;--mut:#5d6a62;--bd:#e1e7e3;--row:#f6faf7;--gold:#c9a227;--warn:#fff4d6;--warnt:#7a5a00;
 --sh:0 1px 2px rgba(0,36,15,.06),0 8px 24px rgba(0,36,15,.07)}
[data-theme=dark]{--pri:#1d7647;--dark:#050f09;--hover:#26905a;--acc:#62d696;--soft:#1a3226;--bg:#0b120e;--card:#131c16;--inp:#0e1711;
 --tx:#e4ede7;--mut:#9aaca1;--bd:#243329;--row:#18241c;--warn:#3a2f0b;--warnt:#f1d37a;
 --sh:0 1px 2px rgba(0,0,0,.4),0 8px 24px rgba(0,0,0,.35);color-scheme:dark}
body{font-family:'Inter','Segoe UI',system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--tx);
 line-height:1.5;-webkit-font-smoothing:antialiased;transition:background .25s,color .25s}
button,input,select,textarea{font-family:inherit}
.bgblur{position:fixed;inset:-30px;z-index:-1;pointer-events:none;background-position:center;background-repeat:no-repeat;
 background-size:cover;filter:blur(8px);opacity:.22}
[data-theme=dark] .bgblur{opacity:.07}
.logo-circle{position:relative;border-radius:50%;background:transparent;display:flex;align-items:center;
 justify-content:center;overflow:visible;color:transparent;font-weight:700;flex:none}
.logo-circle img{position:absolute;inset:0;width:100%;height:100%;object-fit:contain}
label{display:block;margin-bottom:.4rem;font-weight:600;font-size:.84rem;color:var(--tx)}
input,select,textarea{width:100%;padding:.72rem .9rem;border:1px solid var(--bd);background:var(--inp);color:var(--tx);border-radius:9px;font-size:.93rem;transition:border-color .15s,box-shadow .15s}
textarea{resize:vertical}
input[readonly]{opacity:.7;cursor:not-allowed}
input:focus,select:focus,textarea:focus{outline:none;border-color:var(--pri);box-shadow:0 0 0 3px rgba(31,122,71,.25)}
.form-group{margin-bottom:1.1rem}
.btn{border:none;padding:.8rem 1.3rem;border-radius:9px;font-size:.93rem;font-weight:600;cursor:pointer;
 background:var(--pri);color:#fff;text-decoration:none;display:inline-block;transition:.18s;text-align:center;letter-spacing:.1px}
.btn:hover{background:var(--hover);transform:translateY(-1px);box-shadow:0 4px 12px rgba(0,61,31,.25)}
.btn-full{width:100%}
.btn-danger{background:#c62828}.btn-danger:hover{background:#a81f1f;box-shadow:0 4px 12px rgba(198,40,40,.3)}
.btn-sm{padding:.45rem .85rem;font-size:.8rem}
.btn-ghost{background:transparent;color:var(--acc);border:1px solid var(--acc)}.btn-ghost:hover{background:var(--soft);box-shadow:none}
.msg{padding:.85rem 1rem;border-radius:9px;margin-bottom:1rem;border-left:4px solid;transition:opacity .35s;font-size:.9rem}
.msg.error{background:#fff2f2;color:#a30000;border-color:#e53935}
.msg.ok{background:#eefaf1;color:#1b5e20;border-color:#43a047}
[data-theme=dark] .msg.error{background:#3a1717;color:#ffb4b4}
[data-theme=dark] .msg.ok{background:#14301f;color:#9be3b6}
.hint{font-size:.76rem;color:var(--mut);margin-top:.3rem;line-height:1.4}
.top-bar{background:var(--dark);color:#d6e6dc;padding:.45rem 2rem;font-size:.78rem;letter-spacing:.3px}
.header-main{padding:.8rem 2rem;border-bottom:1px solid var(--bd);display:flex;align-items:center;
 justify-content:space-between;flex-wrap:wrap;gap:.8rem 1.5rem;background:var(--card);position:sticky;top:0;z-index:100;
 box-shadow:0 1px 0 var(--bd),0 4px 14px rgba(0,36,15,.05)}
.logo-group{display:flex;align-items:center;gap:.8rem;min-width:0}
.logo-group .logo-circle{width:46px;height:46px;font-size:.7rem}
.logo-text h1{font-size:.98rem;color:var(--acc);letter-spacing:.3px;font-weight:700}.logo-text p{font-size:.76rem;color:var(--mut)}
.nav-menu{display:flex;gap:.25rem;list-style:none;flex-wrap:wrap}
.nav-menu a{text-decoration:none;color:var(--mut);font-weight:500;padding:.55rem .95rem;border-radius:8px;font-size:.88rem;display:block;transition:.15s}
.nav-menu a:hover,.nav-menu a.active{background:var(--soft);color:var(--acc)}
.user-area{display:flex;align-items:center;gap:.6rem}
.user-badge{background:var(--soft);color:var(--acc);padding:.45rem .95rem;border-radius:2rem;font-size:.83rem;font-weight:500;
 max-width:230px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.theme-btn{width:38px;height:38px;border-radius:50%;border:1px solid var(--bd);background:var(--card);color:var(--acc);cursor:pointer;font-size:.95rem;transition:.18s;flex:none}
.theme-btn:hover{background:var(--soft)}
.av{width:28px;height:28px;border-radius:50%;object-fit:cover;vertical-align:middle;margin-right:.3rem}
.av-lg{width:110px;height:110px;border-radius:50%;object-fit:cover;border:3px solid var(--soft);flex:none;display:block}
.av-ph{background:var(--soft);color:var(--acc);display:flex;align-items:center;justify-content:center;font-size:2.8rem}
.av-row{display:flex;align-items:center;gap:1.4rem;margin-bottom:1.4rem;flex-wrap:wrap}.av-row>div:last-child{flex:1;min-width:200px}
.avwrap{position:relative;width:110px;height:110px;flex:none}
.pen{position:absolute;right:0;bottom:0;width:34px;height:34px;border-radius:50%;border:3px solid var(--card);
 background:var(--pri);color:#fff;cursor:pointer;font-size:.75rem;display:flex;align-items:center;justify-content:center}
.pen:hover{background:var(--hover)}
.pop{display:none;position:absolute;left:0;top:118px;min-width:210px;background:var(--card);border:1px solid var(--bd);
 border-radius:10px;box-shadow:var(--sh);padding:.35rem;z-index:50}.pop.open{display:block}
.pop button{display:flex;gap:.6rem;align-items:center;width:100%;text-align:left;background:none;border:0;color:var(--tx);
 padding:.6rem .7rem;border-radius:6px;cursor:pointer;font-size:.88rem}.pop button:hover{background:var(--soft)}
.hid{display:none!important}
.page-container{max-width:1280px;margin:0 auto;padding:2rem}
.section,.tab-content{display:none;animation:fi .3s ease}
.section.active,.tab-content.active{display:block}
@keyframes fi{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
h2.t{color:var(--acc);margin-bottom:1.4rem;padding-bottom:.7rem;border-bottom:2px solid var(--soft);font-size:1.45rem;font-weight:700;position:relative}
h2.t::after{content:"";position:absolute;left:0;bottom:-2px;width:70px;height:2px;background:var(--gold)}
h3.sub{color:var(--acc);margin:1.8rem 0 .2rem;font-size:1.05rem}
.card{background:var(--card);border:1px solid var(--bd);border-radius:14px;box-shadow:var(--sh);padding:1.6rem;margin-bottom:1.4rem}
.banner{width:100%;aspect-ratio:3/1;border-radius:14px;overflow:hidden;margin-bottom:1.75rem;
 background:linear-gradient(135deg,var(--pri),var(--dark));box-shadow:var(--sh)}
.banner img{width:100%;height:100%;object-fit:cover;display:block}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:1.1rem;margin:1.4rem 0}
.stat{background:var(--card);border:1px solid var(--bd);border-radius:14px;padding:1.4rem;box-shadow:var(--sh);text-align:center;display:block;color:inherit;text-decoration:none;transition:.18s}
a.stat:hover{transform:translateY(-3px);border-color:var(--acc)}
.stat i{font-size:1.7rem;color:var(--acc);margin-bottom:.6rem;display:block}.stat h3{font-size:1.7rem;color:var(--acc);font-weight:700}
.stat p{font-size:.84rem;color:var(--mut);margin-top:.3rem}
.tw{overflow-x:auto}
.scroll{max-height:440px;overflow:auto;padding:0}
table{width:100%;border-collapse:collapse;background:var(--card)}
th,td{padding:.8rem .9rem;text-align:left;border-bottom:1px solid var(--bd);font-size:.87rem;white-space:nowrap}
th{background:var(--pri);color:#fff;font-size:.74rem;text-transform:uppercase;letter-spacing:.6px;font-weight:600;position:sticky;top:0;z-index:1}
tr:hover td{background:var(--row)}
td.wrap{white-space:normal;min-width:220px;max-width:340px}
.bdg{display:inline-block;padding:.2rem .7rem;border-radius:2rem;font-size:.74rem;font-weight:600;background:var(--soft);color:var(--acc)}
.bdg.done{background:var(--bd);color:var(--mut)}
.bdg.pend{background:var(--warn);color:var(--warnt)}
.pill{display:inline-block;min-width:1.7rem;text-align:center;padding:.1rem .55rem;border-radius:2rem;font-size:.74rem;font-weight:700;background:var(--acc);color:var(--card);margin-left:.4rem}
.empty{padding:2.5rem;text-align:center;color:var(--mut)}
.footer{background:var(--dark);color:#cfe0d5;padding:1.6rem 1rem;margin-top:2.5rem;text-align:center;font-size:.82rem;line-height:1.7;border-top:3px solid var(--gold)}
.footer strong{color:#fff}
body.sticky{display:flex;flex-direction:column;min-height:100vh}.sticky .page-container{flex:1;width:100%}
.more{position:relative}.mb{background:none;border:0;cursor:pointer;color:var(--mut);font-weight:500;font-size:.88rem;padding:.55rem .95rem;border-radius:8px}
.mb:hover,.mb.active{background:var(--soft);color:var(--acc)}
.dd{display:none;position:absolute;right:0;top:100%;min-width:200px;background:var(--card);border:1px solid var(--bd);border-radius:10px;box-shadow:var(--sh);padding:.4rem;list-style:none;z-index:200}.dd.open{display:block}
a.user-badge{text-decoration:none;cursor:pointer}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:0 1.25rem}.g3{display:grid;grid-template-columns:repeat(3,1fr);gap:0 1.25rem}
.ct{color:var(--acc);margin-bottom:.8rem;font-size:1.05rem}.prose p,.prose li{line-height:1.75;color:var(--mut)}.prose h4{margin:1rem 0 .3rem;color:var(--acc)}.prose ul{padding-left:1.2rem}
.prose ul.cl{padding:0;list-style:none}
.prose .cl li{display:flex;gap:1rem;padding:.9rem 0;border-bottom:1px solid var(--bd);color:var(--tx)}
.prose .cl li:last-child{border-bottom:0}
.cl i{color:var(--acc);width:1.4rem;font-size:1.1rem;margin-top:.2rem;text-align:center;flex:none}
.cl a{color:var(--acc);word-break:break-all}.soon{color:var(--mut);font-style:italic}
.fnlist li{margin-bottom:.55rem}
.dlist{columns:1}.dlist>li{margin-bottom:.35rem;break-inside:avoid}.dlist ul,.dlist ol{margin:.3rem 0 .5rem}
.note{background:var(--soft);border-left:4px solid var(--acc);border-radius:8px;padding:.8rem 1rem;margin:.5rem 0;color:var(--tx)}
.note li{color:var(--tx)}
.alert{display:flex;gap:.9rem;align-items:flex-start;background:var(--warn);color:var(--warnt);border:1px solid var(--gold);border-radius:12px;padding:1rem 1.2rem;margin-bottom:1.4rem;line-height:1.55}
.alert i{font-size:1.3rem;margin-top:.15rem}
details{border-bottom:1px solid var(--bd);padding:.8rem 0}summary{cursor:pointer;font-weight:600}details p{margin-top:.5rem;color:var(--mut);line-height:1.6}
details.pwd{border:1px solid var(--bd);padding:1rem 1.4rem}
details.pwd summary{font-weight:500;color:var(--mut);font-size:.92rem}
details.pwd[open] summary{margin-bottom:1rem}
details.cg{border:1px solid var(--bd);border-radius:12px;background:var(--card);margin-bottom:1rem;padding:0;box-shadow:var(--sh);overflow:hidden}
details.cg>summary{display:flex;justify-content:space-between;align-items:center;gap:1rem;padding:.9rem 1.2rem;background:var(--soft);color:var(--acc);font-weight:700;list-style:none}
details.cg>summary::-webkit-details-marker{display:none}
.yg{padding:.2rem 1.2rem 1rem}.yh{margin:1rem 0 .3rem;font-size:.88rem;color:var(--acc);text-transform:uppercase;letter-spacing:.7px}
.modal{display:none;position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:500;align-items:center;justify-content:center;padding:1rem}
.modal.open{display:flex}
.mbox{background:var(--card);border-radius:14px;padding:1.4rem;width:100%;max-width:360px;text-align:center;color:var(--tx);position:relative}
.mbox.wide{max-width:600px;text-align:left;max-height:90vh;overflow:auto}
.mbox .x{position:absolute;right:.8rem;top:.6rem;background:none;border:0;font-size:1.6rem;color:var(--mut);cursor:pointer}
.mbox canvas{width:100%;max-width:300px;aspect-ratio:1;border-radius:12px;touch-action:none;cursor:grab;background:#000;display:block;margin:0 auto 1rem}
.mbox input[type=range]{padding:0;border:0;box-shadow:none}
.mbtn{display:flex;gap:.6rem;justify-content:center;margin-top:1rem}
.pm-head{display:flex;gap:1.2rem;align-items:center;margin-bottom:1.2rem}.pm-head h3{color:var(--acc)}
.pm-grid{display:grid;grid-template-columns:140px 1fr;gap:.55rem 1rem;font-size:.9rem;margin-bottom:1rem}
.pm-grid dt{color:var(--mut);font-weight:600}.pm-grid dd{word-break:break-word}
.pm-ap{padding:.5rem 0;border-bottom:1px solid var(--bd);font-size:.86rem}.pm-ap:last-child{border:0}
.plink{color:var(--acc);font-weight:600;text-decoration:none}.plink:hover{text-decoration:underline}
.searchbar{position:relative;margin-bottom:1rem}
.searchbar .ic{position:absolute;left:1rem;top:.9rem;color:var(--mut)}
.searchbar input{padding-left:2.6rem}
.sw{display:flex;gap:.6rem;align-items:flex-start;cursor:pointer;font-size:.88rem;line-height:1.5;margin-top:.8rem}.sw input{width:auto;margin-top:.2rem}
.reqbox{background:var(--soft);border:1px solid var(--bd);border-left:4px solid var(--gold);border-radius:12px;padding:1rem 1.2rem;margin:0 0 1.2rem}
.rq-h{font-weight:700;color:var(--acc);margin-bottom:.6rem}
.rq-l ul,.rl{list-style:none;padding:0!important}.rq-l li,.rl li{padding:.22rem 0}.rq-l ul ul,.rl ul{padding-left:1.6rem!important;list-style:none}
.rq{display:flex;gap:.6rem;align-items:flex-start;font-size:.9rem;cursor:pointer}.rq input{width:auto;margin-top:.25rem}
.rq-t{font-weight:600;font-size:.9rem;margin-top:.3rem}
.stp{display:flex;gap:1rem;padding:1.1rem 0;border-bottom:1px solid var(--bd)}.stp:last-child{border:0}
.stp .n{width:36px;height:36px;border-radius:50%;background:var(--pri);color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;flex:none}
.stp h4{margin:0 0 .25rem!important}.stp p{margin-bottom:.3rem}
.chips{display:flex;gap:.5rem;flex-wrap:wrap;margin:.5rem 0}.chip{background:var(--soft);color:var(--acc);padding:.25rem .75rem;border-radius:2rem;font-size:.78rem;font-weight:600}
.rq-key{background:var(--warn);border:1px solid var(--gold);border-left:4px solid #e0a100;border-radius:10px;padding:.7rem 1rem;margin-bottom:.9rem}
.rq-kt{font-weight:700;color:var(--warnt);margin-bottom:.35rem}.rq-key li{padding:.2rem 0}.rq-key ul{list-style:none;padding:0!important}
.alert.danger{background:#fdecea;color:#8a1c1c;border-color:#c62828}
[data-theme=dark] .alert.danger{background:#3a1717;color:#ffb4b4}
.bdg.bad{background:#fdecea;color:#b3261e}[data-theme=dark] .bdg.bad{background:#3a1717;color:#ffb4b4}
@media(max-width:700px){.g2,.g3{grid-template-columns:1fr}.pm-grid{grid-template-columns:1fr}.pm-grid dd{margin-bottom:.4rem}}
@media(min-width:900px){.dlist{columns:2;column-gap:2.5rem}}
@media(max-width:768px){
 .top-bar{padding:.5rem 1rem;font-size:.72rem}
 .header-main{padding:.8rem 1rem}
 .header-main nav{order:3;width:100%}
 .nav-menu{justify-content:center;gap:.2rem}.nav-menu a,.mb{padding:.5rem .7rem;font-size:.85rem}
 .user-badge{max-width:140px}
 .page-container{padding:1rem}
 .card{padding:1.1rem}
 .banner{aspect-ratio:16/9}
 .tw.card{background:none;box-shadow:none;border:0;padding:0;overflow:visible}
 .scroll{max-height:none;overflow:visible}
 table.rt,table.rt tbody,table.rt tr,table.rt td{display:block;width:100%}
 table.rt{background:none;margin-top:0}
 table.rt tr.hr{display:none}
 table.rt tr{border:1px solid var(--bd);border-radius:10px;margin-bottom:.8rem;padding:.4rem .9rem;background:var(--card)}
 table.rt td{display:flex;justify-content:space-between;gap:1rem;white-space:normal;text-align:right;border:0;padding:.45rem 0;min-width:0;max-width:none}
 table.rt td::before{content:attr(data-label);font-weight:600;color:var(--mut);text-align:left;flex:none}
}

/* ========== MOBILE RESPONSIVE STYLES (phones / cellphone browsers) ========== */
html{-webkit-text-size-adjust:100%}
img,svg,canvas,video{max-width:100%}
@media only screen and (max-width:768px){
  html,body{overflow-x:hidden}
  body{padding:0}

  /* Header - stack items vertically */
  .header-main{flex-direction:column;align-items:center;text-align:center;padding:12px;gap:10px;position:static}
  .logo-group{justify-content:center}
  .header-main nav{width:100%;margin-top:4px}
  .user-area{justify-content:center;flex-wrap:wrap}
  .user-badge{max-width:100%}

  /* Navigation - make links wrap nicely, easy to tap */
  .nav-menu{flex-wrap:wrap;justify-content:center;gap:6px}
  .nav-menu a,.mb{font-size:14px;padding:8px 12px;min-height:40px;display:flex;align-items:center;justify-content:center}
  .dd{position:fixed;left:12px;right:12px;min-width:0;margin-top:6px;max-height:60vh;overflow:auto}

  /* Main content - better spacing on small screens */
  .page-container{padding:15px;max-width:100%}
  .content{padding:12px}

  /* Headings - adjust size */
  .lh h1{font-size:20px}
  h2.t{font-size:18px;margin-bottom:1rem}
  .ct,h3.sub,.pn>h3{font-size:16px}

  /* Cards - full width on mobile */
  .card,.pn{width:100%;margin:10px 0;padding:14px}
  .grid{grid-template-columns:1fr}
  .banner{aspect-ratio:auto}
  .banner img{height:auto;object-fit:contain}

  /* Forms - 16px stops iPhone from zooming in, bigger tap targets */
  input,select,textarea{font-size:16px;padding:.8rem .9rem}
  input[type=checkbox],input[type=radio]{width:auto;min-height:0}

  /* Buttons - easier to tap (small table/icon buttons keep their size) */
  form .btn:not(.btn-sm),.btn-full,.btn-danger.btn-full{width:100%;padding:12px;font-size:16px}
  .btn-sm{min-height:38px;padding:.5rem .9rem}
  table.rt td[data-label="Action"]{flex-wrap:wrap;justify-content:flex-end;gap:.5rem}
  table.rt td .nm{justify-content:flex-end}

  /* Grouped lists, dialogs, footer */
  details.cg>summary{padding:.8rem;font-size:.9rem}
  .yg{padding:.2rem .8rem 1rem}
  .modal{padding:.5rem}
  .mbox,.mbox.wide{max-width:100%;padding:1.1rem}
  .mbox.wide{max-height:92vh}
  .footer{padding:1.2rem 1rem calc(1.2rem + env(safe-area-inset-bottom));font-size:.78rem}

  /* Admin dashboard */
  .tb{gap:.6rem}
  .gs{max-width:none;min-width:0}
  .tiles{gap:.7rem}.tile b{font-size:1.35rem}
  .filtbar{gap:.5rem}.sbx{min-width:0;flex-basis:100%}
  .filtbar select{width:100%;max-width:none;min-width:0}
  .act .when{display:none}
}
@media only screen and (max-width:768px){
  .nav-menu{flex-wrap:nowrap;justify-content:flex-start;overflow-x:auto;-webkit-overflow-scrolling:touch;
    scrollbar-width:none;padding:2px 2px 6px}
  .nav-menu::-webkit-scrollbar{display:none}
  .nav-menu>li{flex:none}.nav-menu a,.mb{white-space:nowrap;border-radius:2rem;background:var(--soft);color:var(--acc)}
  .nav-menu a.active,.mb.active{background:var(--pri);color:#fff}
  .header-main nav{margin-top:0}
}
"""

HEAD_LINKS = ('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">'
              '<link rel="preconnect" href="https://fonts.googleapis.com">'
              '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">')
FA = HEAD_LINKS
THEME_INIT = ("<script>(function(){var t=null;try{t=localStorage.getItem('slsu-theme')}catch(e){}"
              "if(!t&&window.matchMedia&&matchMedia('(prefers-color-scheme: dark)').matches)t='dark';"
              "document.documentElement.setAttribute('data-theme',t||'light')})();</script>")
THEME_JS = ("(function(){const b=document.getElementById('themeBtn');if(!b)return;const r=document.documentElement;"
            "function paint(){const d=r.dataset.theme==='dark';b.innerHTML=d?'<i class=\"fas fa-sun\"></i>':'<i class=\"fas fa-moon\"></i>';"
            "b.title=d?'Switch to light mode':'Switch to dark mode'}"
            "b.addEventListener('click',()=>{const n=r.dataset.theme==='dark'?'light':'dark';r.dataset.theme=n;"
            "try{localStorage.setItem('slsu-theme',n)}catch(e){}paint()});paint()})();")
THEME_BTN = '<button type="button" class="theme-btn" id="themeBtn" aria-label="Toggle dark mode"></button>'
LOGO_HTML = ('<div class="logo-circle"><span>SLSU</span><img src="{{ logo }}" alt="" '
             'onerror="this.remove()"></div>')
BLUR_BG = '<div class="bgblur" style="background-image:url(\'{{ logo }}\')"></div>'
FOOTER = ('<footer class="footer"><strong>Office of the Registrar</strong> · Southern Luzon State University — JGE Tagkawayan Campus<br>'
          '© 2026 Southern Luzon State University. All rights reserved. Proudly powered by '
          '<strong>SLSU-JGE Tagkawayan ICT Student Government</strong></footer>')
# Notifications: auto-remove after flash_ms, or on click.
FLASH_JS = ("document.querySelectorAll('.msg').forEach(m=>{m.style.cursor='pointer';m.title='Click to dismiss';"
            "const rm=()=>{m.style.opacity=0;setTimeout(()=>m.remove(),350)};m.addEventListener('click',rm);"
            "setTimeout(rm,{{ flash_ms }})});")

# ========== LOGIN / REGISTER ==========
# Light frosted card with a gold top edge, over the tinted office photo.
LOGIN_TPL = """<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<meta name="theme-color" content="#00240f">
<title>SLSU JGE - Office of the Registrar</title>""" + FA + """
<style>{{ css|safe }}
html{min-height:100%;background:#00240f}
body{background:transparent;min-height:100vh;min-height:100dvh;display:flex;align-items:center;justify-content:center;
 padding:1.25rem 1rem calc(1.25rem + env(safe-area-inset-bottom))}
body::before{content:"";position:fixed;inset:0;z-index:-2;background:url('{{ bg }}') center/cover no-repeat}
body::after{content:"";position:fixed;inset:0;z-index:-1;background:linear-gradient(rgba(0,61,31,.45),rgba(0,36,15,.7))}

/* ---- light frosted card with gold top edge ---- */
.lcard{position:relative;width:100%;max-width:460px;padding:2rem 2rem 1.4rem;color:#1b2620;border-radius:22px;
 background:rgba(255,255,255,.93);
 -webkit-backdrop-filter:blur(14px) saturate(130%);backdrop-filter:blur(14px) saturate(130%);
 border-top:5px solid #c9a227;
 box-shadow:0 18px 50px rgba(0,0,0,.35),0 2px 6px rgba(0,0,0,.15)}
.lh{text-align:center}
.lh .logo-circle{width:96px;height:96px;margin:0 auto 1rem;background:transparent;border:0;overflow:visible;
 filter:drop-shadow(0 4px 8px rgba(0,0,0,.3))}
.lh .logo-circle img{object-fit:contain}
.lh h1{font-size:1.3rem;font-weight:700;color:#003d1f;line-height:1.25}
.lh p{font-size:.88rem;color:#5d6a62;margin-top:.5rem}
.lform{margin-top:1.6rem}

/* ---- form controls ---- */
.lcard label{color:#1b2620;font-size:.86rem}
.lcard input,.lcard select{background:#fff;border:1px solid #dde3df;color:#1b2620;border-radius:12px;
 padding:.85rem 1rem;font-size:16px}
.lcard input::placeholder{color:#8a948e}
.lcard input:focus,.lcard select:focus{border-color:#003d1f;box-shadow:0 0 0 3px rgba(0,61,31,.18)}
.lcard .btn{background:#003d1f;color:#fff;border-radius:12px;padding:.9rem 1.2rem;font-size:1rem;box-shadow:none}
.lcard .btn:hover{background:#005a2d;box-shadow:0 4px 12px rgba(0,61,31,.3)}
.lcard .hint{color:#5d6a62}
.lcard .msg{background:#eefaf1;color:#14532d;border-color:#2e9d68}
.lcard .msg.error{background:#fff2f2;color:#a30000;border-color:#e53935}
.iw{position:relative}.iw input{padding-right:4.2rem}
.tpw{position:absolute;right:6px;top:50%;transform:translateY(-50%);background:none;border:0;color:#5d6a62;cursor:pointer;
 font-size:.84rem;font-weight:500;height:40px;padding:0 .7rem}
.tpw:hover{color:#003d1f}
.row{display:flex;justify-content:space-between;align-items:center;margin:.2rem 0 1.2rem;flex-wrap:wrap;gap:.5rem}
.row label{display:flex;align-items:center;gap:.45rem;margin:0;font-weight:600}.row input{width:auto}
.lkb,a.lk{color:#003d1f;text-decoration:none;font-size:.88rem;background:none;border:0;cursor:pointer;font-weight:500}
.lkb:hover,a.lk:hover{text-decoration:underline}
.agree{display:flex;gap:.6rem;align-items:flex-start;font-weight:400;font-size:.84rem;line-height:1.45;margin:.2rem 0 1.1rem;cursor:pointer}
.agree input{width:auto;margin-top:.2rem;flex:none}
.lcard .g3{grid-template-columns:1fr 1fr 1fr;gap:0 .6rem}

/* ---- help section (register page) ---- */
.hp{margin-top:1.3rem;border:1px solid #dde3df;border-radius:14px;background:#f6faf7;padding:0}
.hp summary{cursor:pointer;list-style:none;padding:.85rem 1rem;font-weight:600;font-size:.9rem;display:flex;align-items:center;gap:.6rem;color:#003d1f}
.hp summary::-webkit-details-marker{display:none}
.hp summary::after{content:"\\25BE";margin-left:auto;transition:.2s}
.hp[open] summary::after{transform:rotate(180deg)}
.hp ol{list-style:none;counter-reset:s;padding:.2rem 1rem 1rem}
.hp li{counter-increment:s;display:flex;gap:.8rem;padding:.55rem 0;font-size:.86rem;line-height:1.45;color:#1b2620}
.hp li::before{content:counter(s);flex:none;width:26px;height:26px;border-radius:50%;background:#003d1f;color:#fff;
 font-weight:700;font-size:.78rem;display:flex;align-items:center;justify-content:center;margin-top:.05rem}
.hp li b{color:#003d1f}
.hp .tip{margin:0 1rem 1rem;padding:.65rem .8rem;border-radius:10px;background:#e3f0e8;font-size:.8rem;color:#1b2620}

.center{text-align:center;margin-top:1.2rem;font-size:.9rem;color:#5d6a62}
.center a{color:#003d1f;text-decoration:none;font-weight:600}.center a:hover{text-decoration:underline}
.copy{text-align:center;font-size:.76rem;color:#8a948e;margin-top:1.3rem;line-height:1.6}
.copy .lkb{font-size:.76rem;color:#003d1f;font-weight:700}
@media(max-width:480px){
 body{padding:.8rem .7rem calc(.8rem + env(safe-area-inset-bottom));align-items:flex-start}
 .lcard{padding:1.5rem 1.2rem 1.1rem;border-radius:20px;margin:auto 0}
 .lh .logo-circle{width:84px;height:84px}.lh h1{font-size:1.15rem}
 .lcard .g3,.lcard .g2{grid-template-columns:1fr}
}
</style></head><body>
<div class="lcard">
 <div class="lh">""" + LOGO_HTML + """<h1>SLSU JGE - Office of the Registrar</h1><p>JGE Tagkawayan Campus · Registrar Appointment System</p></div>
 {% for cat, m in get_flashed_messages(with_categories=true) %}<div class="msg {{ cat }}" style="margin-top:1rem">{{ m }}</div>{% endfor %}

 {% if page == 'login' %}
  <form method="POST" action="/login" class="lform">
   <div class="form-group"><label>Email or Student ID</label>
    <input type="text" name="email" required autocomplete="username" placeholder="yourname@gmail.com or 2023-00123"></div>
   <div class="form-group"><label>Password</label><div class="iw">
    <input type="password" name="password" id="lp" required autocomplete="current-password" placeholder="Enter password">
    <button type="button" class="tpw" onclick="tp('lp',this)" aria-label="Show password">Show</button></div></div>
   <div class="row"><label><input type="checkbox" name="remember"> Remember me</label>
    <button type="button" class="lkb" onclick="document.getElementById('fp').style.display='block'">Forgot password?</button></div>
   <div id="fp" class="msg" style="display:none">To reset your password, please visit the Registrar's Office or contact the system administrator.</div>
   <button class="btn btn-full">Log In</button></form>
  <p class="center">No account yet? <a href="/register">Register here</a></p>

 {% elif page == 'register' %}
  <form method="POST" action="/register" class="lform">
   <div class="g3">
    <div class="form-group"><label>Last Name *</label><input name="last_name" required maxlength="60" value="{{ f.last_name }}"></div>
    <div class="form-group"><label>First Name *</label><input name="first_name" required maxlength="60" value="{{ f.first_name }}"></div>
    <div class="form-group"><label>Middle Name *</label><input name="middle_name" required maxlength="60" value="{{ f.middle_name }}" placeholder="N/A if none"></div></div>
   <div class="form-group"><label>Student ID *</label><input name="studentid" required placeholder="e.g. 2023-00123" value="{{ f.studentid }}"></div>
   <div class="form-group"><label>I am a *</label><select name="level" id="level" onchange="lv()">
    <option value="college" {{ 'selected' if f.level!='lhs' }}>College Student (Bachelor's program)</option>
    <option value="lhs" {{ 'selected' if f.level=='lhs' }}>Laboratory High School Student</option></select></div>
   <div id="blkCollege">
    <div class="form-group"><label>Course / Program *</label><select name="course" required><option value="">-- Select Program --</option>
     {% for c in courses %}<option {{ 'selected' if f.course==c }}>{{ c }}</option>{% endfor %}</select></div>
    <div class="form-group"><label>Year Level *</label><select name="year_level" required><option value="">-- Select Year --</option>
     {% for y in years %}<option {{ 'selected' if f.year_level==y }}>{{ y }}</option>{% endfor %}</select></div></div>
   <div id="blkLhs" class="hid">
    <div class="g2"><div class="form-group"><label>Grade Level *</label><select name="grade" disabled><option value="">-- Select Grade --</option>
      {% for g in grades %}<option {{ 'selected' if f.grade==g }}>{{ g }}</option>{% endfor %}</select></div>
     <div class="form-group"><label>Section *</label><input name="section" maxlength="30" placeholder="e.g. Newton" value="{{ f.section }}" disabled></div></div></div>
   <div class="form-group"><label>Gender *</label><select name="gender" required>
    <option value="">-- Select --</option>{% for g in ['Male','Female','Prefer not to say'] %}<option {{ 'selected' if f.gender==g }}>{{ g }}</option>{% endfor %}</select></div>
   <div class="form-group"><label>Birthday *</label><input type="date" name="birthday" required value="{{ f.birthday }}">
    <p class="hint">College students must be at least 16 years old; Laboratory High School students at least 11.</p></div>
   <div class="form-group"><label>Gmail Address *</label><input type="email" name="email" required placeholder="yourname@gmail.com" value="{{ f.email }}"></div>
   <div class="form-group"><label>Password *</label><div class="iw"><input type="password" name="password" id="p1" required>
    <button type="button" class="tpw" onclick="tp('p1',this)" aria-label="Show password">Show</button></div>
    <p class="hint">8+ characters · 1 uppercase · 1 number · 1 symbol (!@#$%^&*)</p></div>
   <div class="form-group"><label>Confirm Password *</label><div class="iw"><input type="password" name="confirm_pw" id="p2" required>
    <button type="button" class="tpw" onclick="tp('p2',this)" aria-label="Show password">Show</button></div></div>
   <button class="btn btn-full">Submit for Activation</button></form>
  <p class="center">Already have an account? <a href="/login">Log In</a></p>

  <details class="hp" open><summary><i class="fas fa-circle-question"></i> Need help? How to register an account</summary>
   <ol>
    <li><span>Fill in the form on this page.</span></li>
    <li><span>Choose <b>College Student</b> or <b>Laboratory High School Student</b>, then type your last, first and middle name (write <b>N/A</b> if you have none) and your <b>Student ID</b>.</span></li>
    <li><span>Select your <b>program and year level</b> (or <b>grade level and section</b> for Laboratory High School), your gender and birthday.</span></li>
    <li><span>Enter a valid <b>Gmail address</b> and a strong password: 8+ characters with an uppercase letter, a number and a symbol.</span></li>
    <li><span>Press <b>Submit for Activation</b>.</span></li>
    <li><span><b>Wait for approval.</b> Keep the page open: it tells you when the administrator approves your account.</span></li>
    <li><span>Go to <b>Log In</b> and use your Email or Student ID and password. Then open <b>Book Appointment</b> to request your document.</span></li></ol>
   <p class="tip"><i class="fas fa-lightbulb"></i> Use your real details exactly as in your school records. Wrong information can delay approval. Forgot your password? Visit the Registrar's Office.</p></details>

 {% else %}
  <div style="text-align:center;padding:1.4rem 0 .6rem"><i class="fas fa-clock" id="pic" style="font-size:3rem;color:#003d1f"></i>
   <h2 id="ptt" style="margin:1rem 0;font-size:1.25rem;color:#003d1f">Awaiting Activation</h2></div>
  <p id="ptx" style="text-align:center;line-height:1.6;color:#1b2620">Your account has been submitted. Please wait for the administrator to approve it. Keep this page open and we will notify you here as soon as it is approved.</p>
  <div class="center" id="pgo"><a class="lk" href="/login">← Back to Log In</a></div>
 {% endif %}

 <p class="copy">© Southern Luzon State University — JGE Tagkawayan Campus
  {% if page == 'login' %}<br><button type="button" class="lkb" onclick="openTerms()">Terms and Conditions</button>{% endif %}</p>
</div>

<div class="modal" id="terms"><div class="mbox wide"><button type="button" class="x" onclick="closeTerms()" aria-label="Close">&times;</button>
 <h3 class="ct"><i class="fas fa-file-contract"></i> Terms and Conditions</h3>
 <div class="prose"><p>By creating an account and using the SLSU JGE Tagkawayan Registrar Appointment System you agree to the following:</p>
  <ul>
   <li><strong>Purpose.</strong> The system is for requesting documents from the Office of the Registrar and scheduling a visit. A booking is a request for a schedule, not a guarantee that your document is ready.</li>
   <li><strong>Accurate information.</strong> Give true and complete details. False information may lead to rejection or removal of your account.</li>
   <li><strong>Your account.</strong> Registration must be approved by the administrator. Keep your password private; you are responsible for all activity under your account.</li>
   <li><strong>Your own records.</strong> Request only your own records, or records you are authorized to request.</li>
   <li><strong>Attendance.</strong> Come on your scheduled date and time. An appointment you do not attend is removed after that day and counted as failed. After 3 failed appointments you cannot book for 3 months.</li>
   <li><strong>Requirements and fees.</strong> Bring the required documents and pay the processing fee at the SLSU JGE Campus Cashier. Processing time and fees follow Registrar policy.</li>
   <li><strong>Data privacy.</strong> Your information is handled under the Data Privacy Act of 2012 (RA 10173), used only to verify you and process your requests, and seen only by authorized registrar staff and administrators.</li>
   <li><strong>Changes.</strong> The campus may update these terms and may suspend accounts that misuse the system.</li></ul></div>
 <div class="mbtn"><button type="button" class="btn btn-sm" onclick="closeTerms()">I understand</button></div></div></div>

<script>
function tp(id,b){const i=document.getElementById(id),s=i.type==='password';i.type=s?'text':'password';
 b.textContent=s?'Hide':'Show';b.setAttribute('aria-label',s?'Hide password':'Show password')}
function lv(){const l=document.getElementById('level');if(!l)return;const c=l.value!=='lhs';
 [['blkCollege',c],['blkLhs',!c]].forEach(a=>{const b=document.getElementById(a[0]);b.classList.toggle('hid',!a[1]);
  b.querySelectorAll('select,input').forEach(x=>{x.disabled=!a[1];x.required=a[1]})})}
lv();
const tm=document.getElementById('terms');
function openTerms(){tm.classList.add('open')}function closeTerms(){tm.classList.remove('open')}
tm.addEventListener('click',e=>{if(e.target===tm)closeTerms()});
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeTerms()});
document.querySelectorAll('.msg').forEach(m=>{if(m.id==='fp')return;m.style.cursor='pointer';
 setTimeout(()=>{m.style.opacity=0;setTimeout(()=>m.remove(),350)},{{ flash_ms }}+2500);m.addEventListener('click',()=>m.remove())});
</script>
{% if page == 'pending' %}<script>
(function(){const ic=document.getElementById('pic'),tt=document.getElementById('ptt'),tx=document.getElementById('ptx'),go=document.getElementById('pgo');
 function show(ok){ic.className=ok?'fas fa-check-circle':'fas fa-times-circle';
  tt.textContent=ok?'Account Approved!':'Registration Not Approved';
  tx.textContent=ok?'Good news! The administrator has approved your account. You can now log in and book your appointments.':'Sorry, your registration was not approved. Please visit the Registrars Office, or register again with the correct details.';
  go.innerHTML=ok?'<a class="btn btn-full" style="color:#fff" href="/login">Log In Now</a>':'<a class="lk" href="/register">Register again</a>'}
 function chk(){fetch('/register/status',{cache:'no-store'}).then(r=>r.json()).then(d=>{
  if(d.status==='approved'){show(true);clearInterval(t)}else if(d.status==='rejected'){show(false);clearInterval(t)}}).catch(()=>{})}
 const t=setInterval(chk,4000);chk()})();
</script>{% endif %}
</body></html>"""

# ========== STUDENT PORTAL ==========
USER_TPL = """<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Student Portal — SLSU JGE Tagkawayan</title>""" + THEME_INIT + FA + """
<script>function fb(i){const l=(i.dataset.fb||'').split('|').filter(Boolean),n=l.shift();if(n){i.dataset.fb=l.join('|');i.src=n}else{i.remove()}}</script>
<style>{{ css|safe }}</style></head><body class="sticky">
""" + BLUR_BG + """
<div class="top-bar">Republic of the Philippines · Southern Luzon State University — JGE Tagkawayan Campus</div>
<header class="header-main">
 <div class="logo-group">""" + LOGO_HTML + """<div class="logo-text"><h1>SLSU JGE TAGKAWAYAN</h1><p>Student Appointment Portal</p></div></div>
 <nav><ul class="nav-menu">
  <li><a href="#home" class="active">Home</a></li><li><a href="#services">Services</a></li>
  <li><a href="#book">Book Appointment</a></li><li><a href="#my-appointments">My Appointments</a></li>
  <li class="more"><button type="button" id="moreBtn" class="mb">More ▾</button><ul class="dd" id="dd">
   <li><a href="#help">Help</a></li><li><a href="#about">About Us</a></li><li><a href="#faqs">FAQs</a></li><li><a href="#terms">Terms of Use</a></li>
   <li><a href="#privacy">Privacy Policy</a></li><li><a href="#contact">Contact Us</a></li><li><a href="#feedback">Send Feedback</a></li></ul></li></ul></nav>
 <div class="user-area">""" + THEME_BTN + """
  <a href="#profile" class="user-badge" onclick="sw('profile');return false">{% if avatar %}<img class="av" src="{{ avatar }}" alt="">{% else %}<i class="fas fa-user-circle"></i>{% endif %} {{ session.fullname }}</a></div>
</header>
<div class="page-container">
 {% for cat, m in get_flashed_messages(with_categories=true) %}<div class="msg {{ cat }}">{{ m }}</div>{% endfor %}
 <section id="home" class="section active">
  <div class="banner"><img src="{{ banner }}" alt="" data-fb="{{ bg }}" onerror="fb(this)"></div>
  <h2 class="t">Welcome, {{ greet }}!</h2>
  <p style="line-height:1.8;margin-bottom:.4rem">Student ID: <strong>{{ session.studentid }}</strong> · Use this portal to request documents and schedule visits to the Office of the Registrar.</p>
  <div class="grid">
   <a class="stat" href="#book" onclick="sw('book');return false"><i class="fas fa-calendar-plus"></i><h3 style="font-size:1.1rem">Book Now</h3><p>Fill out the form and submit your request.</p></a>
   <a class="stat" href="#my-appointments" onclick="sw('my-appointments');return false"><i class="fas fa-history"></i><h3 style="font-size:1.1rem">Track Status</h3><p>{{ active_appts|length }} upcoming · {{ history|length }} completed</p></a>
   <a class="stat" href="#services" onclick="sw('services');return false"><i class="fas fa-graduation-cap"></i><h3 style="font-size:1.1rem">Services</h3><p>See available documents.</p></a></div>
  <div class="card prose"><h3 class="ct"><i class="fas fa-laptop-file"></i> About the Student Appointment Portal</h3><p>The SLSU JGE Tagkawayan Registrar Appointment System lets students request documents from the Office of the Registrar and reserve a visit schedule online, so you can skip the long lines. Choose the document you need, pick an available weekday and time slot, and submit your request. Then visit the office on your scheduled date with a valid ID to process and claim your document.</p><p>You can track all your bookings under <strong>My Appointments</strong>, update your details and profile picture in <strong>My Profile</strong>, and find help, FAQs and policies under <strong>More</strong>.</p></div>
  <div class="card prose"><h3 class="ct"><i class="fas fa-building-columns"></i> Office of the University Registrar</h3>
   <p>{{ univ.intro }}</p><ul class="fnlist">{% for f in univ.functions %}<li>{{ f }}</li>{% endfor %}</ul></div>
  <div class="card prose"><h3 class="ct"><i class="fas fa-file-lines"></i> Documents Processed by the Office of the University Registrar</h3>
   <ul class="dlist">{% for d in univ.docs %}{% if d is string %}<li>{{ d }}</li>{% else %}<li><strong>{{ d.title }}</strong>
    {% if d.sub %}<ul>{% for s in d.sub %}<li>{{ s }}</li>{% endfor %}</ul>{% endif %}
    {% if d.steps %}<div class="note"><strong>Instructions:</strong><ol>{% for s in d.steps %}<li>{{ s }}</li>{% endfor %}</ol></div>{% endif %}</li>{% endif %}{% endfor %}</ul></div></section>
 <section id="services" class="section"><h2 class="t">Documents &amp; Services</h2>
  <div class="alert"><i class="fas fa-circle-info"></i><div><strong>Online processing notice</strong><br>The documents and services listed on this page are the only ones available and can be processed online through this portal. For any other request, please visit the Registrar's Office.</div></div>
  {% for title, items in services.items() %}<div class="card"><h3 class="ct">{{ title }}</h3><ul style="list-style:none">
   {% for d in items %}<li style="padding:.7rem 0;{{ 'border-bottom:1px solid var(--bd)' if not loop.last }}"><i class="fas fa-circle-check" style="color:var(--acc)"></i>&nbsp; {{ d }}</li>{% endfor %}</ul></div>{% endfor %}</section>
 <section id="book" class="section"><h2 class="t">Schedule an Appointment</h2>
  {% if restricted_until %}<div class="alert danger"><i class="fas fa-ban"></i><div><strong>Appointment booking is restricted</strong><br>Your account missed 3 appointments, so booking is locked until <strong>{{ restricted_until }}</strong>. You can still sign in and view your records. If you think this is a mistake, please contact the Registrar's Office.</div></div>
  {% else %}
  <div class="alert"><i class="fas fa-triangle-exclamation"></i><div><strong>Attendance reminder</strong><br>Come on your scheduled date and time. If you do not attend, the appointment is <strong>removed after that day</strong> and counted as a <strong>failed appointment</strong>. After <strong>3 failed appointments</strong> your account is <strong>restricted from booking for 3 months</strong>.{% if strikes %} You currently have <strong>{{ strikes }} of 3</strong>.{% endif %}</div></div>
  <div class="card">
  <form method="POST" action="/book">
   <div class="g3">
    <div class="form-group"><label>Last Name *</label><input name="last_name" required maxlength="60" value="{{ nm.ln }}"></div>
    <div class="form-group"><label>First Name *</label><input name="first_name" required maxlength="60" value="{{ nm.fn }}"></div>
    <div class="form-group"><label>Middle Name *</label><input name="middle_name" required maxlength="60" value="{{ nm.mn }}" placeholder="Write N/A if none"></div></div>
   {% if is_lhs %}
   <div class="g3">
    <div class="form-group"><label>Student ID</label><input value="{{ session.studentid }}" readonly></div>
    <div class="form-group"><label>Grade Level *</label><select name="year_level" required><option value="">-- Select Grade --</option>
     {% for g in grades %}<option {{ 'selected' if g==me.get('year_level') }}>{{ g }}</option>{% endfor %}</select></div>
    <div class="form-group"><label>Section *</label><input name="section" required maxlength="30" value="{{ me.get('section','') }}"></div></div>
   <p class="hint" style="margin:-.5rem 0 1rem">Laboratory High School student</p>
   {% else %}
   <div class="g2">
    <div class="form-group"><label>Student ID</label><input value="{{ session.studentid }}" readonly></div>
    <div class="form-group"><label>Year Level *</label><select name="year_level" required><option value="">-- Select Year --</option>
     {% for y in years %}<option {{ 'selected' if y==me.get('year_level') }}>{{ y }}</option>{% endfor %}</select></div></div>
   <div class="form-group"><label>Course / Program *</label><select name="course" required><option value="">-- Select Program --</option>
    {% for c in courses %}<option {{ 'selected' if c==me.get('course') }}>{{ c }}</option>{% endfor %}</select></div>
   {% endif %}
   <div class="form-group"><label>Document to Request *</label><select name="document" required><option value="">-- Select Document --</option>
    {% for d in docs %}<option>{{ d }}</option>{% endfor %}</select></div>
   <div class="reqbox"><div class="rq-h"><i class="fas fa-clipboard-check"></i> <span id="reqTitle">Requirements checklist</span></div>
    <div class="rq-l" id="reqList"><p class="hint">Select a document above to see what you need to bring.</p></div>
    <label class="sw"><input type="checkbox" name="agree_req" required> I have read the requirements above and will complete and bring them on my appointment date. I understand that missing my appointment counts as a failed appointment (3 failed appointments = booking restricted for 3 months).</label></div>
   <div class="form-group"><label>Comments / Specifications</label>
    <textarea name="comment" rows="4" maxlength="500" placeholder="Specify details of the document you are requesting (e.g. number of copies, purpose, school year/semester) or write your concern here."></textarea>
    <p class="hint">Optional · up to 500 characters</p></div>
   <div class="g2">
    <div class="form-group"><label>Preferred Date * (Mon–Fri)</label><input type="date" name="sched_date" required></div>
    <div class="form-group"><label>Preferred Time *</label><select name="sched_time" required><option value="">-- Select Time --</option>
     {% for t in times %}<option>{{ t }}</option>{% endfor %}</select></div></div>
   <div class="g2">
    <div class="form-group"><label>Payment Method *</label><select name="payment" required>
     {% for p in payments %}<option {{ 'selected' if loop.length==1 }}>{{ p }}</option>{% endfor %}</select>
     <p class="hint">Fees are paid at the campus cashier.</p></div>
    <div class="form-group"><label>Contact Number *</label><input type="tel" name="contact" required placeholder="09XX-XXX-XXXX" value="{{ me.get('contact','') }}" pattern="[0-9+\\- ]{11,16}"></div></div>
   <button class="btn">SUBMIT APPOINTMENT</button></form></div>{% endif %}</section>
 <section id="my-appointments" class="section"><h2 class="t">My Appointments</h2>
  {% if active_appts %}<div class="card tw"><table class="rt"><tr class="hr"><th>#</th><th>Document</th><th>Date</th><th>Time</th><th>Payment</th><th>Comments</th><th>Status</th></tr>
   {% for a in active_appts %}<tr><td data-label="#">{{ loop.index }}</td><td data-label="Document">{{ a.document }}</td><td data-label="Date">{{ a.sched_label }}</td><td data-label="Time">{{ a.sched_time }}</td><td data-label="Payment">{{ a.payment }}</td><td class="wrap" data-label="Comments">{{ a.comment or '—' }}</td><td data-label="Status"><span class="bdg pend">{{ a.status }}</span></td></tr>{% endfor %}</table></div>
  {% else %}<div class="card empty">You have no upcoming appointments. <a href="#book" onclick="sw('book')" style="color:var(--acc)">Book one now</a>.</div>{% endif %}
  {% if strikes or restricted_until %}<div class="alert danger"><i class="fas fa-user-xmark"></i><div><strong>Missed appointments: {{ strikes }} of 3</strong><br>{% if restricted_until %}Booking is locked until <strong>{{ restricted_until }}</strong> because of 3 missed appointments.{% else %}Appointments you do not attend are removed after the scheduled day. At 3 missed appointments, booking is locked for 3 months.{% endif %}</div></div>{% endif %}
  {% if active_appts %}<div class="reqbox"><div class="rq-h"><i class="fas fa-clipboard-check"></i> Reminder: bring these on your appointment date</div>
   {% for a in active_appts %}{% set key = doc_reqs.get(a.document) %}{% if key %}<div class="rq-key"><div class="rq-kt"><i class="fas fa-triangle-exclamation"></i> Important for {{ a.document }} · {{ a.sched_label }}</div><ul>{% for it in key %}<li>{{ it }}</li>{% endfor %}</ul></div>{% endif %}{% endfor %}
   <div class="rq-t">Also bring (all requests)</div>
   <ul class="rl">{% for it in reqs %}{% if it is string %}<li><i class="fas fa-check" style="color:var(--acc)"></i>&nbsp; {{ it }}</li>{% else %}<li><strong>{{ it.title }}</strong><ul>{% for x in it.sub %}<li>• {{ x }}</li>{% endfor %}</ul></li>{% endif %}{% endfor %}</ul></div>{% endif %}
  {% if missed %}<h3 class="sub">Missed Appointments</h3>
  <div class="card tw"><table class="rt"><tr class="hr"><th>#</th><th>Document</th><th>Scheduled</th><th>Status</th></tr>
   {% for a in missed %}<tr><td data-label="#">{{ loop.index }}</td><td data-label="Document">{{ a.document }}</td><td data-label="Scheduled">{{ a.sched_label }} · {{ a.sched_time }}</td><td data-label="Status"><span class="bdg bad">Missed</span></td></tr>{% endfor %}</table></div>{% endif %}
  {% if history %}<h3 class="sub">Completed Transactions</h3>
  <div class="card tw"><table class="rt"><tr class="hr"><th>#</th><th>Document</th><th>Scheduled</th><th>Completed On</th></tr>
   {% for a in history %}<tr><td data-label="#">{{ loop.index }}</td><td data-label="Document">{{ a.document }}</td><td data-label="Scheduled">{{ a.sched_label }} · {{ a.sched_time }}</td><td data-label="Completed On"><span class="bdg done">{{ a.completed_at }}</span></td></tr>{% endfor %}</table></div>{% endif %}</section>
 <section id="profile" class="section"><h2 class="t">My Profile</h2>
  <div class="card"><h3 class="ct">Profile Information</h3><form method="POST" action="/profile" enctype="multipart/form-data">
   <div class="av-row">
    <div class="avwrap">
     <img id="avPrev" class="av-lg {{ 'hid' if not avatar }}" src="{{ avatar or '' }}" alt="Profile picture">
     <div id="avPh" class="av-lg av-ph {{ 'hid' if avatar }}"><i class="fas fa-user"></i></div>
     <button type="button" class="pen" id="penBtn" title="Edit profile picture"><i class="fas fa-pen"></i></button>
     <div class="pop" id="pop">
      <button type="button" id="popChoose"><i class="fas fa-image"></i> Change &amp; adjust photo</button>
      <button type="button" id="popRemove"><i class="fas fa-trash"></i> Remove photo</button></div></div>
    <div><strong>{{ session.fullname }}</strong>
     <p class="hint">Tap the pen to change, adjust or remove your photo, then press Save Profile.</p></div>
    <input type="file" name="avatar" id="avIn" accept="image/png,image/jpeg,image/webp,image/gif" class="hid">
    <input type="checkbox" name="remove_avatar" id="rmAv" class="hid">
    <input type="file" id="avPick" accept="image/png,image/jpeg,image/webp,image/gif" class="hid"></div>
   <div class="g3">
    <div class="form-group"><label>Last Name *</label><input name="last_name" required maxlength="60" value="{{ nm.ln }}"></div>
    <div class="form-group"><label>First Name *</label><input name="first_name" required maxlength="60" value="{{ nm.fn }}"></div>
    <div class="form-group"><label>Middle Name *</label><input name="middle_name" required maxlength="60" value="{{ nm.mn }}" placeholder="N/A if none"></div></div>
   <div class="g2"><div class="form-group"><label>Email</label><input value="{{ session.email }}" readonly></div>
    <div class="form-group"><label>Student ID</label><input value="{{ session.studentid }}" readonly></div>
    <div class="form-group"><label>Birthday *</label><input type="date" name="birthday" required value="{{ me.get('birthday','') }}"></div>
    {% if is_lhs %}
    <div class="form-group"><label>Grade Level</label><select name="year_level"><option value="">-- Not set --</option>
     {% for g in grades %}<option {{ 'selected' if g==me.get('year_level') }}>{{ g }}</option>{% endfor %}</select></div>
    <div class="form-group"><label>Section *</label><input name="section" required maxlength="30" value="{{ me.get('section','') }}"></div>
    <div class="form-group"><label>Contact Number</label><input type="tel" name="contact" placeholder="09XX-XXX-XXXX" value="{{ me.get('contact','') }}"></div>
    <div class="form-group"><label>Student Type</label><input value="Laboratory High School" readonly></div></div>
    {% else %}
    <div class="form-group"><label>Year Level</label><select name="year_level"><option value="">-- Not set --</option>
     {% for y in years %}<option {{ 'selected' if y==me.get('year_level') }}>{{ y }}</option>{% endfor %}</select></div>
    <div class="form-group"><label>Contact Number</label><input type="tel" name="contact" placeholder="09XX-XXX-XXXX" value="{{ me.get('contact','') }}"></div>
    <div class="form-group"><label>Default Course / Program</label><select name="course"><option value="">-- Not set --</option>
     {% for c in courses %}<option {{ 'selected' if c==me.get('course') }}>{{ c }}</option>{% endfor %}</select></div></div>
    {% endif %}
   <div class="form-group"><label>Address</label><input name="address" maxlength="200" placeholder="Barangay, Municipality, Province" value="{{ me.get('address','') }}"></div>
   <button class="btn">Save Profile</button></form></div>
  <details class="card pwd"><summary><i class="fas fa-lock"></i>&nbsp; Change password</summary>
   <form method="POST" action="/profile/password">
    <div class="form-group"><label>Current Password</label><input type="password" name="current" required autocomplete="current-password"></div>
    <div class="g2"><div class="form-group"><label>New Password</label><input type="password" name="new" required autocomplete="new-password"><p class="hint">8+ characters with an uppercase letter, a number and a symbol</p></div>
     <div class="form-group"><label>Confirm New Password</label><input type="password" name="confirm" required autocomplete="new-password"></div></div>
    <button class="btn btn-sm btn-ghost">Update Password</button></form></details>
  <a href="/logout" class="btn btn-danger btn-full"><i class="fas fa-sign-out-alt"></i> Sign Out</a></section>
 <section id="help" class="section"><h2 class="t">Help &amp; Student Guide</h2>
  <div class="card prose"><h3 class="ct"><i class="fas fa-route"></i> How to get your document in 7 steps</h3>
   <p>Follow these steps from creating your account to claiming your document. College students and Laboratory High School students use the same process.</p>
   <div class="stp"><div class="n">1</div><div><h4>Create your account</h4><p>On the sign-in page press <strong>Register here</strong>. Choose <strong>College Student</strong> or <strong>Laboratory High School Student</strong>, then enter your last, first and middle name (write <em>N/A</em> if none), Student ID, your program and year level (or grade level and section), birthday, a Gmail address and a strong password.</p><p class="hint">College students must be at least 16 years old and Laboratory High School students at least 11. Your password needs 8+ characters with an uppercase letter, a number and a symbol.</p></div></div>
   <div class="stp"><div class="n">2</div><div><h4>Wait for approval</h4><p>The administrator must approve your account first. Keep the page open; it tells you when you are approved. Then sign in with your <strong>Gmail or Student ID</strong> and password.</p></div></div>
   <div class="stp"><div class="n">3</div><div><h4>Check the available services</h4><p>Open <strong>Services</strong> to see the documents that can be processed online. Documents that are not on the list must be requested at the Registrar's Office.</p></div></div>
   <div class="stp"><div class="n">4</div><div><h4>Prepare your requirements</h4><p>Have these ready before your visit:</p>
    <ul class="rl">{% for it in reqs %}{% if it is string %}<li><i class="fas fa-check" style="color:var(--acc)"></i>&nbsp; {{ it }}</li>{% else %}<li><strong>{{ it.title }}</strong><ul>{% for x in it.sub %}<li>• {{ x }}</li>{% endfor %}</ul></li>{% endif %}{% endfor %}</ul>
    <p class="hint">When you choose a document on the booking form, the <strong>important requirements for that document</strong> are highlighted above this general list, and you must confirm them before submitting.</p></div></div>
   <div class="stp"><div class="n">5</div><div><h4>Book your appointment</h4><p>Open <strong>Book Appointment</strong>. Your details are filled in for you. Choose the document, add specifications in the comments (copies, purpose, school year/semester), pick a weekday and a time slot, enter your mobile number, tick the requirements confirmation and press <strong>Submit Appointment</strong>.</p><div class="chips"><span class="chip">Mon–Fri only</span><span class="chip">Future dates only</span><span class="chip">Limited slots per time</span></div></div></div>
   <div class="stp"><div class="n">6</div><div><h4>Track your request</h4><p>Go to <strong>My Appointments</strong>. A request shows <span class="bdg pend">Pending</span> until the registrar marks it done. Finished requests move to <strong>Completed Transactions</strong> with the date and time.</p></div></div>
   <div class="stp"><div class="n">7</div><div><h4>Visit the office and claim</h4><p>Come on your scheduled date and time with your requirements and pay the fee at the <strong>SLSU JGE Campus Cashier</strong>. If someone claims for you, bring an authorization letter, a copy of your ID and the representative's valid ID.</p><p class="hint">Office days: {{ cdays }}</p><p class="hint"><strong>Do not miss your appointment:</strong> an appointment you do not attend is removed after that day and counted as failed. 3 failed appointments lock your booking for 3 months.</p></div></div></div>
  <div class="card prose"><h3 class="ct"><i class="fas fa-circle-question"></i> Common problems</h3>
   <details><summary>I cannot sign in.</summary><p>Use the Gmail or Student ID you registered with. If you registered recently, your account may still be waiting for approval. Forgot your password? Visit the Registrar's Office or contact the administrator.</p></details>
   <details><summary>The date I want is not accepted.</summary><p>Appointments must be on a future weekday (Monday to Friday). Weekends and today cannot be booked.</p></details>
   <details><summary>My time slot is full.</summary><p>Each time slot has limited capacity. Pick another time or another date.</p></details>
   <details><summary>The system will not let me submit.</summary><p>Check that every required field is filled, your mobile number is valid (09XXXXXXXXX) and the requirements confirmation is ticked.</p></details>
   <details><summary>I need to change my name, program, grade or section.</summary><p>Update your details in <strong>My Profile</strong> (click your name at the top). For a correction of name or records on official documents, request it from the Services list or visit the office.</p></details>
   <details><summary>I missed my appointment. What happens?</summary><p>The appointment is removed after the scheduled day and recorded as a failed appointment. After 3 failed appointments your account cannot book for 3 months, but you can still sign in. If you actually attended or had a valid reason, tell the Registrar's Office so they can correct the record.</p></details>
   <details><summary>I need to change or cancel a booking.</summary><p>Please contact the Registrar's Office before your appointment date.</p></details></div>
  <div class="card prose"><h3 class="ct"><i class="fas fa-headset"></i> Still need help?</h3>
   <p>Read the <a href="#faqs" onclick="sw('faqs')" style="color:var(--acc)">FAQs</a>, see our <a href="#contact" onclick="sw('contact')" style="color:var(--acc)">contact details</a>, or send a message through <a href="#feedback" onclick="sw('feedback')" style="color:var(--acc)">Send Feedback</a>.</p></div></section>
 <section id="about" class="section"><h2 class="t">About Us</h2>
  <div class="banner"><img src="{{ about_banner }}" alt="" data-fb="{{ banner }}|{{ bg }}" onerror="fb(this)"></div>
  <div class="card prose"><p>The Office of the Registrar of Southern Luzon State University – JGE Tagkawayan Campus keeps and issues official student academic records. This appointment system was built to make requesting documents faster, more organized and less crowded for students and registrar staff alike.</p></div>
  <div class="g2">
   <div class="card prose"><h3 class="ct"><i class="fas fa-bullseye"></i> Mission</h3><p>{{ about.mission }}</p></div>
   <div class="card prose"><h3 class="ct"><i class="fas fa-eye"></i> Vision</h3><p>{{ about.vision }}</p></div></div>
  <div class="card prose"><h3 class="ct"><i class="fas fa-flag-checkered"></i> Goals</h3><ul>{% for g in about.goals %}<li>{{ g }}</li>{% endfor %}</ul></div>
  <div class="card prose"><h3 class="ct"><i class="fas fa-landmark"></i> Our History</h3>{% for p in about.history %}<p>{{ p }}</p>{% endfor %}</div>
  <div class="card prose"><h3 class="ct"><i class="fas fa-laptop"></i> What the system does</h3><ul><li>Lets students schedule document requests online.</li><li>Gives the registrar a clear list of who is coming, when and for what.</li><li>Limits each time slot so service stays orderly.</li></ul></div></section>
 <section id="faqs" class="section"><h2 class="t">Frequently Asked Questions</h2><div class="card">
  <details><summary>Why can't I log in right after registering?</summary><p>New accounts must be approved by the administrator first. You can sign in once your account is activated.</p></details>
  <details><summary>Can I book on weekends or for today?</summary><p>No. The office is closed on weekends, and appointments must be booked for a future weekday.</p></details>
  <details><summary>What if my preferred time slot is full?</summary><p>Each slot has a limited capacity. Choose another time or date.</p></details>
  <details><summary>Can someone claim my document for me?</summary><p>Yes, with an authorization letter, a copy of your ID and the representative's valid ID.</p></details>
  <details><summary>How do I change my password, details or profile picture?</summary><p>Open <strong>My Profile</strong> by clicking your name at the top of the page.</p></details>
  <details><summary>Where can I see my finished requests?</summary><p>Once the registrar marks your request as done, it moves to <strong>Completed Transactions</strong> under My Appointments, with the date and time it was completed.</p></details>
  <details><summary>What happens if I do not attend my appointment?</summary><p>It is removed after that day and counted as a failed appointment. Three failed appointments restrict your account from booking for 3 months.</p></details>
  <details><summary>Can Laboratory High School students use this portal?</summary><p>Yes. Choose <strong>Laboratory High School Student</strong> when you register and enter your grade level and section. Your requests are listed for the registrar by grade level and section.</p></details>
  <details><summary>I forgot my password.</summary><p>Visit the Registrar's Office or contact the administrator to have it reset.</p></details></div></section>
 <section id="terms" class="section"><h2 class="t">Terms of Use</h2><div class="card prose">
  <ul><li>Use the system only to request your own records or records you are authorized to request.</li><li>Provide accurate and truthful information. False information may lead to account removal.</li>
  <li>Keep your login credentials private; you are responsible for activity under your account.</li><li>Book only what you will attend. An appointment you do not attend is removed after the scheduled day and counted as failed; 3 failed appointments restrict your account from booking for 3 months.</li>
  <li>A booking is a request for a schedule, not a guarantee that a document is ready. Processing times and fees follow Registrar policy.</li><li>The campus may update these terms and may suspend accounts that misuse the system.</li></ul></div></section>
 <section id="privacy" class="section"><h2 class="t">Privacy Policy</h2><div class="card prose">
  <p>We handle your personal information in line with the Data Privacy Act of 2012 (RA 10173).</p>
  <h4>What we collect</h4><p>Your name, student ID, birthday, gender, Gmail address, contact number, address, program, year level, profile picture and appointment details.</p>
  <h4>How we use it</h4><p>To verify your identity, manage your account and process your document requests and schedules. We do not sell your information.</p>
  <h4>Who can see it</h4><p>Authorized Registrar's Office personnel and system administrators only.</p>
  <h4>Your rights</h4><p>You may view and update your details in My Profile, and ask the Registrar's Office to correct or remove your data.</p></div></section>
 <section id="contact" class="section"><h2 class="t">Contact Us</h2><div class="card prose">
  <p><strong>Office of the Registrar</strong><br>Southern Luzon State University – JGE Tagkawayan Campus</p>
  <ul class="cl">
   <li><i class="fas fa-location-dot"></i><div><strong>Address</strong><br>{{ caddr }}</div></li>
   <li><i class="fas fa-envelope"></i><div><strong>Email</strong><br>{% if cemail %}<a href="mailto:{{ cemail }}">{{ cemail }}</a>{% else %}<span class="soon">To be announced</span>{% endif %}</div></li>
   <li><i class="fab fa-facebook"></i><div><strong>Facebook</strong><br>{% if cfb %}<a href="{{ cfb }}" target="_blank" rel="noopener">{{ cfb }}</a>{% else %}<span class="soon">To be announced</span>{% endif %}</div></li>
   {% if cphone %}<li><i class="fas fa-phone"></i><div><strong>Phone</strong><br>{{ cphone }}</div></li>{% endif %}
   <li><i class="fas fa-clock"></i><div><strong>Office days</strong><br>{{ cdays }}</div></li></ul>
  <p>For other concerns, you can also use <a href="#feedback" onclick="sw('feedback')" style="color:var(--acc)">Send Feedback</a>.</p></div></section>
 <section id="feedback" class="section"><h2 class="t">Send Feedback</h2><div class="card"><form method="POST" action="/feedback">
  <div class="g2"><div class="form-group"><label>Category</label><select name="category"><option>Suggestion</option><option>Problem / Bug</option><option>Compliment</option><option>Other</option></select></div>
   <div class="form-group"><label>Rating</label><select name="rating"><option value="5">★★★★★ Excellent</option><option value="4">★★★★ Good</option><option value="3">★★★ Okay</option><option value="2">★★ Poor</option><option value="1">★ Very poor</option></select></div></div>
  <div class="form-group"><label>Your message *</label><textarea name="message" rows="5" maxlength="1000" required placeholder="Tell us what's working and what we can improve"></textarea></div>
  <button class="btn">Send Feedback</button></form></div></section>
</div>
<div class="modal" id="crop"><div class="mbox"><h3 class="ct">Adjust photo</h3>
 <canvas id="cv" width="300" height="300"></canvas>
 <input type="range" id="zoom" min="1" max="3" step="0.01" value="1">
 <p class="hint">Drag to reposition · use the slider to zoom</p>
 <div class="mbtn"><button type="button" class="btn btn-sm btn-ghost" id="cropCancel">Cancel</button><button type="button" class="btn btn-sm" id="cropOk">Use photo</button></div></div></div>
""" + FOOTER + """
<script>
""" + FLASH_JS + THEME_JS + """
const links=document.querySelectorAll('.nav-menu a[href^="#"]'),secs=document.querySelectorAll('.section'),mb=document.getElementById('moreBtn'),dd=document.getElementById('dd');
function sw(id){if(!document.getElementById(id))id='home';
 links.forEach(l=>l.classList.toggle('active',l.getAttribute('href')==='#'+id));
 mb.classList.toggle('active',!!dd.querySelector('a[href="#'+id+'"]'));
 secs.forEach(s=>s.classList.toggle('active',s.id===id));dd.classList.remove('open');
 document.querySelectorAll('.msg').forEach(m=>m.remove());
 history.replaceState(null,'','#'+id);window.scrollTo(0,0)}
links.forEach(l=>l.addEventListener('click',e=>{e.preventDefault();sw(l.getAttribute('href').slice(1))}));
mb.addEventListener('click',e=>{e.stopPropagation();dd.classList.toggle('open')});
document.addEventListener('click',()=>dd.classList.remove('open'));
document.addEventListener('keydown',e=>{if(e.key==='Escape')dd.classList.remove('open')});
sw(location.hash.slice(1)||'home');

/* ---- profile picture: pen menu + crop/zoom editor ---- */
const avIn=document.getElementById('avIn'),avPick=document.getElementById('avPick'),rmAv=document.getElementById('rmAv'),
 avPrev=document.getElementById('avPrev'),avPh=document.getElementById('avPh'),pop=document.getElementById('pop'),
 crop=document.getElementById('crop'),cv=document.getElementById('cv'),cc=cv.getContext('2d'),zm=document.getElementById('zoom'),S=300;
let im=null,sc=1,base=1,ox=0,oy=0,drag=null;
document.getElementById('penBtn').addEventListener('click',e=>{e.stopPropagation();pop.classList.toggle('open')});
document.addEventListener('click',e=>{if(!pop.contains(e.target))pop.classList.remove('open')});
document.getElementById('popChoose').addEventListener('click',()=>{pop.classList.remove('open');avPick.click()});
document.getElementById('popRemove').addEventListener('click',()=>{pop.classList.remove('open');
 rmAv.checked=true;avIn.value='';avPrev.classList.add('hid');avPh.classList.remove('hid')});
function clampPos(){ox=Math.min(0,Math.max(S-im.width*sc,ox));oy=Math.min(0,Math.max(S-im.height*sc,oy))}
function paint(c,size,ring){const k=size/S;c.clearRect(0,0,size,size);c.drawImage(im,ox*k,oy*k,im.width*sc*k,im.height*sc*k);
 if(ring){c.save();c.fillStyle='rgba(0,0,0,.55)';c.beginPath();c.rect(0,0,size,size);c.arc(size/2,size/2,size/2-4,0,Math.PI*2,true);c.fill('evenodd');c.restore()}}
avPick.addEventListener('change',()=>{const f=avPick.files[0];if(!f)return;
 const img=new Image();img.onload=()=>{im=img;base=Math.max(S/img.width,S/img.height);sc=base;zm.value=1;
  ox=(S-img.width*sc)/2;oy=(S-img.height*sc)/2;paint(cc,S,true);crop.classList.add('open')};
 img.onerror=()=>alert('That file could not be read as an image.');
 img.src=URL.createObjectURL(f);avPick.value=''});
zm.addEventListener('input',()=>{const px=(S/2-ox)/sc,py=(S/2-oy)/sc;sc=base*zm.value;ox=S/2-px*sc;oy=S/2-py*sc;clampPos();paint(cc,S,true)});
cv.addEventListener('pointerdown',e=>{drag={x:e.clientX,y:e.clientY,ox:ox,oy:oy};cv.setPointerCapture(e.pointerId);cv.style.cursor='grabbing'});
cv.addEventListener('pointermove',e=>{if(!drag)return;const k=S/cv.getBoundingClientRect().width;
 ox=drag.ox+(e.clientX-drag.x)*k;oy=drag.oy+(e.clientY-drag.y)*k;clampPos();paint(cc,S,true)});
['pointerup','pointercancel'].forEach(n=>cv.addEventListener(n,()=>{drag=null;cv.style.cursor='grab'}));
document.getElementById('cropCancel').addEventListener('click',()=>crop.classList.remove('open'));
document.getElementById('cropOk').addEventListener('click',()=>{
 const out=document.createElement('canvas');out.width=out.height=512;paint(out.getContext('2d'),512,false);
 out.toBlob(b=>{const dt=new DataTransfer();dt.items.add(new File([b],'avatar.jpg',{type:'image/jpeg'}));avIn.files=dt.files;
  rmAv.checked=false;avPrev.src=URL.createObjectURL(b);avPrev.classList.remove('hid');avPh.classList.add('hid');
  crop.classList.remove('open')},'image/jpeg',.9)});

const dIn=document.querySelector('input[name="sched_date"]');
const tmr=new Date();tmr.setDate(tmr.getDate()+1);dIn.min=tmr.toISOString().split('T')[0];
dIn.addEventListener('input',()=>{const g=new Date(dIn.value+'T00:00').getDay();dIn.setCustomValidity(g===0||g===6?'The office is closed on weekends.':'');dIn.reportValidity()});

/* ---- requirements reminder when a document is chosen ---- */
const REQS={{ reqs|tojson }},DREQ={{ doc_reqs|tojson }},docSel=document.querySelector('select[name="document"]');
function reqLi(it){const li=document.createElement('li');
 if(typeof it==='string'){const l=document.createElement('label');l.className='rq';const c=document.createElement('input');c.type='checkbox';
  l.appendChild(c);l.appendChild(document.createTextNode(it));li.appendChild(l)}
 else{const t=document.createElement('div');t.className='rq-t';t.textContent=it.title;li.appendChild(t);
  const u=document.createElement('ul');(it.sub||[]).forEach(x=>u.appendChild(reqLi(x)));li.appendChild(u)}
 return li}
docSel.addEventListener('change',()=>{const box=document.getElementById('reqList'),d=docSel.value,t=document.getElementById('reqTitle');box.innerHTML='';
 if(!d){t.textContent='Requirements checklist';box.innerHTML='<p class="hint">Select a document above to see what you need to bring.</p>';return}
 t.textContent='Requirements for: '+d;
 const key=DREQ[d]||[];
 if(key.length){const k=document.createElement('div');k.className='rq-key';
  const kt=document.createElement('div');kt.className='rq-kt';kt.innerHTML='<i class="fas fa-triangle-exclamation"></i> Important for this document';k.appendChild(kt);
  const ku=document.createElement('ul');key.forEach(x=>ku.appendChild(reqLi(x)));k.appendChild(ku);box.appendChild(k)}
 const gt=document.createElement('div');gt.className='rq-t';gt.textContent=key.length?'Also bring (all requests)':'What to bring';box.appendChild(gt);
 const u=document.createElement('ul');REQS.forEach(it=>u.appendChild(reqLi(it)));box.appendChild(u);
 const p=document.createElement('p');p.className='hint';p.textContent='Tick each item as you prepare it. Incomplete requirements may delay your request.';box.appendChild(p)});
</script></body></html>"""

# ========== ADMIN ==========
ADMIN_TPL = """<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Admin Dashboard — SLSU JGE Tagkawayan</title>""" + THEME_INIT + FA + """
<style>{{ css|safe }}
.adm{display:flex;min-height:100vh}
.sb{width:248px;flex:none;background:var(--card);border-right:1px solid var(--bd);position:sticky;top:0;height:100vh;display:flex;flex-direction:column;padding:1rem .8rem;overflow-y:auto;z-index:300}
.sb-brand{display:flex;align-items:center;gap:.7rem;padding:.3rem .5rem 1.2rem}
.sb-brand .logo-circle{width:42px;height:42px;font-size:.65rem}
.sb-brand b{display:block;color:var(--acc);font-size:.95rem;line-height:1.15}.sb-brand small{color:var(--mut);font-size:.72rem}
.si{display:flex;align-items:center;gap:.75rem;padding:.7rem .9rem;border-radius:10px;color:var(--mut);font-weight:500;font-size:.9rem;cursor:pointer;margin-bottom:.2rem;text-decoration:none;position:relative}
.si i{width:1.2rem;text-align:center}
.si:hover{background:var(--row);color:var(--acc)}
.si.active{background:var(--soft);color:var(--acc);font-weight:700}
.si.active::before{content:"";position:absolute;left:-.8rem;top:20%;bottom:20%;width:4px;border-radius:0 4px 4px 0;background:var(--gold)}
.si .bd2{margin-left:auto;background:var(--pri);color:#fff;border-radius:2rem;font-size:.68rem;font-weight:700;padding:.1rem .5rem;min-width:1.4rem;text-align:center}
.sb-foot{margin-top:auto;padding-top:1rem;border-top:1px solid var(--bd)}
.mainc{flex:1;min-width:0;display:flex;flex-direction:column}
.tb{display:flex;align-items:center;gap:1rem;padding:.75rem 1.6rem;background:var(--card);border-bottom:1px solid var(--bd);position:sticky;top:0;z-index:200}
.hamb{display:none;width:38px;height:38px;border-radius:10px;border:1px solid var(--bd);background:var(--card);color:var(--acc);cursor:pointer}
.gs{position:relative;flex:1;max-width:400px}
.gs>i{position:absolute;left:.95rem;top:.78rem;color:var(--mut);font-size:.85rem}
.gs input{padding:.58rem .9rem .58rem 2.5rem;border-radius:2rem;background:var(--bg);font-size:.85rem}
.gres{display:none;position:absolute;left:0;right:0;top:112%;background:var(--card);border:1px solid var(--bd);border-radius:12px;box-shadow:var(--sh);z-index:50;padding:.3rem;max-height:320px;overflow:auto}
.gres.open{display:block}
.gres a{display:flex;align-items:center;gap:.7rem;padding:.55rem .7rem;border-radius:8px;text-decoration:none;color:var(--tx);font-size:.86rem}
.gres a:hover{background:var(--soft)}.gres small{color:var(--mut);display:block;font-size:.74rem}
.sp{flex:1}
.who{display:flex;align-items:center;gap:.6rem;font-size:.82rem;line-height:1.25}.who small{color:var(--mut);display:block;font-size:.72rem}
.content{padding:1.6rem;flex:1}
.pn{background:var(--card);border:1px solid var(--bd);border-radius:14px;padding:1.3rem;box-shadow:var(--sh);margin-bottom:1.2rem}
.pn>h3{font-size:1rem;color:var(--tx);margin-bottom:1rem;display:flex;justify-content:space-between;align-items:center;gap:.6rem;flex-wrap:wrap}
.pn>h3 .lg{font-size:.74rem;font-weight:500;color:var(--mut)}
.dt{display:inline-block;width:9px;height:9px;border-radius:50%;margin:0 .3rem 0 .8rem}
.tiles{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem}
.tile{border-radius:12px;padding:1.1rem 1.2rem;display:flex;justify-content:space-between;align-items:center;gap:.6rem}
.tile small{display:block;font-size:.78rem;color:var(--mut);margin-bottom:.15rem}.tile b{font-size:1.6rem;color:var(--tx);font-weight:700;line-height:1}
.tile i{font-size:1.8rem}
.t1{background:#ece4fb}.t1 i{color:#7c4ddb}.t2{background:#d9eefb}.t2 i{color:#2f8fd1}.t3{background:#fde7de}.t3 i{color:#e7824f}.t4{background:#dcf5e3}.t4 i{color:#25a35a}
[data-theme=dark] .t1{background:#2a2144}[data-theme=dark] .t2{background:#17303f}[data-theme=dark] .t3{background:#3d2a21}[data-theme=dark] .t4{background:#163324}
.two{display:grid;grid-template-columns:minmax(0,1.7fr) minmax(0,1fr);gap:1.2rem}
.two>.pn{min-width:0}
.gl{stroke:var(--bd)}.ax{fill:var(--mut);font-size:10px}.ink{fill:var(--tx)}
.dn{display:flex;flex-direction:column;align-items:center;gap:.8rem}
.dn .leg{display:flex;gap:1.2rem;font-size:.82rem;color:var(--mut);flex-wrap:wrap;justify-content:center}
.act{display:flex;align-items:center;gap:.8rem;padding:.65rem 0;border-bottom:1px solid var(--bd)}
.act:last-of-type{border:0}
.ai{width:38px;height:38px;border-radius:10px;display:flex;align-items:center;justify-content:center;flex:none;font-size:.95rem}
.c1{background:#d9eefb;color:#2f8fd1}.c2{background:#fde7de;color:#e7824f}.c3{background:#dcf5e3;color:#25a35a}
[data-theme=dark] .c1{background:#17303f}[data-theme=dark] .c2{background:#3d2a21}[data-theme=dark] .c3{background:#163324}
.act b{font-size:.84rem;display:block}.act small{color:var(--mut);font-size:.74rem;display:block;line-height:1.35}
.act>div{min-width:0;flex:1}.act .when{font-size:.68rem;color:var(--mut);text-align:right;max-width:70px;line-height:1.3}
.filtbar{display:flex;gap:.7rem;flex-wrap:wrap;align-items:center;margin-bottom:1rem}
.sbx{position:relative;flex:1;min-width:220px}.sbx i{position:absolute;left:1rem;top:.85rem;color:var(--mut)}.sbx input{padding-left:2.6rem}
.filtbar select{width:auto;min-width:170px;max-width:260px}
.nm{display:flex;align-items:center;gap:.7rem}
.nm img,.avi{width:34px;height:34px;border-radius:50%;object-fit:cover;flex:none;margin:0}
.avi{background:var(--soft);color:var(--acc);display:flex;align-items:center;justify-content:center;font-size:.85rem}
.adm th{background:transparent;color:var(--mut);border-bottom:1px solid var(--bd);text-transform:none;letter-spacing:0;font-size:.78rem;font-weight:600;position:static}
.adm .scroll th{position:sticky;background:var(--card)}
.adm td{font-size:.85rem}
.adm td.wrap{min-width:140px;max-width:210px}
.adm tr.dr td{border-bottom:1px solid var(--bd)}
.mut{color:var(--mut);font-size:.76rem}
form.in{display:inline}
.sbov{display:none}
@media(max-width:1100px){.tiles{grid-template-columns:1fr 1fr}.two{grid-template-columns:1fr}}
@media(max-width:960px){
 .sb{position:fixed;left:-270px;top:0;transition:left .25s;box-shadow:var(--sh)}
 body.sbo .sb{left:0}
 body.sbo .sbov{display:block;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:250}
 .hamb{display:inline-flex;align-items:center;justify-content:center}
 .tb{padding:.7rem 1rem}.content{padding:1rem}.who span{display:none}
}
@media(max-width:560px){.tiles{grid-template-columns:1fr 1fr}.ax.bx{font-size:17px}.tile{padding:.9rem}.tile i{font-size:1.4rem}}
</style></head><body class="adm">
""" + BLUR_BG + """
{% macro who(name, sid, av) %}<div class="nm">{% if av %}<img src="{{ av }}" alt="">{% else %}<span class="avi"><i class="fas fa-user"></i></span>{% endif %}<a href="#" class="plink" data-sid="{{ sid }}">{{ name }}</a></div>{% endmacro %}
{% macro filters(tid, ph, sel) %}<div class="filtbar"><div class="sbx"><i class="fas fa-search"></i><input type="search" class="srch" data-t="{{ tid }}" placeholder="{{ ph }}"></div>
 {% if sel %}<select class="flt-c"><option value="">All programs</option>{% for c in courses %}<option>{{ c }}</option>{% endfor %}<option>{{ lhs }}</option></select>
 <select class="flt-y"><option value="">All years / grades</option>{% for y in years %}<option>{{ y }}</option>{% endfor %}{% for g in grades %}<option>{{ g }}</option>{% endfor %}</select>{% endif %}
 <span class="hint cnt"></span></div>{% endmacro %}
{% macro cy(groups, kind) %}
{% for course, n, yrs in groups %}
<details class="cg" open><summary><span><i class="fas fa-graduation-cap"></i>&nbsp; {{ course }}</span><span class="pill">{{ n }}</span></summary>
 {% for year, rows in yrs %}
 <div class="yg"><h4 class="yh">{{ year }} <span class="pill">{{ rows|length }}</span></h4>
 <div class="tw"><table class="rt">
  {% if kind == 'active' %}<tr class="hr"><th>Student</th><th>ID</th><th>Document</th><th>Schedule</th><th>Comments</th><th>Contact</th><th>Action</th></tr>
  {% for a in rows %}<tr class="dr" data-q="{{ (a.fullname ~ ' ' ~ a.studentid ~ ' ' ~ a.document)|lower }}" data-c="{{ a.course }}" data-y="{{ a.year_level }}"><td data-label="Student">{{ who(a.fullname, a.studentid, a.avatar) }}</td><td data-label="ID">{{ a.studentid }}</td><td data-label="Document" class="wrap">{{ a.document }}</td><td data-label="Schedule"><strong>{{ a.sched_label }}</strong><span class="mut"><br>{{ a.sched_time }}</span></td><td class="wrap" data-label="Comments">{{ a.comment or '—' }}</td><td data-label="Contact">{{ a.contact }}</td>
   <td data-label="Action"><form class="in" method="POST" action="/admin/complete" onsubmit="return confirm('Mark this appointment as done and move it to the archive?')"><input type="hidden" name="id" value="{{ a.id }}"><button class="btn btn-sm">✔ Mark Done</button></form></td></tr>{% endfor %}
  {% elif kind == 'archive' %}<tr class="hr"><th>Student</th><th>ID</th><th>Document</th><th>Scheduled</th><th>Completed On</th><th>Action</th></tr>
  {% for a in rows %}<tr class="dr" data-q="{{ (a.fullname ~ ' ' ~ a.studentid ~ ' ' ~ a.document)|lower }}" data-c="{{ a.course }}" data-y="{{ a.year_level }}"><td data-label="Student">{{ who(a.fullname, a.studentid, a.avatar) }}</td><td data-label="ID">{{ a.studentid }}</td><td data-label="Document" class="wrap">{{ a.document }}</td><td data-label="Scheduled">{{ a.sched_label }}<span class="mut"><br>{{ a.sched_time }}</span></td><td data-label="Completed On"><span class="bdg done">{{ a.completed_at }}</span></td>
   <td data-label="Action"><form class="in" method="POST" action="/admin/reopen" onsubmit="return confirm('Move this back to active appointments?')"><input type="hidden" name="id" value="{{ a.id }}"><button class="btn btn-sm btn-ghost">↩ Restore</button></form></td></tr>{% endfor %}
  {% elif kind == 'missed' %}<tr class="hr"><th>Student</th><th>ID</th><th>Document</th><th>Scheduled</th><th>Student's missed count</th><th>Action</th></tr>
  {% for a in rows %}<tr class="dr" data-q="{{ (a.fullname ~ ' ' ~ a.studentid ~ ' ' ~ a.document)|lower }}" data-c="{{ a.course }}" data-y="{{ a.year_level }}"><td data-label="Student">{{ who(a.fullname, a.studentid, a.avatar) }}</td><td data-label="ID">{{ a.studentid }}</td><td data-label="Document" class="wrap">{{ a.document }}</td><td data-label="Scheduled">{{ a.sched_label }}<span class="mut"><br>{{ a.sched_time }}</span></td><td data-label="Missed count"><span class="bdg bad">{{ a.strikes }} / 3</span>{% if a.restricted %} <span class="bdg done">Restricted</span>{% endif %}</td>
   <td data-label="Action"><form class="in" method="POST" action="/admin/attended" onsubmit="return confirm('The student actually attended? This moves it to the archive as completed and removes the missed mark.')"><input type="hidden" name="id" value="{{ a.id }}"><button class="btn btn-sm">✔ Attended</button></form>
    <form class="in" method="POST" action="/admin/excuse" onsubmit="return confirm('Excuse this absence? It will no longer count toward the 3 missed appointments.')"><input type="hidden" name="id" value="{{ a.id }}"><button class="btn btn-sm btn-ghost">Excuse</button></form></td></tr>{% endfor %}
  {% else %}<tr class="hr"><th>Student</th><th>ID</th><th>Gmail</th><th>Gender</th><th>Contact</th><th>Missed</th><th>Action</th></tr>
  {% for u in rows %}<tr class="dr" data-q="{{ (u.fullname ~ ' ' ~ u.studentid ~ ' ' ~ u.email)|lower }}" data-c="{{ u.course }}" data-y="{{ u.year_level }}"><td data-label="Student">{{ who(u.fullname, u.studentid, u.avatar) }}</td><td data-label="ID">{{ u.studentid }}</td><td data-label="Gmail">{{ u.email }}</td><td data-label="Gender">{{ u.gender }}</td><td data-label="Contact">{{ u.contact or '—' }}</td><td data-label="Missed">{{ u.strikes }} / 3{% if u.restricted %} <span class="bdg bad">Restricted</span>{% endif %}</td>
   <td data-label="Action"><button type="button" class="btn btn-sm btn-ghost" data-sid="{{ u.studentid }}"><i class="fas fa-id-card"></i> View / Edit</button></td></tr>{% endfor %}
  {% endif %}
 </table></div></div>
 {% endfor %}
</details>
{% endfor %}
{% endmacro %}
<aside class="sb" id="sb">
 <div class="sb-brand">""" + LOGO_HTML + """<div><b>SLSU JGE</b><small>Registrar Admin</small></div></div>
 <nav>
  <a class="si active" data-tab="overview"><i class="fas fa-house"></i> Dashboard</a>
  <a class="si" data-tab="all-appointments"><i class="fas fa-calendar-check"></i> Appointments <span class="bd2">{{ all_count }}</span></a>
  <a class="si" data-tab="archive"><i class="fas fa-box-archive"></i> Archive <span class="bd2">{{ archive_count }}</span></a>
  <a class="si" data-tab="missed"><i class="fas fa-user-xmark"></i> Missed <span class="bd2">{{ missed_count }}</span></a>
  <a class="si" data-tab="accounts"><i class="fas fa-user-clock"></i> Pending Accounts <span class="bd2">{{ total_pending }}</span></a>
  <a class="si" data-tab="users-list"><i class="fas fa-user-graduate"></i> Students <span class="bd2">{{ total_approved }}</span></a>
  <a class="si" data-tab="feedback-list"><i class="fas fa-comments"></i> Feedback <span class="bd2">{{ feedback|length }}</span></a>
 </nav>
 <div class="sb-foot"><a href="/logout" class="si" style="color:#c62828"><i class="fas fa-right-from-bracket"></i> Sign Out</a></div>
</aside>
<div class="sbov" id="sbov"></div>
<div class="mainc">
 <header class="tb">
  <button type="button" class="hamb" id="hamb" aria-label="Menu"><i class="fas fa-bars"></i></button>
  <div class="gs"><i class="fas fa-search"></i><input type="search" id="gs" placeholder="Find a student by name, ID or Gmail…" autocomplete="off"><div class="gres" id="gres"></div></div>
  <div class="sp"></div>""" + THEME_BTN + """
  <div class="who"><span class="avi"><i class="fas fa-crown"></i></span><span><b>Administrator</b><small>Registrar Office</small></span></div>
 </header>
 <div class="content">
 {% for cat, m in get_flashed_messages(with_categories=true) %}<div class="msg {{ cat }}">{{ m }}</div>{% endfor %}

 <div class="tab-content active" id="overview">
  <div class="pn"><h3>Admin Dashboard</h3>
   <div class="tiles">
    <div class="tile t1"><div><small>Students</small><b>{{ total_approved }}</b></div><i class="fas fa-user-graduate"></i></div>
    <div class="tile t2"><div><small>Pending Accounts</small><b>{{ total_pending }}</b></div><i class="fas fa-user-clock"></i></div>
    <div class="tile t3"><div><small>Active Appointments</small><b>{{ all_count }}</b></div><i class="fas fa-calendar-check"></i></div>
    <div class="tile t4"><div><small>Completed</small><b>{{ archive_count }}</b></div><i class="fas fa-circle-check"></i></div></div></div>
  <div class="two">
   <div class="pn"><h3>Appointments Overview <span class="lg"><i class="dt" style="background:#f2a33a"></i>Pending<i class="dt" style="background:#2e9d68"></i>Completed</span></h3>
    <svg id="barc" viewBox="0 0 640 250" style="width:100%;height:auto"></svg></div>
   <div class="pn"><h3>Students</h3><div class="dn"><svg id="donut" viewBox="0 0 180 180" style="width:190px;height:190px"></svg>
    <div class="leg"><span><i class="dt" style="background:#2e9d68;margin-left:0"></i>College · {{ donut.college }}</span><span><i class="dt" style="background:#f2a33a"></i>Laboratory HS · {{ donut.lhs }}</span></div></div></div></div>
  <div class="two">
   <div class="pn"><h3>Recent Appointments <span class="lg">Latest 50 · click a name to open the profile</span></h3>
    {% if recent %}{{ filters('blk-recent', 'Search by student name or ID…', false) }}
    <div id="blk-recent" class="tw scroll"><table class="rt"><tr class="hr"><th>Student</th><th>ID</th><th>Document</th><th>Date</th><th>Status</th></tr>
     {% for a in recent %}<tr class="dr" data-q="{{ (a.fullname ~ ' ' ~ a.studentid)|lower }}"><td data-label="Student">{{ who(a.fullname, a.studentid, a.avatar) }}</td><td data-label="ID">{{ a.studentid }}</td><td data-label="Document" class="wrap">{{ a.document }}</td><td data-label="Date">{{ a.sched_label }}</td><td data-label="Status"><span class="bdg {{ {'Completed': 'done', 'Pending': 'pend'}.get(a.status, 'bad') }}">{{ a.status }}</span></td></tr>{% endfor %}</table>
     <div class="empty nores" style="display:none">No appointments match that name.</div></div>
    {% else %}<div class="empty">No appointments yet.</div>{% endif %}</div>
   <div class="pn"><h3>Recent Activity</h3>
    {% for x in activity %}<div class="act"><span class="ai {{ x.cls }}"><i class="fas {{ x.icon }}"></i></span><div><b>{{ x.title }}</b><small>{{ x.sub }}</small></div><span class="when">{{ x.when }}</span></div>
    {% else %}<div class="empty" style="padding:1.5rem">No activity yet.</div>{% endfor %}
    <button type="button" class="btn btn-full" style="margin-top:.9rem;background:var(--soft);color:var(--acc)" onclick="go('all-appointments')">View All</button></div></div>
 </div>

 <div class="tab-content" id="missed"><h2 class="t">Missed Appointments <small style="font-size:.7em;color:var(--mut);font-weight:500">· students who did not attend their schedule</small></h2>
  <div class="alert"><i class="fas fa-circle-info"></i><div>A pending appointment is moved here automatically after its scheduled day. When a student reaches <strong>3 missed appointments</strong>, booking is locked for <strong>3 months</strong>. Use <strong>Attended</strong> if the student did come, or <strong>Excuse</strong> for a valid reason; both remove the missed mark.</div></div>
  <div class="pn"><h3>Restricted accounts <span class="lg">booking locked for 3 months</span></h3>
   {% if restricted %}<div class="tw"><table class="rt"><tr class="hr"><th>Student</th><th>ID</th><th>Locked until</th><th>Action</th></tr>
    {% for r in restricted %}<tr class="dr"><td data-label="Student">{{ who(r.name, r.sid, r.avatar) }}</td><td data-label="ID">{{ r.sid }}</td><td data-label="Locked until"><span class="bdg bad">{{ r.until }}</span></td>
     <td data-label="Action"><form class="in" method="POST" action="/admin/restriction/lift" onsubmit="return confirm('Lift the booking restriction for this student?')"><input type="hidden" name="email" value="{{ r.email }}"><button class="btn btn-sm btn-ghost">Lift restriction</button></form></td></tr>{% endfor %}</table></div>
   {% else %}<div class="empty" style="padding:1rem">No restricted accounts.</div>{% endif %}</div>
  {% if missed_groups %}<div class="pn" style="padding-bottom:.4rem">{{ filters('blk-missed', 'Search by student name, ID or document…', true) }}</div>
  <div id="blk-missed">{{ cy(missed_groups, 'missed') }}<div class="pn empty nores" style="display:none">No matching records found.</div></div>
  {% else %}<div class="pn empty">No missed appointments.</div>{% endif %}</div>

 <div class="tab-content" id="accounts"><h2 class="t">Pending Account Activation</h2>
  {% if pending %}<div class="pn tw"><table class="rt"><tr class="hr"><th>Student</th><th>ID</th><th>Program / Level</th><th>Year · Section</th><th>Age</th><th>Gender</th><th>Gmail</th><th>Action</th></tr>
   {% for e, u in pending.items() %}<tr class="dr"><td data-label="Student">{{ who(u.fullname, '', '') }}</td><td data-label="ID">{{ u.studentid }}</td><td data-label="Program" class="wrap">{{ u.course }}</td><td data-label="Year">{{ u.year_level }}{% if u.section %} · Section {{ u.section }}{% endif %}</td><td data-label="Age">{{ u.age }}</td><td data-label="Gender">{{ u.gender }}</td><td data-label="Gmail">{{ e }}</td><td data-label="Action">
    <form class="in" method="POST" action="/admin/approve"><input type="hidden" name="email" value="{{ e }}"><button class="btn btn-sm">✅ Approve</button></form>
    <form class="in" method="POST" action="/admin/reject" onsubmit="return confirm('Reject this account?')"><input type="hidden" name="email" value="{{ e }}"><button class="btn btn-sm btn-danger">❌ Reject</button></form></td></tr>{% endfor %}</table></div>
  {% else %}<div class="pn empty"><i class="fas fa-check-circle" style="font-size:2.5rem;color:#4CAF50"></i><p style="margin-top:1rem">No pending accounts to review.</p></div>{% endif %}</div>

 <div class="tab-content" id="all-appointments"><h2 class="t">Active Appointments <small style="font-size:.7em;color:var(--mut);font-weight:500">· by program &amp; year / grade &amp; section</small></h2>
  {% if active_groups %}<div class="pn" style="padding-bottom:.4rem">{{ filters('blk-active', 'Search by student name, ID or document…', true) }}</div>
  <div id="blk-active">{{ cy(active_groups, 'active') }}<div class="pn empty nores" style="display:none">No matching appointments found.</div></div>
  {% else %}<div class="pn empty">No active appointments.</div>{% endif %}</div>

 <div class="tab-content" id="archive"><h2 class="t">Archive — Completed Transactions <small style="font-size:.7em;color:var(--mut);font-weight:500">· by program &amp; year / grade &amp; section</small></h2>
  {% if archive_groups %}<div class="pn" style="padding-bottom:.4rem">{{ filters('blk-archive', 'Search history by student name, ID or document…', true) }}</div>
  <div id="blk-archive">{{ cy(archive_groups, 'archive') }}<div class="pn empty nores" style="display:none">No matching records found in the archive.</div></div>
  {% else %}<div class="pn empty">No completed transactions yet.</div>{% endif %}</div>

 <div class="tab-content" id="users-list"><h2 class="t">Students <small style="font-size:.7em;color:var(--mut);font-weight:500">· approved accounts by program &amp; year / grade &amp; section</small></h2>
  {% if approved_groups %}<div class="pn" style="padding-bottom:.4rem">{{ filters('blk-users', 'Search students by name, ID or Gmail…', true) }}</div>
  <div id="blk-users">{{ cy(approved_groups, 'users') }}<div class="pn empty nores" style="display:none">No matching students found.</div></div>
  {% else %}<div class="pn empty">No approved accounts yet.</div>{% endif %}</div>

 <div class="tab-content" id="feedback-list"><h2 class="t">Student Feedback</h2>
  {% if feedback %}<div class="pn tw"><table class="rt"><tr class="hr"><th>Date</th><th>Student</th><th>Category</th><th>Rating</th><th>Message</th></tr>
   {% for f in feedback %}<tr class="dr"><td data-label="Date">{{ f.at }}</td><td data-label="Student">{{ f.name }} ({{ f.studentid }})</td><td data-label="Category">{{ f.category }}</td><td data-label="Rating">{{ '★' * f.rating }}</td><td class="wrap" data-label="Message" style="min-width:260px">{{ f.message }}</td></tr>{% endfor %}</table></div>
  {% else %}<div class="pn empty">No feedback yet.</div>{% endif %}</div>
 </div>
""" + FOOTER + """
</div>
<div class="modal" id="pm"><div class="mbox wide"><button type="button" class="x" id="pmx" aria-label="Close">&times;</button>
 <div id="pmView">
  <div class="pm-head"><div id="pmAv"></div><div><h3 id="pmName"></h3><p class="hint" id="pmSub"></p></div></div>
  <dl class="pm-grid" id="pmGrid"></dl>
  <h4 style="color:var(--acc);margin-bottom:.4rem">Appointments</h4><div id="pmAppts"></div>
  <div class="mbtn" style="justify-content:flex-start"><button type="button" class="btn btn-sm" id="pmEdit"><i class="fas fa-pen"></i> Edit / correct information</button></div></div>
 <form id="pmForm" class="hid" method="POST" action="/admin/student/update">
  <h3 style="color:var(--acc);margin-bottom:.4rem">Edit student information</h3><p class="hint" style="margin-bottom:1rem">Correct wrong data the student entered. Changes also update the student's name and program on their appointments.</p>
  <input type="hidden" name="orig" id="fOrig">
  <div class="g3"><div class="form-group"><label>Last name</label><input name="last_name" id="fLn" required maxlength="60"></div>
   <div class="form-group"><label>First name</label><input name="first_name" id="fFn" required maxlength="60"></div>
   <div class="form-group"><label>Middle name</label><input name="middle_name" id="fMn" required maxlength="60" placeholder="N/A if none"></div></div>
  <div class="g2"><div class="form-group"><label>Student ID</label><input name="studentid" id="fSid" required></div>
   <div class="form-group"><label>Gmail</label><input type="email" name="email" id="fEm" required></div>
   <div class="form-group"><label>Gender</label><select name="gender" id="fGe" required><option value="">--</option><option>Male</option><option>Female</option><option>Prefer not to say</option></select></div>
   <div class="form-group"><label>Birthday</label><input type="date" name="birthday" id="fBd" required></div></div>
  <div class="form-group"><label>Student type</label><select name="level" id="fLv" onchange="fLvT()"><option value="college">College</option><option value="lhs">Laboratory High School</option></select></div>
  <div id="fCol"><div class="form-group"><label>Course / Program</label><select name="course" id="fCo" required><option value="">--</option>{% for c in courses %}<option>{{ c }}</option>{% endfor %}</select></div>
   <div class="form-group"><label>Year level</label><select name="year_level" id="fYe" required><option value="">--</option>{% for y in years %}<option>{{ y }}</option>{% endfor %}</select></div></div>
  <div id="fLhs" class="hid"><div class="g2"><div class="form-group"><label>Grade level</label><select name="grade" id="fGr" disabled><option value="">--</option>{% for g in grades %}<option>{{ g }}</option>{% endfor %}</select></div>
   <div class="form-group"><label>Section</label><input name="section" id="fSe" maxlength="30" disabled></div></div></div>
  <div class="g2"><div class="form-group"><label>Contact number</label><input name="contact" id="fCt" placeholder="09XXXXXXXXX (leave empty to remove)"></div>
   <div class="form-group"><label>Address</label><input name="address" id="fAd" maxlength="200" placeholder="Leave empty to remove"></div></div>
  <label class="sw"><input type="checkbox" name="remove_avatar"> Remove the profile photo</label>
  <label class="sw"><input type="checkbox" name="clear_restriction"> Lift the booking restriction and reset the missed-appointment count</label>
  <div class="mbtn" style="justify-content:flex-end"><button type="button" class="btn btn-sm btn-ghost" id="pmCancel">Cancel</button><button class="btn btn-sm">Save changes</button></div></form>
</div></div>
<script>
""" + FLASH_JS + THEME_JS + """
const tabs=document.querySelectorAll('.si[data-tab]'),cs=document.querySelectorAll('.tab-content');
function go(id){if(!document.getElementById(id))id='overview';tabs.forEach(t=>t.classList.toggle('active',t.dataset.tab===id));
 cs.forEach(c=>c.classList.toggle('active',c.id===id));history.replaceState(null,'','#'+id);document.body.classList.remove('sbo');window.scrollTo(0,0)}
tabs.forEach(t=>t.addEventListener('click',()=>go(t.dataset.tab)));go(location.hash.slice(1)||'overview');
document.getElementById('hamb').addEventListener('click',()=>document.body.classList.add('sbo'));
document.getElementById('sbov').addEventListener('click',()=>document.body.classList.remove('sbo'));

/* ---- search + program/year filters (flat tables and grouped lists) ---- */
document.querySelectorAll('.srch').forEach(inp=>{
 const box=document.getElementById(inp.dataset.t),rows=[...box.querySelectorAll('tr.dr')],nr=box.querySelector('.nores'),
  bar=inp.closest('.filtbar'),cnt=bar.querySelector('.cnt'),fc=bar.querySelector('.flt-c'),fy=bar.querySelector('.flt-y');
 const vis=r=>r.style.display!=='none';
 const run=()=>{const q=inp.value.trim().toLowerCase(),c=fc?fc.value:'',y=fy?fy.value:'';let n=0;
  rows.forEach(r=>{const ok=(!q||r.dataset.q.includes(q))&&(!c||r.dataset.c===c)&&(!y||r.dataset.y===y);r.style.display=ok?'':'none';if(ok)n++});
  const on=q||c||y;
  box.querySelectorAll('.yg').forEach(g=>{g.style.display=[...g.querySelectorAll('tr.dr')].some(vis)?'':'none'});
  box.querySelectorAll('details.cg').forEach(d=>{const any=[...d.querySelectorAll('tr.dr')].some(vis);d.style.display=any?'':'none';if(on&&any)d.open=true});
  if(nr)nr.style.display=(on&&!n)?'block':'none';
  cnt.textContent=on?n+' of '+rows.length+' shown':rows.length+' record(s)'};
 inp.addEventListener('input',run);if(fc)fc.addEventListener('change',run);if(fy)fy.addEventListener('change',run);run()});

/* ---- charts ---- */
const CH={{ chart|tojson }},DN={{ donut|tojson }};
(function(){const el=document.getElementById('barc');if(!el)return;
 const W=640,H=250,L=34,B=26,T=10,mx=Math.max(4,...CH.p,...CH.c),step=Math.ceil(mx/4),top=step*4;let s='';
 for(let i=0;i<=4;i++){const y=T+(H-T-B)*(1-i/4);
  s+='<line class="gl" x1="'+L+'" x2="'+W+'" y1="'+y+'" y2="'+y+'"/><text class="ax bx" x="'+(L-6)+'" y="'+(y+3)+'" text-anchor="end">'+(step*i)+'</text>'}
 const bw=(W-L)/12;
 CH.m.forEach((m,i)=>{const x=L+i*bw+bw/2;
  [[CH.p[i],'#f2a33a',-11],[CH.c[i],'#2e9d68',1]].forEach(a=>{const h=(H-T-B)*a[0]/top;
   s+='<rect x="'+(x+a[2])+'" y="'+(H-B-h)+'" width="10" height="'+h+'" rx="3" fill="'+a[1]+'"/>'});
  s+='<text class="ax bx" x="'+x+'" y="'+(H-8)+'" text-anchor="middle">'+m+'</text>'});
 el.innerHTML=s})();
(function(){const el=document.getElementById('donut');if(!el)return;
 const a=DN.college,b=DN.lhs,tot=a+b,R=62,C=2*Math.PI*R;
 function seg(v,off,col){return '<circle cx="90" cy="90" r="'+R+'" fill="none" stroke="'+col+'" stroke-width="18" stroke-dasharray="'+(C*v/tot)+' '+C+'" stroke-dashoffset="'+(-off)+'" transform="rotate(-90 90 90)"/>'}
 let s='<circle class="gl" cx="90" cy="90" r="'+R+'" fill="none" stroke-width="18"/>';
 if(tot){s+=seg(a,0,'#2e9d68')+seg(b,C*a/tot,'#f2a33a')}
 s+='<text class="ax" x="90" y="84" text-anchor="middle" font-size="11">Total</text><text class="ink" x="90" y="106" text-anchor="middle" font-size="22" font-weight="700">'+tot+'</text>';
 el.innerHTML=s})();

/* ---- student profile viewer + editor ---- */
const PROFILES={{ profiles|tojson }};
const pm=document.getElementById('pm'),pv=document.getElementById('pmView'),pf=document.getElementById('pmForm');let CUR=null;
function mk(t,c,x){const e=document.createElement(t);if(c)e.className=c;if(x!==undefined)e.textContent=x;return e}
function openProfile(sid){const p=PROFILES[sid];if(!p)return;CUR=p;pf.classList.add('hid');pv.classList.remove('hid');
 const av=document.getElementById('pmAv');av.innerHTML='';
 if(p.avatar){const i=mk('img','av-lg');i.src=p.avatar;av.appendChild(i)}
 else{const d=mk('div','av-lg av-ph');d.innerHTML='<i class="fas fa-user"></i>';av.appendChild(d)}
 const lhs=p.level==='lhs';
 document.getElementById('pmName').textContent=p.name;
 document.getElementById('pmSub').textContent=lhs?'Laboratory High School · '+p.year+' · Section '+p.section:(p.year&&p.course?p.year+' · '+p.course:(p.year||p.course||''));
 const g=document.getElementById('pmGrid');g.innerHTML='';
 const rows=[['Full name',p.name],['Last name',p.ln],['First name',p.fn],['Middle name',p.mn],['Student ID',p.sid],['Student type',lhs?'Laboratory High School':'College'],['Gmail',p.email],['Gender',p.gender],
  ['Birthday',p.birthday?p.birthday+' ('+p.age+' yrs)':'']]
  .concat(lhs?[['Grade level',p.year],['Section',p.section]]:[['Year level',p.year],['Course / Program',p.course]])
  .concat([['Contact number',p.contact],['Address',p.address],['Missed appointments',p.strikes+' of 3'+(p.restricted_until?' · booking locked until '+p.restricted_until:'')]]);
 rows.forEach(r=>{g.appendChild(mk('dt','',r[0]));g.appendChild(mk('dd','',r[1]||'—'))});
 const ap=document.getElementById('pmAppts');ap.innerHTML='';
 if(!p.appts.length)ap.appendChild(mk('p','hint','No appointments yet.'));
 p.appts.forEach(a=>ap.appendChild(mk('div','pm-ap',a.document+' — '+a.date+' · '+a.time+' ['+a.status+']')));
 pm.classList.add('open')}
function fLvT(){const l=document.getElementById('fLv').value==='lhs';
 [['fCol',!l],['fLhs',l]].forEach(a=>{const b=document.getElementById(a[0]);b.classList.toggle('hid',!a[1]);
  b.querySelectorAll('select,input').forEach(x=>{x.disabled=!a[1];x.required=a[1]})})}
document.getElementById('pmEdit').addEventListener('click',()=>{const p=CUR;if(!p)return;const lhs=p.level==='lhs';
 const s=(id,v)=>{document.getElementById(id).value=v||''};
 s('fOrig',p.email);s('fLn',p.ln);s('fFn',p.fn);s('fMn',p.mn);s('fSid',p.sid);s('fEm',p.email);s('fGe',p.gender);s('fBd',p.birthday);
 s('fLv',lhs?'lhs':'college');s('fCo',lhs?'':p.course);s('fYe',lhs?'':p.year);s('fGr',lhs?p.year:'');s('fSe',p.section);s('fCt',p.contact);s('fAd',p.address);
 pf.querySelectorAll('input[type=checkbox]').forEach(c=>{c.checked=false});
 fLvT();pv.classList.add('hid');pf.classList.remove('hid')});
document.getElementById('pmCancel').addEventListener('click',()=>{pf.classList.add('hid');pv.classList.remove('hid')});
document.addEventListener('click',e=>{const a=e.target.closest('[data-sid]');if(a){e.preventDefault();openProfile(a.dataset.sid);document.getElementById('gres').classList.remove('open')}});
document.getElementById('pmx').addEventListener('click',()=>pm.classList.remove('open'));
pm.addEventListener('click',e=>{if(e.target===pm)pm.classList.remove('open')});
document.addEventListener('keydown',e=>{if(e.key==='Escape')pm.classList.remove('open')});

/* ---- top bar: find any student ---- */
const gi=document.getElementById('gs'),gr=document.getElementById('gres');
gi.addEventListener('input',()=>{const q=gi.value.trim().toLowerCase();gr.innerHTML='';if(!q){gr.classList.remove('open');return}
 const hits=Object.values(PROFILES).filter(p=>(p.name+' '+p.sid+' '+p.email).toLowerCase().includes(q)).slice(0,6);
 if(!hits.length){const d=mk('div','hint','No student found.');d.style.padding='.6rem .8rem';gr.appendChild(d)}
 hits.forEach(p=>{const a=mk('a');a.href='#';a.dataset.sid=p.sid;const s=mk('span','avi');s.innerHTML='<i class="fas fa-user"></i>';a.appendChild(s);
  const w=mk('div');w.appendChild(mk('b','',p.name));w.appendChild(mk('small','',p.sid+' · '+(p.level==='lhs'?p.year+' · Sec. '+p.section:p.course)));a.appendChild(w);gr.appendChild(a)});
 gr.classList.add('open')});
document.addEventListener('click',e=>{if(!e.target.closest('.gs'))gr.classList.remove('open')});
</script></body></html>"""


# ========== ROUTES ==========
@app.before_request
def auto_sweep():
    if request.endpoint != 'static':
        sweep_missed()


@app.before_request
def protect_routes():
    if request.endpoint in ('static', 'reg_status'):
        return
    if request.endpoint in ('home', 'login', 'register'):
        if session.get('email'):
            return redirect('/admin' if session['email'] == ADMIN_EMAIL else '/dashboard')
        return
    if not session.get('email'):
        return redirect('/')
    if request.path.startswith('/admin') and session['email'] != ADMIN_EMAIL:
        return redirect('/dashboard')


@app.errorhandler(413)
def too_large(e):
    flash("That photo is too large. Maximum size is 3 MB.", 'error')
    return redirect('/dashboard#profile' if session.get('email') else '/')


def notify_registration_result():
    """If this browser registered earlier, tell the student whether the account was approved."""
    pe = session.get('pending_email')
    if pe in approved_users:
        session.pop('pending_email', None)
        flash("🎉 Your account has been approved! You can now sign in.", 'ok')
    elif pe in rejected_accounts:
        session.pop('pending_email', None)
        flash("Your registration was not approved. Please visit the Registrar's Office or register again.", 'error')


@app.route('/')
def home():
    notify_registration_result()
    return render(LOGIN_TPL, page='login')


@app.route('/register/status')
def reg_status():
    pe = session.get('pending_email')
    if pe in approved_users:
        st = 'approved'
    elif pe in pending_accounts:
        st = 'pending'
    elif pe in rejected_accounts:
        st = 'rejected'
    else:
        st = 'unknown'
    return jsonify(status=st)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method != 'POST':
        notify_registration_result()
        return render(LOGIN_TPL, page='login')
    key = request.form.get('email', '').strip().lower()
    pw = request.form.get('password', '')
    session.permanent = bool(request.form.get('remember'))

    if key == ADMIN_EMAIL.lower() and pw == ADMIN_PASSWORD:
        session.update(email=ADMIN_EMAIL, fullname='Administrator', studentid='ADMIN')
        return redirect('/admin')

    e = find_user(key)
    if e and check_password_hash(approved_users[e]['password'], pw):
        u = approved_users[e]
        session.update(email=e, fullname=u['fullname'], studentid=u['studentid'])
        return redirect('/dashboard')

    for pe, u in pending_accounts.items():
        if key in (pe, u['studentid'].strip().lower()) and check_password_hash(u['password'], pw):
            flash("⏳ Your account is awaiting administrator approval.", 'error')
            return render(LOGIN_TPL, page='login')
    flash("Invalid credentials or account not activated.", 'error')
    return render(LOGIN_TPL, page='login')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method != 'POST':
        return render(LOGIN_TPL, page='register', f={})
    f = {k: request.form.get(k, '').strip() for k in
         ('last_name', 'first_name', 'middle_name', 'studentid', 'birthday', 'gender', 'email',
          'course', 'year_level', 'level', 'grade', 'section')}
    f['email'] = f['email'].lower()
    pw, cpw = request.form.get('password', ''), request.form.get('confirm_pw', '')

    def fail(msg):
        flash(msg, 'error')
        return render(LOGIN_TPL, page='register', f=f)

    if not (f['last_name'] and f['first_name'] and f['middle_name'] and f['studentid'] and f['gender']):
        return fail("Please complete all required fields (write N/A if you have no middle name)")
    lhs = f['level'] == 'lhs'
    if lhs:
        if f['grade'] not in GRADES or not f['section']:
            return fail("Please select your grade level and enter your section")
        f['course'], f['year_level'] = LHS, f['grade']
    elif f['course'] not in COURSES or f['year_level'] not in YEARS:
        return fail("Please select your course / program and year level")
    if not is_gmail_valid(f['email']):
        return fail("Please use a valid Gmail account (@gmail.com)")
    sid = f['studentid'].lower()
    if f['email'] in approved_users or f['email'] in pending_accounts:
        return fail("This email is already registered")
    if any(u['studentid'].strip().lower() == sid for u in list(approved_users.values()) + list(pending_accounts.values())):
        return fail("This Student ID is already registered or pending approval")
    age = calculate_age(f['birthday'])
    min_age = MIN_AGE_LHS if lhs else MIN_AGE_COLLEGE
    if age < min_age:
        return fail(f"Access Denied. Your age is {age}. Must be at least {min_age} years old.")
    ok, msg = is_password_valid(pw)
    if not ok:
        return fail(msg)
    if pw != cpw:
        return fail("Passwords do not match")

    ln, fn, mn = f['last_name'][:60], f['first_name'][:60], f['middle_name'][:60]
    pending_accounts[f['email']] = dict(fullname=compose_name(ln, fn, mn), ln=ln, fn=fn, mn=mn,
                                        studentid=f['studentid'], birthday=f['birthday'], gender=f['gender'],
                                        age=age, course=f['course'], year_level=f['year_level'],
                                        level='lhs' if lhs else 'college',
                                        section=f['section'].title()[:30] if lhs else '',
                                        registered_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                        password=generate_password_hash(pw))
    rejected_accounts.discard(f['email'])
    session['pending_email'] = f['email']
    return render(LOGIN_TPL, page='pending')


@app.route('/dashboard')
def dashboard():
    if session['email'] == ADMIN_EMAIL:
        return redirect('/admin')
    me = approved_users.get(session['email'])
    if me is None:                      # stale session (e.g. server restarted)
        session.clear()
        return redirect('/')
    mine = appointments_db.get(session['email'], [])
    session['fullname'], session['studentid'] = me['fullname'], me['studentid']
    active_appts = sorted([a for a in mine if a['status'] == 'Pending'], key=slot_key)
    history = sorted([a for a in mine if a['status'] == 'Completed'],
                     key=lambda a: a['completed_raw'], reverse=True)
    missed = sorted([a for a in mine if a['status'] == 'Missed'], key=lambda a: a['sched_date'], reverse=True)
    return render(USER_TPL, active_appts=active_appts, history=history, missed=missed, me=me,
                  avatar=me.get('avatar'), nm=name_parts(me), greet=greeting_name(me),
                  is_lhs=me.get('level') == 'lhs', strikes=me.get('strikes', 0),
                  restricted_until=fmt_date(me['restricted_until']) if is_restricted(me) else '')


@app.route('/profile', methods=['POST'])
def profile():
    me = approved_users.get(session['email'])
    if me is None:
        return redirect('/')
    g = lambda k: request.form.get(k, '').strip()
    ln, fn, mn = g('last_name')[:60], g('first_name')[:60], g('middle_name')[:60]
    contact = re.sub(r'[\s-]', '', request.form.get('contact', ''))
    course = request.form.get('course', '')
    year = request.form.get('year_level', '')
    address = g('address')[:200]
    birthday = g('birthday')
    photo = request.files.get('avatar')
    new_avatar = None

    if not (ln and fn and mn):
        flash("Last, first and middle name cannot be empty (write N/A if none).", 'error')
        return redirect('/dashboard#profile')
    is_lhs = me.get('level') == 'lhs'
    section = g('section').title()[:30]
    if is_lhs and not section:
        flash("Please enter your section.", 'error')
        return redirect('/dashboard#profile')
    age = calculate_age(birthday)
    min_age = MIN_AGE_LHS if is_lhs else MIN_AGE_COLLEGE
    if age < min_age:
        flash(f"Enter a valid birthday. You must be at least {min_age} years old.", 'error')
        return redirect('/dashboard#profile')
    if contact and not re.fullmatch(r'(09\d{9}|\+639\d{9})', contact):
        flash("Enter a valid PH mobile number (09XXXXXXXXX).", 'error')
        return redirect('/dashboard#profile')

    if photo and photo.filename:
        data = photo.read()
        ext = detect_image(data)
        if not ext:
            flash("Profile picture must be a JPG, PNG, WEBP or GIF image.", 'error')
            return redirect('/dashboard#profile')
        fname = f"{uuid.uuid4().hex}.{ext}"
        with open(os.path.join(AVATAR_DIR, fname), 'wb') as fh:
            fh.write(data)
        new_avatar = '/static/avatars/' + fname

    if new_avatar:
        delete_avatar(me.get('avatar'))
        me['avatar'] = new_avatar
    elif request.form.get('remove_avatar'):
        delete_avatar(me.get('avatar'))
        me.pop('avatar', None)

    name = compose_name(ln, fn, mn)
    me.update(fullname=name, ln=ln, fn=fn, mn=mn, contact=contact,
              course=LHS if is_lhs else (course if course in COURSES else ''), birthday=birthday, age=age,
              year_level=(year if year in GRADES else '') if is_lhs else (year if year in YEARS else ''),
              section=section if is_lhs else '', address=address)
    session['fullname'] = name
    flash("✅ Profile updated.", 'ok')
    return redirect('/dashboard#profile')


@app.route('/profile/password', methods=['POST'])
def change_password():
    me = approved_users.get(session['email'])
    if me is None:
        return redirect('/')
    cur, new, conf = (request.form.get(k, '') for k in ('current', 'new', 'confirm'))
    ok, msg = is_password_valid(new)
    if not check_password_hash(me['password'], cur):
        flash("Current password is incorrect.", 'error')
    elif not ok:
        flash(msg, 'error')
    elif new != conf:
        flash("New passwords do not match.", 'error')
    else:
        me['password'] = generate_password_hash(new)
        flash("✅ Password updated.", 'ok')
    return redirect('/dashboard#profile')


@app.route('/feedback', methods=['POST'])
def feedback():
    msg = request.form.get('message', '').strip()[:1000]
    if not msg:
        flash("Please write your feedback first.", 'error')
        return redirect('/dashboard#feedback')
    try:
        rating = min(5, max(1, int(request.form.get('rating', 5))))
    except ValueError:
        rating = 5
    feedback_db.append(dict(name=session['fullname'], studentid=session['studentid'],
                            category=request.form.get('category', 'Other')[:30], rating=rating,
                            message=msg, at=datetime.now().strftime('%Y-%m-%d %H:%M')))
    flash("✅ Thank you! Your feedback was sent.", 'ok')
    return redirect('/dashboard#feedback')


@app.route('/book', methods=['POST'])
def book():
    if session['email'] == ADMIN_EMAIL:
        return redirect('/admin')
    me = approved_users.get(session['email'])
    if me is None:
        return redirect('/')
    g = lambda k: request.form.get(k, '').strip()
    back = '/dashboard#book'
    if is_restricted(me):
        flash(f"Booking is locked until {fmt_date(me['restricted_until'])} because of 3 missed appointments.", 'error')
        return redirect(back)

    ln, fn, mn = g('last_name')[:60], g('first_name')[:60], g('middle_name')[:60]
    if not (ln and fn and mn):
        flash("Please enter your complete name: last, first and middle name (write N/A if none).", 'error')
        return redirect(back)
    fullname = compose_name(ln, fn, mn)

    try:
        d = datetime.strptime(g('sched_date'), '%Y-%m-%d').date()
    except ValueError:
        flash("Please choose a valid date.", 'error'); return redirect(back)
    if d <= date.today():
        flash("Please choose a future date.", 'error'); return redirect(back)
    if d.weekday() >= 5:
        flash("The office is closed on weekends. Choose a weekday.", 'error'); return redirect(back)

    if me.get('level') == 'lhs':
        course, year, section = LHS, g('year_level'), g('section').title()[:30]
        year_ok = year in GRADES and bool(section)
    else:
        course, year, section = g('course'), g('year_level'), ''
        year_ok = course in COURSES and year in YEARS
    if (not year_ok or g('document') not in DOCS or g('sched_time') not in TIMES
            or g('payment') not in PAYMENTS):
        flash("Please complete all fields with valid options.", 'error'); return redirect(back)
    if g('agree_req') != 'on':
        flash("Please confirm that you have read the requirements and will bring them complete.", 'error')
        return redirect(back)
    contact = re.sub(r'[\s-]', '', g('contact'))
    if not re.fullmatch(r'(09\d{9}|\+639\d{9})', contact):
        flash("Enter a valid PH mobile number (09XXXXXXXXX).", 'error'); return redirect(back)

    taken = sum(1 for lst in appointments_db.values() for a in lst
                if a['sched_date'] == g('sched_date') and a['sched_time'] == g('sched_time'))
    if taken >= SLOT_CAPACITY:
        flash("That time slot is already full. Please pick another.", 'error'); return redirect(back)

    appointments_db.setdefault(session['email'], []).append({
        'id': uuid.uuid4().hex[:10], 'status': 'Pending', 'completed_at': '', 'completed_raw': '',
        'email': session['email'], 'level': me.get('level', 'college'),
        'fullname': fullname, 'studentid': session['studentid'],
        'year_level': year, 'section': section, 'course': course, 'document': g('document'),
        'comment': g('comment')[:500], 'payment': g('payment'), 'req_confirmed': True,
        'sched_date': g('sched_date'), 'sched_label': d.strftime('%a, %b %d, %Y'),
        'sched_time': g('sched_time'),
        'contact': contact, 'submitted_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
    flash("✅ Appointment submitted successfully!", 'ok')
    return redirect('/dashboard#my-appointments')     # PRG: no duplicate on refresh


def _when(ts):
    try:
        return datetime.strptime(ts, '%Y-%m-%d %H:%M:%S').strftime('%b %d, %I:%M %p')
    except ValueError:
        return ''


@app.route('/admin')
def admin_dashboard():
    st = lambda a: approved_users.get(a.get('email'), {})
    appts = [dict(a, avatar=st(a).get('avatar', ''), strikes=st(a).get('strikes', 0), restricted=is_restricted(st(a)))
             for lst in appointments_db.values() for a in lst]
    active = sorted([a for a in appts if a['status'] == 'Pending'], key=slot_key)
    archive = sorted([a for a in appts if a['status'] == 'Completed'],
                     key=lambda a: a['completed_raw'], reverse=True)
    missed = sorted([a for a in appts if a['status'] == 'Missed'], key=lambda a: a['sched_date'], reverse=True)
    recent = sorted(appts, key=lambda a: a['submitted_at'], reverse=True)[:50]
    people = sorted((dict(u, email=e, strikes=u.get('strikes', 0), restricted=is_restricted(u))
                     for e, u in approved_users.items()), key=lambda u: u['fullname'].lower())
    restricted = [dict(name=u['fullname'], sid=u['studentid'], email=e, avatar=u.get('avatar', ''),
                       until=fmt_date(u['restricted_until'])) for e, u in approved_users.items() if is_restricted(u)]

    profiles = {}
    for e, u in approved_users.items():
        np_ = name_parts(u)
        profiles[u['studentid']] = dict(
            name=u['fullname'], ln=np_['ln'], fn=np_['fn'], mn=np_['mn'], sid=u['studentid'], email=e,
            level=u.get('level', 'college'), section=u.get('section', ''),
            gender=u.get('gender', ''), birthday=u.get('birthday', ''), age=u.get('age', ''),
            course=u.get('course', ''), year=u.get('year_level', ''), contact=u.get('contact', ''),
            address=u.get('address', ''), avatar=u.get('avatar', ''), strikes=u.get('strikes', 0),
            restricted_until=fmt_date(u['restricted_until']) if is_restricted(u) else '',
            appts=[dict(document=a['document'], date=a['sched_label'], time=a['sched_time'], status=a['status'])
                   for a in sorted(appointments_db.get(e, []), key=lambda a: a['submitted_at'], reverse=True)])

    year = str(date.today().year)
    chart = dict(m=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
                 p=[0] * 12, c=[0] * 12)
    for a in appts:
        if a['submitted_at'][:4] == year and a['status'] in ('Pending', 'Completed'):
            chart['c' if a['status'] == 'Completed' else 'p'][int(a['submitted_at'][5:7]) - 1] += 1
    n_lhs = sum(1 for u in approved_users.values() if u.get('level') == 'lhs')
    donut = dict(college=len(approved_users) - n_lhs, lhs=n_lhs)

    ev = []
    for u in pending_accounts.values():
        ev.append((u.get('registered_at', ''), 'fa-user-plus', 'c2', 'New registration',
                   f"{u['fullname']} · awaiting approval"))
    for a in appts:
        ev.append((a['submitted_at'], 'fa-calendar-plus', 'c1', 'New appointment', f"{a['fullname']} · {a['document']}"))
        if a['status'] == 'Completed':
            ev.append((a['completed_raw'], 'fa-circle-check', 'c3', 'Request completed', f"{a['fullname']} · {a['document']}"))
        if a['status'] == 'Missed':
            ev.append((a.get('missed_at', ''), 'fa-user-xmark', 'c2', 'Missed appointment', f"{a['fullname']} · {a['document']}"))
    ev.sort(key=lambda x: x[0], reverse=True)
    activity = [dict(icon=i, cls=c, title=t, sub=s_, when=_when(ts)) for ts, i, c, t, s_ in ev[:6]]

    return render(ADMIN_TPL, pending=pending_accounts, total_pending=len(pending_accounts),
                  total_approved=len(approved_users), all_count=len(active), archive_count=len(archive),
                  missed_count=len(missed), active_groups=group_cy(active), archive_groups=group_cy(archive),
                  missed_groups=group_cy(missed), approved_groups=group_cy(people), restricted=restricted,
                  recent=recent, profiles=profiles, chart=chart, donut=donut, activity=activity,
                  feedback=feedback_db[::-1])


def find_appt(aid):
    for lst in appointments_db.values():
        for a in lst:
            if a['id'] == aid:
                return a
    return None


@app.route('/admin/complete', methods=['POST'])
def complete():
    a = find_appt(request.form.get('id', ''))
    if a and a['status'] == 'Pending':
        now = datetime.now()
        a.update(status='Completed', completed_raw=now.strftime('%Y-%m-%d %H:%M:%S'),
                 completed_at=now.strftime('%b %d, %Y · %I:%M %p'))
        flash(f"Marked as done and archived: {a['document']} — {a['fullname']}", 'ok')
    else:
        flash("Appointment not found.", 'error')
    return redirect('/admin#all-appointments')


@app.route('/admin/reopen', methods=['POST'])
def reopen():
    a = find_appt(request.form.get('id', ''))
    if a and a['status'] == 'Completed':
        a.update(status='Pending', completed_raw='', completed_at='', exempt=True)   # exempt: never auto-missed
        flash("Moved back to active appointments.", 'ok')
    else:
        flash("Appointment not found.", 'error')
    return redirect('/admin#archive')


@app.route('/admin/attended', methods=['POST'])
def attended():
    a = find_appt(request.form.get('id', ''))
    if a and a['status'] == 'Missed':
        refund_strike(a)
        now = datetime.now()
        a.update(status='Completed', completed_raw=now.strftime('%Y-%m-%d %H:%M:%S'),
                 completed_at=now.strftime('%b %d, %Y · %I:%M %p'))
        flash(f"Corrected: {a['fullname']} attended. Moved to the archive.", 'ok')
    else:
        flash("Appointment not found.", 'error')
    return redirect('/admin#missed')


@app.route('/admin/excuse', methods=['POST'])
def excuse():
    a = find_appt(request.form.get('id', ''))
    if a and a['status'] == 'Missed':
        refund_strike(a)
        a['status'] = 'Excused'
        flash(f"Excused: {a['fullname']} · {a['document']}. It no longer counts as missed.", 'ok')
    else:
        flash("Appointment not found.", 'error')
    return redirect('/admin#missed')


@app.route('/admin/restriction/lift', methods=['POST'])
def lift_restriction():
    u = approved_users.get(request.form.get('email', '').strip().lower())
    if u:
        u.pop('restricted_until', None)
        u['strikes'] = 0
        flash(f"Booking restriction lifted for {u['fullname']}.", 'ok')
    return redirect('/admin#missed')


@app.route('/admin/student/update', methods=['POST'])
def admin_update_student():
    g = lambda k: request.form.get(k, '').strip()
    back = '/admin#users-list'
    orig = g('orig').lower()
    u = approved_users.get(orig)
    if u is None:
        flash("Student not found.", 'error'); return redirect(back)
    ln, fn, mn = g('last_name')[:60], g('first_name')[:60], g('middle_name')[:60]
    sid, email = g('studentid')[:40], g('email').lower()
    lhs = g('level') == 'lhs'
    if not (ln and fn and mn and sid):
        flash("Name (write N/A if no middle name) and Student ID are required.", 'error'); return redirect(back)
    if not is_gmail_valid(email):
        flash("Please enter a valid Gmail address.", 'error'); return redirect(back)
    if g('gender') not in ('Male', 'Female', 'Prefer not to say'):
        flash("Please choose a gender.", 'error'); return redirect(back)
    age = calculate_age(g('birthday'))
    if age <= 0:
        flash("Please enter a valid birthday.", 'error'); return redirect(back)
    if lhs:
        grade, section = g('grade'), g('section').title()[:30]
        if grade not in GRADES or not section:
            flash("Please choose a grade level and enter the section.", 'error'); return redirect(back)
        course, year = LHS, grade
    else:
        course, year, section = g('course'), g('year_level'), ''
        if course not in COURSES or year not in YEARS:
            flash("Please choose a course / program and year level.", 'error'); return redirect(back)
    contact = re.sub(r'[\s-]', '', g('contact'))
    if contact and not re.fullmatch(r'(09\d{9}|\+639\d{9})', contact):
        flash("Enter a valid PH mobile number (09XXXXXXXXX) or leave it empty.", 'error'); return redirect(back)
    others = [x for e, x in approved_users.items() if e != orig] + list(pending_accounts.values())
    if any(x['studentid'].strip().lower() == sid.lower() for x in others):
        flash("Another account already uses that Student ID.", 'error'); return redirect(back)
    if email != orig and (email in approved_users or email in pending_accounts):
        flash("That Gmail address is already registered.", 'error'); return redirect(back)

    name = compose_name(ln, fn, mn)
    u.update(fullname=name, ln=ln, fn=fn, mn=mn, studentid=sid, gender=g('gender'), birthday=g('birthday'), age=age,
             level='lhs' if lhs else 'college', course=course, year_level=year, section=section,
             contact=contact, address=g('address')[:200])
    if request.form.get('remove_avatar'):
        delete_avatar(u.get('avatar'))
        u.pop('avatar', None)
    if request.form.get('clear_restriction'):
        u.pop('restricted_until', None)
        u['strikes'] = 0
    if email != orig:
        approved_users[email] = approved_users.pop(orig)
        if orig in appointments_db:
            appointments_db[email] = appointments_db.pop(orig)
    for a in appointments_db.get(email, []):
        a.update(email=email, fullname=name, studentid=sid)
        if a['status'] != 'Completed':
            a.update(course=course, year_level=year, section=section, level='lhs' if lhs else 'college')
    flash(f"Updated the information of {name}.", 'ok')
    return redirect(back)


@app.route('/admin/approve', methods=['POST'])
def approve():
    e = request.form.get('email', '').strip().lower()
    if e in pending_accounts:
        approved_users[e] = pending_accounts.pop(e)
        flash(f"Approved {e}", 'ok')
    return redirect('/admin#accounts')


@app.route('/admin/reject', methods=['POST'])
def reject():
    e = request.form.get('email', '').strip().lower()
    if pending_accounts.pop(e, None):
        rejected_accounts.add(e)
        flash(f"Rejected {e}", 'ok')
    return redirect('/admin#accounts')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


if __name__ == '__main__':
    print("SLSU JGE TAGKAWAYAN — Registrar Appointment System")
    print(f"Admin login: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    print("Running at http://127.0.0.1:5000  (logo: static/jgetocopy.png)")
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1', port=5000)
