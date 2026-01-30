from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from backend import models, crud, database, ai 
from pydantic import BaseModel
import random

# 1. Inicializácia databázy
models.Base.metadata.create_all(bind=database.engine)
app = FastAPI()

# 2. HTML GRAFIKA - PRO VERZIA S GRAFOM
html_content = """
<!DOCTYPE html>
<html lang="sk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Betting PRO Analytics</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    
    <style>
        body { margin: 0; padding: 0; font-family: 'Segoe UI', sans-serif; background-color: #0b0c10; color: #c5c6c7; display: flex; height: 100vh; overflow: hidden; }
        
        /* Sidebar */
        .sidebar { width: 260px; background-color: #1f2833; display: flex; flex-direction: column; padding: 20px; border-right: 1px solid #45a29e; }
        .logo { font-size: 24px; font-weight: bold; color: #66fcf1; margin-bottom: 40px; text-transform: uppercase; letter-spacing: 2px; text-align: center; }
        .menu-item { padding: 15px; margin-bottom: 5px; cursor: pointer; border-radius: 5px; color: #fff; font-weight: 500; transition: 0.3s; display: flex; align-items: center; gap: 10px; }
        .menu-item:hover, .menu-item.active { background-color: #45a29e; color: #0b0c10; box-shadow: 0 0 10px rgba(102, 252, 241, 0.4); }
        
        /* Main Content */
        .main-content { flex: 1; padding: 30px; overflow-y: auto; background: radial-gradient(circle at top, #1f2833 0%, #0b0c10 80%); }
        
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; border-bottom: 2px solid #45a29e; padding-bottom: 15px; }
        .header h1 { margin: 0; color: #fff; }
        
        /* Tlačidlo */
        .btn-analyze { 
            background: linear-gradient(45deg, #45a29e, #66fcf1); border: none; padding: 15px 40px; 
            font-size: 18px; font-weight: bold; color: #0b0c10; border-radius: 30px; cursor: pointer; 
            box-shadow: 0 0 20px rgba(102, 252, 241, 0.3); transition: transform 0.2s;
            display: block; margin: 0 auto 30px auto;
        }
        .btn-analyze:hover { transform: scale(1.05); }

        /* KARTA ZÁPASU */
        .match-card { 
            background: #1f2833; border-radius: 10px; margin-bottom: 25px; overflow: hidden; 
            border: 1px solid #333; box-shadow: 0 5px 15px rgba(0,0,0,0.5);
            animation: slideUp 0.5s ease;
        }
        .match-header { background: #0b0c10; padding: 15px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #45a29e; }
        .teams { font-size: 20px; font-weight: bold; color: white; }
        .league { font-size: 14px; color: #66fcf1; font-weight: bold; }
        .match-body { padding: 20px; display: flex; gap: 20px; flex-wrap: wrap; }
        .stats-col { flex:
