import requests
import random
import time
from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI()

# ==========================================
# 🔑 API KĽÚČ
# ==========================================
API_KEY = "3e42c726ab364fb9eeede03b0017964c"
# ==========================================

CACHE = {"data": [], "last_update": 0}

def get_live_data():
    if time.time() - CACHE["last_update"] < 3600 and CACHE["data"]:
        return CACHE["data"]

    if API_KEY == "VLOZ_SVOJ_API_KLUC_SEM":
        return generate_demo_data()

    try:
        url = f"https://api.the-odds-api.com/v4/sports/soccer/odds/?regions=eu&markets=h2h&apiKey={API_KEY}"
        response = requests.get(url)
        data = response.json()
        
        matches = []
        for item in data[:25]:
            try:
                bookmakers = item.get('bookmakers', [])
                if not bookmakers: continue
                odds = bookmakers[0]['markets'][0]['outcomes']
                home = item['home_team']
                away = item['away_team']
                
                o1 = next((x['price'] for x in odds if x['name'] == home), 0)
                o2 = next((x['price'] for x in odds if x['name'] == away), 0)
                
                if o1 == 0 or o2 == 0: continue

                risk = 1; tip = "1"; dovera = 75; analyza = "Vyrovnaný duel."
                if o1 < 1.45:
                    risk = 1; tip = f"Výhra {home}"; dovera = random.randint(88, 98)
                    analyza = f"{home} doma dominuje. {away} sa trápi."
                elif o2 < 1.45:
                    risk = 1; tip = f"Výhra {away}"; dovera = random.randint(88, 98)
                    analyza = f"{away} má majstrovskú formu."
                elif o1 < 2.00:
                    risk = 2; tip = "1"; dovera = random.randint(70, 85)
                    analyza = "Domáce prostredie rozhodne."
                elif o2 < 2.00:
                    risk = 2; tip = "2"; dovera = random.randint(70, 85)
                    analyza = "Hostia sú miernym favoritom."
                else:
                    risk = 3; tip = "X / BTTS"; dovera = random.randint(40, 65)
                    analyza = "Vysoké kurzy, očakávame remízu."

                stats = {
                    "utok_domaci": int(100/o1) if o1 > 1 else 95,
                    "utok_hostia": int(100/o2) if o2 > 1 else 95,
                    "forma_domaci": generate_form(o1),
                    "forma_hostia": generate_form(o2),
                    "zranenia": random.choice(["Bez absencií", "Otázny útok", "Kľúčový obranca (Out)", "Kompletná zostava"])
                }

                matches.append({
                    "domaci": home, "hostia": away, 
                    "kurz": o1 if "Výhra " + home in tip or tip == "1" else (o2 if "Výhra " + away in tip or tip == "2" else 3.20),
                    "tip": tip, "risk": risk, "liga": item['sport_title'].replace("Soccer ", ""), "dovera": dovera,
                    "stats": stats, "analyza_text": analyza,
                    "analyza_body": [
                        f"{home} má priemer {round(random.uniform(1.2, 2.5), 1)} gólu na zápas.",
                        f"Vzájomná bilancia hovorí pre {home if o1 < o2 else away}.",
                        "AI model našiel hodnotu v kurze."
                    ]
                })
            except: continue
        
        CACHE["data"] = matches
        CACHE["last_update"] = time.time()
        return matches

    except:
        return generate_demo_data()

def generate_form(odds):
    if odds < 1.5: return "WWWDW"
    if odds < 2.0: return "WDLWW"
    return "LLDWL"

def generate_demo_data():
    return [{"domaci": "DEMO DATA", "hostia": "VLOŽ API KĽÚČ", "kurz": 1.00, "tip": "Nastavenia", "risk": 1, "liga": "System", "dovera": 0, "stats": {"utok_domaci":50, "utok_hostia":50, "forma_domaci": "?????", "forma_hostia": "?????", "zranenia": "-"}, "analyza_text": "Vlož API kľúč do súboru main.py", "analyza_body": ["Demo bod 1", "Demo bod 2"]}]

@app.get("/api/analyza")
def get_analysis(): return get_live_data()

@app.get("/api/tiket-dna")
def get_ticket_day():
    data = get_live_data()
    safe = [m for m in data if m['risk'] == 1]
    if len(safe) < 3: safe += [m for m in data if m['risk'] == 2]
    return safe[:3]

@app.get("/api/vlastny-tiket")
def get_custom(risk: int = 1, count: int = 2):
    data = get_live_data()
    filtered = [m for m in data if m['risk'] == risk]
    if len(filtered) < count: filtered = data 
    return filtered[:count]

# --- HTML FRONTEND (Mobile Optimized) ---
html_content = """
<!DOCTYPE html>
<html lang="sk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Betting PRO Analytics</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        :root { --bg-dark: #050a10; --bg-card: #151b24; --primary: #66fcf1; --text-main: #c5c6c7; --green: #00ff88; --red: #ff4444; --yellow: #ffcc00; }
        * { box-sizing: border-box; }
        body { margin: 0; padding: 0; font-family: 'Segoe UI', sans-serif; background-color: #0b0c10; color: var(--text-main); height: 100vh; overflow: hidden; display: flex; flex-direction: column; }
        
        /* LAYOUT PRE PC (Sidebar vľavo) */
        @media (min-width: 769px) {
            body { flex-direction: row; }
            .sidebar { width: 260px; height: 100vh; background-color: #111; display: flex; flex-direction: column; padding: 25px; border-right: 1px solid #333; }
            .mobile-nav { display: none; }
            .main-content { flex: 1; padding: 40px; }
        }

        /* LAYOUT PRE MOBIL (Spodná lišta) */
        @media (max-width: 768px) {
            .sidebar { display: none; }
            .mobile-nav { 
                position: fixed; bottom: 0; left: 0; width: 100%; height: 70px; background: #111; border-top: 1px solid #333; 
                display: flex; justify-content: space-around; align-items: center; z-index: 100;
            }
            .nav-item { display: flex; flex-direction: column; align-items: center; color: #666; font-size: 10px; cursor: pointer; }
            .nav-item.active { color: var(--primary); }
            .nav-icon { font-size: 20px; margin-bottom: 3px; }
            .main-content { flex: 1; padding: 20px; padding-bottom: 90px; overflow-y: auto; width: 100%; }
            
            .header h1 { font-size: 24px; }
            .dash-card { margin-bottom: 15px; margin-right: 0 !important; }
            .ac-body { flex-direction: column; }
            .ac-left { border-right: none; border-bottom: 1px solid #333; padding-bottom: 20px; padding-right: 0; }
            .ac-right { padding-left: 0; padding-top: 20px; }
            .chart-box { height: 250px; }
        }

        .logo { font-size: 24px; font-weight: 800; color: var(--primary); margin-bottom: 40px; text-transform: uppercase; text-align: center; text-shadow: 0 0 10px rgba(102, 252, 241, 0.4); }
        .menu-item { padding: 15px; margin-bottom: 5px; cursor: pointer; border-radius: 8px; color: #888; font-weight: 600; transition: 0.3s; }
        .menu-item:hover, .menu-item.active { background-color: #1f2833; color: #fff; border-left: 4px solid var(--primary); }
        
        .main-content { overflow-y: auto; background: radial-gradient(circle at top right, #1f2833 0%, #0b0c10 80%); }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; border-bottom: 1px solid #333; padding-bottom: 20px; }
        
        .dash-card { background: var(--bg-card); padding: 20px; border-radius: 16px; border: 1px solid #2c3e50; flex: 1; text-align: center; }
        .dash-card h1 { font-size: 32px; color: white; margin: 5px 0; }
        
        .btn-analyze { background: var(--primary); border: none; padding: 15px 40px; font-size: 16px; font-weight: 800; color: #0b0c10; border-radius: 50px; cursor: pointer; box-shadow: 0 0 25px rgba(102, 252, 241, 0.3); transition: 0.2s; text-transform: uppercase; width: 100%; max-width: 300px; margin: 0 auto; display: block; }
        .btn-analyze:hover { transform: scale(1.05); background: #fff; }
        
        /* CARD STYLES */
        .analysis-card { background: #11161d; border-radius: 12px; margin-bottom: 20px; border: 1px solid #2c3e50; padding: 15px; animation: slideUp 0.5s ease; box-shadow: 0 5px 20px rgba(0,0,0,0.5); }
        .ac-header { padding-bottom: 15px; border-bottom: 1px solid #2c3e50; display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
        .ac-teams { font-size: 20px; font-weight: 800; color: #fff; }
        .ac-body { display: flex; gap: 20px; }
        
        .ac-stat-title { font-size: 12px; color: #888; margin-bottom: 5px; font-weight: 600; }
        .ac-dots { display: flex; gap: 4px; margin-bottom: 15px; }
        .ac-dot { width: 18px; height: 18px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 9px; font-weight: bold; color: #000; }
        .v { background: var(--green); } .r { background: var(--yellow); } .p { background: var(--red); }
        .ac-progress-container { display: flex; height: 6px; background: #222; border-radius: 4px; overflow: hidden; margin-top: 5px; }
        .ac-bar-home { background: var(--primary); height: 100%; }
        
        .ac-tip-box { background: #1a222e; border: 1px solid #2c3e50; border-radius: 8px; padding: 15px; display: flex; justify-content: space-between; align-items: center; border-left: 4px solid var(--primary); margin-top: 15px; }
        .ac-tip-value { font-size: 20px; font-weight: 800; color: #fff; }
        .ac-conf-badge { background: var(--primary); color: #000; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }

        .ticket-wrapper { max-width: 600px; margin: 0 auto 30px auto; background: #151b24; border: 2px solid var(--primary); border-radius: 12px; overflow: hidden; animation: slideUp 0.5s ease; }
        .ticket-header { background: rgba(102, 252, 241, 0.1); padding: 15px; text-align: center; border-bottom: 1px solid var(--primary); }
        .ticket-body { padding: 15px; }
        .ticket-row { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px dashed #444; padding: 10px 0; }
        .ticket-footer { background: #0b0c10; padding: 15px; display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #333; }
        .btn-ticket { width: 100%; padding: 15px; background: var(--primary); border: none; font-weight: bold; cursor: pointer; color: black; font-size: 16px; text-transform: uppercase; }

        .gen-controls { max-width: 600px; margin: 0 auto; background: #151b24; padding: 20px; border-radius: 12px; }
        select { width: 100%; padding: 15px; background: #0b0c10; border: 1px solid #333; color: #fff; border-radius: 8px; font-size: 16px; margin-bottom: 20px; outline: none; }

        .page { display: none; } .page.active { display: block; animation: fadeIn 0.3s; }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        @keyframes slideUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
        
        table { width: 100%; border-collapse: collapse; margin-top: 20px; color: #ccc; font-size: 14px; }
        th { text-align: left; padding: 10px; border-bottom: 1px solid #333; color:#666; font-size:10px; text-transform:uppercase; }
        td { padding: 10px; border-bottom: 1px solid #222; }
        .win { color: var(--green); font-weight: bold; } .lose { color: var(--red); font-weight: bold; } .pending { color: var(--yellow); }
    </style>
</head>
<body>

    <!-- PC SIDEBAR -->
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
                <div style="font-size:10px; color:#666; margin-bottom:2px;">BANKROLL</div>
                <div style="font-size:24px; font-weight:bold; color:var(--primary);" id="bankroll-display">€1,000.00</div>
            </div>
        </div>

        <div id="home" class="page active">
            <div style="display:flex; flex-wrap:wrap; gap:15px; margin-bottom:30px;">
                <div class="dash-card"><h3>Stav Konta</h3><h1 id="dash-bankroll">€1,000</h1></div>
                <div class="dash-card"><h3>Simulácia</h3><p style="color:#888; font-size:12px; margin-bottom:10px;">Vyhodnotiť tikety</p><button class="btn-analyze" style="padding:10px; font-size:12px; width:auto;" onclick="evaluateTickets()">🔄 Spustiť</button></div>
            </div>
            <div class="chart-box" style="background:#151b24; padding:15px; border-radius:16px; border:1px solid #2c3e50;">
                <canvas id="profitChart" height="200"></canvas>
            </div>
        </div>

        <div id="generator" class="page">
            <div style="text-align:center; margin-bottom:30px;">
                <button class="btn-analyze" onclick="loadAnalysis()">Načítať Live Analýzy</button>
            </div>
            <div id="analysis-output"></div>
        </div>

        <div id="ticket-day" class="page">
            <div style="text-align:center; margin-bottom:30px;">
                <h2 style="color:var(--primary)">🔥 DENNÁ TUTOVKA</h2>
                <button class="btn-analyze" onclick="loadTiketDna()">VYGENEROVAŤ TIKET</button>
            </div>
            <div id="ticket-dna-result"></div>
        </div>

        <div id="custom-ticket" class="page">
            <div class="gen-controls">
                <label style="color:var(--primary); font-weight:bold; font-size:12px;">RIZIKO</label>
                <select id="riskLevel"><option value="1">🟢 Nízke (1.2 - 1.5)</option><option value="2">🟡 Stredné (1.8 - 2.2)</option><option value="3">🔴 Vysoké (3.0+)</option></select>
                <label style="color:var(--primary); font-weight:bold; font-size:12px;">POČET ZÁPASOV</label>
                <select id="matchCount"><option value="2">2 Zápasy</option><option value="3">3 Zápasy</option><option value="5">5 Zápasov</option></select>
                <button class="btn-analyze" style="width:100%" onclick="loadCustom()">GENEROVAŤ</button>
            </div>
            <div id="custom-ticket-output" style="margin-top:30px;"></div>
        </div>

        <div id="results-page" class="page">
            <h2>Moje Tikety</h2>
            <div id="history-output"></div>
        </div>
    </div>

    <!-- MOBILE NAV -->
    <div class="mobile-nav">
        <div class="nav-item active" onclick="showPage('home', this)"><div class="nav-icon">🏠</div>Prehľad</div>
        <div class="nav-item" onclick="showPage('generator', this)"><div class="nav-icon">📊</div>Analýza</div>
        <div class="nav-item" onclick="showPage('ticket-day', this)"><div class="nav-icon">🎯</div>Tiket</div>
        <div class="nav-item" onclick="showPage('custom-ticket', this)"><div class="nav-icon">🛠️</div>Vlastný</div>
        <div class="nav-item" onclick="showPage('results-page', this); renderHistory()"><div class="nav-icon">✅</div>História</div>
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
            chart = new Chart(ctx, {
                type: 'line',
                data: { labels: dataPoints.map((_, i) => ''), datasets: [{ label: 'Bankroll', data: dataPoints, borderColor: '#66fcf1', backgroundColor: 'rgba(102, 252, 241, 0.1)', fill: true, tension: 0.4 }] },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { grid: { color: '#2c3e50' } }, x: { display: false } } }
            });
        }
        setTimeout(initChart, 500);

        function showPage(id, el) {
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.menu-item').forEach(m => m.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(m => m.classList.remove('active'));
            
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

        async function loadAnalysis() {
            const div = document.getElementById('analysis-output');
            div.innerHTML = '<p style="text-align:center;color:#66fcf1">Načítavam...</p>';
            try {
                const res = await fetch('/api/data'); const data = await res.json();
                let html = '';
                data.forEach(m => {
                    const circles = (f) => { let h=''; for(let c of f) h+=`<div class="ac-dot ${c==='W'?'v':(c==='L'?'p':'r')}">${c==='W'?'V':(c==='L'?'P':'R')}</div>`; return h; };
                    html += `
                    <div class="analysis-card">
                        <div class="ac-header"><div class="ac-teams">${m.domaci} vs ${m.hostia}</div><div style="background:#1a2634; color:#66fcf1; padding:5px 10px; border-radius:5px;">${m.kurz}</div></div>
                        <div class="ac-body">
                            <div class="ac-left">
                                <div style="margin-bottom:15px;"><div class="ac-stat-title">Forma</div><div class="ac-dots">${circles(m.stats.forma_domaci)}</div></div>
                                <div style="margin-bottom:15px;"><div class="ac-stat-title">Sila Útoku</div><div class="ac-progress-container"><div class="ac-bar-home" style="width:${m.stats.utok_domaci}%"></div></div></div>
                                <div style="color:#ff4444; font-size:12px;">${m.stats.zranenia}</div>
                            </div>
                            <div class="ac-right">
                                <div class="ac-ai-title">🧠 AI ANALÝZA</div>
                                <div style="font-size:13px; color:#ccc; margin-bottom:10px;">${m.analyza_text}</div>
                                <div class="ac-tip-box">
                                    <div><div style="font-size:10px; color:#888;">TIP</div><div class="ac-tip-value">${m.tip}</div></div>
                                    <div class="ac-conf-badge">${m.dovera}%</div>
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
            div.innerHTML = `<div class="ticket-wrapper"><div class="ticket-header"><h2 style="margin:0; color:var(--primary);">${title}</h2></div><div class="ticket-body">${rows}</div><div class="ticket-footer"><div style="color:#888;">CELKOVÝ KURZ</div><div style="font-size:24px; font-weight:bold; color:var(--primary);">${total.toFixed(2)}</div></div><button class="btn-ticket" onclick='saveTicket(${total.toFixed(2)}, ${JSON.stringify(ticketInfo)})'>ULOŽIŤ DO HISTÓRIE (VKLAD €50)</button></div>`;
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

class WhopInput(BaseModel): message: str
@app.post("/whop")
def whop(data: WhopInput): return {"status": "ok"}
@app.get("/", response_class=HTMLResponse)
def home(): return html_content

