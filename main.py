"""
Apke Gharka Sathi - Full Python Backend (FastAPI + SQLite + WebSockets)
Tagline: "Your Trusted Partner for Every Home Need."
Author: Rohan
"""

import hashlib
import hmac
import json
import os
import random
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Header,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ---------------------------------------------------------
# 1. Configuration & App Setup
# ---------------------------------------------------------
SECRET_KEY = os.environ.get("SECRET_KEY", "apke_gharka_sathi_super_secret_key_2026")
DB_NAME = os.environ.get("DB_PATH", "apke_gharka_sathi.db")

app = FastAPI(
    title="Apke Gharka Sathi API",
    description="Production-grade on-demand home service marketplace backend by Rohan.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# 2. Database Initialization (SQLite)
# ---------------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Users Table (Customers, Partners, Admin)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT UNIQUE NOT NULL,
        email TEXT,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'customer',
        address TEXT,
        skills TEXT,
        experience_years INTEGER DEFAULT 0,
        kyc_status TEXT DEFAULT 'pending',
        is_available INTEGER DEFAULT 0,
        current_lat REAL DEFAULT 0.0,
        current_lng REAL DEFAULT 0.0,
        rating_avg REAL DEFAULT 5.0,
        rating_count INTEGER DEFAULT 0,
        wallet_balance REAL DEFAULT 0.0,
        created_at TEXT NOT NULL
    )
    """)

    # Services Catalog Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_name TEXT UNIQUE NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        icon TEXT,
        description TEXT,
        sub_services TEXT NOT NULL
    )
    """)

    # Bookings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id TEXT UNIQUE NOT NULL,
        customer_id INTEGER NOT NULL,
        partner_id INTEGER,
        service_category TEXT NOT NULL,
        sub_service TEXT NOT NULL,
        service_address TEXT NOT NULL,
        booking_type TEXT DEFAULT 'instant',
        scheduled_slot TEXT DEFAULT 'immediate',
        status TEXT DEFAULT 'PENDING_MATCH',
        doorstep_otp TEXT NOT NULL,
        is_otp_verified INTEGER DEFAULT 0,
        inspection_fee REAL DEFAULT 49.0,
        service_charge REAL NOT NULL,
        total_amount REAL NOT NULL,
        platform_commission REAL NOT NULL,
        partner_earnings REAL NOT NULL,
        payment_method TEXT DEFAULT 'cod',
        payment_status TEXT DEFAULT 'pending',
        warranty_until TEXT,
        notes TEXT,
        created_at TEXT NOT NULL,
        completed_at TEXT,
        FOREIGN KEY (customer_id) REFERENCES users(id),
        FOREIGN KEY (partner_id) REFERENCES users(id)
    )
    """)

    # Reviews Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id TEXT NOT NULL,
        customer_id INTEGER NOT NULL,
        partner_id INTEGER NOT NULL,
        rating INTEGER NOT NULL,
        comment TEXT,
        created_at TEXT NOT NULL
    )
    """)

    conn.commit()

    # Seed 6 Default Service Categories if empty
    cursor.execute("SELECT COUNT(*) FROM services")
    if cursor.fetchone()[0] == 0:
        default_services = [
            (
                "Plumbing Solutions",
                "plumbing-solutions",
                "fa-faucet-drip",
                "Pipe leakage repairs, tap/sanitary installations, drain clearing, and pump troubleshooting.",
                json.dumps([
                    {"title": "Pipe Leakage Repair", "base_price": 249, "inspection_fee": 49, "time_mins": 45},
                    {"title": "Tap & Sanitary Installation", "base_price": 299, "inspection_fee": 49, "time_mins": 60},
                    {"title": "Drain Clearing & Clog Removal", "base_price": 349, "inspection_fee": 49, "time_mins": 45},
                    {"title": "Water Pump Troubleshooting", "base_price": 499, "inspection_fee": 99, "time_mins": 90}
                ])
            ),
            (
                "Masonry & Tile Work (Rajmistri)",
                "masonry-tile-work",
                "fa-trowel-bricks",
                "Wall repairs, plaster patching, brickwork, tile/marble fitting, and minor civil jobs.",
                json.dumps([
                    {"title": "Plaster Patching & Crack Repair", "base_price": 499, "inspection_fee": 99, "time_mins": 120},
                    {"title": "Floor & Wall Tile Fitting", "base_price": 699, "inspection_fee": 99, "time_mins": 180},
                    {"title": "Brickwork & Partition Wall", "base_price": 899, "inspection_fee": 99, "time_mins": 240}
                ])
            ),
            (
                "Electrical Repairs",
                "electrical-repairs",
                "fa-bolt",
                "Switchboard fixes, wiring repairs, appliance installations, and emergency fault resolution.",
                json.dumps([
                    {"title": "Switchboard Repair / Socket Fix", "base_price": 199, "inspection_fee": 49, "time_mins": 30},
                    {"title": "House Wiring & Fault Inspection", "base_price": 349, "inspection_fee": 49, "time_mins": 60},
                    {"title": "Ceiling Fan & Light Installation", "base_price": 199, "inspection_fee": 49, "time_mins": 45},
                    {"title": "Emergency Short Circuit Resolution", "base_price": 449, "inspection_fee": 99, "time_mins": 60}
                ])
            ),
            (
                "Carpentry & Woodwork",
                "carpentry-woodwork",
                "fa-hammer",
                "Furniture assembly/repair, door locks, hinges, window fittings, and custom wood maintenance.",
                json.dumps([
                    {"title": "Main Door Lock / Deadbolt Fitting", "base_price": 299, "inspection_fee": 49, "time_mins": 45},
                    {"title": "Furniture Assembly & Repair", "base_price": 399, "inspection_fee": 49, "time_mins": 90},
                    {"title": "Cabinet Hinges & Channel Fix", "base_price": 249, "inspection_fee": 49, "time_mins": 45}
                ])
            ),
            (
                "Painting & Waterproofing",
                "painting-waterproofing",
                "fa-paint-roller",
                "Wall painting, damp treatment, ceiling leak sealing, and touch-ups.",
                json.dumps([
                    {"title": "Damp Treatment & Primer Coating", "base_price": 599, "inspection_fee": 99, "time_mins": 120},
                    {"title": "Ceiling Leakage Sealing", "base_price": 699, "inspection_fee": 99, "time_mins": 120},
                    {"title": "Interior Wall Painting Touch-up", "base_price": 499, "inspection_fee": 49, "time_mins": 90}
                ])
            ),
            (
                "Appliance Maintenance",
                "appliance-maintenance",
                "fa-fan",
                "AC, washing machine, and refrigerator servicing.",
                json.dumps([
                    {"title": "AC Deep Cleaning & Gas Refill", "base_price": 499, "inspection_fee": 99, "time_mins": 60},
                    {"title": "Washing Machine Drum & Motor Repair", "base_price": 399, "inspection_fee": 99, "time_mins": 60},
                    {"title": "Refrigerator Cooling Repair", "base_price": 349, "inspection_fee": 99, "time_mins": 60}
                ])
            )
        ]
        cursor.executemany(
            "INSERT INTO services (category_name, slug, icon, description, sub_services) VALUES (?, ?, ?, ?, ?)",
            default_services
        )
        conn.commit()
    conn.close()

# ---------------------------------------------------------
# 3. Security & Token Utilities
# ---------------------------------------------------------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def create_access_token(user_id: int, role: str) -> str:
    payload = {
        "user_id": user_id,
        "role": role,
        "exp": int(time.time()) + (30 * 24 * 3600)  # 30 days
    }
    raw_data = json.dumps(payload, separators=(',', ':'))
    signature = hmac.new(SECRET_KEY.encode(), raw_data.encode(), hashlib.sha256).hexdigest()
    return f"{raw_data}.{signature}"

def verify_token(token: str) -> Dict:
    try:
        raw_data, signature = token.rsplit('.', 1)
        expected_sig = hmac.new(SECRET_KEY.encode(), raw_data.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            raise HTTPException(status_code=401, detail="Invalid token signature")
        payload = json.loads(raw_data)
        if payload.get("exp", 0) < int(time.time()):
            raise HTTPException(status_code=401, detail="Token expired")
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Authentication token invalid or missing")

def get_current_user(authorization: Optional[str] = Header(None)) -> Dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required in Authorization header")
    token = authorization.split(" ")
    payload = verify_token(token)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (payload["user_id"],))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return dict(user)

# ---------------------------------------------------------
# 4. Request / Response Schemas
# ---------------------------------------------------------
class UserRegister(BaseModel):
    name: str
    phone: str
    password: str
    email: Optional[str] = None
    role: str = "customer"  # 'customer', 'partner', 'admin'
    address: Optional[str] = None
    skills: Optional[List[str]] = None
    experience_years: Optional[int] = 0

class UserLogin(BaseModel):
    phone: str
    password: str

class BookingCreate(BaseModel):
    service_category: str
    sub_service: str
    service_address: str
    booking_type: str = "instant"
    scheduled_slot: str = "immediate"
    estimated_price: float = 249.0
    payment_method: str = "cod"
    notes: Optional[str] = None

class OtpVerify(BaseModel):
    otp: str

class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None

class LocationUpdate(BaseModel):
    lat: float
    lng: float

class KycAction(BaseModel):
    status: str

# ---------------------------------------------------------
# 5. REST API Endpoints
# ---------------------------------------------------------

@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/")
def root():
    return {
        "platform": "Apke Gharka Sathi API",
        "tagline": "Your Trusted Partner for Every Home Need.",
        "version": "1.0.0",
        "status": "ONLINE",
        "author": "Rohan",
        "docs_url": "/docs"
    }

# --- Authentication Endpoints ---
@app.post("/api/v1/auth/register", status_code=status.HTTP_201_CREATED)
def register(req: UserRegister):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM users WHERE phone = ?", (req.phone,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Phone number already registered")
    
    pwd_hash = hash_password(req.password)
    now = datetime.utcnow().isoformat()
    skills_json = json.dumps(req.skills or [])
    
    cursor.execute("""
    INSERT INTO users (name, phone, email, password_hash, role, address, skills, experience_years, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (req.name, req.phone, req.email, pwd_hash, req.role, req.address, skills_json, req.experience_years, now))
    
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    token = create_access_token(user_id, req.role)
    return {
        "success": True,
        "message": "User registered successfully",
        "token": token,
        "user": {"id": user_id, "name": req.name, "phone": req.phone, "role": req.role}
    }

@app.post("/api/v1/auth/login")
def login(req: UserLogin):
    conn = get_db()
    cursor = conn.cursor()
    pwd_hash = hash_password(req.password)
    
    cursor.execute("SELECT * FROM users WHERE phone = ? AND password_hash = ?", (req.phone, pwd_hash))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid phone number or password")
    
    token = create_access_token(user["id"], user["role"])
    return {
        "success": True,
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "phone": user["phone"],
            "role": user["role"],
            "wallet_balance": user["wallet_balance"]
        }
    }

@app.get("/api/v1/auth/me")
def get_me(current_user: Dict = Depends(get_current_user)):
    return {"success": True, "user": current_user}

# --- Service Catalog Endpoints ---
@app.get("/api/v1/services")
def list_services():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM services")
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for r in rows:
        item = dict(r)
        item["sub_services"] = json.loads(item["sub_services"])
        result.append(item)
    return {"success": True, "data": result}

# --- Booking & Lifecycle Endpoints ---
@app.post("/api/v1/bookings", status_code=status.HTTP_201_CREATED)
def create_booking(req: BookingCreate, current_user: Dict = Depends(get_current_user)):
    if current_user["role"] != "customer":
        raise HTTPException(status_code=403, detail="Only customers can create bookings")
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Auto-match nearest available verified partner
    cursor.execute("""
    SELECT id, name, phone, rating_avg FROM users
    WHERE role = 'partner' AND kyc_status = 'approved' AND is_available = 1
    """)
    partners = cursor.fetchall()
    matched_partner = partners[0] if partners else None

    booking_id = f"AGS-{int(time.time())}-{random.randint(100, 999)}"
    doorstep_otp = str(random.randint(1000, 9999))
    
    total = req.estimated_price
    inspection_fee = 49.0
    service_charge = max(0.0, total - inspection_fee)
    commission = round(total * 0.15, 2)  # 15% platform commission
    partner_earnings = round(total - commission, 2)
    now = datetime.utcnow().isoformat()
    partner_id = matched_partner["id"] if matched_partner else None
    status_val = "ASSIGNED" if matched_partner else "PENDING_MATCH"
    
    cursor.execute("""
    INSERT INTO bookings (
        booking_id, customer_id, partner_id, service_category, sub_service,
        service_address, booking_type, scheduled_slot, status, doorstep_otp,
        inspection_fee, service_charge, total_amount, platform_commission, partner_earnings,
        payment_method, notes, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        booking_id, current_user["id"], partner_id, req.service_category, req.sub_service,
        req.service_address, req.booking_type, req.scheduled_slot, status_val, doorstep_otp,
        inspection_fee, service_charge, total, commission, partner_earnings,
        req.payment_method, req.notes, now
    ))
    
    conn.commit()
    conn.close()
    
    return {
        "success": True,
        "message": "Booking created successfully",
        "booking_id": booking_id,
        "doorstep_otp": doorstep_otp,
        "status": status_val,
        "matched_technician": dict(matched_partner) if matched_partner else None
    }

@app.get("/api/v1/bookings")
def get_my_bookings(current_user: Dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    
    if current_user["role"] == "customer":
        cursor.execute("SELECT * FROM bookings WHERE customer_id = ? ORDER BY id DESC", (current_user["id"],))
    elif current_user["role"] == "partner":
        cursor.execute("SELECT * FROM bookings WHERE partner_id = ? ORDER BY id DESC", (current_user["id"],))
    else:
        cursor.execute("SELECT * FROM bookings ORDER BY id DESC")
        
    rows = cursor.fetchall()
    conn.close()
    return {"success": True, "count": len(rows), "data": [dict(r) for r in rows]}

@app.post("/api/v1/bookings/{b_id}/verify-otp")
def verify_doorstep_otp(b_id: str, req: OtpVerify, current_user: Dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM bookings WHERE booking_id = ?", (b_id,))
    booking = cursor.fetchone()
    
    if not booking:
        conn.close()
        raise HTTPException(status_code=404, detail="Booking not found")
        
    if booking["doorstep_otp"] != req.otp:
        conn.close()
        raise HTTPException(status_code=400, detail="Invalid OTP. Please check with the customer.")
        
    cursor.execute("UPDATE bookings SET is_otp_verified = 1, status = 'IN_PROGRESS' WHERE booking_id = ?", (b_id,))
    conn.commit()
    conn.close()
    
    return {"success": True, "message": "OTP verified successfully. Job in progress."}

@app.post("/api/v1/bookings/{b_id}/complete")
def complete_job(b_id: str, current_user: Dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bookings WHERE booking_id = ?", (b_id,))
    booking = cursor.fetchone()
    
    if not booking:
        conn.close()
        raise HTTPException(status_code=404, detail="Booking not found")
        
    now = datetime.utcnow()
    warranty = (now + timedelta(days=30)).isoformat()
    now_str = now.isoformat()
    
    cursor.execute("""
    UPDATE bookings SET status = 'COMPLETED', payment_status = 'paid', completed_at = ?, warranty_until = ?
    WHERE booking_id = ?
    """, (now_str, warranty, b_id))
    
    if booking["partner_id"]:
        cursor.execute("""
        UPDATE users SET wallet_balance = wallet_balance + ? WHERE id = ?
        """, (booking["partner_earnings"], booking["partner_id"]))
        
    conn.commit()
    conn.close()
    
    return {
        "success": True,
        "message": "Job marked as completed. 30-Day warranty active.",
        "warranty_until": warranty
    }

# --- Service Partner Portal Endpoints ---
@app.put("/api/v1/partners/toggle-status")
def toggle_partner_status(current_user: Dict = Depends(get_current_user)):
    if current_user["role"] != "partner":
        raise HTTPException(status_code=403, detail="Only partners can toggle duty status")
        
    new_status = 0 if current_user["is_available"] else 1
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_available = ? WHERE id = ?", (new_status, current_user["id"]))
    conn.commit()
    conn.close()
    
    return {
        "success": True,
        "is_available": bool(new_status),
        "status_text": "ONLINE" if new_status else "OFFLINE"
    }

@app.put("/api/v1/partners/location")
def update_partner_location(req: LocationUpdate, current_user: Dict = Depends(get_current_user)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET current_lat = ?, current_lng = ? WHERE id = ?", (req.lat, req.lng, current_user["id"]))
    conn.commit()
    conn.close()
    return {"success": True, "message": "Location updated successfully"}

@app.get("/api/v1/partners/dashboard")
def get_partner_dashboard(current_user: Dict = Depends(get_current_user)):
    if current_user["role"] != "partner":
        raise HTTPException(status_code=403, detail="Partner access only")
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM bookings WHERE partner_id = ? AND status = 'COMPLETED'", (current_user["id"],))
    completed_jobs = cursor.fetchone()[0]
    conn.close()
    
    return {
        "success": True,
        "data": {
            "partner_name": current_user["name"],
            "wallet_balance": current_user["wallet_balance"],
            "rating_avg": current_user["rating_avg"],
            "completed_jobs": completed_jobs,
            "kyc_status": current_user["kyc_status"],
            "is_online": bool(current_user["is_available"])
        }
    }

# --- Admin Operations Endpoints ---
@app.get("/api/v1/admin/metrics")
def get_admin_metrics(current_user: Dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'customer'")
    customers = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'partner'")
    partners = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'partner' AND kyc_status = 'pending'")
    pending_kyc = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM bookings WHERE status IN ('PENDING_MATCH', 'ASSIGNED', 'IN_PROGRESS')")
    active_jobs = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(platform_commission), SUM(total_amount) FROM bookings WHERE status = 'COMPLETED'")
    rev_row = cursor.fetchone()
    conn.close()
    
    return {
        "success": True,
        "metrics": {
            "total_customers": customers,
            "total_technicians": partners,
            "pending_kyc_reviews": pending_kyc,
            "active_bookings": active_jobs,
            "platform_revenue": rev_row[0] or 0.0,
            "gross_booking_volume": rev_row or 0.0
        }
    }

@app.put("/api/v1/admin/kyc/{partner_id}")
def verify_partner_kyc(partner_id: int, req: KycAction, current_user: Dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
        
    if req.status not in ["approved", "rejected"]:
        raise HTTPException(status_code=400, detail="Status must be 'approved' or 'rejected'")
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET kyc_status = ? WHERE id = ? AND role = 'partner'", (req.status, partner_id))
    conn.commit()
    conn.close()
    return {"success": True, "message": f"Partner KYC marked as {req.status}"}

# ---------------------------------------------------------
# 6. WebSocket Live Tracking Room
# ---------------------------------------------------------
active_tracking_connections: Dict[str, List[WebSocket]] = {}

@app.websocket("/ws/tracking/{booking_id}")
async def websocket_tracking_endpoint(websocket: WebSocket, booking_id: str):
    await websocket.accept()
    if booking_id not in active_tracking_connections:
        active_tracking_connections[booking_id] = []
    active_tracking_connections[booking_id].append(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            # Broadcast live position to all clients listening on this booking ID
            for client in active_tracking_connections[booking_id]:
                await client.send_text(json.dumps({
                    "booking_id": booking_id,
                    "lat": payload.get("lat"),
                    "lng": payload.get("lng"),
                    "eta_mins": payload.get("eta_mins", 5),
                    "timestamp": datetime.utcnow().isoformat()
                }))
    except WebSocketDisconnect:
        active_tracking_connections[booking_id].remove(websocket)

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Apke Gharka Sathi Python Backend Server on http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)
