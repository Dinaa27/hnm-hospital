import functools
import os
from datetime import datetime
from flask import Flask, jsonify, request, session, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash

from db import get_db, init_db

app = Flask(__name__, static_folder="static")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "hnm-hospital-vibrant-secret-key-2026")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


# Initialize database on startup
with app.app_context():
    init_db()


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if "user" not in session:
            return jsonify({"error": "Authentication required. Please log in."}), 401
        return view(**kwargs)
    return wrapped_view


def staff_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if "user" not in session:
            return jsonify({"error": "Authentication required."}), 401
        if session.get("role") != "staff":
            return jsonify({"error": "Staff access required. Patient accounts do not have permission."}), 403
        return view(**kwargs)
    return wrapped_view


# Static routes
@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/<path:path>")
def static_proxy(path):
    if os.path.exists(os.path.join("static", path)):
        return send_from_directory("static", path)
    return send_from_directory("static", "index.html")


# ================= AUTHENTICATION (NO OTP) =================

@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip().lower()
    password = (data.get("password") or "").strip()
    role = (data.get("role") or "patient").strip().lower()
    name = (data.get("name") or "").strip()
    mobile = (data.get("mobile_no") or "").strip()

    if not username or len(username) < 3:
        return jsonify({"error": "Username must be at least 3 characters long"}), 400
    if not password or len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters long"}), 400
    if role not in ["staff", "patient"]:
        return jsonify({"error": "Role must be either 'staff' or 'patient'"}), 400

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT USERNAME FROM USER_DATA WHERE USERNAME = ?", (username,))
    if cursor.fetchone():
        conn.close()
        return jsonify({"error": "Username already taken. Please choose another."}), 409

    hashed_pw = generate_password_hash(password)
    cursor.execute(
        "INSERT INTO USER_DATA (USERNAME, PASSWORD, ROLE, NAME, MOBILE_NO) VALUES (?, ?, ?, ?, ?)",
        (username, hashed_pw, role, name or username.capitalize(), mobile),
    )

    # Automatically create patient record if registering as patient
    if role == "patient":
        cursor.execute("SELECT COUNT(*) FROM PATIENTS")
        count = cursor.fetchone()[0] + 1
        pid = f"PAT{count:03d}"
        bill_no = f"BILL-{1000 + count}"
        cursor.execute(
            "INSERT INTO PATIENTS (PID, NAME, ISSUE, AGE, GENDER, FEES, MOBILE_NO, BILL_NO, USERNAME) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (pid, name or username.capitalize(), "Registered Online Patient", 30, "Not Specified", 0.0, mobile, bill_no, username),
        )

    conn.commit()
    conn.close()

    # Automatically set user session
    session["user"] = username
    session["role"] = role
    session["name"] = name or username.capitalize()

    return jsonify({
        "message": f"Account successfully created as {role.upper()}!",
        "user": {
            "username": username,
            "role": role,
            "name": name or username.capitalize()
        }
    }), 201


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip().lower()
    password = (data.get("password") or "").strip()

    if not username or not password:
        return jsonify({"error": "Please enter both username and password"}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT USERNAME, PASSWORD, ROLE, NAME, MOBILE_NO FROM USER_DATA WHERE USERNAME = ?", (username,))
    row = cursor.fetchone()
    conn.close()

    if not row or not check_password_hash(row["PASSWORD"], password):
        return jsonify({"error": "Invalid username or password"}), 401

    session["user"] = row["USERNAME"]
    session["role"] = row["ROLE"]
    session["name"] = row["NAME"] or row["USERNAME"]

    return jsonify({
        "message": "Login successful",
        "user": {
            "username": row["USERNAME"],
            "role": row["ROLE"],
            "name": row["NAME"] or row["USERNAME"],
            "mobile_no": row["MOBILE_NO"]
        }
    })


@app.route("/api/auth/me", methods=["GET"])
def get_current_user():
    if "user" not in session:
        return jsonify({"authenticated": False}), 200

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT USERNAME, ROLE, NAME, MOBILE_NO FROM USER_DATA WHERE USERNAME = ?", (session["user"],))
    user_row = cursor.fetchone()

    patient_profile = None
    if user_row and user_row["ROLE"] == "patient":
        cursor.execute("SELECT * FROM PATIENTS WHERE USERNAME = ? OR MOBILE_NO = ?", (user_row["USERNAME"], user_row["MOBILE_NO"]))
        p_row = cursor.fetchone()
        if p_row:
            patient_profile = dict(p_row)

    conn.close()

    if not user_row:
        session.clear()
        return jsonify({"authenticated": False}), 200

    return jsonify({
        "authenticated": True,
        "user": {
            "username": user_row["USERNAME"],
            "role": user_row["ROLE"],
            "name": user_row["NAME"] or user_row["USERNAME"],
            "mobile_no": user_row["MOBILE_NO"],
            "patient_profile": patient_profile
        }
    })


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully"})


# ================= DASHBOARD METRICS =================

@app.route("/api/dashboard/stats", methods=["GET"])
@login_required
def get_stats():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM EMPLOYEES")
    employees_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM PATIENTS")
    patients_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM EMT WHERE VNO IN (SELECT VNO FROM EMT_STATUS WHERE STATUS = 'Available')")
    available_ambulances = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM PHARMACY WHERE STOCK < 50")
    low_stock_medicines = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM CONSULTATION WHERE STATUS = 'Scheduled'")
    scheduled_consultations = cursor.fetchone()[0]

    conn.close()

    return jsonify({
        "employees": employees_count,
        "patients": patients_count,
        "available_ambulances": available_ambulances,
        "low_stock_medicines": low_stock_medicines,
        "scheduled_consultations": scheduled_consultations,
        "current_user_role": session.get("role")
    })


# ================= EMPLOYEES =================

@app.route("/api/employees", methods=["GET"])
@login_required
def get_employees():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM EMPLOYEES ORDER BY EID ASC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify(rows)


@app.route("/api/employees", methods=["POST"])
@staff_required
def add_employee():
    data = request.get_json() or {}
    eid = data.get("EID", "").strip().upper()
    name = data.get("NAME", "").strip()
    dept = data.get("DEPARTMENT", "").strip()
    age = data.get("AGE")
    gender = data.get("GENDER", "").strip()
    salary = data.get("SALARY", 0.0)
    mobile = data.get("MOBILE_NO", "").strip()

    if not eid or not name or not dept:
        return jsonify({"error": "EID, Name, and Department are required"}), 400

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO EMPLOYEES (EID, NAME, DEPARTMENT, AGE, GENDER, SALARY, MOBILE_NO) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (eid, name, dept, age, gender, salary, mobile),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": f"Employee ID {eid} already exists"}), 409

    conn.close()
    return jsonify({"message": f"Employee {name} added successfully", "EID": eid}), 201


@app.route("/api/employees/<eid>", methods=["DELETE"])
@staff_required
def delete_employee(eid):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM CONSULTATION WHERE EMP_ID = ?", (eid,))
    if cursor.fetchone()[0] > 0:
        conn.close()
        return jsonify({"error": "Cannot delete doctor/employee with existing consultations"}), 400

    cursor.execute("DELETE FROM EMPLOYEES WHERE EID = ?", (eid,))
    conn.commit()
    conn.close()
    return jsonify({"message": f"Employee {eid} removed successfully"})


# ================= PATIENTS =================

@app.route("/api/patients", methods=["GET"])
@login_required
def get_patients():
    conn = get_db()
    cursor = conn.cursor()
    
    if session.get("role") == "patient":
        cursor.execute("SELECT * FROM PATIENTS WHERE USERNAME = ? OR MOBILE_NO = (SELECT MOBILE_NO FROM USER_DATA WHERE USERNAME = ?)", (session["user"], session["user"]))
    else:
        cursor.execute("SELECT * FROM PATIENTS ORDER BY PID ASC")
        
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify(rows)


@app.route("/api/patients", methods=["POST"])
@login_required
def add_patient():
    data = request.get_json() or {}
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM PATIENTS")
    next_idx = cursor.fetchone()[0] + 1
    pid = data.get("PID") or f"PAT{next_idx:03d}"
    bill_no = data.get("BILL_NO") or f"BILL-{1000 + next_idx}"
    name = data.get("NAME", "").strip()
    issue = data.get("ISSUE", "").strip()
    age = data.get("AGE")
    gender = data.get("GENDER", "Not Specified")
    fees = data.get("FEES", 0.0)
    mobile = data.get("MOBILE_NO", "").strip()
    username = session.get("user") if session.get("role") == "patient" else data.get("USERNAME")

    if not name:
        conn.close()
        return jsonify({"error": "Patient name is required"}), 400

    try:
        cursor.execute(
            "INSERT INTO PATIENTS (PID, NAME, ISSUE, AGE, GENDER, FEES, MOBILE_NO, BILL_NO, USERNAME) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (pid, name, issue, age, gender, fees, mobile, bill_no, username),
        )
        conn.commit()
    except sqlite3.IntegrityError as e:
        conn.close()
        return jsonify({"error": "Patient ID or Bill No duplicate error: " + str(e)}), 409

    conn.close()
    return jsonify({"message": f"Patient record created with ID {pid}", "PID": pid}), 201


@app.route("/api/patients/<pid>", methods=["DELETE"])
@staff_required
def delete_patient(pid):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM CONSULTATION WHERE PATIENT_ID = ?", (pid,))
    if cursor.fetchone()[0] > 0:
        conn.close()
        return jsonify({"error": "Cannot delete patient who has consultation history."}), 400

    cursor.execute("DELETE FROM PATIENTS WHERE PID = ?", (pid,))
    conn.commit()
    conn.close()
    return jsonify({"message": f"Patient {pid} deleted"})


# ================= EMT / AMBULANCE =================

@app.route("/api/emt", methods=["GET"])
@login_required
def get_emt():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT E.VNO, E.VTYPE, E.DRIVER_NAME, E.MOBILE_NO, COALESCE(S.STATUS, 'Available') AS STATUS
        FROM EMT E
        LEFT JOIN EMT_STATUS S ON E.VNO = S.VNO
        ORDER BY E.VNO ASC
    """
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify(rows)


@app.route("/api/emt", methods=["POST"])
@staff_required
def add_emt():
    data = request.get_json() or {}
    vno = data.get("VNO", "").strip().upper()
    vtype = data.get("VTYPE", "").strip()
    driver = data.get("DRIVER_NAME", "").strip()
    mobile = data.get("MOBILE_NO", "").strip()
    status = data.get("STATUS", "Available")

    if not vno or not driver:
        return jsonify({"error": "Vehicle No and Driver Name are required"}), 400

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO EMT (VNO, VTYPE, DRIVER_NAME, MOBILE_NO) VALUES (?, ?, ?, ?)", (vno, vtype, driver, mobile))
        cursor.execute("INSERT OR REPLACE INTO EMT_STATUS (VNO, STATUS) VALUES (?, ?)", (vno, status))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": f"Ambulance {vno} already registered"}), 409

    conn.close()
    return jsonify({"message": f"Ambulance {vno} added successfully"}), 201


@app.route("/api/emt/<vno>/status", methods=["PATCH"])
@staff_required
def update_emt_status(vno):
    data = request.get_json() or {}
    status = data.get("STATUS")
    if status not in ["Available", "Dispatched", "Maintenance"]:
        return jsonify({"error": "Invalid status"}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO EMT_STATUS (VNO, STATUS) VALUES (?, ?)", (vno, status))
    conn.commit()
    conn.close()
    return jsonify({"message": f"Ambulance {vno} status updated to {status}"})


# ================= PHARMACY =================

@app.route("/api/pharmacy", methods=["GET"])
@login_required
def get_pharmacy():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM PHARMACY ORDER BY MEDICINE_NAME ASC")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify(rows)


@app.route("/api/pharmacy", methods=["POST"])
@staff_required
def add_medicine():
    data = request.get_json() or {}
    name = data.get("MEDICINE_NAME", "").strip()
    mtype = data.get("MEDICINE_TYPE", "").strip()
    stock = int(data.get("STOCK", 0))
    price = float(data.get("PRICE", 0.0))

    if not name or not mtype:
        return jsonify({"error": "Medicine Name and Type are required"}), 400

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO PHARMACY (MEDICINE_NAME, MEDICINE_TYPE, STOCK, PRICE) VALUES (?, ?, ?, ?)",
            (name, mtype, stock, price),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": f"Medicine {name} already exists. Update stock instead."}), 409

    conn.close()
    return jsonify({"message": f"Medicine {name} added to pharmacy inventory"}), 201


@app.route("/api/pharmacy/<medicine_name>", methods=["PATCH"])
@staff_required
def update_stock(medicine_name):
    data = request.get_json() or {}
    stock = data.get("STOCK")
    price = data.get("PRICE")

    conn = get_db()
    cursor = conn.cursor()
    if stock is not None:
        cursor.execute("UPDATE PHARMACY SET STOCK = ? WHERE MEDICINE_NAME = ?", (int(stock), medicine_name))
    if price is not None:
        cursor.execute("UPDATE PHARMACY SET PRICE = ? WHERE MEDICINE_NAME = ?", (float(price), medicine_name))
    conn.commit()
    conn.close()
    return jsonify({"message": f"Updated {medicine_name}"})


# ================= CONSULTATIONS =================

@app.route("/api/consultations", methods=["GET"])
@login_required
def get_consultations():
    conn = get_db()
    cursor = conn.cursor()

    query = """
        SELECT C.*, P.NAME AS PATIENT_NAME, E.NAME AS DOCTOR_NAME, E.DEPARTMENT
        FROM CONSULTATION C
        JOIN PATIENTS P ON C.PATIENT_ID = P.PID
        JOIN EMPLOYEES E ON C.EMP_ID = E.EID
    """
    params = []

    if session.get("role") == "patient":
        query += " WHERE P.USERNAME = ? OR P.MOBILE_NO = (SELECT MOBILE_NO FROM USER_DATA WHERE USERNAME = ?)"
        params = [session["user"], session["user"]]

    query += " ORDER BY C.TIME DESC"
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify(rows)


@app.route("/api/consultations", methods=["POST"])
@login_required
def book_consultation():
    data = request.get_json() or {}
    patient_id = data.get("PATIENT_ID")
    emp_id = data.get("EMP_ID")
    reason = data.get("REASON", "General Checkup")
    fees = data.get("FEES", 500.0)
    time = data.get("TIME") or datetime.now().strftime("%Y-%m-%d %H:%M")

    conn = get_db()
    cursor = conn.cursor()

    if session.get("role") == "patient":
        cursor.execute("SELECT PID FROM PATIENTS WHERE USERNAME = ?", (session["user"],))
        p_row = cursor.fetchone()
        if p_row:
            patient_id = p_row["PID"]
        else:
            return jsonify({"error": "No patient profile associated with this account. Please add your profile first."}), 400

    if not patient_id or not emp_id:
        conn.close()
        return jsonify({"error": "Patient ID and Doctor ID are required"}), 400

    cursor.execute("SELECT COUNT(*) FROM CONSULTATION")
    next_idx = cursor.fetchone()[0] + 1
    cid = f"CON-{next_idx:03d}"

    cursor.execute(
        "INSERT INTO CONSULTATION (CONSULTATION_ID, PATIENT_ID, EMP_ID, REASON, FEES, TIME, STATUS) VALUES (?, ?, ?, ?, ?, ?, 'Scheduled')",
        (cid, patient_id, emp_id, reason, fees, time),
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Consultation scheduled successfully", "CONSULTATION_ID": cid}), 201


# ================= PRESCRIPTIONS =================

@app.route("/api/prescriptions", methods=["GET"])
@login_required
def get_prescriptions():
    conn = get_db()
    cursor = conn.cursor()

    query = """
        SELECT PR.PRESCRIPTION_ID, PR.CONSULTATION_ID, PR.DATE, PR.DIAGNOSIS, PR.INSTRUCTIONS,
               P.NAME AS PATIENT_NAME, P.PID AS PATIENT_ID, E.NAME AS DOCTOR_NAME
        FROM PRESCRIPTION PR
        JOIN CONSULTATION C ON PR.CONSULTATION_ID = C.CONSULTATION_ID
        JOIN PATIENTS P ON C.PATIENT_ID = P.PID
        JOIN EMPLOYEES E ON C.EMP_ID = E.EID
    """
    params = []
    if session.get("role") == "patient":
        query += " WHERE P.USERNAME = ? OR P.MOBILE_NO = (SELECT MOBILE_NO FROM USER_DATA WHERE USERNAME = ?)"
        params = [session["user"], session["user"]]

    query += " ORDER BY PR.DATE DESC"
    cursor.execute(query, params)
    prescriptions = [dict(r) for r in cursor.fetchall()]

    for pres in prescriptions:
        cursor.execute("SELECT * FROM PRESCRIBED_MEDICINE WHERE PRESCRIPTION_ID = ?", (pres["PRESCRIPTION_ID"],))
        pres["medicines"] = [dict(m) for m in cursor.fetchall()]

    conn.close()
    return jsonify(prescriptions)


@app.route("/api/prescriptions", methods=["POST"])
@staff_required
def create_prescription():
    data = request.get_json() or {}
    consultation_id = data.get("CONSULTATION_ID")
    diagnosis = data.get("DIAGNOSIS", "")
    instructions = data.get("INSTRUCTIONS", "")
    medicines = data.get("MEDICINES", [])
    date_str = datetime.now().strftime("%Y-%m-%d")

    if not consultation_id:
        return jsonify({"error": "Consultation ID is required"}), 400

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM PRESCRIPTION")
    next_idx = cursor.fetchone()[0] + 1
    pres_id = f"RX-{next_idx:03d}"

    try:
        cursor.execute(
            "INSERT INTO PRESCRIPTION (PRESCRIPTION_ID, CONSULTATION_ID, DATE, DIAGNOSIS, INSTRUCTIONS) VALUES (?, ?, ?, ?, ?)",
            (pres_id, consultation_id, date_str, diagnosis, instructions),
        )

        for med in medicines:
            med_name = med.get("name")
            dosage = med.get("dosage", "1 Tablet")
            freq = med.get("frequency", "Twice daily")
            dur = med.get("duration", "5 days")

            cursor.execute(
                "INSERT INTO PRESCRIBED_MEDICINE (PRESCRIPTION_ID, MEDICINE_NAME, DOSAGE, FREQUENCY, DURATION) VALUES (?, ?, ?, ?, ?)",
                (pres_id, med_name, dosage, freq, dur),
            )
            cursor.execute("UPDATE PHARMACY SET STOCK = MAX(0, STOCK - 1) WHERE MEDICINE_NAME = ?", (med_name,))

        cursor.execute("UPDATE CONSULTATION SET STATUS = 'Completed' WHERE CONSULTATION_ID = ?", (consultation_id,))
        conn.commit()
    except sqlite3.IntegrityError as e:
        conn.close()
        return jsonify({"error": f"Could not create prescription: {str(e)}"}), 400

    conn.close()
    return jsonify({"message": "Digital Prescription generated successfully", "PRESCRIPTION_ID": pres_id}), 201


# ================= DATABASE RESET =================

@app.route("/api/admin/reset", methods=["POST"])
@staff_required
def reset_database():
    conn = get_db()
    cursor = conn.cursor()
    tables = ["PRESCRIBED_MEDICINE", "PRESCRIPTION", "CONSULTATION", "EMT_STATUS", "EMT", "PHARMACY", "PATIENTS", "EMPLOYEES", "USER_DATA"]
    for t in tables:
        cursor.execute(f"DROP TABLE IF EXISTS {t}")
    conn.commit()
    conn.close()
    init_db()
    return jsonify({"message": "Database reset and seeded with default vibrant data!"})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
