import requests
import random
import time
import google.generativeai as genai
from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from dateutil import parser 

app = FastAPI()

# ==========================================
# 🔑 API KĽÚČE (VLOŽ OBA!)
# ==========================================
# 1. Kľúč na dáta (kurzy): https://the-odds-api.com/
ODDS_API_KEY = "3e42c726ab364fb9eeede03b0017964c"    

# 2. Kľúč na texty (AI): https://aistudio.google.com/app/apikey
GEMINI_API_KEY = "AIzaSyCreRpXTUwxzJegxQKUJ2RiX5BwSagdljg"    
# ==========================================

# Nastavenie Gemini
if GEMINI_API_KEY != "VLOZ_SVOJ_GEMINI_KLUC_SEM":
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-pro')

CACHE = {"data": [], "last_update": 0}

# --- 1. SMART LOGIC (Matematika) ---
def calculate_smart_stats(o1, o2):
    """
    Toto je náš 'Mozog'. Počíta štatistiky na základe kurzov, 
    pretože kurzy od bookmakerov sú najpresnejší indikátor sily.
    """
    prob_h = (1 / o1) * 100
    prob_a = (1 / o2) * 100
    
    # Sila útoku (čím nižší kurz, tým silnejší útok)
    att_h = min(99, int(prob_h + random.randint(-5, 5)))
    att_a = min(99, int(prob_a + random.randint(-5, 5)))
    
    # Forma (Generovaná logicky podľa sily)
    def get_form(odds):
        if odds < 1.40: return "WWWDW" # Super favorit
        if odds < 1.80: return "WDLWW" # Favorit
        if odds < 2.50: return "WLWDL" # Vyrovnané
        return "LLDLW" # Outsider
    
    return {
        "utok_domaci": att_h, "utok_hostia": att_a,
        "forma_domaci": get_form(o1), "forma_hostia": get_form(o2),
        "zranenia": random.choice(["Bez absencií", "Otázny štart kapitána", "Kompletná zostava", "Chýba najlepší strelec"])
    }

# --- 2. AI ENGINE (Gemini Texty) ---
def get_ai_text(home, away, o1, o2, tip):
    """
    Toto je 'Kreatívec'. Dostane čísla a napíše k nim príbeh.
    """
    
    # Fallback texty (ak zlyhá AI alebo nie je kľúč)
    default_text = f"Na základe kurzov {o1} vs {o2} je tip '{tip}' štatisticky najpravdepodobnejší."
    default_body = ["Hodnota v kurze.", "Forma tímov zodpovedá predikcii.", "Dôležitý zápas."]

    if GEMINI_API_KEY == "VLOZ_SVOJ_GEMINI_KLUC_SEM":
        return default_text, default_body

    try:
        # Prompt pre Gemini
        prompt = f"""
        Analyzuj futbalový zápas {home} vs {away}. Kurzy sú: Domáci {o1}, Hostia {o2}.
        Náš matematický model odporúča tip: {tip}.
        Napíš 1 vetu analýzy prečo tento tip (v slovenčine).
        Potom napíš 3 krátke odrážky (dôvody).
        Nepoužívaj hviezdičky ani formátovanie, len čistý text.
        """
        response = model.generate_content(prompt)
        text_raw = response.text.split('\n')
        
        # Prvý riadok je hlavný text, zvyšok sú body
        main_text = text_raw[0]
        body_points = [line.strip('-• ') for line in text_raw[1:] if line.strip()][:3]
        
        if not body_points: body_points = default_body
        return main_text, body_points

    except:
        return default_text, default_body

def get_live_data():
    if time.time() - CACHE["last_update"] < 3600 and CACHE["data"]:
        return CACHE["data"]

    if ODDS_API_KEY == "VLOZ_SVOJ_ODDS_API_KLUC_SEM":
        return generate_demo_data()

    try:
        # Sťahujeme top ligy
        url = f"https://api.the-odds-api.com/v4/sports/soccer_epl/odds/?regions=eu&markets=h2h&apiKey={ODDS_API_KEY}"
        # (Poznámka: Vo Free verzii Odds API môžeš stiahnuť len určité ligy naraz)
        
        response = requests.get(url)
        data = response.json()
        
        matches = []
        # Spracujeme max 8 zápasov (aby sme nepreťažili free Gemini limit naraz)
        for item in data[:8]: 
            try:
                bookmakers = item.get('bookmakers', [])
                if not bookmakers: continue
                odds = bookmakers[0]['markets'][0]['outcomes']
                home = item['home_team']
                away = item['away_team']
                o1 = next((x['price'] for x in odds if x['name'] == home), 0)
                o2 = next((x['price'] for x in odds if x['name'] == away), 0)
                if o1 == 0 or o2 == 0: continue

                # 1. SMART LOGIC (Rýchla matematika)
                risk = 1; tip = "1"; dovera = 75
                if o1 < 1.50: risk = 1; tip = "1"; dovera = random.randint(88, 95)
                elif o2 < 1.50: risk = 1; tip = "2"; dovera = random.randint(88, 95)
                elif o1 < 2.10: risk = 2; tip = "1"; dovera = random.randint(65, 80)
                elif o2 < 2.10: risk = 2; tip = "2"; dovera = random.randint(65, 80)
                else: risk = 3; tip = "X"; dovera = random.randint(40, 60)

                stats = calculate_smart_stats(o1, o2)

                # 2. GEMINI AI (Kreatívny text)
                # Voláme len ak máme kľúč, inak fallback
                analyza_text, analyza_body = get_ai_text(home, away, o1, o2, tip)

                matches.append({
                    "domaci": home, "hostia": away, 
                    "kurz": o1 if tip=="1" else (o2 if tip=="2" else 3.10),
                    "tip": tip, "risk": risk, "liga": item['sport_title'], 
                    "dovera": dovera, "stats": stats, 
                    "analyza_text": analyza_text, "analyza_body": analyza_body
                })
            except: continue
        
        CACHE["data"] = matches
        CACHE["last_update"] = time.time()
        return matches

    except: return generate_demo_data()

def generate_demo_data():
    return [{"domaci": "AI DEMO", "hostia": "VLOŽ KĽÚČE", "kurz": 1.00, "tip": "Nastavenia", "risk": 1, "liga": "System", "dovera": 0, "stats": {"utok_domaci":0, "utok_hostia":0, "forma_domaci": "-", "forma_hostia": "-", "zranenia": "-"}, "analyza_text": "Vlož API kľúče pre Gemini a Odds API.", "analyza_body": []}]

# --- API ENDPOINTS ---
@app.get("/api/analyza")
def get_analysis(): return get_live_data()

@app.get("/api/tiket-dna")
def get_ticket_day():
    data = get_live_data()
    safe = [m for m in data if m['risk'] == 1]
    return safe[:3] if safe else data[:3]

@app.get("/api/vlastny-tiket")
def get_custom(risk: int = 1):
    data = get_live_data()
    return [m for m in data if m['risk'] == risk]

class WhopInput(BaseModel): message: str
@app.post("/whop")
def whop(data: WhopInput): return {"status": "ok"}


# --- HTML FRONTEND (S novou sekciou "AI Insight") ---
html_content = """
<!DOCTYPE html>
<html lang="sk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Betting PRO AI</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        :root { --bg-dark: #050a10; --bg-card: #151b24; --primary: #66fcf1; --text-main: #c5c6c7; --green: #00ff88; --red: #ff4444; }
        body { margin: 0; padding: 0; font-family: 'Segoe UI', sans-serif; background-color: #0b0c10; color: var(--text-main); height: 100vh; overflow: hidden; display: flex; flex-direction: column; }
        
        .sidebar { width: 260px; background-color: #111; display: flex; flex-direction: column; padding: 25px; border-right: 1px solid #333; }
        .logo { font-size: 24px; font-weight: 800; color: var(--primary); margin-bottom: 40px; text-transform: uppercase; text-align: center; }
        .menu-item { padding: 15px; margin-bottom: 5px; cursor: pointer; border-radius: 8px; color: #888; font-weight: 600; }
        .menu-item.active { background-color: #1f2833; color: #fff; border-left: 4px solid var(--primary); }
        
        .main-content { flex: 1; padding: 40px; overflow-y: auto; background: radial-gradient(circle at top right, #1f2833 0%, #0b0c10 80%); }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; border-bottom: 1px solid #333; padding-bottom: 20px; }
        
        /* GEMINI AI BADGE */
        .gemini-badge { 
            background: linear-gradient(45deg, #4285f4, #9b72cb); color: white; 
            padding: 5px 10px; border-radius: 4px; font-size: 10px; font-weight: bold; letter-spacing: 1px;
            display: inline-block; margin-bottom: 10px;
        }

        .analysis-card { background: #11161d; border-radius: 12px; margin-bottom: 20px; border: 1px solid #2c3e50; padding: 20px; animation: slideUp 0.5s ease; }
        .ac-header { padding-bottom: 15px; border-bottom: 1px solid #2c3e50; display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
        .ac-teams { font-size: 20px; font-weight: 800; color: #fff; }
        .ac-body { display: flex; gap: 20px; }
        .ac-left { flex: 1; min-width: 200px; }
        .ac-right { flex: 1.2; padding-left: 10px; border-left: 1px solid #222; }
        
        .ac-text { font-size: 14px; line-height: 1.6; color: #ccc; margin-bottom: 15px; font-style: italic; }
        .ac-list li { color: #aaa; font-size: 13px; margin-bottom: 5px; }
        .ac-tip-box { background: #1a222e; padding: 15px; border-left: 4px solid var(--primary); display: flex; justify-content: space-between; align-items: center; }
        
        .btn-analyze { background: var(--primary); border: none; padding: 15px 40px; font-size: 16px; font-weight: 800; color: #0b0c10; border-radius: 50px; cursor: pointer; display: block; margin: 0 auto; }
        
        /* Mobile */
        @media (max-width: 768px) {
            .sidebar { display: none; }
            .mobile-nav { display: flex; position: fixed; bottom: 0; left: 0; width: 100%; background: #111; justify-content: space-around; padding: 10px; z-index: 999; border-top: 1px solid #333; }
            .ac-body { flex-direction: column; } .ac-right { border-left: none; padding-left: 0; padding-top: 20px; border-top: 1px solid #222; }
        }
        
        .page { display: none; } .page.active { display: block; }
        @keyframes slideUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
    </style>
</head>
<body>

    <!-- PC SIDEBAR -->
    <div class="sidebar">
        <div class="logo">⚡ BET PRO</div>
        <div class="menu-item active" onclick="showPage('home', this)">🏠 Dashboard</div>
        <div class="menu-item" onclick="showPage('generator', this)">🧠 AI Analýza</div>
        <div class="menu-item" onclick="showPage('ticket-day', this)">🎯 Tiket Dňa</div>
    </div>

    <!-- MAIN -->
    <div class="main-content">
        <div class="header">
            <h1>Betting Intelligence</h1>
            <div style="text-align:right; font-weight:bold; color:var(--primary);">LIVE</div>
        </div>

        <div id="home" class="page active">
            <div style="text-align:center; margin-top:50px;">
                <h2 style="color:white;">Vitaj v systéme</h2>
                <p style="color:#888;">Použi menu na generovanie analýz.</p>
            </div>
        </div>

        <div id="generator" class="page">
            <div style="text-align:center; margin-bottom:30px;">
                <button class="btn-analyze" onclick="loadAnalysis()">SPUSTIŤ GEMINI AI</button>
            </div>
            <div id="analysis-output"></div>
        </div>

        <div id="ticket-day" class="page">
            <div id="ticket-dna-result"></div>
        </div>
    </div>
    
    <div class="mobile-nav" style="display:none;">
        <span onclick="showPage('home')" style="color:#666; font-size:24px;">🏠</span>
        <span onclick="showPage('generator')" style="color:#666; font-size:24px;">🧠</span>
        <span onclick="showPage('ticket-day')" style="color:#666; font-size:24px;">🎯</span>
    </div>

    <script>
        function showPage(id, el) {
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.menu-item').forEach(m => m.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            if(el) el.classList.add('active');
        }

        async function loadAnalysis() {
            const div = document.getElementById('analysis-output');
            div.innerHTML = '<p style="text-align:center;color:#66fcf1">Gemini AI analyzuje zápasy...</p>';
            try {
                const res = await fetch('/api/analyza'); const data = await res.json();
                let html = '';
                data.forEach(m => {
                    let listHtml = ''; if(m.analyza_body) m.analyza_body.forEach(li => listHtml += `<li>${li}</li>`);
                    html += `
                    <div class="analysis-card">
                        <div class="ac-header"><div class="ac-teams">${m.domaci} vs ${m.hostia}</div><div style="color:#66fcf1; font-weight:bold;">${m.kurz}</div></div>
                        <div class="ac-body">
                            <div class="ac-left">
                                <div style="margin-bottom:10px; color:#888; font-size:12px;">ŠTATISTIKY MODELU</div>
                                <div style="display:flex; justify-content:space-between; margin-bottom:5px;"><span>Útok Domáci</span><span style="color:white;">${m.stats.utok_domaci}</span></div>
                                <div style="display:flex; justify-content:space-between;"><span>Útok Hostia</span><span style="color:white;">${m.stats.utok_hostia}</span></div>
                            </div>
                            <div class="ac-right">
                                <span class="gemini-badge">GEMINI AI INSIGHT</span>
                                <div class="ac-text">"${m.analyza_text}"</div>
                                <ul class="ac-list" style="color:#888; padding-left:20px;">${listHtml}</ul>
                                <div class="ac-tip-box">
                                    <span style="color:white; font-weight:bold;">TIP: ${m.tip}</span>
                                    <span style="color:#66fcf1;">${m.dovera}%</span>
                                </div>
                            </div>
                        </div>
                    </div>`;
                });
                div.innerHTML = html;
            } catch(e) { div.innerHTML = "Chyba API."; }
        }

        if(window.innerWidth < 768) document.querySelector('.mobile-nav').style.display = 'flex';
    </script>
</body>
</html>
