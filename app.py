"""Face Attendance System - Flask backend."""
import base64
import csv
import io
import json
import logging
import os
import uuid
from datetime import datetime, date, timedelta
from logging.handlers import RotatingFileHandler

import numpy as np
from flask import Flask, jsonify, render_template, request, Response, send_from_directory
from sqlalchemy import and_, or_
from sqlalchemy.orm import joinedload

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import face_recognition
except ImportError:
    face_recognition = None

from flask_sqlalchemy import SQLAlchemy

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "faces")
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

app = Flask(__name__, static_folder="static")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me-in-production")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'attendance.db')}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB

db = SQLAlchemy(app)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
log_fmt = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
file_handler = RotatingFileHandler(
    os.path.join(LOG_DIR, "app.log"), maxBytes=5 * 1024 * 1024, backupCount=5
)
file_handler.setFormatter(log_fmt)
file_handler.setLevel(logging.INFO)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(log_fmt)
stream_handler.setLevel(logging.INFO)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(file_handler)
root_logger.addHandler(stream_handler)
app.logger.setLevel(logging.INFO)

FACE_MATCH_THRESHOLD = 0.5


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response


@app.route("/api/<path:_any>", methods=["OPTIONS"])
def cors_preflight(_any):
    return ("", 204)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class Employee(db.Model):
    __tablename__ = "employees"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    employee_id = db.Column(db.String(64), unique=True, nullable=False)
    department = db.Column(db.String(120))
    role = db.Column(db.String(120))
    email = db.Column(db.String(255))
    phone = db.Column(db.String(64))
    photo_path = db.Column(db.String(255))
    encoding = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    attendance = db.relationship(
        "AttendanceRecord", backref="employee", cascade="all, delete-orphan"
    )
    leave_requests = db.relationship(
        "LeaveRequest", backref="employee", cascade="all, delete-orphan"
    )

    def to_dict(self, include_encoding=False):
        data = {
            "id": self.id,
            "name": self.name,
            "employee_id": self.employee_id,
            "department": self.department,
            "role": self.role,
            "email": self.email,
            "phone": self.phone,
            "photo_path": self.photo_path,
            "is_active": self.is_active,
            "has_face": bool(self.encoding),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_encoding:
            data["encoding"] = self.encoding
        return data


class AttendanceRecord(db.Model):
    __tablename__ = "attendance_records"
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False)
    date = db.Column(db.Date, nullable=False, index=True)
    check_in = db.Column(db.DateTime)
    check_out = db.Column(db.DateTime)
    status = db.Column(db.String(32), default="present")
    working_hours = db.Column(db.Float)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "employee_name": self.employee.name if self.employee else None,
            "employee_code": self.employee.employee_id if self.employee else None,
            "department": self.employee.department if self.employee else None,
            "date": self.date.isoformat() if self.date else None,
            "check_in": self.check_in.isoformat() if self.check_in else None,
            "check_out": self.check_out.isoformat() if self.check_out else None,
            "status": self.status,
            "working_hours": self.working_hours,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class LeaveRequest(db.Model):
    __tablename__ = "leave_requests"
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False)
    leave_type = db.Column(db.String(32), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text)
    status = db.Column(db.String(32), default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "employee_name": self.employee.name if self.employee else None,
            "leave_type": self.leave_type,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "reason": self.reason,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Holiday(db.Model):
    __tablename__ = "holidays"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    date = db.Column(db.Date, nullable=False, unique=True)
    description = db.Column(db.Text)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "date": self.date.isoformat() if self.date else None,
            "description": self.description,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_known_faces():
    """Return (encodings_array, employee_objects) for all active employees with face data."""
    employees = Employee.query.filter(
        Employee.is_active.is_(True), Employee.encoding.isnot(None)
    ).all()
    encodings = []
    valid = []
    for emp in employees:
        try:
            enc = np.array(json.loads(emp.encoding), dtype=np.float64)
            encodings.append(enc)
            valid.append(emp)
        except (ValueError, TypeError) as exc:
            app.logger.warning("Bad encoding for employee %s: %s", emp.id, exc)
    return encodings, valid


def decode_image(data_uri):
    """Decode a base64 data URI (or raw base64) into an OpenCV BGR ndarray."""
    if cv2 is None:
        raise RuntimeError("OpenCV (cv2) is not installed")
    if not data_uri:
        raise ValueError("No image data provided")
    if "," in data_uri:
        data_uri = data_uri.split(",", 1)[1]
    try:
        raw = base64.b64decode(data_uri)
    except Exception as exc:
        raise ValueError(f"Invalid base64 image: {exc}")
    arr = np.frombuffer(raw, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image bytes")
    return img


def bgr_to_rgb(img_bgr):
    if cv2 is None:
        return img_bgr
    return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)


def compute_working_hours(check_in, check_out):
    if not check_in or not check_out:
        return 0.0
    delta = check_out - check_in
    return round(delta.total_seconds() / 3600.0, 2)


def send_notification(employee, action):
    """Placeholder for email/webhook notification."""
    app.logger.info(
        "NOTIFY: employee=%s (%s) action=%s",
        employee.name,
        employee.employee_id,
        action,
    )


def get_date_range(start, end):
    """Return inclusive list of date objects between two YYYY-MM-DD strings."""
    s = datetime.strptime(start, "%Y-%m-%d").date() if isinstance(start, str) else start
    e = datetime.strptime(end, "%Y-%m-%d").date() if isinstance(end, str) else end
    if s > e:
        s, e = e, s
    return [s + timedelta(days=i) for i in range((e - s).days + 1)]


def parse_date(value, default=None):
    if not value:
        return default
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return default


def parse_datetime(value):
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def err(message, status=400):
    return jsonify({"error": message}), status


# ---------------------------------------------------------------------------
# Employee routes
# ---------------------------------------------------------------------------
@app.route("/api/employees", methods=["GET"])
def list_employees():
    q = Employee.query
    department = request.args.get("department")
    active = request.args.get("active")
    if department:
        q = q.filter(Employee.department == department)
    if active is not None:
        q = q.filter(Employee.is_active.is_(active.lower() in ("1", "true", "yes")))
    employees = q.order_by(Employee.name.asc()).all()
    return jsonify([e.to_dict() for e in employees])


@app.route("/api/employees", methods=["POST"])
def create_employee():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    emp_code = (data.get("employee_id") or "").strip()
    if not name or not emp_code:
        return err("name and employee_id are required")
    if Employee.query.filter_by(employee_id=emp_code).first():
        return err("employee_id already exists", 409)
    emp = Employee(
        name=name,
        employee_id=emp_code,
        department=data.get("department"),
        role=data.get("role"),
        email=data.get("email"),
        phone=data.get("phone"),
    )
    db.session.add(emp)
    db.session.commit()
    app.logger.info("Created employee %s (%s)", emp.name, emp.employee_id)
    return jsonify(emp.to_dict()), 201


@app.route("/api/employees/<int:emp_id>", methods=["GET"])
def get_employee(emp_id):
    emp = Employee.query.get(emp_id)
    if not emp:
        return err("Employee not found", 404)
    records = (
        AttendanceRecord.query.filter_by(employee_id=emp.id)
        .order_by(AttendanceRecord.date.desc())
        .limit(30)
        .all()
    )
    data = emp.to_dict()
    data["recent_records"] = [r.to_dict() for r in records]
    return jsonify(data)


@app.route("/api/employees/<int:emp_id>", methods=["PUT"])
def update_employee(emp_id):
    emp = Employee.query.get(emp_id)
    if not emp:
        return err("Employee not found", 404)
    data = request.get_json(silent=True) or {}
    for field in ("name", "department", "role", "email", "phone"):
        if field in data:
            setattr(emp, field, data[field])
    if "is_active" in data:
        emp.is_active = bool(data["is_active"])
    db.session.commit()
    return jsonify(emp.to_dict())


@app.route("/api/employees/<int:emp_id>", methods=["DELETE"])
def delete_employee(emp_id):
    emp = Employee.query.get(emp_id)
    if not emp:
        return err("Employee not found", 404)
    permanent = request.args.get("permanent", "").lower() in ("1", "true", "yes")
    if permanent:
        if emp.photo_path:
            try:
                full = os.path.join(BASE_DIR, emp.photo_path.lstrip("/"))
                if os.path.exists(full):
                    os.remove(full)
            except OSError as exc:
                app.logger.warning("Failed to delete photo: %s", exc)
        db.session.delete(emp)
        db.session.commit()
        return jsonify({"deleted": True, "permanent": True})
    emp.is_active = False
    db.session.commit()
    return jsonify({"deleted": True, "permanent": False})


# ---------------------------------------------------------------------------
# Face routes
# ---------------------------------------------------------------------------
def _detect_single_face(img_bgr):
    if face_recognition is None:
        raise RuntimeError("face_recognition library is not installed")
    rgb = bgr_to_rgb(img_bgr)
    locations = face_recognition.face_locations(rgb)
    if not locations:
        raise ValueError("No face detected")
    if len(locations) > 1:
        raise ValueError(f"Expected exactly 1 face, found {len(locations)}")
    encodings = face_recognition.face_encodings(rgb, known_face_locations=locations)
    if not encodings:
        raise ValueError("Could not extract face encoding")
    return locations[0], encodings[0]


def _save_face_crop(img_bgr, box, employee_code):
    top, right, bottom, left = box
    crop = img_bgr[max(0, top):bottom, max(0, left):right]
    filename = f"{employee_code}_{uuid.uuid4().hex[:8]}.jpg"
    full_path = os.path.join(UPLOAD_FOLDER, filename)
    cv2.imwrite(full_path, crop)
    return os.path.relpath(full_path, BASE_DIR).replace(os.sep, "/")


@app.route("/api/register-face", methods=["POST"])
def register_face():
    data = request.get_json(silent=True) or {}
    emp_id = data.get("employee_id") or data.get("id")
    image = data.get("image")
    if not emp_id or not image:
        return err("employee_id and image are required")
    emp = Employee.query.get(emp_id) if str(emp_id).isdigit() else Employee.query.filter_by(employee_id=str(emp_id)).first()
    if not emp:
        return err("Employee not found", 404)
    try:
        img = decode_image(image)
        box, encoding = _detect_single_face(img)
    except (ValueError, RuntimeError) as exc:
        return err(str(exc))
    except Exception as exc:
        app.logger.exception("register_face failed")
        return err(f"Face processing error: {exc}", 500)

    try:
        photo_path = _save_face_crop(img, box, emp.employee_id)
    except Exception as exc:
        app.logger.exception("Save crop failed")
        return err(f"Could not save photo: {exc}", 500)

    emp.encoding = json.dumps(encoding.tolist())
    emp.photo_path = photo_path
    db.session.commit()
    top, right, bottom, left = box
    return jsonify({
        "success": True,
        "employee": emp.to_dict(),
        "bounding_box": {"top": top, "right": right, "bottom": bottom, "left": left},
    })


@app.route("/api/register-face-multiple", methods=["POST"])
def register_face_multiple():
    data = request.get_json(silent=True) or {}
    emp_id = data.get("employee_id") or data.get("id")
    images = data.get("images") or []
    if not emp_id or not images:
        return err("employee_id and images[] are required")
    if len(images) > 5:
        return err("Maximum 5 images allowed")
    emp = Employee.query.get(emp_id) if str(emp_id).isdigit() else Employee.query.filter_by(employee_id=str(emp_id)).first()
    if not emp:
        return err("Employee not found", 404)

    encodings = []
    last_img = None
    last_box = None
    for idx, img_data in enumerate(images):
        try:
            img = decode_image(img_data)
            box, enc = _detect_single_face(img)
            encodings.append(enc)
            last_img = img
            last_box = box
        except (ValueError, RuntimeError) as exc:
            return err(f"Image {idx + 1}: {exc}")
        except Exception as exc:
            app.logger.exception("multi register failed")
            return err(f"Image {idx + 1}: {exc}", 500)

    avg = np.mean(np.array(encodings), axis=0)
    emp.encoding = json.dumps(avg.tolist())
    try:
        emp.photo_path = _save_face_crop(last_img, last_box, emp.employee_id)
    except Exception as exc:
        app.logger.warning("Failed to save crop: %s", exc)
    db.session.commit()
    return jsonify({
        "success": True,
        "employee": emp.to_dict(),
        "images_used": len(encodings),
    })


@app.route("/api/employees/<int:emp_id>/face", methods=["DELETE"])
def remove_face(emp_id):
    emp = Employee.query.get(emp_id)
    if not emp:
        return err("Employee not found", 404)
    if emp.photo_path:
        try:
            full = os.path.join(BASE_DIR, emp.photo_path.lstrip("/"))
            if os.path.exists(full):
                os.remove(full)
        except OSError as exc:
            app.logger.warning("Photo delete failed: %s", exc)
    emp.encoding = None
    emp.photo_path = None
    db.session.commit()
    return jsonify({"success": True, "employee": emp.to_dict()})


# ---------------------------------------------------------------------------
# Attendance routes
# ---------------------------------------------------------------------------
def _determine_status(check_in_dt):
    """Mark late if check-in past 09:00 local."""
    if not check_in_dt:
        return "absent"
    return "late" if check_in_dt.time() > datetime.strptime("09:00", "%H:%M").time() else "present"


@app.route("/api/recognize", methods=["POST"])
def recognize():
    if face_recognition is None:
        return err("face_recognition library unavailable", 503)
    data = request.get_json(silent=True) or {}
    image = data.get("image")
    if not image:
        return err("image is required")
    try:
        img = decode_image(image)
        rgb = bgr_to_rgb(img)
        locations = face_recognition.face_locations(rgb)
        encodings = face_recognition.face_encodings(rgb, known_face_locations=locations)
    except (ValueError, RuntimeError) as exc:
        return err(str(exc))
    except Exception as exc:
        app.logger.exception("recognize failed")
        return err(f"Face processing error: {exc}", 500)

    known_encs, known_emps = load_known_faces()
    if not known_encs:
        return jsonify({"results": [], "message": "No registered faces"})

    known_array = np.array(known_encs)
    today = date.today()
    now = datetime.utcnow()
    results = []
    seen_emp_ids = set()

    for face_enc, loc in zip(encodings, locations):
        distances = np.linalg.norm(known_array - face_enc, axis=1)
        best_idx = int(np.argmin(distances))
        best_dist = float(distances[best_idx])
        if best_dist > FACE_MATCH_THRESHOLD:
            top, right, bottom, left = loc
            results.append({
                "matched": False,
                "confidence": max(0.0, 1.0 - best_dist),
                "bounding_box": {"top": top, "right": right, "bottom": bottom, "left": left},
            })
            continue

        emp = known_emps[best_idx]
        if emp.id in seen_emp_ids:
            continue
        seen_emp_ids.add(emp.id)

        record = AttendanceRecord.query.filter_by(employee_id=emp.id, date=today).first()
        action = "skipped"
        if not record:
            record = AttendanceRecord(
                employee_id=emp.id,
                date=today,
                check_in=now,
                status=_determine_status(now),
            )
            db.session.add(record)
            action = "check_in"
            send_notification(emp, "check_in")
        elif record.check_in and not record.check_out:
            record.check_out = now
            record.working_hours = compute_working_hours(record.check_in, record.check_out)
            action = "check_out"
            send_notification(emp, "check_out")
        else:
            action = "already_complete"

        db.session.commit()
        top, right, bottom, left = loc
        results.append({
            "matched": True,
            "id": emp.id,
            "employee_id": emp.employee_id,
            "name": emp.name,
            "department": emp.department,
            "confidence": round(1.0 - best_dist, 4),
            "action": action,
            "time": now.isoformat(),
            "check_in": record.check_in.isoformat() if record.check_in else None,
            "check_out": record.check_out.isoformat() if record.check_out else None,
            "working_hours": record.working_hours,
            "status": record.status,
            "bounding_box": {"top": top, "right": right, "bottom": bottom, "left": left},
        })

    return jsonify({"results": results, "count": len(results)})


@app.route("/api/attendance", methods=["GET"])
def list_attendance():
    q = AttendanceRecord.query.options(joinedload(AttendanceRecord.employee))
    d = parse_date(request.args.get("date"))
    if d:
        q = q.filter(AttendanceRecord.date == d)
    emp_id = request.args.get("employee_id")
    if emp_id:
        q = q.filter(AttendanceRecord.employee_id == int(emp_id))
    status = request.args.get("status")
    if status:
        q = q.filter(AttendanceRecord.status == status)
    department = request.args.get("department")
    if department:
        q = q.join(Employee).filter(Employee.department == department)
    records = q.order_by(AttendanceRecord.date.desc(), AttendanceRecord.check_in.desc()).all()
    return jsonify([r.to_dict() for r in records])


@app.route("/api/attendance/manual", methods=["POST"])
def manual_attendance():
    data = request.get_json(silent=True) or {}
    emp_id = data.get("employee_id")
    d = parse_date(data.get("date"))
    if not emp_id or not d:
        return err("employee_id and date are required")
    emp = Employee.query.get(emp_id)
    if not emp:
        return err("Employee not found", 404)
    record = AttendanceRecord.query.filter_by(employee_id=emp.id, date=d).first()
    if not record:
        record = AttendanceRecord(employee_id=emp.id, date=d)
        db.session.add(record)
    record.check_in = parse_datetime(data.get("check_in")) or record.check_in
    record.check_out = parse_datetime(data.get("check_out")) or record.check_out
    record.status = data.get("status") or record.status or "present"
    record.notes = data.get("notes", record.notes)
    if record.check_in and record.check_out:
        record.working_hours = compute_working_hours(record.check_in, record.check_out)
    db.session.commit()
    return jsonify(record.to_dict()), 201


@app.route("/api/attendance/<int:rec_id>", methods=["PUT"])
def update_attendance(rec_id):
    record = AttendanceRecord.query.get(rec_id)
    if not record:
        return err("Record not found", 404)
    data = request.get_json(silent=True) or {}
    if "check_in" in data:
        record.check_in = parse_datetime(data["check_in"])
    if "check_out" in data:
        record.check_out = parse_datetime(data["check_out"])
    if "status" in data:
        record.status = data["status"]
    if "notes" in data:
        record.notes = data["notes"]
    if record.check_in and record.check_out:
        record.working_hours = compute_working_hours(record.check_in, record.check_out)
    db.session.commit()
    return jsonify(record.to_dict())


@app.route("/api/attendance/<int:rec_id>", methods=["DELETE"])
def delete_attendance(rec_id):
    record = AttendanceRecord.query.get(rec_id)
    if not record:
        return err("Record not found", 404)
    db.session.delete(record)
    db.session.commit()
    return jsonify({"deleted": True})


# ---------------------------------------------------------------------------
# Stats & reports
# ---------------------------------------------------------------------------
@app.route("/api/stats", methods=["GET"])
def stats_daily():
    d = parse_date(request.args.get("date"), default=date.today())
    total = Employee.query.filter_by(is_active=True).count()
    records = AttendanceRecord.query.filter_by(date=d).all()
    present = sum(1 for r in records if r.status == "present")
    late = sum(1 for r in records if r.status == "late")
    absent_count = total - len([r for r in records if r.status in ("present", "late")])
    leaves = LeaveRequest.query.filter(
        LeaveRequest.status == "approved",
        LeaveRequest.start_date <= d,
        LeaveRequest.end_date >= d,
    ).count()
    hrs = [r.working_hours for r in records if r.working_hours]
    avg_hours = round(sum(hrs) / len(hrs), 2) if hrs else 0.0
    return jsonify({
        "date": d.isoformat(),
        "total_employees": total,
        "present": present,
        "late": late,
        "absent": max(0, absent_count - leaves),
        "on_leave": leaves,
        "avg_working_hours": avg_hours,
    })


@app.route("/api/stats/monthly", methods=["GET"])
def stats_monthly():
    try:
        year = int(request.args.get("year") or date.today().year)
        month = int(request.args.get("month") or date.today().month)
    except ValueError:
        return err("Invalid year/month")
    first = date(year, month, 1)
    next_month = date(year + (month // 12), (month % 12) + 1, 1)
    last = next_month - timedelta(days=1)
    total = Employee.query.filter_by(is_active=True).count()
    records = AttendanceRecord.query.filter(
        AttendanceRecord.date >= first, AttendanceRecord.date <= last
    ).all()
    by_date = {}
    for r in records:
        by_date.setdefault(r.date, []).append(r)
    days = []
    for d in get_date_range(first, last):
        recs = by_date.get(d, [])
        present = sum(1 for r in recs if r.status == "present")
        late = sum(1 for r in recs if r.status == "late")
        absent_count = total - len([r for r in recs if r.status in ("present", "late")])
        days.append({
            "date": d.isoformat(),
            "present": present,
            "late": late,
            "absent": max(0, absent_count),
        })
    return jsonify({"year": year, "month": month, "days": days})


@app.route("/api/stats/employee/<int:emp_id>", methods=["GET"])
def stats_employee(emp_id):
    emp = Employee.query.get(emp_id)
    if not emp:
        return err("Employee not found", 404)
    start = parse_date(request.args.get("start"), default=date.today().replace(day=1))
    end = parse_date(request.args.get("end"), default=date.today())
    records = AttendanceRecord.query.filter(
        AttendanceRecord.employee_id == emp.id,
        AttendanceRecord.date >= start,
        AttendanceRecord.date <= end,
    ).all()
    total_days = len(get_date_range(start, end))
    present = sum(1 for r in records if r.status == "present")
    late = sum(1 for r in records if r.status == "late")
    attended = present + late
    absent = max(0, total_days - attended)
    hrs = [r.working_hours for r in records if r.working_hours]
    avg = round(sum(hrs) / len(hrs), 2) if hrs else 0.0
    punctuality = round((present / attended) * 100, 2) if attended else 0.0
    return jsonify({
        "employee": emp.to_dict(),
        "range": {"start": start.isoformat(), "end": end.isoformat()},
        "total_days": total_days,
        "present": present,
        "late": late,
        "absent": absent,
        "avg_working_hours": avg,
        "punctuality_rate": punctuality,
    })


@app.route("/api/attendance/export", methods=["GET"])
def export_attendance():
    start = parse_date(request.args.get("start"), default=date.today().replace(day=1))
    end = parse_date(request.args.get("end"), default=date.today())
    fmt = (request.args.get("format") or "csv").lower()
    records = (
        AttendanceRecord.query.options(joinedload(AttendanceRecord.employee))
        .filter(AttendanceRecord.date >= start, AttendanceRecord.date <= end)
        .order_by(AttendanceRecord.date.asc())
        .all()
    )
    if fmt == "json":
        return jsonify([r.to_dict() for r in records])

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "date", "employee_id", "employee_code", "name", "department",
        "check_in", "check_out", "status", "working_hours", "notes",
    ])
    for r in records:
        writer.writerow([
            r.date.isoformat() if r.date else "",
            r.employee_id,
            r.employee.employee_id if r.employee else "",
            r.employee.name if r.employee else "",
            r.employee.department if r.employee else "",
            r.check_in.isoformat() if r.check_in else "",
            r.check_out.isoformat() if r.check_out else "",
            r.status or "",
            r.working_hours if r.working_hours is not None else "",
            r.notes or "",
        ])
    csv_data = buf.getvalue()
    filename = f"attendance_{start.isoformat()}_{end.isoformat()}.csv"
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ---------------------------------------------------------------------------
# Leave routes
# ---------------------------------------------------------------------------
@app.route("/api/leave", methods=["GET"])
def list_leave():
    q = LeaveRequest.query.options(joinedload(LeaveRequest.employee))
    status = request.args.get("status")
    if status:
        q = q.filter(LeaveRequest.status == status)
    emp_id = request.args.get("employee_id")
    if emp_id:
        q = q.filter(LeaveRequest.employee_id == int(emp_id))
    rows = q.order_by(LeaveRequest.created_at.desc()).all()
    return jsonify([r.to_dict() for r in rows])


@app.route("/api/leave", methods=["POST"])
def create_leave():
    data = request.get_json(silent=True) or {}
    emp_id = data.get("employee_id")
    leave_type = data.get("leave_type")
    start = parse_date(data.get("start_date"))
    end = parse_date(data.get("end_date"))
    if not emp_id or not leave_type or not start or not end:
        return err("employee_id, leave_type, start_date, end_date required")
    if leave_type not in ("sick", "annual", "emergency"):
        return err("leave_type must be sick|annual|emergency")
    if not Employee.query.get(emp_id):
        return err("Employee not found", 404)
    lr = LeaveRequest(
        employee_id=emp_id,
        leave_type=leave_type,
        start_date=start,
        end_date=end,
        reason=data.get("reason"),
        status="pending",
    )
    db.session.add(lr)
    db.session.commit()
    return jsonify(lr.to_dict()), 201


@app.route("/api/leave/<int:leave_id>", methods=["PUT"])
def update_leave(leave_id):
    lr = LeaveRequest.query.get(leave_id)
    if not lr:
        return err("Leave request not found", 404)
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status not in ("approved", "rejected", "pending"):
        return err("status must be approved|rejected|pending")
    lr.status = status
    db.session.commit()
    return jsonify(lr.to_dict())


@app.route("/api/leave/<int:leave_id>", methods=["DELETE"])
def delete_leave(leave_id):
    lr = LeaveRequest.query.get(leave_id)
    if not lr:
        return err("Leave request not found", 404)
    if lr.status != "pending":
        return err("Only pending requests can be cancelled", 400)
    db.session.delete(lr)
    db.session.commit()
    return jsonify({"deleted": True})


# ---------------------------------------------------------------------------
# Holiday routes
# ---------------------------------------------------------------------------
@app.route("/api/holidays", methods=["GET"])
def list_holidays():
    q = Holiday.query
    year = request.args.get("year")
    if year:
        try:
            y = int(year)
            q = q.filter(Holiday.date >= date(y, 1, 1), Holiday.date <= date(y, 12, 31))
        except ValueError:
            return err("Invalid year")
    return jsonify([h.to_dict() for h in q.order_by(Holiday.date.asc()).all()])


@app.route("/api/holidays", methods=["POST"])
def create_holiday():
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    d = parse_date(data.get("date"))
    if not name or not d:
        return err("name and date required")
    if Holiday.query.filter_by(date=d).first():
        return err("Holiday already exists on that date", 409)
    h = Holiday(name=name, date=d, description=data.get("description"))
    db.session.add(h)
    db.session.commit()
    return jsonify(h.to_dict()), 201


@app.route("/api/holidays/<int:holiday_id>", methods=["DELETE"])
def delete_holiday(holiday_id):
    h = Holiday.query.get(holiday_id)
    if not h:
        return err("Holiday not found", 404)
    db.session.delete(h)
    db.session.commit()
    return jsonify({"deleted": True})


# ---------------------------------------------------------------------------
# Static photo serving
# ---------------------------------------------------------------------------
@app.route("/static/faces/<path:filename>")
def serve_face(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "time": datetime.utcnow().isoformat(),
        "face_recognition": face_recognition is not None,
        "opencv": cv2 is not None,
    })


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------
@app.errorhandler(404)
def not_found(_e):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def server_error(e):
    app.logger.exception("Unhandled 500: %s", e)
    return jsonify({"error": "Internal server error"}), 500


@app.errorhandler(413)
def too_large(_e):
    return jsonify({"error": "Payload too large (16MB max)"}), 413


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
def init_db():
    with app.app_context():
        db.create_all()
        if Holiday.query.count() == 0:
            year = date.today().year
            db.session.add(Holiday(
                name="New Year",
                date=date(year, 1, 1),
                description="New Year's Day",
            ))
            db.session.commit()
            app.logger.info("Seeded default holiday: New Year %d", year)


init_db()


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")
    app.logger.info("Starting Face Attendance System on 0.0.0.0:5000 (debug=%s)", debug)
    app.run(host="0.0.0.0", port=5000, debug=debug)
