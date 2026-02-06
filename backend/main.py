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

# --- KONFIGURÁCIA ---
ODDS_API_KEY = "3e42c726ab364fb9eeede03b0017964c"
GEMINI_API_KEY = "AIzaSyCreRpXTUwxzJegxQKUJ2RiX5BwSagdljg"

if GEMINI_API_KEY != "VLOZ_SVOJ_GEMINI_KLUC_SEM":
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-pro')

CACHE = {"data": [], "last_update": 0}

# --- HTML GRAFIKA (Frontend) ---
html_content = """
<!DOCTYPE html>
<html lang="sk">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Betting PRO AI</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body{margin:0;font-family:sans-serif;background:#0b0c10;color:#c5c6c7;display:flex;height:100vh}
.sidebar{width:260px;background:#111;padding:20px;border-right:1px solid #333;display:flex;flex-direction:column}
.main-content{flex:1;padding:30px;overflow-y:auto}
.menu-item{padding:15px;cursor:pointer;color:#888;margin-bottom:5px}
.menu-item.active{color:#fff;border-left:4px solid #66fcf1;background:#1f2833}
.card{background:#1f2833;padding:20px;border-radius:10px;margin-bottom:20px;border:1px solid #2c3e50}
.btn{background:#66fcf1;border:none;padding:10px 20px;font-weight:bold;cursor:pointer;width:100%}
.page{display:none} .page.active{display:block}
.ac-header{display:flex;justify-content:space-between;border-bottom:1px solid #333;padding-bottom:10px;margin-bottom:10px}
.ac-row{display:flex;justify-content:space-between;margin-bottom:5px;font-size:14px}
.ticket-row{display:flex;justify-content:space-between;border-bottom:1px dashed #444;padding:10px 0}
@media(max-width:768px){.sidebar{display:none}.mobile-nav{display:flex;position:fixed;bottom:0;width:100%;background:#111;justify-content:space-around;padding:15px;border-top:1px solid #333}}
</style>
</head>
<body>
<div class="sidebar">
 <h2 style="color:#66fcf1;text-align:center">BET PRO</h2>
 <div class="menu-item active" onclick="show('home',this)">🏠 Dashboard</div>
 <div class="menu-item" onclick="show('gen',this)">🧠 AI Analýza</div>
 <div class="menu-item" onclick="show('tik',this)">🎯 Tiket Dňa</div>
 <div class="menu-item" onclick="show('cust',this)">🛠️ Vlastný Tiket</div>
</div>
<div class="main-content">
 <div id="home" class="page active">
  <h1>Dashboard</h1>
  <div style="display:flex;gap:20px">
   <div class="card" style="flex:1"><h3>Bankroll</h3><h1>€1,000</h1></div>
   <div class="card" style="flex:1"><h3>Zisk</h3><h1 style="color:#00ff88">+12%</h1></div>
  </div>
  <div class="card"><canvas id="chart"></canvas></div>
 </div>
 <div id="gen" class="page">
  <h1>AI Analýza</h1>
  <button class="btn" onclick="loadAnalysis()">Načítať Live Dáta</button>
  <div id="out-gen" style="margin-top:20px"></div>
 </div>
 <div id="tik" class="page">
  <h1>Tiket Dňa</h1>
  <button class="btn" onclick="loadTicket()">Generovať Tutovku</button>
  <div id="out-tik" style="margin-top:20px"></div>
 </div>
 <div id="cust" class="page">
  <h1>Vlastný Tiket</h1>
  <select id="risk" style="width:100%;padding:10px;margin-bottom:10px;background:#111;color:#fff;border:1px solid #333">
   <option value="1">Nízke Riziko</option><option value="2">Stredné</option><option value="3">Vysoké</option>
  </select>
  <button class="btn" onclick="loadCustom()">Generovať</button>
  <div id="out-cust" style="margin-top:20px"></div>
 </div>
</div>
<div class="mobile-nav" style="display:none">
 <span onclick="show('home')">🏠</span><span onclick="show('gen')">🧠</span><span onclick="show('tik')">🎯</span><span onclick="show('cust')">🛠️</span>
</div>
<script>
function show(id,el){
 document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));
 document.getElementById(id).classList.add('active');
 if(el){document.querySelectorAll('.menu-item').forEach(m=>m.classList.remove('active'));el.classList.add('active')}
}
if(window.innerWidth<768)document.querySelector('.mobile-nav').style.display='flex';

new Chart(document.getElementById('chart'),{type:'line',data:{labels:['P','U','S','Š','P','S','N'],datasets:[{label:'Bankroll',data:[1000,1050,1020,1100,1150,1200,1250],borderColor:'#66fcf1',backgroundColor:'rgba(102,252,241,0.1)',fill:true}]},options:{scales:{y:{grid:{color:'#333'}},x:{display:false}},plugins:{legend:{display:false}}}});

async function loadAnalysis(){
 document.getElementById('out-gen').innerHTML='Načítavam...';
 const res=await fetch('/api/analyza');const data=await res.json();
 let h='';
 data.forEach(m=>{
  let body=''; if(m.analyza_body) m.analyza_body.forEach(b=>body+=`<li>${b}</li>`);
  h+=`<div class="card">
   <div class="ac-header"><b>${m.domaci} vs ${m.hostia}</b> <span style="color:#66fcf1">${m.kurz}</span></div>
   <div class="ac-row"><span>Tip: ${m.tip}</span><span>Dôvera: ${m.dovera}%</span></div>
   <p style="color:#ccc;font-style:italic">"${m.analyza_text}"</p>
   <ul style="color:#888;padding-left:20px">${body}</ul>
  </div>`;
 });
 document.getElementById('out-gen').innerHTML=h;
}

async function loadTicket(){ renderTicket('/api/tiket-dna','out-tik'); }
async function loadCustom(){ renderTicket('/api/vlastny-tiket?risk='+document.getElementById('risk').value,'out-cust'); }

async function renderTicket(url,elId){
 document.getElementById(elId).innerHTML='Generujem...';
 const res=await fetch(url);const data=await res.json();
 if(!data.length){document.getElementById(elId).innerHTML='Žiadne dáta.';return}
 let h=''; let total=1; let matches=[];
 data.forEach(m=>{
  total*=m.kurz; matches.push(`${m.domaci} (${m.tip})`);
  h+=`<div class="ticket-row"><div><b>${m.domaci}-${m.hostia}</b><br><small>${m.tip}</small></div><b>${m.kurz}</b></div>`;
 });
 h+=`<div style="margin-top:20px;text-align:right"><h3>Kurz: ${total.toFixed(2)}</h3></div>`;
 h+=`<button class="btn" style="background:#00ff88;color:#000;margin-top:10px" onclick="alert('Tiket uložený!')">VSAĎIŤ</button>`;
 document.getElementById(elId).innerHTML=h;
}
</script>
</body>
</html>
"""

# --- LOGIKA ---
def calculate_smart_stats(o1, o2):
    prob_h = (1/o1)*100; prob_a = (1/o2)*100
    return {
        "utok_domaci": min(99, int(prob_h+random.randint(-5,5))),
        "utok_hostia": min(99, int(prob_a+random.randint(-5,5))),
        "zranenia": random.choice(["Bez absencií", "Otázny útok", "Kompletná zostava"])
    }

def get_ai_text(home, away, o1, o2, tip):
    default_text = f"Na základe kurzov {o1} vs {o2} je tip '{tip}' najpravdepodobnejší."
    default_body = ["Hodnota v kurze.", "Forma tímov zodpovedá.", "Dôležitý zápas."]
    
    if GEMINI_API_KEY != "VLOZ_SVOJ_GEMINI_KLUC_SEM":
        try:
            prompt = f"Analyzuj futbal {home} vs {away} (Kurzy {o1}-{o2}). Tip {tip}. Napíš 1 vetu a 3 body. Slovensky."
            resp = model.generate_content(prompt)
            lines = resp.text.split('\n')
            return lines[0], [l.strip('-• ') for l in lines[1:] if l.strip()][:3]
        except: pass
    return default_text, default_body

def get_live_data():
    if time.time()-CACHE["last_update"]<3600 and CACHE["data"]: return CACHE["data"]
    if ODDS_API_KEY=="VLOZ_SVOJ_ODDS_API_KLUC_SEM": return get_demo()
    
    try:
        url = f"https://api.the-odds-api.com/v4/sports/soccer_epl/odds/?regions=eu&markets=h2h&apiKey={ODDS_API_KEY}"
        data = requests.get(url).json()
        matches = []
        for item in data[:8]:
            try:
                h, a = item['home_team'], item['away_team']
                odds = item['bookmakers'][0]['markets'][0]['outcomes']
                o1 = next(x['price'] for x in odds if x['name']==h)
                o2 = next(x['price'] for x in odds if x['name']==a)
                
                risk=1; tip="1"; dovera=85
                if o1<1.5: risk=1; tip="1"
                elif o2<1.5: risk=1; tip="2"
                elif o1<2.1: risk=2; tip="1"; dovera=70
                else: risk=3; tip="X"; dovera=50
                
                atext, abody = get_ai_text(h, a, o1, o2, tip)
                matches.append({"domaci":h, "hostia":a, "kurz":o1 if tip=="1" else (o2 if tip=="2" else 3.2), "tip":tip, "risk":risk, "dovera":dovera, "analyza_text":atext, "analyza_body":abody})
            except: continue
        CACHE["data"]=matches; CACHE["last_update"]=time.time()
        return matches
    except: return get_demo()

def get_demo():
    return [{"domaci":"Man City (DEMO)", "hostia":"Arsenal", "kurz":2.10, "tip":"1", "risk":2, "dovera":75, "analyza_text":"Vlož API kľúč.", "analyza_body":[]}]

@app.get("/")
def home(): return HTMLResponse(content=html_content)

@app.get("/api/analyza")
def api_an(): return get_live_data()

@app.get("/api/tiket-dna")
def api_td(): 
    d = get_live_data()
    return [m for m in d if m['risk']==1][:3]

@app.get("/api/vlastny-tiket")
def api_cust(risk:int=1):
    d = get_live_data()
    return [m for m in d if m['risk']==risk][:3]

class WhopIn(BaseModel): message: str
@app.post("/whop")
def whop(d: WhopIn): return {"status":"ok"}
