import requests
import random
import json
import time
import logging
import os
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from passlib.context import CryptContext
from jose import JWTError, jwt

# Nastavenie logovania
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==========================================
# ⚙️ KONFIGURÁCIA
# ==========================================
API_KEY = "3e42c726ab364fb9eeede03b0017964c"  # <-- TU VLOŽ SVOJ KĽÚČ Z THE-ODDS-API
SECRET_KEY = "super_tajny_kluc_pre_sifrovanie_zmen_ma"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 600

# ==========================================
# 💾 DATABÁZA (POSTGRESQL / SQLITE)
# ==========================================
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if not DATABASE_URL:
    # Fallback pre lokálne testovanie, ak nie je nastavená DB na Renderi
    DATABASE_URL = "sqlite:///./betting_pro.db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- MODELY ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    bankroll = Column(Float, default=1000.0)

class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    match_info = Column(String)
    tip = Column(String)
    kurz = Column(Float)
    vklad = Column(Float)
    potencialna_vyhra = Column(Float)
    status = Column(String, default="PENDING")
    timestamp = Column(DateTime, default=datetime.utcnow)

class CachedMatch(Base):
    __tablename__ = "matches"
    id = Column(Integer, primary_key=True, index=True)
    data_json = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow)

# Vytvorenie tabuliek
Base.metadata.create_all(bind=engine)

# ==========================================
# 🔐 BEZPEČNOSŤ
# ==========================================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def verify_password(plain, hashed): return pwd_context.verify(plain, hashed)
def get_password_hash(password): return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None: raise HTTPException(status_code=401)
    except JWTError: raise HTTPException(status_code=401)
    user = db.query(User).filter(User.username == username).first()
    if user is None: raise HTTPException(status_code=401)
    return user

# ==========================================
# 🧠 LOGIKA A API
# ==========================================
app = FastAPI()

class UserCreate(BaseModel):
    username: str
    password: str

class BetRequest(BaseModel):
    match_info: str
    tip: str
    kurz: float
    vklad: float

@app.post("/api/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    if not user.username.strip(): raise HTTPException(status_code=400, detail="Meno povinné")
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Užívateľ existuje")
    new_user = User(username=user.username, hashed_password=get_password_hash(user.password), bankroll=1000.0)
    db.add(new_user)
    db.commit()
    return {"msg": "OK"}

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Zlé meno alebo heslo")
    return {"access_token": create_access_token(data={"sub": user.username}), "token_type": "bearer"}

@app.get("/api/me")
def read_users_me(current_user: User = Depends(get_current_user)):
    return {"username": current_user.username, "bankroll": current_user.bankroll}

# --- FETCH DÁT ---
def get_matches_internal(db: Session):
    cached = db.query(CachedMatch).first()
    if cached and cached.updated_at > datetime.utcnow() - timedelta(minutes=45):
        return json.loads(cached.data_json)
    
    if API_KEY == "VLOZ_SVOJ_API_KLUC_SEM": return generate_demo_data()

    try:
        url = f"https://api.the-odds-api.com/v4/sports/soccer/odds/?regions=eu&markets=h2h&apiKey={API_KEY}"
        data = requests.get(url).json()
        matches = []
        for item in data[:15]:
            try:
                odds = item['bookmakers'][0]['markets'][0]['outcomes']
                h, a = item['home_team'], item['away_team']
                o1 = next((x['price'] for x in odds if x['name'] == h), 0)
                o2 = next((x['price'] for x in odds if x['name'] == a), 0)
                if o1==0 or o2==0: continue
                
                risk = 1 if o1 < 1.5 or o2 < 1.5 else (2 if o1 < 2.1 else 3)
                tip = "1" if o1 < o2 else "2"
                stats = {"utok_domaci": int(100/o1) if o1>1 else 90, "utok_hostia": int(100/o2) if o2>1 else 90, "forma_domaci": "WDLWW", "forma_hostia": "LLWDW", "zranenia": "Bez absencií"}
                
                matches.append({"domaci": h, "hostia": a, "kurz": o1 if tip=="1" else o2, "tip": tip, "risk": risk, "liga": item['sport_title'], "dovera": random.randint(60,95), "stats": stats, "analyza_text": "AI detekovala hodnotu.", "analyza_body": ["Dobrý kurz.", "Forma tímu stúpa."]})
            except: continue
        
        if cached: db.delete(cached)
        db.add(CachedMatch(data_json=json.dumps(matches), updated_at=datetime.utcnow()))
        db.commit()
        return matches
    except: return generate_demo_data()

def generate_demo_data():
    return [{"domaci": "DEMO MODE", "hostia": "VLOŽ API KĽÚČ", "kurz": 1.00, "tip": "X", "risk": 1, "liga": "System", "dovera": 0, "stats": {"utok_domaci":0, "utok_hostia":0, "forma_domaci": "LLLLL", "forma_hostia": "LLLLL", "zranenia": "-"}, "analyza_text": "Vlož svoj API kľúč do main.py", "analyza_body": []}]

@app.get("/api/generuj-tiket")
def api_get_matches(db: Session = Depends(get_db)): return get_matches_internal(db)

@app.get("/api/tiket-dna")
def api_tiket_dna(db: Session = Depends(get_db)):
    data = get_matches_internal(db)
    safe = [m for m in data if m['risk'] == 1]
    return safe[:3] if safe else data[:3]

@app.get("/api/vlastny-tiket")
def api_custom(risk: int = 1, db: Session = Depends(get_db)):
    data = get_matches_internal(db)
    filtered = [m for m in data if m['risk'] == risk]
    return filtered if filtered else data

@app.post("/api/bet")
def place_bet(bet: BetRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.bankroll < bet.vklad: raise HTTPException(status_code=400, detail="Málo peňazí")
    current_user.bankroll -= bet.vklad
    db.add(Ticket(user_id=current_user.id, match_info=bet.match_info, tip=bet.tip, kurz=bet.kurz, vklad=bet.vklad, potencialna_vyhra=bet.vklad*bet.kurz))
    db.commit()
    return {"msg": "OK"}

@app.get("/api/history")
def get_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Ticket).filter(Ticket.user_id == current_user.id).order_by(Ticket.timestamp.desc()).all()

@app.post("/api/admin/evaluate")
def evaluate_tickets(db: Session = Depends(get_db)):
    tickets = db.query(Ticket).filter(Ticket.status == "PENDING").all()
    count = 0
    for t in tickets:
        won = random.random() < 0.7 
        t.status = "WON" if won else "LOST"
        if won:
            user = db.query(User).filter(User.id == t.user_id).first()
            user.bankroll += t.potencialna_vyhra
        count += 1
    db.commit()
    return {"msg": f"Vyhodnotených {count} tiketov."}

# --- FRONTEND ---
html_content = """
<!DOCTYPE html>
<html lang="sk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Betting PRO</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        :root { --bg-dark: #050a10; --bg-card: #151b24; --primary: #66fcf1; --text-main: #c5c6c7; --green: #00ff88; --red: #ff4444; }
        body { margin: 0; padding: 0; font-family: 'Segoe UI', sans-serif; background-color: #0b0c10; color: var(--text-main); height: 100vh; overflow: hidden; display: flex; }
        #login-screen { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #050a10; z-index: 999; display: flex; align-items: center; justify-content: center; flex-direction: column; }
        .login-box { background: #151b24; padding: 40px; border-radius: 12px; border: 1px solid #66fcf1; width: 350px; text-align: center; }
        input { width: 90%; padding: 12px; margin: 10px 0; background: #0b0c10; border: 1px solid #333; color: white; border-radius: 6px; }
        #app-container { display: none; width: 100%; height: 100%; display: flex; }
        .sidebar { width: 260px; background-color: #111; display: flex; flex-direction: column; padding: 25px; border-right: 1px solid #333; }
        .main-content { flex: 1; padding: 40px; overflow-y: auto; background: radial-gradient(circle at top right, #1f2833 0%, #0b0c10 80%); }
        .menu-item { padding: 15px; margin-bottom: 5px; cursor: pointer; border-radius: 8px; color: #888; font-weight: 600; }
        .menu-item.active { background-color: #1f2833; color: #fff; border-left: 4px solid var(--primary); }
        .btn-action { background: var(--primary); border: none; padding: 12px 30px; font-weight: 800; color: #0b0c10; border-radius: 6px; cursor: pointer; text-transform: uppercase; width: 100%; margin-top: 10px; }
        .dash-card { background: var(--bg-card); padding: 25px; border-radius: 16px; border: 1px solid #2c3e50; flex: 1; margin-right: 20px; }
        .analysis-card { background: #11161d; border-radius: 12px; margin-bottom: 20px; border: 1px solid #2c3e50; padding: 20px; animation: slideUp 0.5s ease; }
        .page { display: none; } .page.active { display: block; animation: fadeIn 0.4s; }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        td { padding: 15px 10px; border-bottom: 1px solid #222; }
        .status-won { color: var(--green); } .status-lost { color: var(--red); }
    </style>
</head>
<body>

    <div id="login-screen">
        <div class="login-box">
            <h1 style="color:#66fcf1; margin-bottom:20px;">BET PRO</h1>
            <input type="text" id="username" placeholder="Meno (skús: admin)">
            <input type="password" id="password" placeholder="Heslo (skús: admin)">
            <button class="btn-action" onclick="doLogin()">Vstúpiť</button>
            <p style="color:#666; font-size:12px; margin-top:15px; cursor:pointer;" onclick="doRegister()">Registrovať nový účet</p>
        </div>
    </div>

    <div id="app-container">
        <div class="sidebar">
            <div style="font-size:24px; color:#66fcf1; font-weight:bold; margin-bottom:40px; text-align:center;">BET PRO</div>
            <div class="menu-item active" onclick="showPage('home', this)">🏠 Dashboard</div>
            <div class="menu-item" onclick="showPage('generator', this)">📊 VIP Analýza</div>
            <div class="menu-item" onclick="showPage('ticket-day', this)">🎯 Tiket Dňa</div>
            <div class="menu-item" onclick="showPage('results-page', this); loadHistory()">✅ História</div>
            <div class="menu-item" onclick="logout()" style="margin-top:auto; color:var(--red)">🚪 Odhlásiť</div>
        </div>

        <div class="main-content">
            <div style="display:flex; justify-content:space-between; margin-bottom:40px; border-bottom:1px solid #333; padding-bottom:20px;">
                <h1 id="page-title">Dashboard</h1>
                <div style="text-align:right;">
                    <div style="font-size:12px; color:#666;">BANKROLL</div>
                    <div style="font-size:24px; font-weight:bold; color:#66fcf1;" id="user-bankroll">€0.00</div>
                </div>
            </div>

            <div id="home" class="page active">
                <div style="display:flex; margin-bottom:30px;">
                    <div class="dash-card"><h3>Stav Konta</h3><h1 id="dash-bal">€--</h1></div>
                    <div class="dash-card"><h3>Status</h3><h1 style="color:var(--green)">ONLINE</h1></div>
                    <div class="dash-card"><h3>Admin</h3><button class="btn-action" style="padding:5px;" onclick="runSimulation()">Vyhodnotiť Tikety</button></div>
                </div>
            </div>

            <div id="generator" class="page">
                <button class="btn-action" style="width:auto;" onclick="loadAnalysis()">Načítať Analýzy</button>
                <div id="analysis-output" style="margin-top:30px;"></div>
            </div>

            <div id="ticket-day" class="page">
                <button class="btn-action" style="width:auto;" onclick="loadTiketDna()">Zobraziť Tiket Dňa</button>
                <div id="ticket-dna-result" style="margin-top:30px;"></div>
            </div>

            <div id="results-page" class="page">
                <h3>História Tiketov</h3>
                <div id="history-output"></div>
            </div>
        </div>
    </div>

    <script>
        let token = localStorage.getItem("token");
        if(token) { document.getElementById('login-screen').style.display='none'; document.getElementById('app-container').style.display='flex'; updateUser(); }

        async function doLogin() {
            const u = document.getElementById('username').value;
            const p = document.getElementById('password').value;
            const formData = new URLSearchParams(); formData.append('username', u); formData.append('password', p);
            try {
                const res = await fetch('/token', { method:'POST', body: formData });
                if(!res.ok) throw new Error();
                const data = await res.json();
                localStorage.setItem("token", data.access_token);
                location.reload();
            } catch(e) { alert("Chyba prihlásenia! Skontroluj meno/heslo."); }
        }

        async function doRegister() {
            const u = document.getElementById('username').value;
            const p = document.getElementById('password').value;
            try {
                await fetch('/api/register', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({username:u, password:p}) });
                alert("Účet vytvorený! Teraz sa prihlás.");
            } catch(e) { alert("Chyba registrácie."); }
        }

        function logout() { localStorage.removeItem("token"); location.reload(); }

        async function updateUser() {
            const res = await fetch('/api/me', { headers: { 'Authorization': 'Bearer ' + localStorage.getItem("token") } });
            if (!res.ok) { logout(); return; }
            const data = await res.json();
            document.getElementById('user-bankroll').innerText = '€' + data.bankroll.toFixed(2);
            document.getElementById('dash-bal').innerText = '€' + data.bankroll.toFixed(2);
        }

        function showPage(id, el) {
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            if(el) el.classList.add('active');
            document.getElementById(id).classList.add('active');
        }

        async function loadAnalysis() {
            const res = await fetch('/api/generuj-tiket', { headers: { 'Authorization': 'Bearer ' + localStorage.getItem("token") } });
            const data = await res.json();
            renderMatches(data, 'analysis-output');
        }

        async function loadTiketDna() {
            const res = await fetch('/api/tiket-dna', { headers: { 'Authorization': 'Bearer ' + localStorage.getItem("token") } });
            const data = await res.json();
            renderMatches(data, 'ticket-dna-result');
        }

        function renderMatches(data, elId) {
            let html = '';
            data.forEach(m => {
                html += `<div class="analysis-card"><h2>${m.domaci} vs ${m.hostia}</h2><p>Tip: ${m.tip} | Kurz: ${m.kurz}</p><p>${m.analyza_text}</p><button class="btn-action" onclick="placeBet('${m.domaci} vs ${m.hostia}', '${m.tip}', ${m.kurz})">VSAĎIŤ 50€</button></div>`;
            });
            document.getElementById(elId).innerHTML = html;
        }

        async function placeBet(match, tip, kurz) {
            if(!confirm("Vsaďiť 50€?")) return;
            const res = await fetch('/api/bet', { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + localStorage.getItem("token") }, body: JSON.stringify({ match_info: match, tip: tip, kurz: kurz, vklad: 50.0 }) });
            if(res.ok) { alert("Stavené!"); updateUser(); } else alert("Chyba / Málo peňazí");
        }

        async function loadHistory() {
            const res = await fetch('/api/history', { headers: { 'Authorization': 'Bearer ' + localStorage.getItem("token") } });
            const data = await res.json();
            let html = '<table>';
            data.forEach(t => html += `<tr><td>${t.match_info}</td><td>${t.tip}</td><td>€${t.vklad}</td><td class="${t.status==='WON'?'status-won':(t.status==='LOST'?'status-lost':'')}">${t.status}</td></tr>`);
            html += '</table>';
            document.getElementById('history-output').innerHTML = html;
        }

        async function runSimulation() {
            await fetch('/api/admin/evaluate', { method:'POST', headers: { 'Authorization': 'Bearer ' + localStorage.getItem("token") } });
            alert("Hotovo! (Skontroluj históriu)"); updateUser();
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def home(): return html_content
