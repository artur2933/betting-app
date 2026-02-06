import requests
import random
import time
import os
import google.generativeai as genai
from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from dateutil import parser 

app = FastAPI()

# ==========================================
# 🔑 API KĽÚČE (VLOŽ OBA SEM!)
# ==========================================
# 1. Dáta (Kurzy): https://the-odds-api.com/
ODDS_API_KEY = "3e42c726ab364fb9eeede03b0017964c"    

# 2. AI (Texty): https://aistudio.google.com/app/apikey
GEMINI_API_KEY = "AIzaSyCreRpXTUwxzJegxQKUJ2RiX5BwSagdljg"    
# ==========================================

# Nastavenie Gemini
if GEMINI_API_KEY != "AIzaSyCreRpXTUwxzJegxQKUJ2RiX5BwSagdljg":
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-pro')
    except: pass

CACHE = {"data": [], "last_update": 0}

# --- 1. SMART LOGIC (Matematika) ---
def calculate_smart_stats(o1, o2):
    """Vypočíta štatistiky na základe kurzov"""
    try:
        prob_h = (1 / o1) * 100
        prob_a = (1 / o2) * 100
    except ZeroDivisionError:
        prob_h, prob_a = 50, 50
    
    att_h = min(99, int(prob_h + random.randint(-5, 5)))
    att_a = min(99, int(prob_a + random.randint(-5, 5)))
    
    def get_form(odds):
        if odds < 1.40: return "WWWDW" 
        if odds < 1.80: return "WDLWW" 
        if odds < 2.50: return "WLWDL" 
        return "LLDLW" 
    
    return {
        "utok_domaci": att_h, "utok_hostia": att_a,
        "forma_domaci": get_form(o1), "forma_hostia": get_form(o2),
        "zranenia": random.choice(["Bez absencií", "Otázny štart kapitána", "Kompletná zostava", "Chýba najlepší strelec"])
    }

# --- 2. AI ENGINE (Gemini Texty) ---
def get_ai_text(home, away, o1, o2, tip):
    """Vygeneruje text pomocou Gemini alebo fallback"""
    
    default_text = f"Na základe kurzov {o1} vs {o2} je tip '{tip}' štatisticky najpravdepodobnejší."
    default_body = ["Hodnota v kurze.", "Forma tímov zodpovedá predikcii.", "Dôležitý zápas."]

    if GEMINI_API_KEY == "AIzaSyCreRpXTUwxzJegxQKUJ2RiX5BwSagdljg":
        return default_text, default_body

    try:
        prompt = f"""
        Analyzuj futbalový zápas {home} vs {away}. Kurzy sú: Domáci {o1}, Hostia {o2}.
        Náš model odporúča tip: {tip}.
        Napíš 1 vetu analýzy prečo tento tip (v slovenčine).
        Potom napíš 3 krátke odrážky (dôvody).
        Nepoužívaj hviezdičky ani formátovanie, len čistý text.
        """
        response = model.generate_content(prompt)
        text_raw = response.text.split('\n')
        
        main_text = text_raw[0]
        # Vyčistenie odrážok
        body_points = [line.strip('-•* ') for line in text_raw[1:] if line.strip()]
        
        if not body_points: body_points = default_body
        return main_text, body_points[:3]

    except:
        return default_text, default_body

def get_live_data():
    if time.time() - CACHE["last_update"] < 3600 and CACHE["data"]:
        return CACHE["data"]

    if ODDS_API_KEY == "AIzaSyCreRpXTUwxzJegxQKUJ2RiX5BwSagdljg":
        return generate_demo_data()

    try:
        url = f"https://api.the-odds-api.com/v4/sports/soccer_epl/odds/?regions=eu&markets=h2h&apiKey={ODDS_API_KEY}"
        
        response = requests.get(url)
        data = response.json()
        
        matches = []
        for item in data[:10]: 
            try:
                bookmakers = item.get('bookmakers', [])
                if not bookmakers: continue
                odds = bookmakers[0]['markets'][0]['outcomes']
                home = item['home_team']
                away = item['away_team']
                o1 = next((x['price'] for x in odds if x['name'] == home), 0)
                o2 = next((x['price'] for x in odds if x['name'] == away), 0)
                if o1 == 0 or o2 == 0: continue

                risk = 1; tip = "1"; dovera = 75
                if o1 < 1.50: risk = 1; tip = "1"; dovera = random.randint(88, 95)
                elif o2 < 1.50: risk = 1; tip = "2"; dovera = random.randint(88, 95)
                elif o1 < 2.10: risk = 2; tip = "1"; dovera = random.randint(65, 80)
                elif o2 < 2.10: risk = 2; tip = "2"; dovera = random.randint(65, 80)
                else: risk = 3; tip = "X"; dovera = random.randint(40, 60)

                stats = calculate_smart_stats(o1, o2)
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
    return [{"domaci": "AI DEMO", "hostia": "VLOŽ KĽÚČE", "kurz": 1.00, "tip": "Nastavenia", "risk": 1, "liga": "System", "dovera": 0, "stats": {"utok_domaci":0, "utok_hostia":0, "forma_domaci": "-", "forma_hostia": "-", "zranenia": "-"}, "analyza_text": "Vlož API kľúče pre Gemini a Odds API do súboru main.py", "analyza_body": []}]

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


# --- HTML FRONTEND (BLUE CYBERPUNK) ---
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

        .analysis-card { background: #11161d; border-radius: 12px; margin-bottom: 20px; border: 1px solid #2c3e50; padding: 20px; animation: slideUp 0.5s ease; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }
        .ac-header { padding-bottom: 15px; border-bottom: 1px solid #2c3e50; display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
        .ac-teams { font-size: 20px; font-weight: 800; color: #fff; }
        .ac-body { display: flex; gap: 20px; }
        .ac-left { flex: 1; min-width: 200px; }
        .ac-right { flex: 1.2; padding-left: 10px; border-left: 1px solid #222; }
        
        .ac-text { font-size: 14px; line-height: 1.6; color: #ccc; margin-bottom: 15px; font-style: italic; }
        .ac-list li { color: #aaa; font-size: 13px; margin-bottom: 5px; list-style-type: none; }
        .ac-list li:before { content: "• "; color: var(--primary); }
        
        .ac-tip-box { background: #1a222e; padding: 15px; border-left: 4px solid var(--primary); display: flex; justify-content: space-between; align-items: center; }
        .ac-tip-value { font-size: 20px; font-weight: 800; color: #fff; }
        .ac-conf-badge { background: var(--primary); color: #000; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }
        
        .btn-analyze { background: var(--primary); border: none; padding: 15px 40px; font-size: 16px; font-weight: 800; color: #0b0c10; border-radius: 50px; cursor: pointer; display: block; margin: 0 auto; box-shadow: 0 0 20px rgba(102, 252, 241, 0.4); transition: 0.3s; }
        .btn-analyze:hover { transform: scale(1.05); background: white; }
        
        .btn-bet { background: transparent; border: 1px solid var(--primary); color: var(--primary); padding: 8px 20px; border-radius: 5px; cursor: pointer; font-weight: bold; width: 100%; transition: 0.2s; }
        .btn-bet:hover { background: var(--primary); color: black; }

        /* TICKET STYLE */
        .ticket-wrapper { max-width: 600px; margin: 0 auto 30px auto; background: #151b24; border: 2px solid var(--primary); border-radius: 12px; overflow: hidden; animation: slideUp 0.5s ease; box-shadow: 0 0 40px rgba(102, 252, 241, 0.2); }
        .ticket-header { background: rgba(102, 252, 241, 0.1); padding: 20px; text-align: center; border-bottom: 1px solid var(--primary); }
        .ticket-title { font-size: 24px; font-weight: 900; color: var(--primary); margin: 0; letter-spacing: 2px; text-transform: uppercase; }
        .ticket-body { padding: 20px; }
        .ticket-row { display: flex; justify-content: space-between; padding: 15px; border-bottom: 1px dashed #444; align-items: center; }
        .ticket-footer { background: #0b0c10; padding: 20px; display: flex; justify-content: space-between; font-weight: bold; font-size: 20px; color: var(--primary); border-top: 1px solid #333; }
        .btn-ticket { width: 100%; padding: 18px; background: var(--primary); border: none; font-weight: 800; cursor: pointer; color: black; font-size: 18px; text-transform: uppercase; }
        .btn-ticket:hover { background: white; }

        .gen-controls { max-width: 600px; margin: 0 auto; background: #151b24; padding: 30px; border-radius: 12px; }
        select { width: 100%; padding: 15px; background: #0b0c10; border: 1px solid #333; color: #fff; border-radius: 8px; font-size: 16px; margin-bottom: 20px; outline: none; }
        label { color: var(--primary); font-weight: bold; font-size: 12px; margin-bottom: 5px; display: block; }

        .page { display: none; } .page.active { display: block; animation: fadeIn 0.4s; }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        @keyframes slideUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
        
        table { width: 100%; border-collapse: collapse; margin-top: 20px; color: #ccc; font-size: 14px; }
        th { text-align: left; padding: 10px; border-bottom: 1px solid #333; color:#666; font-size:10px; text-transform:uppercase; }
        td { padding: 10px; border-bottom: 1px solid #222; }
        .win { color: var(--green); font-weight: bold; } .lose { color: var(--red); font-weight: bold; } .pending { color: var(--yellow); }
        
        /* Mobile */
        @media (max-width: 768px) {
            .sidebar { display: none; }
            .mobile-nav { display: flex; position: fixed; bottom: 0; left: 0; width: 100%; background: #111; justify-content: space-around; padding: 10px; z-index: 999; border-top: 1px solid #333; }
            .ac-body { flex-direction: column; } .ac-right { border-left: none; padding-left: 0; padding-top: 20px; border-top: 1px solid #222; }
        }
    </style>
</head>
<body>

    <!-- PC SIDEBAR -->
    <div class="sidebar">
        <div class="logo">⚡ BET PRO</div>
        <div class="menu-item active" onclick="showPage('home', this)">🏠 Dashboard</div>
        <div class="menu-item" onclick="showPage('generator', this)">🧠 AI Analýza</div>
        <div class="menu-item" onclick="showPage('ticket-day', this)">🎯 Tiket Dňa</div>
        <div class="menu-item" onclick="showPage('custom-ticket', this)">🛠️ Vlastný Tiket</div>
        <div class="menu-item" onclick="showPage('results-page', this); renderHistory()">✅ História</div>
        <div class="menu-item" onclick="resetApp()" style="margin-top:auto; color:var(--red)">🗑️ Resetovať</div>
    </div>

    <!-- MAIN -->
    <div class="main-content">
        <div class="header">
            <h1>Prehľad</h1>
            <div style="text-align:right;">
                <div style="font-size:10px; color:#666; margin-bottom:2px;">BANKROLL</div>
                <div style="font-size:24px; font-weight:bold; color:var(--primary);" id="bankroll-display">€1,000.00</div>
            </div>
        </div>

        <!-- 1. DASHBOARD -->
        <div id="home" class="page active">
            <div style="display:flex; flex-wrap:wrap; gap:15px; margin-bottom:30px;">
                <div class="dash-card" style="background:#151b24; padding:20px; border-radius:16px; border:1px solid #2c3e50; flex:1; text-align:center;"><h3>Stav Konta</h3><h1 id="dash-bankroll" style="color:white; margin:10px 0;">€1,000</h1></div>
                <div class="dash-card" style="background:#151b24; padding:20px; border-radius:16px; border:1px solid #2c3e50; flex:1; text-align:center;"><h3>Simulácia</h3><p style="color:#888; font-size:12px; margin-bottom:10px;">Vyhodnotiť tikety</p><button class="btn-analyze" style="padding:10px; font-size:12px; width:auto;" onclick="evaluateTickets()">🔄 Spustiť</button></div>
            </div>
            <div class="chart-box" style="background:#151b24; padding:15px; border-radius:16px; border:1px solid #2c3e50;">
                <canvas id="profitChart" height="200"></canvas>
            </div>
        </div>

        <!-- 2. VIP ANALÝZA (Bez Vsaďiť) -->
        <div id="generator" class="page">
            <div style="text-align:center; margin-bottom:30px;">
                <button class="btn-analyze" onclick="loadAnalysis()">Načítať Live Analýzy</button>
            </div>
            <div id="analysis-output"></div>
        </div>

        <!-- 3. TIKET DŇA (S Vsaďiť) -->
        <div id="ticket-day" class="page">
            <div style="text-align:center; margin-bottom:30px;">
                <h2 style="color:var(--primary)">🔥 DENNÁ TUTOVKA</h2>
                <button class="btn-analyze" onclick="loadTiketDna()">VYGENEROVAŤ TIKET</button>
            </div>
            <div id="ticket-dna-result"></div>
        </div>

        <!-- 4. VLASTNÝ GENERÁTOR (S Vsaďiť) -->
        <div id="custom-ticket" class="page">
            <div class="gen-controls">
                <label>RIZIKO</label><select id="riskLevel"><option value="1">🟢 Nízke</option><option value="2">🟡 Stredné</option><option value="3">🔴 Vysoké</option></select>
                <label>POČET ZÁPASOV</label><select id="matchCount"><option value="2">2 Zápasy</option><option value="3">3 Zápasy</option><option value="5">5 Zápasov</option></select>
                <button class="btn-analyze" style="width:100%" onclick="loadCustom()">GENEROVAŤ TIKET</button>
            </div>
            <div id="custom-ticket-output" style="margin-top:30px;"></div>
        </div>

        <!-- 5. HISTÓRIA -->
        <div id="results-page" class="page">
            <h2>Moje Tikety</h2>
            <div id="history-output"></div>
        </div>
    </div>
    
    <!-- MOBILE NAV -->
    <div class="mobile-nav" style="display:none;">
        <span onclick="showPage('home')" style="color:#666; font-size:24px;">🏠</span>
        <span onclick="showPage('generator')" style="color:#666; font-size:24px;">🧠</span>
        <span onclick="showPage('ticket-day')" style="color:#666; font-size:24px;">🎯</span>
        <span onclick="showPage('results-page'); renderHistory()" style="color:#666; font-size:24px;">✅</span>
    </div>

    <script>
        // --- KLIENTSKSÁ LOGIKA ---
        let bankroll = parseFloat(localStorage.getItem('betpro_bankroll')) || 1000.00;
        let history = JSON.parse(localStorage.getItem('betpro_history')) || [];
        updateUI();

        // Graf
        let chart;
        function initChart() {
            const ctx = document.getElementById('profitChart').getContext('2d');
            let dataPoints = history.length ? history.map(t => t.balance_after || 1000).reverse() : [1000, 1000];
            if(history.length === 0) dataPoints = [1000, 1000, 1000, 1000, 1000];
            if(chart) chart.destroy();
            chart = new Chart(ctx, {
                type: 'line',
                data: { labels: dataPoints.map((_, i) => ''), datasets: [{ label: 'Bankroll', data: dataPoints, borderColor: '#66fcf1', backgroundColor: 'rgba(102, 252, 241, 0.1)', fill: true, tension: 0.4 }] },
                options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { grid: { color: '#2c3e50' } }, x: { display: false } } }
            });
        }
        setTimeout(initChart, 500);

        function showPage(id, el) {
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.menu-item').forEach(m => m.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            if(el) el.classList.add('active');
        }

        function updateUI() {
            document.getElementById('bankroll-display').innerText = '€' + bankroll.toFixed(2);
            document.getElementById('dash-bankroll').innerText = '€' + bankroll.toFixed(2);
            localStorage.setItem('betpro_bankroll', bankroll);
            localStorage.setItem('betpro_history', JSON.stringify(history));
        }

        function resetApp() { if(confirm("Naozaj?")) { localStorage.clear(); location.reload(); } }

        // --- FETCHING ---
        async function loadAnalysis() {
            const div = document.getElementById('analysis-output');
            div.innerHTML = '<p style="text-align:center;color:#66fcf1">Načítavam...</p>';
            try {
                const res = await fetch('/api/analyza'); const data = await res.json();
                let html = '';
                data.forEach(m => {
                    let listHtml = ''; if(m.analyza_body) m.analyza_body.forEach(li => listHtml += `<li>${li}</li>`);
                    const circles = (f) => { let h=''; for(let c of f) h+=`<div class="ac-dot ${c==='W'?'v':(c==='L'?'p':'r')}">${c==='W'?'V':(c==='L'?'P':'R')}</div>`; return h; };
                    
                    html += `
                    <div class="analysis-card">
                        <div class="ac-header"><div class="ac-teams">${m.domaci} vs ${m.hostia}</div><div style="background:#1a2634; color:#66fcf1; padding:5px 10px; border-radius:5px;">${m.kurz}</div></div>
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

        async function loadTiketDna() { renderTicketSection('/api/tiket-dna', 'ticket-dna-result', 'VIP TIKET DŇA'); }
        async function loadCustom() { 
            const r = document.getElementById('riskLevel').value; const c = document.getElementById('matchCount').value;
            renderTicketSection(`/api/vlastny-tiket?risk=${r}&count=${c}`, 'custom-ticket-output', 'TVOJ TIKET'); 
        }

        async function renderTicketSection(url, elId, title) {
            const div = document.getElementById(elId);
            div.innerHTML = '<p style="text-align:center;color:#66fcf1">Generujem...</p>';
            const res = await fetch(url); const data = await res.json();
            if(data.length === 0) { div.innerHTML = "Žiadne dáta."; return; }
            
            let rows = ''; let total = 1; let ticketInfo = [];
            data.forEach(m => {
                total *= m.kurz; ticketInfo.push(`${m.domaci} (${m.tip})`);
                rows += `<div class="ticket-row"><div><div style="font-weight:bold; color:white;">${m.domaci} - ${m.hostia}</div><div style="color:#888; font-size:12px;">Tip: ${m.tip}</div></div><div style="color:var(--primary); font-weight:bold;">${m.kurz}</div></div>`;
            });
            div.innerHTML = `<div class="ticket-wrapper"><div class="ticket-header"><h2 style="margin:0; color:var(--primary);">${title}</h2></div><div class="ticket-body">${rows}</div><div class="ticket-footer"><div style="color:#888;">CELKOVÝ KURZ</div><div style="font-size:24px; font-weight:bold; color:var(--primary);">${total.toFixed(2)}</div></div><button class="btn-ticket" onclick='saveTicket(${total.toFixed(2)}, ${JSON.stringify(ticketInfo)})'>VSAĎIŤ 50€</button></div>`;
        }

        function saveTicket(odds, matches) {
            if(bankroll < 50) { alert("Nemáš dosť peňazí!"); return; }
            bankroll -= 50;
            history.unshift({ matches: matches.join(", "), odds: odds, stake: 50, status: "PENDING", profit: 0, date: new Date().toLocaleString(), balance_after: bankroll });
            updateUI(); alert("Tiket uložený!"); initChart();
        }

        function evaluateTickets() {
            let changes = false;
            history.forEach(t => {
                if(t.status === "PENDING") {
                    let won = Math.random() < 0.55; 
                    t.status = won ? "WON" : "LOST";
                    t.profit = won ? (t.stake * t.odds) : 0;
                    if(won) bankroll += t.profit;
                    t.balance_after = bankroll;
                    changes = true;
                }
            });
            if(changes) { updateUI(); renderHistory(); initChart(); alert("Tikety vyhodnotené!"); } else { alert("Žiadne nové tikety."); }
        }

        function renderHistory() {
            const div = document.getElementById('history-output');
            if(history.length === 0) { div.innerHTML = "<p style='color:#666'>Žiadna história.</p>"; return; }
            let html = '<table style="width:100%; text-align:left; color:#ccc;"><tr><th>Dátum</th><th>Zápasy</th><th>Kurz</th><th>Stav</th><th>Zisk</th></tr>';
            history.forEach(t => {
                let color = t.status === "WON" ? "#00ff88" : (t.status === "LOST" ? "#ff4444" : "#ffcc00");
                html += `<tr><td>${t.date}</td><td>${t.matches}</td><td>${t.odds}</td><td style="color:${color}; font-weight:bold;">${t.status}</td><td>€${t.profit.toFixed(2)}</td></tr>`;
            });
            div.innerHTML = html + '</table>';
        }
        
        if(window.innerWidth < 768) { document.querySelector('.mobile-nav').style.display = 'flex'; }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def home(): return html_content
