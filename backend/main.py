import requests
import random
import time
import json
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI()

# ==========================================
# 🔑 MIESTO PRE TVOJ KĽÚČ (ZADARMO)
# Získaj ho tu: https://the-odds-api.com/
# ==========================================
API_KEY = "3e42c726ab364fb9eeede03b0017964c" 
# ==========================================

# Cache pre dáta (aby sme neplatili za každé načítanie)
CACHE = {"data": [], "last_update": 0}

def get_live_matches():
    # 1. Ak máme čerstvé dáta (menej ako 45 minút), použijeme tie
    if time.time() - CACHE["last_update"] < 2700 and CACHE["data"]:
        return CACHE["data"]

    # 2. Ak nie je kľúč, vrátime DEMO (aby appka nespadla)
    if API_KEY == "VLOZ_SVOJ_API_KLUC_SEM" or not API_KEY:
        return get_demo_data()

    # 3. Sťahujeme z internetu
    try:
        # Sťahujeme futbal
        url = f"https://api.the-odds-api.com/v4/sports/soccer/odds/?regions=eu&markets=h2h&apiKey={API_KEY}"
        response = requests.get(url)
        
        if response.status_code != 200:
            return get_demo_data() # Ak API zlyhá, vráť demo
            
        data = response.json()
        matches = []
        
        for item in data[:20]: # Limit 20 zápasov
            try:
                bookmakers = item.get('bookmakers', [])
                if not bookmakers: continue
                
                # Získame kurzy
                odds = bookmakers[0]['markets'][0]['outcomes']
                home = item['home_team']
                away = item['away_team']
                
                # Nájdenie kurzov
                o1 = next((x['price'] for x in odds if x['name'] == home), 0)
                o2 = next((x['price'] for x in odds if x['name'] == away), 0)
                
                if o1 == 0 or o2 == 0: continue

                # AI Logika (Výpočet tipu)
                risk = 1
                tip = "1"
                dovera = 75
                analyza = "Vyrovnaný zápas."
                
                # Logika pre favorita
                if o1 < 1.45:
                    risk = 1; tip = "1"; dovera = random.randint(88, 98)
                    analyza = f"{home} je doma dominantný. {away} má problémy v obrane."
                elif o2 < 1.45:
                    risk = 1; tip = "2"; dovera = random.randint(88, 98)
                    analyza = f"{away} bojuje o titul a má lepšiu formu."
                elif o1 < 2.05:
                    risk = 2; tip = "1"; dovera = random.randint(65, 80)
                    analyza = "Domáce prostredie bude rozhodujúce."
                elif o2 < 2.05:
                    risk = 2; tip = "2"; dovera = random.randint(65, 80)
                    analyza = "Hostia majú kvalitnejší káder."
                else:
                    risk = 3; tip = "X"; dovera = random.randint(40, 55)
                    analyza = "Vysoké kurzy naznačujú remízu."

                # Generovanie štatistík
                matches.append({
                    "domaci": home, "hostia": away,
                    "kurz": o1 if tip=="1" else (o2 if tip=="2" else 3.10),
                    "tip": tip, "risk": risk, "liga": item['sport_title'].replace("Soccer ", ""), 
                    "dovera": dovera,
                    "stats": {
                        "utok_domaci": int(100/o1) if o1 > 1 else 95,
                        "utok_hostia": int(100/o2) if o2 > 1 else 95,
                        "forma_domaci": generate_form(o1),
                        "forma_hostia": generate_form(o2),
                        "zranenia": random.choice(["Bez absencií", "Otázny štart kapitána", "Kompletná zostava"])
                    },
                    "analyza_text": analyza
                })
            except: continue
        
        CACHE["data"] = matches
        CACHE["last_update"] = time.time()
        return matches

    except:
        return get_demo_data()

def generate_form(odds):
    if odds < 1.5: return "WWWDW"
    if odds < 2.2: return "WDLWW"
    return "LLDWL"

def get_demo_data():
    return [
        {"domaci": "Man City", "hostia": "Burnley", "kurz": 1.15, "tip": "1", "risk": 1, "liga": "Premier League", "dovera": 95, "stats": {"utok_domaci":95, "utok_hostia":20, "forma_domaci": "WWWWW", "forma_hostia": "LLLLL", "zranenia": "De Bruyne (Out)"}, "analyza_text": "City doma valcuje. Tutovka."},
        {"domaci": "Barcelona", "hostia": "Getafe", "kurz": 1.30, "tip": "1", "risk": 1, "liga": "La Liga", "dovera": 88, "stats": {"utok_domaci":85, "utok_hostia":30, "forma_domaci": "WDWWW", "forma_hostia": "DLLLL", "zranenia": "Gavi (Out)"}, "analyza_text": "Barca potrebuje body. Getafe vonku neškodné."},
        {"domaci": "Arsenal", "hostia": "Chelsea", "kurz": 2.10, "tip": "1", "risk": 2, "liga": "Premier League", "dovera": 70, "stats": {"utok_domaci":75, "utok_hostia":65, "forma_domaci": "WWDLW", "forma_hostia": "WLDLW", "zranenia": "-"}, "analyza_text": "Derby o Londýn. Arsenal má lepšiu formu."},
        {"domaci": "Dortmund", "hostia": "Lipsko", "kurz": 2.45, "tip": "X", "risk": 3, "liga": "Bundesliga", "dovera": 45, "stats": {"utok_domaci":70, "utok_hostia":72, "forma_domaci": "DDWLD", "forma_hostia": "WWWWL", "zranenia": "-"}, "analyza_text": "Vyrovnaný zápas o Ligu Majstrov."}
    ]

# --- API ENDPOINTS ---
@app.get("/api/data")
def api_data():
    return get_live_matches()

@app.get("/api/tiket-dna")
def api_ticket_day():
    data = get_live_matches()
    # Vyberie najlepšie tutovky (risk 1)
    safe = [m for m in data if m['risk'] == 1]
    if len(safe) < 2: safe = [m for m in data if m['risk'] <= 2]
    return safe[:3]

@app.get("/api/vlastny-tiket")
def api_custom(risk: int = 1, count: int = 2):
    data = get_live_matches()
    filtered = [m for m in data if m['risk'] == risk]
    if len(filtered) < count: filtered = data # Fallback
    return filtered[:count]

class WhopInput(BaseModel):
    message: str

@app.post("/whop")
def whop(data: WhopInput): return {"status": "ok"}


# --- HTML FRONTEND (BLUE CYBERPUNK - FINAL) ---
html_content = """
<!DOCTYPE html>
<html lang="sk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Betting PRO Analytics</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        :root { --bg-dark: #050a10; --bg-card: #151b24; --primary: #66fcf1; --text-main: #c5c6c7; --green: #00ff88; --red: #ff4444; --yellow: #ffcc00; }
        body { margin: 0; padding: 0; font-family: 'Segoe UI', sans-serif; background-color: #0b0c10; color: var(--text-main); height: 100vh; overflow: hidden; display: flex; }
        
        .sidebar { width: 260px; background-color: #111; display: flex; flex-direction: column; padding: 25px; border-right: 1px solid #333; }
        .logo { font-size: 24px; font-weight: 800; color: var(--primary); margin-bottom: 40px; text-transform: uppercase; text-align: center; text-shadow: 0 0 10px rgba(102, 252, 241, 0.4); }
        .menu-item { padding: 15px; margin-bottom: 5px; cursor: pointer; border-radius: 8px; color: #888; font-weight: 600; transition: 0.3s; }
        .menu-item:hover, .menu-item.active { background-color: #1f2833; color: #fff; border-left: 4px solid var(--primary); }
        
        .main-content { flex: 1; padding: 40px; overflow-y: auto; background: radial-gradient(circle at top right, #1f2833 0%, #0b0c10 80%); }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 40px; border-bottom: 1px solid #333; padding-bottom: 20px; }
        
        .dash-card { background: var(--bg-card); padding: 25px; border-radius: 16px; border: 1px solid #2c3e50; flex: 1; margin-right: 20px; text-align: center; }
        .dash-card h1 { font-size: 40px; color: white; margin: 10px 0; }
        
        .btn-analyze { background: var(--primary); border: none; padding: 15px 40px; font-size: 16px; font-weight: 800; color: #0b0c10; border-radius: 50px; cursor: pointer; box-shadow: 0 0 25px rgba(102, 252, 241, 0.3); transition: 0.2s; text-transform: uppercase; }
        .btn-analyze:hover { transform: scale(1.05); background: #fff; }
        .btn-bet { background: transparent; border: 1px solid var(--primary); color: var(--primary); padding: 8px 20px; border-radius: 5px; cursor: pointer; font-weight: bold; margin-top: 10px; width: 100%; }
        .btn-bet:hover { background: var(--primary); color: black; }
        
        .analysis-card { background: #11161d; border-radius: 12px; margin-bottom: 20px; border: 1px solid #2c3e50; padding: 20px; animation: slideUp 0.5s ease; }
        .ac-header { padding: 15px; background: #151b24; border-bottom: 1px solid #2c3e50; display: flex; justify-content: space-between; align-items: center; }
        .ac-teams { font-size: 22px; font-weight: 800; color: #fff; }
        
        /* TIKET STYLE */
        .ticket-wrapper { max-width: 600px; margin: 0 auto; background: #151b24; border: 2px solid var(--primary); border-radius: 12px; overflow: hidden; animation: slideUp 0.5s ease; }
        .ticket-header { background: rgba(102, 252, 241, 0.1); padding: 20px; text-align: center; border-bottom: 1px solid var(--primary); }
        .ticket-row { display: flex; justify-content: space-between; padding: 15px; border-bottom: 1px dashed #444; }
        .ticket-footer { background: #0b0c10; padding: 20px; display: flex; justify-content: space-between; font-weight: bold; font-size: 20px; color: var(--primary); }

        .gen-controls { max-width: 600px; margin: 0 auto; background: #151b24; padding: 30px; border-radius: 12px; }
        select { width: 100%; padding: 15px; background: #0b0c10; border: 1px solid #333; color: #fff; border-radius: 8px; margin-bottom: 20px; }

        .page { display: none; } .page.active { display: block; animation: fadeIn 0.4s; }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        @keyframes slideUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
        
        table { width: 100%; border-collapse: collapse; margin-top: 20px; color: #ccc; }
        th { text-align: left; padding: 10px; border-bottom: 1px solid #333; color:#666; font-size:12px; text-transform:uppercase; }
        td { padding: 15px 10px; border-bottom: 1px solid #222; }
        .win { color: var(--green); font-weight: bold; } .lose { color: var(--red); font-weight: bold; } .pending { color: var(--yellow); }
    </style>
</head>
<body>

    <div class="sidebar">
        <div class="logo">⚡ BET PRO</div>
        <div class="menu-item active" onclick="showPage('home', this)">🏠 Dashboard</div>
        <div class="menu-item" onclick="showPage('generator', this)">📊 VIP Analýza</div>
        <div class="menu-item" onclick="showPage('ticket-day', this)">🎯 Tiket Dňa</div>
        <div class="menu-item" onclick="showPage('custom-ticket', this)">🛠️ Vlastný Tiket</div>
        <div class="menu-item" onclick="showPage('results-page', this); renderHistory()">✅ História</div>
        <div class="menu-item" onclick="resetApp()" style="margin-top:auto; color:var(--red)">🗑️ Resetovať</div>
    </div>

    <div class="main-content">
        <div class="header">
            <h1>Prehľad</h1>
            <div style="text-align:right;">
                <div style="font-size:12px; color:#666;">BANKROLL</div>
                <div style="font-size:32px; font-weight:bold; color:var(--primary);" id="bankroll-display">€1,000.00</div>
            </div>
        </div>

        <!-- 1. DASHBOARD -->
        <div id="home" class="page active">
            <div style="display:flex; margin-bottom:30px;">
                <div class="dash-card"><h3>Stav Konta</h3><h1 id="dash-bankroll">€1,000</h1></div>
                <div class="dash-card"><h3>Vyhodnotenie</h3><p style="color:#888; margin-bottom:10px;">Simulovať zápasy a pripísať výhry</p><button class="btn-analyze" style="padding:10px 30px; font-size:14px;" onclick="evaluateTickets()">🔄 Skontrolovať Tikety</button></div>
            </div>
            <div style="background:#151b24; padding:20px; border-radius:16px; border:1px solid #2c3e50;">
                <h3 style="color:#fff; margin:0 0 20px 0;">Vývoj Zisku</h3>
                <canvas id="profitChart" height="100"></canvas>
            </div>
        </div>

        <!-- 2. VIP ANALÝZA -->
        <div id="generator" class="page">
            <div style="text-align:center; margin-bottom:30px;">
                <button class="btn-analyze" onclick="loadAnalysis()">Načítať Live Analýzy</button>
            </div>
            <div id="analysis-output"></div>
        </div>

        <!-- 3. TIKET DŇA -->
        <div id="ticket-day" class="page">
            <div style="text-align:center; margin-bottom:30px;">
                <h2 style="color:var(--primary)">🔥 DENNÁ TUTOVKA</h2>
                <button class="btn-analyze" onclick="loadTiketDna()">VYGENEROVAŤ TIKET</button>
            </div>
            <div id="ticket-dna-result"></div>
        </div>

        <!-- 4. VLASTNÝ GENERÁTOR -->
        <div id="custom-ticket" class="page">
            <div class="gen-controls">
                <label style="color:var(--primary);">RIZIKO</label>
                <select id="riskLevel"><option value="1">🟢 Nízke (1.2 - 1.5)</option><option value="2">🟡 Stredné (1.8 - 2.2)</option><option value="3">🔴 Vysoké (3.0+)</option></select>
                <label style="color:var(--primary);">POČET ZÁPASOV</label>
                <select id="matchCount"><option value="2">2 Zápasy</option><option value="3">3 Zápasy</option><option value="5">5 Zápasov</option></select>
                <button class="btn-analyze" style="width:100%" onclick="loadCustom()">GENEROVAŤ TIKET</button>
            </div>
            <div id="custom-ticket-result" style="margin-top:30px;"></div>
        </div>

        <!-- 5. HISTÓRIA -->
        <div id="results-page" class="page">
            <h2>Moje Tikety</h2>
            <div id="history-output"></div>
        </div>
    </div>

    <script>
        let bankroll = parseFloat(localStorage.getItem('betpro_bankroll')) || 1000.00;
        let history = JSON.parse(localStorage.getItem('betpro_history')) || [];
        updateUI();

        let chart;
        function initChart() {
            const ctx = document.getElementById('profitChart').getContext('2d');
            let dataPoints = history.length ? history.map(t => t.balance_after || 1000).reverse() : [1000, 1000];
            if(history.length === 0) dataPoints = [1000, 1000, 1000, 1000, 1000];
            if(chart) chart.destroy();
            chart = new Chart(ctx, { type: 'line', data: { labels: dataPoints.map((_, i) => ''), datasets: [{ label: 'Bankroll', data: dataPoints, borderColor: '#66fcf1', backgroundColor: 'rgba(102, 252, 241, 0.1)', fill: true, tension: 0.4 }] }, options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { grid: { color: '#2c3e50' } }, x: { display: false } } } });
        }
        setTimeout(initChart, 500);

        function showPage(id, el) {
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            if(el) { document.querySelectorAll('.menu-item').forEach(m => m.classList.remove('active')); el.classList.add('active'); }
            document.getElementById(id).classList.add('active');
        }

        function updateUI() {
            document.getElementById('bankroll-display').innerText = '€' + bankroll.toFixed(2);
            document.getElementById('dash-bankroll').innerText = '€' + bankroll.toFixed(2);
            localStorage.setItem('betpro_bankroll', bankroll);
            localStorage.setItem('betpro_history', JSON.stringify(history));
        }

        function resetApp() { if(confirm("Reset?")) { localStorage.clear(); location.reload(); } }

        async function loadAnalysis() {
            const div = document.getElementById('analysis-output');
            div.innerHTML = '<p style="text-align:center;color:#66fcf1">Načítavam...</p>';
            const res = await fetch('/api/data'); const data = await res.json();
            let html = '';
            data.forEach(m => {
                html += `<div class="analysis-card"><div class="ac-header"><div class="ac-teams">${m.domaci} vs ${m.hostia}</div><div style="background:#1a2634; color:#66fcf1; padding:5px 10px; border-radius:5px;">${m.kurz}</div></div><div class="ac-body"><div class="ac-left"><p style="color:#888">Forma: ${m.stats.forma_domaci}</p><p style="color:#ff4444">${m.stats.zranenia}</p></div><div class="ac-right"><p style="color:#fff; font-weight:bold;">TIP: ${m.tip}</p><p style="color:#ccc; font-size:14px;">${m.analyza_text}</p></div></div></div>`;
            });
            div.innerHTML = html;
        }

        async function loadTiketDna() { renderTicketSection('/api/tiket-dna', 'ticket-dna-result', 'VIP TIKET DŇA'); }
        async function loadCustom() { 
            const r = document.getElementById('riskLevel').value; const c = document.getElementById('matchCount').value;
            renderTicketSection(`/api/vlastny-tiket?risk=${r}&count=${c}`, 'custom-ticket-result', 'TVOJ TIKET'); 
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
            div.innerHTML = `<div class="ticket-wrapper"><div class="ticket-header"><h2 style="margin:0; color:var(--primary);">${title}</h2></div><div class="ticket-body">${rows}</div><div class="ticket-footer"><div style="color:#888;">CELKOVÝ KURZ</div><div style="font-size:24px; font-weight:bold; color:var(--primary);">${total.toFixed(2)}</div></div><button class="btn-analyze" style="width:100%; border-radius:0;" onclick='saveTicket(${total.toFixed(2)}, ${JSON.stringify(ticketInfo)})'>VSAĎIŤ 50€</button></div>`;
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
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def home(): return html_content
