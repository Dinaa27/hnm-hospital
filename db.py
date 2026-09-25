import os
import sqlite3
from werkzeug.security import generate_password_hash

# Vercel serverless environments require writable files to reside in /tmp
if os.environ.get("VERCEL"):
    DATABASE = "/tmp/hnm_hospital.db"
else:
    DATABASE = os.path.join(os.path.abspath(os.path.dirname(__file__)), "hnm_hospital.db")


def get_db():
    conn = sqlite3.connect(DATABASE, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # 1. Employees (Doctors / Clinical Staff)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS EMPLOYEES (
            EID TEXT PRIMARY KEY,
            NAME TEXT NOT NULL,
            DEPARTMENT TEXT NOT NULL,
            AGE INTEGER,
            GENDER TEXT,
            SALARY REAL,
            MOBILE_NO TEXT
        )
    """
    )

    # 2. Patients
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS PATIENTS (
            PID TEXT PRIMARY KEY,
            NAME TEXT NOT NULL,
            ISSUE TEXT,
            AGE INTEGER,
            GENDER TEXT,
            FEES REAL DEFAULT 0,
            MOBILE_NO TEXT,
            BILL_NO TEXT UNIQUE,
            USERNAME TEXT
        )
    """
    )

    # 3. Emergency Medical Fleet (EMT)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS EMT (
            VNO TEXT PRIMARY KEY,
            VTYPE TEXT NOT NULL,
            DRIVER_NAME TEXT NOT NULL,
            MOBILE_NO TEXT NOT NULL
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS EMT_STATUS (
            VNO TEXT PRIMARY KEY,
            STATUS TEXT DEFAULT 'Available' CHECK (STATUS IN ('Available', 'Dispatched', 'Maintenance')),
            FOREIGN KEY (VNO) REFERENCES EMT(VNO) ON DELETE CASCADE
        )
    """
    )

    # 4. Pharmacy Inventory
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS PHARMACY (
            MEDICINE_NAME TEXT PRIMARY KEY,
            MEDICINE_TYPE TEXT NOT NULL,
            STOCK INTEGER NOT NULL CHECK (STOCK >= 0),
            PRICE REAL NOT NULL CHECK (PRICE >= 0)
        )
    """
    )

    # 5. User Authentication & Roles (Staff vs. Patient)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS USER_DATA (
            USERNAME TEXT PRIMARY KEY,
            PASSWORD TEXT NOT NULL,
            ROLE TEXT NOT NULL DEFAULT 'patient' CHECK (ROLE IN ('staff', 'patient')),
            NAME TEXT,
            MOBILE_NO TEXT,
            CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # 6. Consultations & Appointments
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS CONSULTATION (
            CONSULTATION_ID TEXT PRIMARY KEY,
            PATIENT_ID TEXT NOT NULL,
            EMP_ID TEXT NOT NULL,
            REASON TEXT,
            FEES REAL DEFAULT 0,
            TIME TEXT,
            STATUS TEXT DEFAULT 'Scheduled' CHECK (STATUS IN ('Scheduled', 'Completed', 'Cancelled')),
            FOREIGN KEY (PATIENT_ID) REFERENCES PATIENTS(PID) ON DELETE RESTRICT,
            FOREIGN KEY (EMP_ID) REFERENCES EMPLOYEES(EID) ON DELETE RESTRICT
        )
    """
    )

    # 7. Digital Prescriptions
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS PRESCRIPTION (
            PRESCRIPTION_ID TEXT PRIMARY KEY,
            CONSULTATION_ID TEXT NOT NULL UNIQUE,
            DATE TEXT NOT NULL,
            DIAGNOSIS TEXT,
            INSTRUCTIONS TEXT,
            FOREIGN KEY (CONSULTATION_ID) REFERENCES CONSULTATION(CONSULTATION_ID) ON DELETE RESTRICT
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS PRESCRIBED_MEDICINE (
            PM_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            PRESCRIPTION_ID TEXT NOT NULL,
            MEDICINE_NAME TEXT NOT NULL,
            DOSAGE TEXT NOT NULL,
            FREQUENCY TEXT NOT NULL,
            DURATION TEXT NOT NULL,
            FOREIGN KEY (PRESCRIPTION_ID) REFERENCES PRESCRIPTION(PRESCRIPTION_ID) ON DELETE CASCADE,
            FOREIGN KEY (MEDICINE_NAME) REFERENCES PHARMACY(MEDICINE_NAME) ON DELETE RESTRICT
        )
    """
    )

    conn.commit()
    seed_data(conn)
    conn.close()


def seed_data(conn):
    cursor = conn.cursor()

    # Seed Default User Accounts
    cursor.execute("SELECT COUNT(*) FROM USER_DATA")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO USER_DATA (USERNAME, PASSWORD, ROLE, NAME, MOBILE_NO) VALUES (?, ?, ?, ?, ?)",
            [
                (
                    "admin",
                    generate_password_hash("admin123"),
                    "staff",
                    "Dr. Eleanor Vance (Chief Admin)",
                    "9876543210",
                ),
                (
                    "doctor_raj",
                    generate_password_hash("doctor123"),
                    "staff",
                    "Dr. Rajesh Sharma",
                    "9876543211",
                ),
                (
                    "patient_john",
                    generate_password_hash("patient123"),
                    "patient",
                    "Johnathan Doe",
                    "9123456780",
                ),
            ],
        )

    # Seed Doctors & Medical Staff
    cursor.execute("SELECT COUNT(*) FROM EMPLOYEES")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO EMPLOYEES (EID, NAME, DEPARTMENT, AGE, GENDER, SALARY, MOBILE_NO) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                ("EMP001", "Dr. Rajesh Sharma", "Cardiology", 45, "Male", 185000, "9876543211"),
                ("EMP002", "Dr. Priya Patel", "Pediatrics", 38, "Female", 160000, "9876543212"),
                ("EMP003", "Dr. Michael Chen", "Orthopedics", 50, "Male", 195000, "9876543213"),
                ("EMP004", "Dr. Anita Desai", "Neurology", 42, "Female", 175000, "9876543214"),
                ("EMP005", "Nurse Sarah Wilson", "Emergency Care", 29, "Female", 72000, "9876543215"),
            ],
        )

    # Seed Patient Records
    cursor.execute("SELECT COUNT(*) FROM PATIENTS")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO PATIENTS (PID, NAME, ISSUE, AGE, GENDER, FEES, MOBILE_NO, BILL_NO, USERNAME) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("PAT001", "Johnathan Doe", "Chest pain & Mild Hypertension", 52, "Male", 1200, "9123456780", "BILL-1001", "patient_john"),
                ("PAT002", "Emily Watson", "Severe Migraine", 34, "Female", 800, "9123456781", "BILL-1002", None),
                ("PAT003", "Aarav Kumar", "Viral Fever and Throat Infection", 8, "Male", 500, "9123456782", "BILL-1003", None),
                ("PAT004", "Robert Taylor", "Knee Joint Pain", 63, "Male", 1500, "9123456783", "BILL-1004", None),
            ],
        )

    # Seed Ambulance Fleet
    cursor.execute("SELECT COUNT(*) FROM EMT")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO EMT (VNO, VTYPE, DRIVER_NAME, MOBILE_NO) VALUES (?, ?, ?, ?)",
            [
                ("KA01AB1234", "Advanced Life Support (ALS)", "Ramesh Gowda", "9988776655"),
                ("KA01CD5678", "Basic Life Support (BLS)", "Suresh Kumar", "9988776656"),
                ("KA02EF9012", "Patient Transport Unit", "Anil Patil", "9988776657"),
            ],
        )
        cursor.executemany(
            "INSERT INTO EMT_STATUS (VNO, STATUS) VALUES (?, ?)",
            [
                ("KA01AB1234", "Available"),
                ("KA01CD5678", "Dispatched"),
                ("KA02EF9012", "Available"),
            ],
        )

    # Seed Pharmacy Catalog
    cursor.execute("SELECT COUNT(*) FROM PHARMACY")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO PHARMACY (MEDICINE_NAME, MEDICINE_TYPE, STOCK, PRICE) VALUES (?, ?, ?, ?)",
            [
                ("Paracetamol 650mg", "Tablet", 500, 30.0),
                ("Amoxicillin 500mg", "Capsule", 250, 120.0),
                ("Atorvastatin 10mg", "Tablet", 180, 210.0),
                ("Cetirizine 10mg", "Tablet", 400, 45.0),
                ("Salbutamol Inhaler", "Inhaler", 60, 250.0),
                ("Azithromycin 500mg", "Tablet", 140, 160.0),
            ],
        )

    # Seed Consultations & Prescriptions
    cursor.execute("SELECT COUNT(*) FROM CONSULTATION")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO CONSULTATION (CONSULTATION_ID, PATIENT_ID, EMP_ID, REASON, FEES, TIME, STATUS) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                ("CON-001", "PAT001", "EMP001", "Cardiac check-up and ECG", 1200, "2026-09-25 10:30", "Completed"),
                ("CON-002", "PAT002", "EMP004", "Neurology consultation", 800, "2026-09-26 14:00", "Scheduled"),
            ],
        )
        cursor.execute(
            "INSERT INTO PRESCRIPTION (PRESCRIPTION_ID, CONSULTATION_ID, DATE, DIAGNOSIS, INSTRUCTIONS) VALUES (?, ?, ?, ?, ?)",
            ("RX-001", "CON-001", "2026-09-25", "Mild Cardiac Arrhythmia & Hypertension", "Low sodium diet, brisk walking 30 min daily"),
        )
        cursor.executemany(
            "INSERT INTO PRESCRIBED_MEDICINE (PRESCRIPTION_ID, MEDICINE_NAME, DOSAGE, FREQUENCY, DURATION) VALUES (?, ?, ?, ?, ?)",
            [
                ("RX-001", "Atorvastatin 10mg", "1 Tablet", "Once daily after dinner", "30 Days"),
                ("RX-001", "Cetirizine 10mg", "1 Tablet", "If needed for allergies", "5 Days"),
            ],
        )

    conn.commit()


if __name__ == "__main__":
    init_db()
    print("Database initialized and seeded successfully.")
