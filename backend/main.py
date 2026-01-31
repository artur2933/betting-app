from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import random
from typing import List, Optional

app = FastAPI()

# --- 1. KONFIGURÁCIA A STAV SYSTÉMU (Backend "Mozog") ---
# Tieto dáta sa posielajú do Dashboardu. V budúcnosti ich môžeš napojiť na reálnu DB.
SYSTEM_STATUS = {
    "bankroll": 2450.00,
    "weekly_profit": 12.5,  # v percentách
    "daily_potential": 6,   # počet zápasov s vysokou hodnotou
    "ai_success_rate": "78.4%",
    "history_chart": [2100, 2150, 2120, 2250, 2300, 2380, 2450] # Dáta pre graf
}

# --- 2. DATABÁZA ZÁPASOV (Rozšírená a Profesionálna) ---
MATCH_DATABASE = [
    # --- TUTOVKY (Risk 1) ---
    {
        "domaci": "Manchester United", "hostia": "PAOK", "kurz": 1.45, "tip": "Výhra United & Over 1.5", "risk": 1, "liga": "Europa League", "dovera": 88,
        "stats": {"utok_domaci": 82, "utok_hostia": 40, "forma_domaci": "WWDLW", "forma_hostia": "LLDWL", "zranenia": "Man Utd: Maguire (Otázny), Shaw (Out)"},
        "analyza_text": "United pod novým trénerom Amorimom doma dominuje. Old Trafford je pevnosť, zatiaľ čo PAOK vonku v Európe trpí.",
        "analyza_body": ["United má priemer 2.1 xG na domáci zápas.", "PAOK inkasoval v 4 z 5 posledných zápasov.", "Motivácia domácich potvrdiť postup."]
    },
    {
        "domaci": "Man City", "hostia": "Sheffield Utd", "kurz": 1.18, "tip": "Handicap -1.5 City", "risk": 1, "liga": "Premier League", "dovera": 92,
        "stats": {"utok_domaci": 95, "utok_hostia": 15, "forma_domaci": "WWWWW", "forma_hostia": "LLLLL", "zranenia": "De Bruyne (Out)"},
        "analyza_text": "City bojuje o titul a proti poslednému tímu tabuľky si nemôže dovoliť zaváhať. Haaland je oddýchnutý.",
        "analyza_body": ["Sheffield má najhoršiu obranu v lige.", "City vyhralo posledných 12 domácich zápasov.", "Sheffield vonku strelil len 0.5 gólu na zápas."]
    },
    {
        "domaci": "Bayern Mníchov", "hostia": "Mainz", "kurz": 1.30, "tip": "Výhra + Over 2.5", "risk": 1, "liga": "Bundesliga", "dovera": 85,
        "stats": {"utok_domaci": 90, "utok_hostia": 35, "forma_domaci": "WLWWW", "forma_hostia": "LDLDL", "zranenia": "Coman (Quest)"},
        "analyza_text": "Bayern v Allianz Arene strieľa priemerne 3 góly na zápas. Mainz má deravú obranu.",
        "analyza_body": ["Kane skóruje každých 70 minút.", "Mainz prehral 4 z 5 posledných zápasov.", "Bayern potrebuje body na dotiahnutie Leverkusenu."]
    },

    # --- STREDNÉ RIZIKO / VALUE (Risk 2) ---
    {
        "domaci": "Lazio Rím", "hostia": "FC Porto", "kurz": 2.10, "tip": "Obaja dajú gól (BTTS)", "risk": 2, "liga": "Europa League", "dovera": 75,
        "stats": {"utok_domaci": 78, "utok_hostia": 85, "forma_domaci": "WWWWL", "forma_hostia": "WWWWW", "zranenia": "Lazio: Immobile (lavička)"},
        "analyza_text": "Súboj dvoch ofenzívne ladených tímov. Porto má smrtiacu formu, ale v Taliansku sa hrá ťažko.",
        "analyza_body": ["Lazio skórovalo v 90% domácich zápasov.", "Porto má sériu 7 výhier v rade.", "Obrany oboch tímov robia chyby pod tlakom."]
    },
    {
        "domaci": "Arsenal", "hostia": "Chelsea", "kurz": 1.95, "tip": "Výhra Domácich", "risk": 2, "liga": "Premier League", "dovera": 65,
        "stats": {"utok_domaci": 75, "utok_hostia": 65, "forma_domaci": "WWDLW", "forma_hostia": "WLDLW", "zranenia": "Saka (Fit)"},
        "analyza_text": "Londýnske derby. Arsenal je takticky vyspelejší a doma silný. Chelsea je nevyspytateľná.",
        "analyza_body": ["Arsenal neprehral doma s Chelsea 3 roky.", "Chelsea má mladý tím náchylný na chyby.", "Odegaard a Rice kontrolujú stred poľa."]
    },
    {
        "domaci": "Real Sociedad", "hostia": "Betis", "kurz": 2.25, "tip": "Remíza (X)", "risk": 2, "liga": "La Liga", "dovera": 60,
        "stats": {"utok_domaci": 55, "utok_hostia": 50, "forma_domaci": "DDWLD", "forma_hostia": "DLDWW", "zranenia": "Oyarzabal (Out)"},
        "analyza_text": "Oba tímy majú silné obrany a hrajú o Európu. Očakávame taktický boj s málom gólov.",
        "analyza_body": ["Sociedad remizoval 3x v posledných 5 zápasoch.", "Betis vonku hrá defenzívne.", "Under 2.5 gólu je veľmi pravdepodobný."]
    },

    # --- VYSOKÉ RIZIKO / PREKVAPENIA (Risk 3) ---
    {
        "domaci": "Luton", "hostia": "Liverpool", "kurz": 6.50, "tip": "1X (Dvojitá šanca)", "risk": 3, "liga": "Premier League", "dovera": 40,
        "stats": {"utok_domaci": 40, "utok_hostia": 85, "forma_domaci": "LLWDL", "forma_hostia": "WWWWW", "zranenia": "Salah (Out)"},
        "analyza_text": "Liverpool prichádza bez kľúčových hráčov po ťažkom týždni. Luton doma na malom štadióne vie hrýzť.",
        "analyza_body": ["Liverpool má zraneného Salaha.", "Luton doma remizoval s Liverpoolom minulú sezónu.", "Vysoký kurz na prekvapenie (Value bet)."]
    },
    {
        "domaci": "Monza", "hostia": "Juventus", "kurz": 3.80, "tip": "Výhra Domácich", "risk": 3, "liga": "Serie A", "dovera": 35,
        "stats": {"utok_domaci": 50, "utok_hostia": 60, "forma_domaci": "WLDLW", "forma_hostia": "WDWDW", "zranenia": "Chiesa (Out)"},
        "analyza_text": "Juventus má problémy so zraneniami a Monza je doma nepríjemná. Kurz 3.80 má hodnotu.",
        "analyza_body": ["Monza porazila Juventus v minulej sezóne.", "Juve hrá bez Vlahoviča.", "Monza doma hrá ofenzívne."]
    }
]

# 3. HTML GRAFIKA - FINAL PRO VERSION
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
        /* --- GLOBAL STYLES (Cyberpunk Blue Theme) --- */
        :root {
            --bg-dark: #050a10;
            --bg-panel: #11161d;
            --bg-card: #151b24;
            --primary: #66fcf1;
            --secondary: #1f2833;
            --text-main: #c5c6c7;
            --text-white: #ffffff;
            --green: #00ff88;
            --red: #ff4444;
            --yellow: #ffcc00;
        }

        body { margin: 0; padding: 0; font-family: 'Segoe UI', sans-serif; background-color: #0b0c10; color: var(--text-main); display: flex; height: 100vh; overflow: hidden; }
        
        /* SCROLLBAR */
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: #0b0c10; }
        ::-webkit-scrollbar-thumb { background: #1f2833; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--primary); }

        /* SIDEBAR */
        .sidebar { width: 260px; background-color: #111; display: flex; flex-direction: column; padding: 25px; border-right: 1px solid #333; }
        .logo { font-size: 24px; font-weight: 800; color: var(--primary); margin-bottom: 40px; text-transform: uppercase; letter-spacing: 2px; text-align: center; border-bottom: 2px solid var(--primary); padding-bottom: 20px; text-shadow: 0 0 10px rgba(102, 252, 241, 0.4); }
        
        .menu-label { font-size: 11px; text-transform: uppercase; color: #666; margin-top: 20px; margin-bottom: 10px; letter-spacing: 1px; font-weight: bold; }
        .menu-item { padding: 15px; margin-bottom: 5px; cursor: pointer; border-radius: 8px; color: #888; font-weight: 600; transition: 0.3s; display: flex; align-items: center; gap: 15px; }
        .menu-item:hover, .menu-item.active { background-color: var(--secondary); color: #fff; border-left: 4px solid var(--primary); box-shadow: 0 0 15px rgba(0,0,0,0.2); }
        
        /* MAIN CONTENT */
        .main-content { flex: 1; padding: 40px; overflow-y: auto; background: radial-gradient(circle at top right, #1f2833 0%, #0b0c10 80%); }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 40px; border-bottom: 1px solid #333; padding-bottom: 20px; }
        .header h1 { margin: 0; color: #fff; font-size: 32px; font-weight: 700; letter-spacing: 1px; }
        
        /* DASHBOARD CARDS */
        .dash-card { background: var(--bg-card); padding: 25px; flex: 1; border-radius: 16px; border: 1px solid #2c3e50; position: relative; overflow: hidden; }
        .dash-card h3 { color: #888; font-size: 14px; margin-top: 0; text-transform: uppercase; letter-spacing: 1px; }
        .dash-card h1 { color: #fff; font-size: 42px; margin: 10px 0; font-weight: 800; }
        .dash-card small { color: var(--primary); font-weight: bold; font-size: 14px; }
        .dash-card::after { content: ''; position: absolute; top: -50%; right: -50%; width: 200px; height: 200px; background: var(--primary); opacity: 0.05; border-radius: 50%; filter: blur(50px); }

        /* CHART */
        .chart-box { background: var(--bg-card); padding: 25px; border-radius: 16px; border: 1px solid #2c3e50; height: 350px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }

        /* BUTTONS */
        .btn-analyze { 
            background: var(--primary); border: none; padding: 18px 50px; 
            font-size: 16px; font-weight: 800; color: #0b0c10; border-radius: 50px; cursor: pointer; 
            box-shadow: 0 0 25px rgba(102, 252, 241, 0.3); transition: transform 0.2s, box-shadow 0.2s;
            display: block; margin: 0 auto 40px auto; letter-spacing: 2px; text-transform: uppercase;
        }
        .btn-analyze:hover { transform: scale(1.05); background: #fff; box-shadow: 0 0 40px rgba(102, 252, 241, 0.6); }

        /* --- VIP ANALÝZA (LAYOUT PODĽA OBRÁZKA) --- */
        .analysis-card {
            background: #11161d; border-radius: 12px; margin-bottom: 30px; 
            border: 1px solid #2c3e50; padding: 0; overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            animation: slideUp 0.5s ease;
        }
        
        .ac-header {
            padding: 20px 30px; background: #151b24; border-bottom: 1px solid #2c3e50;
            display: flex; justify-content: space-between; align-items: center;
        }
        .ac-teams { font-size: 28px; font-weight: 800; color: #fff; letter-spacing: 0.5px; }
        .ac-vs { color: #666; font-size: 20px; font-weight: 400; margin: 0 10px; }
        .ac-odds-badge { background: #1a2634; color: var(--primary); padding: 8px 15px; border-radius: 8px; font-weight: bold; border: 1px solid #2c3e50; font-size: 16px; }

        .ac-body { padding: 30px; display: flex; gap: 40px; flex-wrap: wrap; }
        .ac-left { flex: 1; min-width: 300px; border-right: 1px solid #2c3e50; padding-right: 30px; }
        .ac-right { flex: 1.2; min-width: 300px; padding-left: 10px; }

        /* Forma Dots */
        .ac-stat-title { font-size: 12px; color: #888; margin-bottom: 10px; font-weight: 600; }
        .ac-form-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; }
        .ac-team-label { font-size: 14px; color: #ccc; margin-bottom: 5px; display: block; font-weight: 600; }
        .ac-dots { display: flex; gap: 5px; }
        .ac-dot { width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: bold; color: #000; box-shadow: 0 2px 5px rgba(0,0,0,0.5); }
        .ac-dot.v { background: var(--green); } 
        .ac-dot.r { background: var(--yellow); } 
        .ac-dot.p { background: var(--red); }

        /* Progress Bar */
        .ac-progress-container { display: flex; height: 8px; background: #222; border-radius: 4px; overflow: hidden; margin-top: 5px; }
        .ac-bar-home { background: var(--primary); height: 100%; box-shadow: 0 0 10px rgba(102, 252, 241, 0.3); }
        .ac-bar-away { background: var(--red); height: 100%; }
        .ac-stat-val { font-size: 12px; color: #888; text-align: right; margin-top: 5px; font-weight: bold; }

        /* Injuries */
        .ac-injuries { color: var(--red); font-size: 13px; margin-top: 5px; font-weight: 500; }

        /* Right Side Analysis */
        .ac-ai-title { color: #ff66cc; font-weight: bold; font-size: 12px; text-transform: uppercase; margin-bottom: 15px; display: flex; align-items: center; gap: 8px; letter-spacing: 1px; }
        .ac-text { font-size: 14px; line-height: 1.7; color: #ccc; margin-bottom: 20px; }
        .ac-list { list-style: none; padding: 0; margin-bottom: 25px; }
        .ac-list li { margin-bottom: 10px; padding-left: 20px; position: relative; color: #aaa; font-size: 14px; }
        .ac-list li::before { content: "•"; color: var(--primary); position: absolute; left: 0; font-weight: bold; font-size: 18px; line-height: 14px; }

        /* Recommendation Box */
        .ac-tip-box { 
            background: #1a222e; border: 1px solid #2c3e50; border-radius: 8px; padding: 20px; 
            display: flex; justify-content: space-between; align-items: center;
            border-left: 4px solid var(--primary);
        }
        .ac-tip-label { font-size: 11px; color: #888; text-transform: uppercase; display: block; margin-bottom: 5px; letter-spacing: 1px; }
        .ac-tip-value { font-size: 22px; font-weight: 800; color: #fff; }
        .ac-conf-badge { background: var(--primary); color: #000; padding: 6px 12px; border-radius: 6px; font-weight: 800; font-size: 16px; }

        /* --- TIKETY (Papierový vzhľad) --- */
        .ticket-wrapper { 
            max-width: 600px; margin: 0 auto; 
            background: #151b24; border: 2px solid var(--primary); border-radius: 12px; 
            box-shadow: 0 0 50px rgba(102, 252, 241, 0.15); overflow: hidden;
            animation: slideUp 0.5s ease;
        }
        .ticket-header { background: rgba(102, 252, 241, 0.1); padding: 25px; text-align: center; border-bottom: 1px solid var(--primary); }
        .ticket-title { font-size: 26px; font-weight: 900; color: var(--primary); margin: 0; letter-spacing: 2px; text-transform: uppercase; }
        .ticket-body { padding: 30px; }
        .ticket-row { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px dashed #444; padding: 15px 0; }
        .ticket-row:last-child { border-bottom: none; }
        .t-match { font-size: 17px; font-weight: 700; color: #fff; }
        .t-tip { font-size: 14px; color: #aaa; margin-top: 5px; }
        .t-odds { background: #0b0c10; color: var(--primary); padding: 6px 12px; border-radius: 6px; border: 1px solid #333; font-weight: 800; }
        .ticket-footer { background: #0b0c10; padding: 25px; display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #333; }
        .t-total-label { font-size: 14px; color: #888; text-transform: uppercase; font-weight: bold; }
        .t-val { color: var(--primary); font-weight: 900; font-size: 32px; text-shadow: 0 0 15px rgba(102, 252, 241, 0.4); }

        /* GENERÁTOR OVLÁDANIE */
        .gen-controls { max-width: 700px; margin: 0 auto; background: #151b24; padding: 40px; border-radius: 16px; border: 1px solid #333; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }
        .control-row { margin-bottom: 25px; }
        .c-label { display: block; color: var(--primary); font-size: 12px; font-weight: bold; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 1px; }
        select { width: 100%; padding: 18px; background: #0b0c10; border: 1px solid #333; color: #fff; border-radius: 8px; font-size: 16px; outline: none; transition: 0.3s; cursor: pointer; }
        select:focus { border-color: var(--primary); box-shadow: 0 0 15px rgba(102, 252, 241, 0.2); }

        .page { display: none; }
        .page.active { display: block; animation: fadeIn 0.4s; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes slideUp { from { transform: translateY(30px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
    </style>
</head>
<body>

    <div class="sidebar">
        <div class="logo">⚡ BET PRO</div>
        
        <div class="menu-label">Hlavné</div>
        <div class="menu-item active" onclick="showPage('home', this)">🏠 Dashboard</div>
        <div class="menu-item" onclick="showPage('generator', this)">📊 VIP Analýza</div>
        
        <div class="menu-label">Tikety</div>
        <div class="menu-item" onclick="loadTiketDna(this)">🎯 Tiket Dňa</div>
        <div class="menu-item" onclick="showPage('custom-ticket', this)">🛠️ Vlastný Generátor</div>
        
        <div class="menu-label">Dáta</div>
        <div class="menu-item" onclick="showPage('results-page', this)">✅ Výsledky</div>
    </div>

    <div class="main-content">
        
        <div id="home" class="page active">
            <div class="header"><h1>Vitaj späť, Trader.</h1></div>
            
            <div style="display:flex; gap:20px; margin-bottom: 30px;">
                <div class="dash-card">
                    <h3>Dnešný Potenciál</h3>
                    <h1 id="dash-potential">--</h1>
                    <small style="color:var(--primary)">AI našla vysokú hodnotu</small>
                </div>
                <div class="dash-card">
                    <h3>Bankroll</h3>
                    <h1 id="dash-bankroll">€--</h1>
                    <small style="color:#00ff88">▲ +12.5% tento týždeň</small>
                </div>
            </div>
            
            <div class="chart-box">
                <h3 style="color:#fff; margin:0 0 20px 0; font-size:18px;">Vývoj Zisku (7 Dní)</h3>
                <canvas id="profitChart"></canvas>
            </div>
        </div>

        <div id="generator" class="page">
            <div class="header"><h1>Deep AI Analysis</h1></div>
            <div style="text-align:center; margin-bottom:40px;">
                <p style="color:#888; margin-bottom:20px;">Spusti hĺbkový sken zápasov. AI analyzuje formu, xG a zranenia.</p>
                <button class="btn-analyze" onclick="generujAnalyzu()">SPUSTIŤ SKENOVANIE</button>
            </div>
            <div id="analysis-output"></div>
        </div>

        <div id="ticket-day" class="page">
            <div class="header"><h1>🔥 Tiket Dňa (Tutovka)</h1></div>
            <div id="ticket-day-result" style="margin-top: 50px;"></div>
        </div>

        <div id="custom-ticket" class="page">
            <div class="header"><h1>🛠️ Vlastný Tiket</h1></div>
            
            <div class="gen-controls">
                <div class="control-row">
                    <label class="c-label">Riziko</label>
                    <select id="riskLevel">
                        <option value="1">🟢 Nízke (Favoriti 1.1 - 1.5)</option>
                        <option value="2">🟡 Stredné (Value 1.8 - 2.3)</option>
                        <option value="3">🔴 Vysoké (Prekvapenia 3.0+)</option>
                    </select>
                </div>
                <div class="control-row">
                    <label class="c-label">Počet zápasov</label>
                    <select id="matchCount">
                        <option value="2">2 Zápasy</option>
                        <option value="3">3 Zápasy</option>
                        <option value="5">5 Zápasov</option>
                    </select>
                </div>
                <div class="control-row">
                    <label class="c-label">Liga</label>
                    <select id="leagueSelect">
                        <option value="all">Všetky Ligy</option>
                        <option value="Premier League">Premier League</option>
                        <option value="La Liga">La Liga</option>
                        <option value="Bundesliga">Bundesliga</option>
                        <option value="Serie A">Serie A</option>
                        <option value="Europa League">Europa League</option>
                    </select>
                </div>
                <button class="btn-analyze" style="margin-bottom:0;" onclick="generujVlastny()">Vygenerovať</button>
            </div>

            <div id="custom-ticket-result" style="margin-top: 50px;"></div>
        </div>

        <div id="results-page" class="page">
            <div class="header"><h1>Výkonnosť Modelu</h1></div>
            <p style="color:#aaa;">Načítavam históriu...</p>
            <div class="match-card" style="padding:20px; text-align:center; color:#666;">
                História je zatiaľ prázdna. Po vyhodnotení tiketov sa tu objavia výsledky.
            </div>
        </div>

    </div>

    <script>
        // Inicializácia pri načítaní
        document.addEventListener("DOMContentLoaded", async function() {
            // 1. Načítaj Dashboard dáta
            try {
                const res = await fetch('/api/stats');
                const stats = await res.json();
                document.getElementById('dash-bankroll').innerText = '€' + stats.bankroll.toFixed(2);
                document.getElementById('dash-potential').innerText = stats.daily_potential + ' Zápasov';
                initChart(stats.history_chart);
            } catch(e) { console.log('Chyba stats'); }
        });

        function initChart(dataPoints) {
            const ctx = document.getElementById('profitChart').getContext('2d');
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: ['Po', 'Ut', 'St', 'Št', 'Pi', 'So', 'Ne'],
                    datasets: [{
                        label: 'Bankroll (€)',
                        data: dataPoints,
                        borderColor: '#66fcf1',
                        backgroundColor: (ctx) => {
                            const grad = ctx.chart.ctx.createLinearGradient(0,0,0,300);
                            grad.addColorStop(0, 'rgba(102, 252, 241, 0.2)');
                            grad.addColorStop(1, 'rgba(102, 252, 241, 0)');
                            return grad;
                        },
                        borderWidth: 3,
                        tension: 0.4,
                        fill: true,
                        pointBackgroundColor: '#111',
                        pointBorderColor: '#66fcf1',
                        pointBorderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { grid: { color: '#2c3e50' }, ticks: { color: '#888' } },
                        x: { grid: { display: false }, ticks: { color: '#888' } }
                    }
                }
            });
        }

        function showPage(id, el) {
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            if(el) { document.querySelectorAll('.menu-item').forEach(m => m.classList.remove('active')); el.classList.add('active'); }
            document.getElementById(id).classList.add('active');
        }

        // --- VIP ANALÝZA (RENDERER PODĽA OBRÁZKA) ---
        async function generujAnalyzu() {
            const out = document.getElementById('analysis-output');
            out.innerHTML = '<p style="text-align:center; color:#66fcf1; font-size:18px;">⏳ Analyzujem milióny dátových bodov...</p>';
            
            try {
                const res = await fetch('/api/analyza'); 
                const data = await res.json();
                
                let html = '';
                data.forEach(m => {
                    const circles = (formStr) => {
                        let h = '';
                        for (let c of formStr) {
                            let cl = c === 'W' ? 'v' : (c === 'L' ? 'p' : 'r');
                            let txt = c === 'W' ? 'V' : (c === 'L' ? 'P' : 'R');
                            h += `<div class="ac-dot ${cl}">${txt}</div>`;
                        }
                        return h;
                    };

                    let listHtml = '';
                    if(m.analyza_body) {
                        m.analyza_body.forEach(li => listHtml += `<li>${li}</li>`);
                    }

                    html += `
                    <div class="analysis-card">
                        <div class="ac-header">
                            <div class="ac-teams">${m.domaci} <span class="ac-vs">vs</span> ${m.hostia}</div>
                            <div class="ac-odds-badge">Kurz: ${m.kurz.toFixed(2)}</div>
                        </div>
                        <div class="ac-body">
                            <div class="ac-left">
                                <div style="margin-bottom: 25px;">
                                    <div class="ac-stat-title">Forma (Posledných 5)</div>
                                    <div class="ac-form-row">
                                        <div><span class="ac-team-label">${m.domaci}</span><div class="ac-dots">${circles(m.stats.forma_domaci)}</div></div>
                                        <div style="text-align:right;"><span class="ac-team-label">${m.hostia}</span><div class="ac-dots" style="justify-content:flex-end;">${circles(m.stats.forma_hostia)}</div></div>
                                    </div>
                                </div>
                                <div style="margin-bottom: 25px;">
                                    <div class="ac-stat-title">Sila Útoku (xG Power)</div>
                                    <div class="ac-progress-container">
                                        <div class="ac-bar-home" style="width:${m.stats.utok_domaci}%"></div>
                                        <div class="ac-bar-away" style="width:${m.stats.utok_hostia}%"></div>
                                    </div>
                                    <div class="ac-stat-val">${m.stats.utok_domaci}% vs ${m.stats.utok_hostia}%</div>
                                </div>
                                <div>
                                    <div class="ac-stat-title">Absencie (Zranenia)</div>
                                    <div class="ac-injuries">${m.stats.zranenia}</div>
                                </div>
                            </div>
                            <div class="ac-right">
                                <div class="ac-ai-title">🧠 AI DEEP DIVE ANALÝZA</div>
                                <div class="ac-text">${m.analyza_text}</div>
                                <ul class="ac-list">${listHtml}</ul>
                                <div class="ac-tip-box">
                                    <div><span class="ac-tip-label">ODPORÚČANÝ TIP</span><div class="ac-tip-value">${m.tip}</div></div>
                                    <div style="text-align:right;"><span class="ac-tip-label">Dôvera</span><div class="ac-conf-badge">${m.dovera}%</div></div>
                                </div>
                            </div>
                        </div>
                    </div>`;
                });
                out.innerHTML = html;
            } catch(e) { out.innerHTML = "Chyba načítania."; }
        }

        // --- TIKET DŇA ---
        async function loadTiketDna(el) {
            showPage('ticket-day', el);
            const div = document.getElementById('ticket-day-result');
            div.innerHTML = '<p style="text-align:center; color:#66fcf1; font-size:18px;">⏳ Generujem najlepší tiket dňa...</p>';
            
            try {
                const res = await fetch('/api/tiket-dna');
                const data = await res.json();
                renderTicket(data, div, "VIP TIKET DŇA");
            } catch(e) { div.innerHTML = "Chyba."; }
        }

        // --- VLASTNÝ GENERÁTOR ---
        async function generujVlastny() {
            const risk = document.getElementById('riskLevel').value;
            const count = document.getElementById('matchCount').value;
            const league = document.getElementById('leagueSelect').value;
            const div = document.getElementById('custom-ticket-result');
            div.innerHTML = '<p style="text-align:center; color:#66fcf1; font-size:18px;">⏳ AI prehľadáva trh...</p>';
            
            try {
                const res = await fetch(`/api/vlastny-tiket?risk=${risk}&count=${count}&league=${league}`);
                const data = await res.json();
                renderTicket(data, div, "TVOJ VLASTNÝ TIKET");
            } catch(e) { div.innerHTML = "Chyba."; }
        }

        // --- RENDERER TIKETU ---
        function renderTicket(data, element, title) {
            if (data.length === 0) { element.innerHTML = "<p style='text-align:center;color:#888'>Pre tento výber sa nenašli žiadne zápasy. Skús zmeniť ligu alebo riziko.</p>"; return; }
            
            let rows = '';
            let total = 1;
            data.forEach(m => {
                total *= m.kurz;
                rows += `
                <div class="ticket-row">
                    <div>
                        <div class="t-match">${m.domaci} - ${m.hostia}</div>
                        <div class="t-tip">Tip: ${m.tip}</div>
                    </div>
                    <div class="t-odds">${m.kurz.toFixed(2)}</div>
                </div>`;
            });

            element.innerHTML = `
            <div class="ticket-wrapper">
                <div class="ticket-header"><h2 class="ticket-title">${title}</h2></div>
                <div class="ticket-body">${rows}</div>
                <div class="ticket-footer">
                    <div class="t-total-label">CELKOVÝ KURZ</div>
                    <div class="t-val">${total.toFixed(2)}</div>
                </div>
            </div>`;
        }
    </script>
</body>
</html>
"""

# --- 4. API ENDPOINTS (Backend Logic) ---

@app.get("/", response_class=HTMLResponse)
def home():
    return html_content

# Dashboard Stats
@app.get("/api/stats")
def get_stats():
    return SYSTEM_STATUS

# VIP Analýza (Všetky zápasy)
@app.get("/api/analyza")
def get_analysis_matches():
    return MATCH_DATABASE

# Tiket Dňa (Najnižšie riziko)
@app.get("/api/tiket-dna")
def get_tiket_dna():
    safe_matches = [m for m in MATCH_DATABASE if m['risk'] == 1]
    # Ak je málo safe zápasov, doplníme risk 2
    if len(safe_matches) < 2:
        safe_matches += [m for m in MATCH_DATABASE if m['risk'] == 2]
    return safe_matches[:3]

# Vlastný Tiket
@app.get("/api/vlastny-tiket")
def get_custom_ticket(risk: int = 1, count: int = 2, league: str = "all"):
    # 1. Filter Riziko
    filtered = [m for m in MATCH_DATABASE if m['risk'] == risk]
    
    # 2. Filter Liga
    if league != "all":
        league_matches = [m for m in filtered if m.get('liga') == league]
        # Ak v lige nie je dosť zápasov pre tento risk, vrátime mix (aby tiket nebol prázdny)
        if len(league_matches) >= count:
            filtered = league_matches
    
    # 3. Ak stále nemáme dosť zápasov, zoberieme všetky dostupné pre daný risk
    if len(filtered) < count:
        filtered = [m for m in MATCH_DATABASE if m['risk'] == risk]
    
    # 4. Náhodný výber
    if len(filtered) >= count:
        return random.sample(filtered, count)
    
    return filtered

class WhopInput(BaseModel):
    message: str

@app.post("/whop")
def whop(data: WhopInput):
    return {"status": "ok"}
