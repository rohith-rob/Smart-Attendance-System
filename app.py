import json
import os
import secrets
from datetime import datetime, timedelta

from flask import Flask, render_template, redirect, url_for, request, session, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import qrcode


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "attendance.db")
DEBUG_LOG_PATH = os.path.join(BASE_DIR, "debug-42b1ff.log")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="student")  # "student" or "admin"

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class AttendanceSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    title = db.Column(db.String(255), nullable=False)


class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey("attendance_session.id"), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User")
    session = db.relationship("AttendanceSession")


def _debug_log(run_id: str, hypothesis_id: str, location: str, message: str, data=None) -> None:
    """Lightweight JSON logger for debug session 42b1ff."""
    payload = {
        "sessionId": "42b1ff",
        "runId": run_id,
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data or {},
        "timestamp": int(datetime.utcnow().timestamp() * 1000),
    }
    try:
        with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")
    except Exception:
        # Logging must never break the app
        pass


def init_db():
    # #region agent log
    _debug_log("pre-fix", "H1", "app.py:54", "init_db called", {})
    # #endregion

    db.create_all()

    # Create a default admin if not present
    created_admin = False
    if not User.query.filter_by(email="admin@example.com").first():
        admin = User(name="Admin", email="admin@example.com", role="admin")
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()
        created_admin = True

    # #region agent log
    _debug_log(
        "pre-fix",
        "H1",
        "app.py:61",
        "init_db completed",
        {"created_admin": created_admin},
    )
    # #endregion


# Removed @app.before_first_request as it is deprecated in Flask 3.0+
# Instead, we will initialize the database within the app context below.


def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return User.query.get(uid)


def login_required(role=None):
    def decorator(fn):
        from functools import wraps

        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user:
                return redirect(url_for("login"))
            if role and user.role != role:
                flash("You are not allowed to access that page.", "danger")
                return redirect(url_for("dashboard"))
            return fn(*args, **kwargs)

        return wrapper

    return decorator


@app.errorhandler(Exception)
def handle_unexpected_error(e):
    """Global error handler to capture unexpected exceptions for debugging."""
    # #region agent log
    try:
        _debug_log(
            "pre-fix",
            "H3",
            "app.py:104",
            "Unhandled exception",
            {
                "type": type(e).__name__,
                "path": request.path if request else None,
            },
        )
    except Exception:
        # If logging fails, we still want the original error
        pass
    # #endregion
    raise e


@app.route("/")
def index():
    if current_user():
        if current_user().role == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session["user_id"] = user.id
            flash("Logged in successfully.", "success")
            if user.role == "admin":
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "danger")
            return render_template("register.html")

        user = User(name=name, email=email, role="student")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/dashboard")
@login_required()
def dashboard():
    user = current_user()
    today = datetime.utcnow().date()
    todays_attendance = (
        Attendance.query.join(AttendanceSession)
        .filter(Attendance.user_id == user.id)
        .filter(AttendanceSession.created_at >= datetime(today.year, today.month, today.day))
        .all()
    )
    total_classes = AttendanceSession.query.count()
    total_present = Attendance.query.filter_by(user_id=user.id).count()
    attendance_percentage = (total_present / total_classes * 100) if total_classes else 0

    return render_template(
        "student_dashboard.html",
        user=user,
        todays_attendance=todays_attendance,
        total_classes=total_classes,
        total_present=total_present,
        attendance_percentage=round(attendance_percentage, 2),
    )


@app.route("/admin/dashboard")
@login_required(role="admin")
def admin_dashboard():
    total_students = User.query.filter_by(role="student").count()
    total_sessions = AttendanceSession.query.count()
    total_attendance = Attendance.query.count()
    recent_sessions = AttendanceSession.query.order_by(AttendanceSession.created_at.desc()).limit(10).all()
    return render_template(
        "admin_dashboard.html",
        total_students=total_students,
        total_sessions=total_sessions,
        total_attendance=total_attendance,
        recent_sessions=recent_sessions,
    )


@app.route("/admin/create_session", methods=["POST"])
@login_required(role="admin")
def create_session():
    title = request.form.get("title") or "Class Session"
    duration_minutes = int(request.form.get("duration") or 15)
    code = secrets.token_urlsafe(8)
    now = datetime.utcnow()
    session_obj = AttendanceSession(
        code=code,
        title=title,
        created_at=now,
        expires_at=now + timedelta(minutes=duration_minutes),
    )
    db.session.add(session_obj)
    db.session.commit()
    flash("Attendance session created.", "success")
    return redirect(url_for("view_session", session_id=session_obj.id))


@app.route("/admin/session/<int:session_id>")
@login_required(role="admin")
def view_session(session_id):
    session_obj = AttendanceSession.query.get_or_404(session_id)
    attendees = Attendance.query.filter_by(session_id=session_id).all()
    return render_template("session_detail.html", session_obj=session_obj, attendees=attendees)


@app.route("/admin/session/<int:session_id>/qr")
@login_required(role="admin")
def session_qr(session_id):
    session_obj = AttendanceSession.query.get_or_404(session_id)
    # QR contents: URL that students visit to mark attendance
    mark_url = url_for("mark_attendance_qr", code=session_obj.code, _external=True)

    img = qrcode.make(mark_url)
    img_path = os.path.join(BASE_DIR, f"qr_{session_obj.code}.png")
    img.save(img_path)
    return send_file(img_path, mimetype="image/png")


@app.route("/attend/qr/<code>")
@login_required()
def mark_attendance_qr(code):
    user = current_user()
    session_obj = AttendanceSession.query.filter_by(code=code).first_or_404()

    now = datetime.utcnow()
    if now > session_obj.expires_at:
        flash("This attendance QR has expired.", "danger")
        return redirect(url_for("dashboard"))

    already = Attendance.query.filter_by(user_id=user.id, session_id=session_obj.id).first()
    if already:
        flash("Your attendance for this session is already recorded.", "info")
        return redirect(url_for("dashboard"))

    attendance = Attendance(user_id=user.id, session_id=session_obj.id)
    db.session.add(attendance)
    db.session.commit()
    flash("Attendance marked successfully via QR.", "success")
    return redirect(url_for("dashboard"))


@app.route("/attend/face", methods=["GET", "POST"])
@login_required()
def face_attendance():
    # NOTE: This is a simplified placeholder endpoint.
    # In a real deployment you would capture an image from the webcam on the client,
    # send it here, and run face recognition using OpenCV / face_recognition.
    user = current_user()
    if request.method == "POST":
        # For demo purposes this simply marks attendance for the latest active session.
        now = datetime.utcnow()
        session_obj = (
            AttendanceSession.query.filter(AttendanceSession.expires_at >= now)
            .order_by(AttendanceSession.created_at.desc())
            .first()
        )
        if not session_obj:
            flash("No active attendance session to mark.", "warning")
            return redirect(url_for("dashboard"))

        already = Attendance.query.filter_by(user_id=user.id, session_id=session_obj.id).first()
        if already:
            flash("Your attendance for this session is already recorded.", "info")
            return redirect(url_for("dashboard"))

        attendance = Attendance(user_id=user.id, session_id=session_obj.id)
        db.session.add(attendance)
        db.session.commit()
        flash("Attendance marked via (demo) face recognition.", "success")
        return redirect(url_for("dashboard"))

    return render_template("face_attendance.html")


@app.route("/admin/attendance")
@login_required(role="admin")
def admin_attendance():
    date_str = request.args.get("date")
    if date_str:
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            date = None
    else:
        date = None

    query = Attendance.query.join(AttendanceSession).join(User)
    if date:
        start = datetime(date.year, date.month, date.day)
        end = start + timedelta(days=1)
        query = query.filter(AttendanceSession.created_at >= start, AttendanceSession.created_at < end)

    records = query.order_by(Attendance.timestamp.desc()).all()
    return render_template("admin_attendance.html", records=records, selected_date=date_str or "")


@app.route("/admin/report")
@login_required(role="admin")
def admin_report():
    # Simple HTML report for now, grouped by student
    students = User.query.filter_by(role="student").all()
    sessions = AttendanceSession.query.order_by(AttendanceSession.created_at).all()
    attendance_map = {
        (a.user_id, a.session_id): a for a in Attendance.query.all()
    }
    return render_template(
        "admin_report.html",
        students=students,
        sessions=sessions,
        attendance_map=attendance_map,
    )


if __name__ == "__main__":
    # #region agent log
    _debug_log("pre-fix", "H1", "app.py:323", "__main__ entry", {})
    # #endregion

    with app.app_context():
        init_db()

    # #region agent log
    _debug_log("pre-fix", "H1", "app.py:326", "after init_db", {})
    # #endregion

    app.run(debug=True)

