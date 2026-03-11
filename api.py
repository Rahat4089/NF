from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
import json
import os
import uuid
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import aiofiles
import random
from datetime import datetime
import threading
from queue import Queue
import time

# Import your checker module
from checker import check_account, parse_proxy, pick_profile

app = FastAPI(title="Netflix Account Checker API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create templates directory
os.makedirs("templates", exist_ok=True)
os.makedirs("static", exist_ok=True)

templates = Jinja2Templates(directory="templates")

# Store active checking sessions
active_sessions: Dict[str, Dict[str, Any]] = {}
session_results: Dict[str, Dict[str, List]] = {}

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)

    def disconnect(self, websocket: WebSocket, session_id: str):
        if session_id in self.active_connections:
            if websocket in self.active_connections[session_id]:
                self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

    async def send_message(self, message: dict, session_id: str):
        if session_id in self.active_connections:
            for connection in self.active_connections[session_id]:
                try:
                    await connection.send_json(message)
                except:
                    pass

manager = ConnectionManager()

# Models
class CheckRequest(BaseModel):
    accounts: List[str]
    proxies: Optional[List[str]] = None
    threads: int = 5

class CheckResponse(BaseModel):
    session_id: str
    message: str

class AccountResult(BaseModel):
    email: str
    password: str
    status: str
    details: Dict[str, Any]
    timestamp: str

# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Netflix Account Checker</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            color: #333;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }

        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }

        .header p {
            opacity: 0.9;
        }

        .main-content {
            padding: 30px;
        }

        .input-section {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
        }

        .input-group {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }

        .input-group h3 {
            margin-bottom: 15px;
            color: #667eea;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .input-group textarea {
            width: 100%;
            height: 200px;
            padding: 15px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-family: monospace;
            font-size: 14px;
            resize: vertical;
            margin-bottom: 15px;
        }

        .input-group textarea:focus {
            outline: none;
            border-color: #667eea;
        }

        .file-upload {
            border: 2px dashed #667eea;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
            margin-bottom: 15px;
        }

        .file-upload:hover {
            background: rgba(102, 126, 234, 0.1);
        }

        .file-upload input {
            display: none;
        }

        .controls {
            display: flex;
            gap: 10px;
            align-items: center;
            flex-wrap: wrap;
        }

        .controls input[type="number"] {
            padding: 10px;
            border: 2px solid #e0e0e0;
            border-radius: 5px;
            width: 100px;
        }

        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }

        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }

        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }

        .btn-success {
            background: #28a745;
            color: white;
        }

        .btn-success:hover {
            background: #218838;
        }

        .btn-danger {
            background: #dc3545;
            color: white;
        }

        .btn-danger:hover {
            background: #c82333;
        }

        .progress-section {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 30px;
        }

        .progress-stats {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }

        .stat-card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }

        .stat-card h4 {
            font-size: 14px;
            color: #666;
            margin-bottom: 10px;
        }

        .stat-card .stat-value {
            font-size: 28px;
            font-weight: bold;
            color: #667eea;
        }

        .progress-bar-container {
            width: 100%;
            height: 30px;
            background: #e0e0e0;
            border-radius: 15px;
            overflow: hidden;
            margin-bottom: 10px;
        }

        .progress-bar {
            height: 100%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 14px;
        }

        .results-section {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }

        .results-box {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            height: 400px;
            display: flex;
            flex-direction: column;
        }

        .results-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e0e0e0;
        }

        .results-header h3 {
            color: #667eea;
        }

        .results-header .count {
            background: #667eea;
            color: white;
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 14px;
        }

        .results-content {
            flex: 1;
            overflow-y: auto;
            font-family: monospace;
            font-size: 13px;
        }

        .result-item {
            background: white;
            border-radius: 5px;
            padding: 10px;
            margin-bottom: 8px;
            border-left: 4px solid;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }

        .result-item.hit {
            border-left-color: #28a745;
        }

        .result-item.custom {
            border-left-color: #ffc107;
        }

        .result-item.fail {
            border-left-color: #dc3545;
        }

        .result-item .email {
            font-weight: bold;
            color: #333;
        }

        .result-item .details {
            font-size: 12px;
            color: #666;
            margin-top: 5px;
        }

        .status-badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 11px;
            font-weight: bold;
            margin-left: 8px;
        }

        .badge-hit {
            background: #28a745;
            color: white;
        }

        .badge-custom {
            background: #ffc107;
            color: #333;
        }

        .timestamp {
            font-size: 10px;
            color: #999;
            margin-top: 5px;
            text-align: right;
        }

        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .hidden {
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎬 Netflix Account Checker</h1>
            <p>Check multiple Netflix accounts with real-time progress and results</p>
        </div>

        <div class="main-content">
            <div class="input-section">
                <div class="input-group">
                    <h3>📧 Accounts (email:password)</h3>
                    <div class="file-upload" onclick="document.getElementById('accounts-file').click()">
                        <input type="file" id="accounts-file" accept=".txt" onchange="loadFile('accounts')">
                        <p>📁 Click or drag to upload accounts.txt</p>
                        <p style="font-size: 12px; color: #666;">or enter manually below</p>
                    </div>
                    <textarea id="accounts-input" placeholder="Enter accounts (one per line, format: email:password)"></textarea>
                </div>

                <div class="input-group">
                    <h3>🌐 Proxies (optional)</h3>
                    <div class="file-upload" onclick="document.getElementById('proxies-file').click()">
                        <input type="file" id="proxies-file" accept=".txt" onchange="loadFile('proxies')">
                        <p>📁 Click or drag to upload proxies.txt</p>
                        <p style="font-size: 12px; color: #666;">or enter manually below</p>
                    </div>
                    <textarea id="proxies-input" placeholder="Enter proxies (one per line, format: ip:port or user:pass@ip:port)"></textarea>
                </div>
            </div>

            <div class="controls">
                <div style="flex: 1;">
                    <label for="threads">Threads:</label>
                    <input type="number" id="threads" min="1" max="20" value="5">
                </div>
                <button class="btn btn-primary" onclick="startChecking()">▶ Start Checking</button>
                <button class="btn btn-success" onclick="stopChecking()" disabled id="stopBtn">⏹ Stop</button>
                <button class="btn btn-danger" onclick="clearResults()">🗑 Clear Results</button>
                <button class="btn" onclick="exportResults()">📥 Export Results</button>
            </div>

            <div class="progress-section" id="progress-section" style="display: none;">
                <div class="progress-stats">
                    <div class="stat-card">
                        <h4>Total</h4>
                        <div class="stat-value" id="total-count">0</div>
                    </div>
                    <div class="stat-card">
                        <h4>Checked</h4>
                        <div class="stat-value" id="checked-count">0</div>
                    </div>
                    <div class="stat-card">
                        <h4>HIT</h4>
                        <div class="stat-value" id="hit-count">0</div>
                    </div>
                    <div class="stat-card">
                        <h4>CUSTOM</h4>
                        <div class="stat-value" id="custom-count">0</div>
                    </div>
                    <div class="stat-card">
                        <h4>Failed</h4>
                        <div class="stat-value" id="fail-count">0</div>
                    </div>
                </div>
                <div class="progress-bar-container">
                    <div class="progress-bar" id="progress-bar" style="width: 0%">0%</div>
                </div>
                <div style="text-align: center; color: #666;" id="status-message">Ready to start</div>
            </div>

            <div class="results-section">
                <div class="results-box">
                    <div class="results-header">
                        <h3>✅ HIT Results</h3>
                        <div class="count" id="hit-count-display">0</div>
                    </div>
                    <div class="results-content" id="hit-results"></div>
                </div>

                <div class="results-box">
                    <div class="results-header">
                        <h3>⚠️ CUSTOM Results</h3>
                        <div class="count" id="custom-count-display">0</div>
                    </div>
                    <div class="results-content" id="custom-results"></div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let ws = null;
        let sessionId = null;
        let isChecking = false;
        let results = {
            hit: [],
            custom: [],
            fail: []
        };

        function loadFile(type) {
            const fileInput = document.getElementById(type + '-file');
            const file = fileInput.files[0];
            if (!file) return;

            const reader = new FileReader();
            reader.onload = function(e) {
                document.getElementById(type + '-input').value = e.target.result;
            };
            reader.readAsText(file);
        }

        async function startChecking() {
            const accounts = document.getElementById('accounts-input').value
                .split('\\n')
                .map(line => line.trim())
                .filter(line => line && line.includes(':'));

            if (accounts.length === 0) {
                alert('Please enter at least one account');
                return;
            }

            const proxies = document.getElementById('proxies-input').value
                .split('\\n')
                .map(line => line.trim())
                .filter(line => line);

            const threads = parseInt(document.getElementById('threads').value);

            // Show progress section
            document.getElementById('progress-section').style.display = 'block';
            document.getElementById('stopBtn').disabled = false;
            
            // Reset progress
            updateProgress({
                total: accounts.length,
                checked: 0,
                hit: 0,
                custom: 0,
                fail: 0,
                current: 0,
                message: 'Starting...'
            });

            try {
                const response = await fetch('/api/check', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        accounts: accounts,
                        proxies: proxies.length > 0 ? proxies : null,
                        threads: threads
                    })
                });

                const data = await response.json();
                sessionId = data.session_id;
                
                // Connect WebSocket
                connectWebSocket();
                
            } catch (error) {
                console.error('Error starting check:', error);
                alert('Error starting check: ' + error.message);
            }
        }

        function connectWebSocket() {
            ws = new WebSocket(`ws://${window.location.host}/ws/${sessionId}`);
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                
                switch(data.type) {
                    case 'progress':
                        updateProgress(data.data);
                        break;
                    case 'result':
                        addResult(data.data);
                        break;
                    case 'complete':
                        onCheckComplete(data.data);
                        break;
                }
            };

            ws.onclose = function() {
                if (isChecking) {
                    console.log('WebSocket closed, attempting to reconnect...');
                    setTimeout(connectWebSocket, 1000);
                }
            };
        }

        function updateProgress(data) {
            document.getElementById('total-count').textContent = data.total;
            document.getElementById('checked-count').textContent = data.checked;
            document.getElementById('hit-count').textContent = data.hit;
            document.getElementById('custom-count').textContent = data.custom;
            document.getElementById('fail-count').textContent = data.fail;
            
            const percent = data.total > 0 ? Math.round((data.checked / data.total) * 100) : 0;
            document.getElementById('progress-bar').style.width = percent + '%';
            document.getElementById('progress-bar').textContent = percent + '%';
            
            document.getElementById('status-message').textContent = data.message || `Checked ${data.checked}/${data.total} accounts`;
        }

        function addResult(data) {
            const resultDiv = document.createElement('div');
            resultDiv.className = `result-item ${data.status.toLowerCase()}`;
            
            let detailsHtml = '';
            if (data.status === 'HIT') {
                detailsHtml = `
                    <div class="details">
                        Plan: ${data.details.plan || 'N/A'} | 
                        Price: ${data.details.price || 'N/A'} | 
                        Next Billing: ${data.details.next_billing || 'N/A'}<br>
                        Payment: ${data.details.payment_method || 'N/A'} ${data.details.card_last_4 || ''}
                    </div>
                `;
            } else if (data.status === 'CUSTOM') {
                detailsHtml = `
                    <div class="details">
                        Message: ${data.details.message || 'Custom response'}<br>
                        Country: ${data.details.country || 'N/A'}
                    </div>
                `;
            }

            resultDiv.innerHTML = `
                <div>
                    <span class="email">${data.email}</span>
                    <span class="status-badge badge-${data.status.toLowerCase()}">${data.status}</span>
                </div>
                ${detailsHtml}
                <div class="timestamp">${data.timestamp}</div>
            `;

            if (data.status === 'HIT') {
                document.getElementById('hit-results').prepend(resultDiv);
                document.getElementById('hit-count-display').textContent = 
                    parseInt(document.getElementById('hit-count-display').textContent) + 1;
            } else if (data.status === 'CUSTOM') {
                document.getElementById('custom-results').prepend(resultDiv);
                document.getElementById('custom-count-display').textContent = 
                    parseInt(document.getElementById('custom-count-display').textContent) + 1;
            }

            // Remove from input
            removeCheckedAccount(data.email);
        }

        function removeCheckedAccount(email) {
            const input = document.getElementById('accounts-input');
            const lines = input.value.split('\\n');
            const filtered = lines.filter(line => {
                const lineEmail = line.split(':')[0];
                return lineEmail !== email;
            });
            input.value = filtered.join('\\n');
        }

        function onCheckComplete(data) {
            isChecking = false;
            document.getElementById('stopBtn').disabled = true;
            document.getElementById('status-message').textContent = '✓ Check complete!';
            
            if (ws) {
                ws.close();
            }
        }

        function stopChecking() {
            if (sessionId) {
                fetch(`/api/stop/${sessionId}`, { method: 'POST' })
                    .then(() => {
                        isChecking = false;
                        document.getElementById('stopBtn').disabled = true;
                        document.getElementById('status-message').textContent = '⏹ Stopped by user';
                        if (ws) {
                            ws.close();
                        }
                    });
            }
        }

        function clearResults() {
            document.getElementById('hit-results').innerHTML = '';
            document.getElementById('custom-results').innerHTML = '';
            document.getElementById('hit-count-display').textContent = '0';
            document.getElementById('custom-count-display').textContent = '0';
            
            // Reset progress
            document.getElementById('total-count').textContent = '0';
            document.getElementById('checked-count').textContent = '0';
            document.getElementById('hit-count').textContent = '0';
            document.getElementById('custom-count').textContent = '0';
            document.getElementById('fail-count').textContent = '0';
            document.getElementById('progress-bar').style.width = '0%';
            document.getElementById('progress-bar').textContent = '0%';
            document.getElementById('status-message').textContent = 'Ready to start';
            document.getElementById('progress-section').style.display = 'none';
        }

        function exportResults() {
            const hitResults = [];
            document.querySelectorAll('#hit-results .result-item').forEach(item => {
                const email = item.querySelector('.email').textContent;
                const details = item.querySelector('.details')?.textContent || '';
                hitResults.push(`${email} | ${details}`);
            });

            const customResults = [];
            document.querySelectorAll('#custom-results .result-item').forEach(item => {
                const email = item.querySelector('.email').textContent;
                const details = item.querySelector('.details')?.textContent || '';
                customResults.push(`${email} | ${details}`);
            });

            const data = {
                hit: hitResults,
                custom: customResults,
                timestamp: new Date().toISOString()
            };

            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `netflix_results_${new Date().getTime()}.json`;
            a.click();
        }

        // Drag and drop support
        ['accounts-input', 'proxies-input'].forEach(id => {
            const textarea = document.getElementById(id);
            
            textarea.addEventListener('dragover', (e) => {
                e.preventDefault();
                textarea.style.borderColor = '#667eea';
            });

            textarea.addEventListener('dragleave', () => {
                textarea.style.borderColor = '#e0e0e0';
            });

            textarea.addEventListener('drop', (e) => {
                e.preventDefault();
                textarea.style.borderColor = '#e0e0e0';
                
                const file = e.dataTransfer.files[0];
                if (file && file.type === 'text/plain') {
                    const reader = new FileReader();
                    reader.onload = (event) => {
                        textarea.value = event.target.result;
                    };
                    reader.readAsText(file);
                }
            });
        });
    </script>
</body>
</html>
"""

# Write HTML template to file
with open("templates/index.html", "w") as f:
    f.write(HTML_TEMPLATE)

# Account checking worker
async def check_accounts_worker(session_id: str, accounts: List[tuple], proxies: List[str], threads: int):
    """Background worker to check accounts"""
    
    # Initialize session data
    session_results[session_id] = {
        "hit": [],
        "custom": [],
        "fail": [],
        "total": len(accounts),
        "checked": 0,
        "current": 0,
        "running": True
    }
    
    # Split accounts into chunks for threading
    chunks = [accounts[i:i + threads] for i in range(0, len(accounts), threads)]
    
    for chunk in chunks:
        if not session_results[session_id]["running"]:
            break
            
        # Check accounts in parallel
        tasks = []
        for email, password in chunk:
            task = asyncio.create_task(
                check_single_account(session_id, email, password, proxies)
            )
            tasks.append(task)
        
        # Wait for all tasks in chunk to complete
        await asyncio.gather(*tasks, return_exceptions=True)
    
    # Send completion message
    await manager.send_message({
        "type": "complete",
        "data": {
            "message": "All accounts checked",
            "stats": {
                "hit": len(session_results[session_id]["hit"]),
                "custom": len(session_results[session_id]["custom"]),
                "fail": len(session_results[session_id]["fail"])
            }
        }
    }, session_id)
    
    # Clean up old sessions (keep for 5 minutes)
    await asyncio.sleep(300)
    if session_id in session_results:
        del session_results[session_id]

async def check_single_account(session_id: str, email: str, password: str, proxies: List[str]):
    """Check a single account"""
    
    if not session_results[session_id]["running"]:
        return
    
    # Select random proxy if available
    proxy = random.choice(proxies) if proxies else None
    
    try:
        # Run the account check in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, 
            check_account,
            email, password, proxy
        )
        
        # Update results
        session_results[session_id]["checked"] += 1
        session_results[session_id]["current"] += 1
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if result["status"] == "HIT":
            session_results[session_id]["hit"].append(result)
            await manager.send_message({
                "type": "result",
                "data": {
                    "email": email,
                    "password": password,
                    "status": "HIT",
                    "details": result,
                    "timestamp": timestamp
                }
            }, session_id)
            
        elif result["status"] == "CUSTOM":
            session_results[session_id]["custom"].append(result)
            await manager.send_message({
                "type": "result",
                "data": {
                    "email": email,
                    "password": password,
                    "status": "CUSTOM",
                    "details": result,
                    "timestamp": timestamp
                }
            }, session_id)
        else:
            session_results[session_id]["fail"].append(result)
        
        # Send progress update
        await manager.send_message({
            "type": "progress",
            "data": {
                "total": session_results[session_id]["total"],
                "checked": session_results[session_id]["checked"],
                "hit": len(session_results[session_id]["hit"]),
                "custom": len(session_results[session_id]["custom"]),
                "fail": len(session_results[session_id]["fail"]),
                "current": session_results[session_id]["current"],
                "message": f"Checked {email}"
            }
        }, session_id)
        
    except Exception as e:
        print(f"Error checking {email}: {str(e)}")
        session_results[session_id]["checked"] += 1
        session_results[session_id]["fail"].append({
            "email": email,
            "status": "ERROR",
            "message": str(e)
        })

# API Routes
@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/check", response_model=CheckResponse)
async def start_check(request: CheckRequest):
    """Start checking accounts"""
    
    # Generate session ID
    session_id = str(uuid.uuid4())
    
    # Parse accounts into list of tuples
    accounts = []
    for account in request.accounts:
        if ":" in account:
            email, password = account.split(":", 1)
            accounts.append((email.strip(), password.strip()))
    
    if not accounts:
        raise HTTPException(status_code=400, detail="No valid accounts provided")
    
    # Start background task
    asyncio.create_task(
        check_accounts_worker(session_id, accounts, request.proxies or [], request.threads)
    )
    
    return CheckResponse(
        session_id=session_id,
        message=f"Started checking {len(accounts)} accounts"
    )

@app.post("/api/stop/{session_id}")
async def stop_check(session_id: str):
    """Stop a checking session"""
    if session_id in session_results:
        session_results[session_id]["running"] = False
        return {"message": "Stopped"}
    raise HTTPException(status_code=404, detail="Session not found")

@app.get("/api/results/{session_id}")
async def get_results(session_id: str):
    """Get results for a session"""
    if session_id in session_results:
        return session_results[session_id]
    raise HTTPException(status_code=404, detail="Session not found")

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket connection for real-time updates"""
    await manager.connect(websocket, session_id)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a file"""
    content = await file.read()
    text = content.decode('utf-8')
    return {"content": text}

if __name__ == "__main__":
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
