import argparse
import os
from datetime import date, datetime, timedelta

from flask import Flask, flash, redirect, render_template, request, url_for
from flask_login import (LoginManager, UserMixin, current_user, login_required,
                         login_user, logout_user)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "instance", "dutyplanner.db")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DATABASE_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

os.makedirs(os.path.join(BASE_DIR, "instance"), exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

SHIFT_TYPES = [
    ("late_weekday", "Spätdienst (Woche)"),
    ("night_weekday", "Nachtdienst (Woche)"),
    ("early_weekend", "Frühdienst (Wochenende)"),
    ("night_weekend", "Nachtdienst (Wochenende)"),
    ("visite_weekend", "Visitendienst (Wochenende)"),
]


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), default="assistant")
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Shift(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    shift_type = db.Column(db.String(50), nullable=False)
    assigned_user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    assigned_user = db.relationship("User")

    def label(self) -> str:
        for key, label in SHIFT_TYPES:
            if key == self.shift_type:
                return label
        return self.shift_type

    @property
    def is_weekend(self) -> bool:
        return self.date.weekday() >= 5


@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))


def _upcoming_shifts():
    today = date.today()
    return (
        Shift.query.filter(Shift.date >= today)
        .order_by(Shift.date.asc())
        .all()
    )


def _ensure_db_initialized():
    with app.app_context():
        db.create_all()


@app.route("/")
@login_required
def dashboard():
    shifts = _upcoming_shifts()
    my_shifts = [s for s in shifts if s.assigned_user_id == current_user.id]
    open_shifts = [s for s in shifts if s.assigned_user_id is None]
    return render_template(
        "dashboard.html",
        my_shifts=my_shifts,
        open_shifts=open_shifts,
        shift_types=dict(SHIFT_TYPES),
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("dashboard"))
        flash("Ungültige Zugangsdaten", "error")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or not password:
            flash("Alle Felder sind Pflichtfelder", "error")
            return render_template("register.html")
        if User.query.filter_by(email=email).first():
            flash("E-Mail ist bereits registriert", "error")
            return render_template("register.html")
        user = User(name=name, email=email, role="assistant")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("Registrierung erfolgreich. Bitte anmelden.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/claim/<int:shift_id>", methods=["POST"])
@login_required
def claim_shift(shift_id: int):
    shift = db.session.get(Shift, shift_id)
    if not shift:
        flash("Schicht nicht gefunden", "error")
    elif shift.assigned_user_id and shift.assigned_user_id != current_user.id:
        flash("Schicht bereits vergeben", "error")
    else:
        shift.assigned_user = current_user
        db.session.commit()
        flash("Schicht übernommen", "success")
    return redirect(url_for("dashboard"))


@app.route("/release/<int:shift_id>", methods=["POST"])
@login_required
def release_shift(shift_id: int):
    shift = db.session.get(Shift, shift_id)
    if not shift or shift.assigned_user_id != current_user.id:
        flash("Schicht konnte nicht freigegeben werden", "error")
    else:
        shift.assigned_user = None
        db.session.commit()
        flash("Schicht freigegeben", "success")
    return redirect(url_for("dashboard"))


def _require_admin():
    if not current_user.is_authenticated or current_user.role != "admin":
        flash("Adminzugang erforderlich", "error")
        return False
    return True


@app.route("/admin", methods=["GET", "POST"])
@login_required
def admin_panel():
    if not _require_admin():
        return redirect(url_for("dashboard"))

    if request.method == "POST" and request.form.get("action") == "create_shift":
        date_str = request.form.get("date")
        shift_type = request.form.get("shift_type")
        try:
            shift_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            flash("Ungültiges Datum", "error")
        else:
            if shift_type not in dict(SHIFT_TYPES):
                flash("Ungültiger Schichttyp", "error")
            else:
                shift = Shift(date=shift_date, shift_type=shift_type)
                db.session.add(shift)
                db.session.commit()
                flash("Schicht erstellt", "success")

    users = User.query.order_by(User.name).all()
    shifts = _upcoming_shifts()
    return render_template(
        "admin.html", users=users, shifts=shifts, shift_types=SHIFT_TYPES
    )


@app.route("/admin/assign", methods=["POST"])
@login_required
def admin_assign():
    if not _require_admin():
        return redirect(url_for("dashboard"))

    shift_id = request.form.get("shift_id", type=int)
    user_id = request.form.get("user_id", type=int)
    shift = db.session.get(Shift, shift_id) if shift_id else None
    user = db.session.get(User, user_id) if user_id else None

    if not shift:
        flash("Schicht nicht gefunden", "error")
    else:
        shift.assigned_user = user
        db.session.commit()
        flash("Zuweisung aktualisiert", "success")
    return redirect(url_for("admin_panel"))


@app.context_processor
def inject_helpers():
    return {"SHIFT_TYPES": SHIFT_TYPES}


_ensure_db_initialized()


def seed_sample_data():
    if User.query.first():
        return

    admin = User(name="Admin", email="admin@example.com", role="admin")
    admin.set_password("admin123")
    anna = User(name="Anna Assistenz", email="anna@example.com", role="assistant")
    anna.set_password("anna123")
    ben = User(name="Ben Assistenz", email="ben@example.com", role="assistant")
    ben.set_password("ben123")

    db.session.add_all([admin, anna, ben])
    db.session.commit()

    today = date.today()
    for offset in range(7):
        shift_date = today + timedelta(days=offset)
        if shift_date.weekday() < 5:
            types = ["late_weekday", "night_weekday"]
        else:
            types = ["early_weekend", "night_weekend", "visite_weekend"]
        for stype in types:
            shift = Shift(date=shift_date, shift_type=stype)
            db.session.add(shift)
    db.session.commit()


def parse_args():
    parser = argparse.ArgumentParser(description="Duty planner webapp")
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Create database with sample users and shifts",
    )
    return parser.parse_args()


if __name__ == "__main__":
    _ensure_db_initialized()
    args = parse_args()
    if args.init_db:
        seed_sample_data()
        print("Database initialized with sample data")
    else:
        app.run(host="0.0.0.0", port=5000, debug=True)
