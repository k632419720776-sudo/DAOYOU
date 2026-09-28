import argparse
import os
import uuid
import json
from datetime import datetime, timedelta
from functools import wraps

import qrcode
from flask import (
    Flask, abort, flash, jsonify, redirect, render_template,
    request, send_from_directory, session, url_for
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")

app = Flask(__name__, instance_relative_config=True)
TRANSLATIONS_DIR = os.path.join(BASE_DIR, "translations")

def load_translations(lang):
    path = os.path.join(TRANSLATIONS_DIR, f"{lang}.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        with open(os.path.join(TRANSLATIONS_DIR, "en.json"), "r", encoding="utf-8") as f:
            return json.load(f)


@app.context_processor
def inject_i18n():
    lang = session.get("lang", "en")
    if lang not in {"en", "vi"}:
        lang = "en"

    translations = load_translations(lang)

    def t(key):
        return translations.get(key, key)

    return {
        "lang": lang,
        "t": t
    }


@app.route("/language/<lang>")
def change_language(lang):
    if lang not in {"en", "vi"}:
        lang = "en"

    session["lang"] = lang

    next_url = request.args.get("next")

    if next_url and next_url.startswith("/"):
        return redirect(next_url)

    return redirect(request.referrer or url_for("index"))
app.config["SECRET_KEY"] = os.environ.get("DAOYOU_SECRET_KEY", "dev-secret-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "instance", "daoyou.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = UPLOAD_DIR
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024

db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="tourist", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    guide_profile = db.relationship("GuideProfile", backref="user", uselist=False, cascade="all, delete-orphan")
    bookings_as_tourist = db.relationship("Booking", foreign_keys="Booking.tourist_id", backref="tourist")
    bookings_as_guide = db.relationship("Booking", foreign_keys="Booking.guide_id", backref="guide")
    reviews_written = db.relationship("Review", foreign_keys="Review.tourist_id", backref="reviewer")


class GuideProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True, nullable=False)
    bio = db.Column(db.Text, default="")
    location = db.Column(db.String(120), default="Hanoi")
    languages = db.Column(db.String(300), default="English")
    specialties = db.Column(db.String(400), default="Culture")
    experience_years = db.Column(db.Integer, default=1)
    price = db.Column(db.Integer, default=1000000)
    guide_type = db.Column(db.String(30), default="Professional")
    certificate_file = db.Column(db.String(255))
    intro_video_file = db.Column(db.String(255))
    status = db.Column(db.String(30), default="pending")
    verified = db.Column(db.Boolean, default=False)
    rating = db.Column(db.Float, default=0.0)
    review_count = db.Column(db.Integer, default=0)
    available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(40), unique=True, nullable=False)
    tourist_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    guide_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    note = db.Column(db.Text, default="")
    base_price = db.Column(db.Integer, nullable=False)
    tourist_fee = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Integer, nullable=False)
    guide_fee = db.Column(db.Integer, nullable=False)
    guide_payout = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(30), default="awaiting_guide")
    payment_status = db.Column(db.String(30), default="unpaid")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    cancelled_at = db.Column(db.DateTime)

    review = db.relationship("Review", backref="booking", uselist=False, cascade="all, delete-orphan")


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("booking.id"), unique=True, nullable=False)
    tourist_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    guide_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SOSAlert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tourist_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    message = db.Column(db.String(500), default="Emergency assistance requested")
    status = db.Column(db.String(30), default="new")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    tourist = db.relationship("User", backref="sos_alerts")


def current_user():
    uid = session.get("user_id")
    return db.session.get(User, uid) if uid else None


@app.context_processor
def inject_globals():
    return {"current_user": current_user(), "now": datetime.utcnow()}


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user():
            flash("Vui lòng đăng nhập trước.", "warning")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapper


def role_required(role):
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user:
                flash("Vui lòng đăng nhập.", "warning")
                return redirect(url_for("login"))
            if user.role != role:
                abort(403)
            return view(*args, **kwargs)
        return wrapper
    return decorator


def parse_int(value, default=0):
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def save_upload(file_storage):
    if not file_storage or not file_storage.filename:
        return None
    allowed = {"pdf", "png", "jpg", "jpeg", "mp4", "mov"}
    ext = file_storage.filename.rsplit(".", 1)[-1].lower() if "." in file_storage.filename else ""
    if ext not in allowed:
        return None
    filename = secure_filename(f"{uuid.uuid4().hex}.{ext}")
    file_storage.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
    return filename


def seed_data():
    db.create_all()
    if User.query.filter_by(email="admin@daoyou.local").first():
        return

    admin = User(
        name="DAOYOU Admin",
        email="admin@daoyou.local",
        password_hash=generate_password_hash("Admin@123"),
        role="admin"
    )
    tourist = User(
        name="Alex Tourist",
        email="tourist@daoyou.local",
        password_hash=generate_password_hash("Tourist@123"),
        role="tourist"
    )
    guide1 = User(
        name="Minh Nguyen",
        email="guide@daoyou.local",
        password_hash=generate_password_hash("Guide@123"),
        role="guide"
    )
    guide2 = User(
        name="Linh Tran",
        email="guide2@daoyou.local",
        password_hash=generate_password_hash("Guide@123"),
        role="guide"
    )
    db.session.add_all([admin, tourist, guide1, guide2])
    db.session.flush()

    profiles = [
        GuideProfile(
            user_id=guide1.id, bio="Local guide specializing in street food, history and hidden corners of Hanoi.",
            location="Hanoi", languages="English,Vietnamese", specialties="Food,History,Photography",
            experience_years=6, price=1000000, guide_type="Professional",
            status="approved", verified=True, rating=4.9, review_count=24
        ),
        GuideProfile(
            user_id=guide2.id, bio="Friendly local friend for culture, cafes, shopping and photography.",
            location="Hoi An", languages="English,French,Vietnamese", specialties="Culture,Cafe,Shopping",
            experience_years=3, price=800000, guide_type="Local Friend",
            status="approved", verified=True, rating=4.7, review_count=15
        )
    ]
    db.session.add_all(profiles)
    db.session.commit()


@app.route("/")
def index():
    guides = (
        GuideProfile.query
        .filter_by(status="approved", available=True)
        .order_by(GuideProfile.rating.desc())
        .limit(6).all()
    )
    return render_template("index.html", guides=guides)


@app.route("/guides")
def guides():
    q = request.args.get("q", "").strip()
    location = request.args.get("location", "").strip()
    language = request.args.get("language", "").strip()
    specialty = request.args.get("specialty", "").strip()
    min_rating = float(request.args.get("min_rating", 0) or 0)
    max_price = parse_int(request.args.get("max_price"), 0)

    query = GuideProfile.query.filter_by(status="approved", available=True)
    if q:
        query = query.join(User).filter(
            or_(
                User.name.ilike(f"%{q}%"),
                GuideProfile.location.ilike(f"%{q}%"),
                GuideProfile.specialties.ilike(f"%{q}%"),
                GuideProfile.languages.ilike(f"%{q}%")
            )
        )
    if location:
        query = query.filter(GuideProfile.location.ilike(f"%{location}%"))
    if language:
        query = query.filter(GuideProfile.languages.ilike(f"%{language}%"))
    if specialty:
        query = query.filter(GuideProfile.specialties.ilike(f"%{specialty}%"))
    if min_rating:
        query = query.filter(GuideProfile.rating >= min_rating)
    if max_price:
        query = query.filter(GuideProfile.price <= max_price)

    return render_template("guides.html", guides=query.order_by(GuideProfile.rating.desc()).all())


@app.route("/guide/<int:guide_id>")
def guide_detail(guide_id):
    profile = db.session.get(GuideProfile, guide_id) or abort(404)
    reviews = (
        Review.query.filter_by(guide_id=profile.user_id)
        .order_by(Review.created_at.desc()).all()
    )
    return render_template("guide_detail.html", profile=profile, reviews=reviews)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "tourist")
        if role not in {"tourist", "guide"}:
            role = "tourist"
        if not name or not email or len(password) < 6:
            flash("Hãy nhập đủ thông tin và mật khẩu tối thiểu 6 ký tự.", "danger")
            return render_template("register.html")
        if User.query.filter_by(email=email).first():
            flash("Email đã tồn tại.", "danger")
            return render_template("register.html")

        user = User(name=name, email=email, password_hash=generate_password_hash(password), role=role)
        db.session.add(user)
        db.session.flush()
        if role == "guide":
            db.session.add(GuideProfile(user_id=user.id, status="pending"))
        db.session.commit()
        flash("Tạo tài khoản thành công. Hãy đăng nhập.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            flash(f"Xin chào {user.name}!", "success")
            return redirect(request.args.get("next") or url_for("index"))
        flash("Email hoặc mật khẩu không đúng.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Bạn đã đăng xuất.", "info")
    return redirect(url_for("index"))


@app.route("/become-guide", methods=["GET", "POST"])
@login_required
def become_guide():
    user = current_user()
    if user.role == "admin":
        abort(403)
    profile = user.guide_profile or GuideProfile(user_id=user.id, status="pending")
    if request.method == "POST":
        user.role = "guide"
        profile.bio = request.form.get("bio", "")
        profile.location = request.form.get("location", "Hanoi")
        profile.languages = request.form.get("languages", "")
        profile.specialties = request.form.get("specialties", "")
        profile.experience_years = parse_int(request.form.get("experience_years"), 1)
        profile.price = parse_int(request.form.get("price"), 1000000)
        profile.guide_type = request.form.get("guide_type", "Professional")
        profile.certificate_file = save_upload(request.files.get("certificate"))
        profile.intro_video_file = save_upload(request.files.get("intro_video"))
        profile.status = "pending"
        profile.verified = False
        if not profile.id:
            db.session.add(profile)
        db.session.commit()
        flash("Hồ sơ đã gửi và đang chờ Admin kiểm duyệt.", "success")
        return redirect(url_for("guide_dashboard"))
    return render_template("become_guide.html", profile=profile)


@app.route("/book/<int:guide_id>", methods=["GET", "POST"])
@login_required
def book(guide_id):
    profile = db.session.get(GuideProfile, guide_id) or abort(404)
    if profile.status != "approved":
        abort(400)
    if current_user().id == profile.user_id:
        abort(403)
    if request.method == "POST":
        raw = request.form.get("start_time", "")
        try:
            start_time = datetime.fromisoformat(raw)
        except ValueError:
            flash("Thời gian không hợp lệ.", "danger")
            return render_template("book.html", profile=profile)

        base = profile.price
        tourist_fee = round(base * 0.10)
        total = base + tourist_fee
        guide_fee = round(base * 0.10)
        guide_payout = base - guide_fee
        order_id = "DY" + datetime.utcnow().strftime("%Y%m%d%H%M%S") + uuid.uuid4().hex[:6].upper()

        booking = Booking(
            order_id=order_id,
            tourist_id=current_user().id,
            guide_id=profile.user_id,
            start_time=start_time,
            location=request.form.get("location", profile.location),
            note=request.form.get("note", ""),
            base_price=base,
            tourist_fee=tourist_fee,
            total_price=total,
            guide_fee=guide_fee,
            guide_payout=guide_payout,
            status="awaiting_guide",
            payment_status="unpaid"
        )
        db.session.add(booking)
        db.session.commit()
        return redirect(url_for("payment", booking_id=booking.id))
    return render_template("book.html", profile=profile)


@app.route("/payment/<int:booking_id>")
@login_required
def payment(booking_id):
    booking = db.session.get(Booking, booking_id) or abort(404)
    if booking.tourist_id != current_user().id and current_user().role != "admin":
        abort(403)

    payload = f"DAOYOU|{booking.order_id}|{booking.total_price}|VND"
    qr_filename = f"qr_{booking.order_id}.png"
    qr_path = os.path.join(app.config["UPLOAD_FOLDER"], qr_filename)
    if not os.path.exists(qr_path):
        qrcode.make(payload).save(qr_path)

    expires_at = booking.created_at + timedelta(minutes=20)
    return render_template("payment.html", booking=booking, expires_at=expires_at, qr_filename=qr_filename)


@app.post("/payment/<int:booking_id>/demo-confirm")
@login_required
def demo_confirm_payment(booking_id):
    booking = db.session.get(Booking, booking_id) or abort(404)
    if booking.tourist_id != current_user().id:
        abort(403)
    booking.payment_status = "paid_escrow"
    booking.paid_at = datetime.utcnow()
    db.session.commit()
    flash("Demo payment thành công. Tiền đang ở trạng thái Escrow.", "success")
    return redirect(url_for("tourist_dashboard"))


@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    if user.role == "admin":
        return redirect(url_for("admin_dashboard"))
    if user.role == "guide":
        return redirect(url_for("guide_dashboard"))
    return redirect(url_for("tourist_dashboard"))


@app.route("/dashboard/tourist")
@role_required("tourist")
def tourist_dashboard():
    bookings = Booking.query.filter_by(tourist_id=current_user().id).order_by(Booking.created_at.desc()).all()
    return render_template("tourist_dashboard.html", bookings=bookings)


@app.post("/booking/<int:booking_id>/cancel")
@login_required
def cancel_booking(booking_id):
    booking = db.session.get(Booking, booking_id) or abort(404)
    if current_user().id not in {booking.tourist_id, booking.guide_id} and current_user().role != "admin":
        abort(403)
    if booking.status in {"completed", "cancelled"}:
        flash("Đơn này không thể hủy.", "warning")
        return redirect(url_for("dashboard"))

    booking.status = "cancelled"
    booking.cancelled_at = datetime.utcnow()
    db.session.commit()
    flash("Booking đã được hủy. Bản demo chưa thực hiện hoàn tiền thật.", "info")
    return redirect(url_for("dashboard"))


@app.route("/dashboard/guide")
@role_required("guide")
def guide_dashboard():
    profile = current_user().guide_profile
    bookings = Booking.query.filter_by(guide_id=current_user().id).order_by(Booking.created_at.desc()).all()
    return render_template("guide_dashboard.html", profile=profile, bookings=bookings)


@app.post("/booking/<int:booking_id>/guide-action")
@role_required("guide")
def guide_action(booking_id):
    booking = db.session.get(Booking, booking_id) or abort(404)
    if booking.guide_id != current_user().id:
        abort(403)
    action = request.form.get("action")
    if action == "accept":
        booking.status = "confirmed"
    elif action == "reject":
        booking.status = "cancelled"
    elif action == "complete":
        booking.status = "completed"
        booking.completed_at = datetime.utcnow()
        booking.payment_status = "released"
    db.session.commit()
    flash("Đã cập nhật trạng thái booking.", "success")
    return redirect(url_for("guide_dashboard"))


@app.post("/review/<int:booking_id>")
@role_required("tourist")
def add_review(booking_id):
    booking = db.session.get(Booking, booking_id) or abort(404)
    if booking.tourist_id != current_user().id or booking.status != "completed":
        abort(403)
    if booking.review:
        flash("Booking này đã có review.", "warning")
        return redirect(url_for("tourist_dashboard"))

    rating = max(1, min(5, parse_int(request.form.get("rating"), 5)))
    review = Review(
        booking_id=booking.id, tourist_id=current_user().id,
        guide_id=booking.guide_id, rating=rating,
        comment=request.form.get("comment", "")
    )
    db.session.add(review)

    profile = GuideProfile.query.filter_by(user_id=booking.guide_id).first()
    if profile:
        old_total = profile.rating * profile.review_count
        profile.review_count += 1
        profile.rating = round((old_total + rating) / profile.review_count, 2)
    db.session.commit()
    flash("Cảm ơn bạn đã đánh giá.", "success")
    return redirect(url_for("tourist_dashboard"))


@app.route("/admin")
@role_required("admin")
def admin_dashboard():
    pending = GuideProfile.query.filter_by(status="pending").order_by(GuideProfile.created_at.desc()).all()
    alerts = SOSAlert.query.order_by(SOSAlert.created_at.desc()).limit(20).all()
    booking_count = Booking.query.count()
    revenue = sum(b.tourist_fee + b.guide_fee for b in Booking.query.all())
    completed = Booking.query.filter_by(status="completed").count()
    cancelled = Booking.query.filter_by(status="cancelled").count()
    return render_template(
        "admin_dashboard.html",
        pending=pending, alerts=alerts,
        booking_count=booking_count, revenue=revenue,
        completed=completed, cancelled=cancelled
    )


@app.post("/admin/guide/<int:profile_id>/decision")
@role_required("admin")
def guide_decision(profile_id):
    profile = db.session.get(GuideProfile, profile_id) or abort(404)
    decision = request.form.get("decision")
    if decision == "approve":
        profile.status = "approved"
        profile.verified = True
    else:
        profile.status = "rejected"
        profile.verified = False
    db.session.commit()
    flash("Đã cập nhật kết quả kiểm duyệt.", "success")
    return redirect(url_for("admin_dashboard"))


@app.post("/sos")
@login_required
def sos():
    data = request.get_json(silent=True) or request.form
    alert = SOSAlert(
        tourist_id=current_user().id,
        latitude=float(data.get("latitude")) if data.get("latitude") else None,
        longitude=float(data.get("longitude")) if data.get("longitude") else None,
        message=data.get("message", "Emergency assistance requested")
    )
    db.session.add(alert)
    db.session.commit()
    return jsonify({"ok": True, "message": "SOS đã được ghi nhận. Admin có thể xem cảnh báo."})


@app.post("/admin/sos/<int:alert_id>/resolve")
@role_required("admin")
def resolve_sos(alert_id):
    alert = db.session.get(SOSAlert, alert_id) or abort(404)
    alert.status = "resolved"
    db.session.commit()
    return redirect(url_for("admin_dashboard"))


@app.route("/uploads/<path:filename>")
@login_required
def uploads(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/health")
def health():
    return jsonify({"status": "ok", "app": "DAOYOU"})


with app.app_context():
    os.makedirs(os.path.join(BASE_DIR, "instance"), exist_ok=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    db.create_all()
    # For the public classroom/demo deployment, Render can set SEED_DEMO=true.
    # This creates the demo accounts automatically on a fresh database.
    if os.environ.get("SEED_DEMO", "false").lower() == "true":
        seed_data()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", action="store_true", help="Create demo accounts/data")
    args = parser.parse_args()
    if args.seed:
        with app.app_context():
            seed_data()
            print("Demo data created.")
    port = int(os.environ.get("PORT", "5000"))
    host = os.environ.get("HOST", "127.0.0.1")
    app.run(debug=True, host=host, port=port)
