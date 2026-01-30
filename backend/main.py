from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from backend import models, crud, database, ai 
from pydantic import BaseModel
import random

# 1. Inicializácia databázy
models.Base.metadata.create_all(bind=database.engine)
app = FastAPI()

# 2. HTML GRAFIKA - ULTRA PRO VERZIA
html_content = """
<!DOCTYPE html>
<html lang="sk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Betting PRO Analytics</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    
    <style>
        body { margin: 0; padding: 0; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0b0c10; color: #c5c6c7; display: flex; height: 100vh; overflow: hidden; }
        
        /* Sidebar */
        .sidebar { width: 260px; background-color: #111; display: flex; flex-direction: column; padding: 25px; border-right: 1px solid #333; }
        .logo { font-size: 22px; font-weight: 800; color: #66fcf1; margin-bottom: 50px; text-transform: uppercase; letter-spacing: 3px; text-align: center; border-bottom: 2px solid #66fcf1; padding-bottom: 20px;}
        .menu-item { padding: 15px; margin-bottom: 10px; cursor: pointer; border-radius: 8px; color: #888; font-weight: 600; transition: 0.3s; display: flex; align-items: center; gap: 15px; }
        .menu-item:hover, .menu-item.active { background-color: #1a1a1a; color: #fff; border-left: 4px solid #66fcf1; }
        
        /* Main Content */
        .main-content { flex: 1; padding: 40px; overflow-y: auto; background: #0b0c10; }
        
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 40px; }
        .header h1 { margin: 0; color: #fff; font-size: 28px; font-weight: 700; }
        
        /* Tlačidlo */
        .btn-analyze { 
            background: #66fcf1; border: none; padding: 18px 50px; 
            font-size: 18px; font-weight: 800; color: #0b0c10; border-radius: 50px; cursor: pointer; 
            box-shadow: 0 0 25px rgba(102, 252, 241, 0.4); transition: transform 0.2s;
            display: block; margin: 0 auto 40px auto; letter-spacing: 1px;
        }
        .btn-analyze:hover { transform: scale(1.05); background: #fff; }

        /* KARTA ZÁPASU (Advanced) */
        .match-card { 
            background: #151b24; border-radius: 16px; margin-bottom: 30px; overflow: hidden; 
            border: 1px solid #2c3e50; box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            animation: slideUp 0.6s cubic-bezier(0.2, 0.8, 0.2, 1);
        }
        
        .match-header { 
            background: linear-gradient(90deg, #0f141a 0%, #1a222e 100%); 
            padding: 20px 30px; display: flex; justify-content: space-between; align-items: center; 
            border-bottom: 1px solid #2c3e50;
        }
        .teams-title { font-size: 22px; font-weight: 700; color: white; }
        .match-meta { font-size: 14px; color: #66fcf1; font-weight: bold; background: rgba(102, 252, 241, 0.1); padding: 5px 15px; border-radius: 20px;}
        
        .match-body { padding: 30px; display: flex; gap: 40px; flex-wrap: wrap; }
        
        /* Stĺpce */
        .col-left { flex: 1; min-width: 300px; border-right: 1px solid #2c3e50; padding-right: 30px; }
        .col-right { flex: 1; min-width: 300px; }

        /* Štatistiky - Forma */
        .form-box { display: flex; gap: 5px; margin-top: 5px; }
        .form-badge { width: 25px; height: 25px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: bold; color: black; }
        .win { background: #2ecc71; }
        .draw { background: #f1c40f; }
        .loss { background: #e74c3c; }

        /* Progress Bary */
        .stat-group { margin-bottom: 20px; }
        .stat-label { display: flex; justify-content: space-between; font-size: 14px; margin-bottom: 5px; color: #888; }
        .progress-bg { height: 8px; background: #222; border-radius: 4px; overflow: hidden; }
        .progress-fill { height: 100%; background: #66fcf1; border-radius: 4px; }

        /* Sekcia Analýzy */
        .analysis-section h4 { color: #66fcf1; margin: 0 0 15px 0; text-transform: uppercase; font-size: 14px; letter-spacing: 1px; }
        .analysis-text { font-size: 15px; line-height: 1.6; color: #dcdcdc; }
        .analysis-list { list-style: none; padding: 0; margin-top: 15px; }
        .analysis-list li { margin-bottom: 8px; padding-left: 20px; position: relative; color: #aaa; }
        .analysis-list li::before { content: "•"; color: #66fcf1; position: absolute; left: 0; font-weight: bold; }

        /* AI Prediction Box */
        .ai-box { 
            background: rgba(102, 252, 241, 0.05); padding: 20px; border-radius: 12px; 
            border: 1px solid rgba(102, 252, 241, 0.2); display: flex; align-items: center; justify-content: space-between;
            margin-top: 20px;
        }
        .ai-tip { font-size: 24px; font-weight: 800; color: #fff; }
        .ai-confidence { background: #66fcf1; color: #000; padding: 5px 15px; border-radius: 5px; font-weight: bold; }

        .page { display: none; }
        .page.active { display: block; animation: fadeIn 0.4s;
