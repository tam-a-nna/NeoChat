"""
NeoChat - Modern LAN Chat System with Admin Features
"""

import asyncio
import threading
import json
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
import os

TCP_PORT = 5000
WEB_PORT = 8080

# Admin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

# Store messages and clients
messages = []
clients = {}
banned_users = []

class ChatServer:
    async def start(self):
        server = await asyncio.start_server(
            self.handle_client,
            '127.0.0.1',
            TCP_PORT
        )
        print(f'TCP Server running on port {TCP_PORT}')
        print(f'Admin Login: {ADMIN_USERNAME} / {ADMIN_PASSWORD}')
        async with server:
            await server.serve_forever()
    
    async def handle_client(self, reader, writer):
        writer.write(b'Enter name: ')
        await writer.drain()
        
        data = await reader.read(100)
        name = data.decode().strip()
        
        # Check if user is banned
        if name in banned_users:
            writer.write(b'You are banned from this chat\n')
            await writer.drain()
            writer.close()
            return
        
        clients[name] = writer
        print(f'{name} joined')
        
        # Check if admin joined
        is_admin = (name == 'Admin')
        
        messages.append({
            'type': 'system',
            'content': f'{name} joined the chat',
            'time': datetime.now().strftime('%H:%M:%S')
        })
        
        while True:
            data = await reader.read(1024)
            if not data:
                break
            msg = data.decode().strip()
            if msg == '/quit':
                break
            
            # Admin commands
            if is_admin and msg.startswith('/'):
                await self.handle_admin_command(msg, name)
                continue
            
            messages.append({
                'type': 'chat',
                'sender': name,
                'content': msg,
                'time': datetime.now().strftime('%H:%M:%S')
            })
            
            for client in clients.values():
                try:
                    client.write(f'{name}: {msg}\n'.encode())
                    await client.drain()
                except:
                    pass
        
        del clients[name]
        messages.append({
            'type': 'system',
            'content': f'{name} left the chat',
            'time': datetime.now().strftime('%H:%M:%S')
        })
    
    async def handle_admin_command(self, command, admin_name):
        parts = command.split()
        cmd = parts[0].lower()
        
        if cmd == '/kick' and len(parts) > 1:
            target = parts[1]
            if target in clients:
                writer = clients[target]
                writer.write(b'You have been kicked by Admin\n')
                await writer.drain()
                writer.close()
                del clients[target]
                messages.append({
                    'type': 'system',
                    'content': f'{target} was kicked by Admin',
                    'time': datetime.now().strftime('%H:%M:%S')
                })
        
        elif cmd == '/ban' and len(parts) > 1:
            target = parts[1]
            if target in clients:
                banned_users.append(target)
                writer = clients[target]
                writer.write(b'You have been banned by Admin\n')
                await writer.drain()
                writer.close()
                del clients[target]
                messages.append({
                    'type': 'system',
                    'content': f'{target} was banned by Admin',
                    'time': datetime.now().strftime('%H:%M:%S')
                })
        
        elif cmd == '/clear':
            messages.clear()
            messages.append({
                'type': 'system',
                'content': 'Chat cleared by Admin',
                'time': datetime.now().strftime('%H:%M:%S')
            })
        
        elif cmd == '/users':
            user_list = list(clients.keys())
            messages.append({
                'type': 'system',
                'content': f'Online users: {", ".join(user_list)}',
                'time': datetime.now().strftime('%H:%M:%S')
            })

class WebHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML.encode())
        elif self.path == '/api/messages':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'messages': messages[-50:]}).encode())
        elif self.path == '/api/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'clients': len(clients), 'users': list(clients.keys())}).encode())
        else:
            self.send_error(404)
    
    def do_POST(self):
        if self.path == '/api/send':
            length = int(self.headers['Content-Length'])
            data = json.loads(self.rfile.read(length))
            nickname = data.get('nickname', '')
            message = data.get('message', '')
            is_admin = data.get('isAdmin', False)
            
            # Handle admin commands from web
            if is_admin and message.startswith('/'):
                self.handle_admin_command_web(message, nickname)
            else:
                messages.append({
                    'type': 'chat',
                    'sender': nickname if not is_admin else 'Admin',
                    'content': message,
                    'time': datetime.now().strftime('%H:%M:%S')
                })
            
            while len(messages) > 100:
                messages.pop(0)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'success': True}).encode())
        elif self.path == '/api/admin/login':
            length = int(self.headers['Content-Length'])
            data = json.loads(self.rfile.read(length))
            username = data.get('username', '')
            password = data.get('password', '')
            
            success = (username == ADMIN_USERNAME and password == ADMIN_PASSWORD)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'success': success}).encode())
    
    def handle_admin_command_web(self, command, admin_name):
        parts = command.split()
        cmd = parts[0].lower()
        
        if cmd == '/kick' and len(parts) > 1:
            target = parts[1]
            if target in clients:
                messages.append({
                    'type': 'system',
                    'content': f'{target} was kicked by Admin',
                    'time': datetime.now().strftime('%H:%M:%S')
                })
        
        elif cmd == '/clear':
            messages.clear()
            messages.append({
                'type': 'system',
                'content': 'Chat cleared by Admin',
                'time': datetime.now().strftime('%H:%M:%S')
            })
        
        elif cmd == '/users':
            user_list = list(clients.keys())
            messages.append({
                'type': 'system',
                'content': f'Online users: {", ".join(user_list)}',
                'time': datetime.now().strftime('%H:%M:%S')
            })
    
    def log_message(self, format, *args):
        pass

HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>NeoChat | Modern LAN Chat</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            overflow: hidden;
            position: relative;
        }

        body::before {
            content: '';
            position: absolute;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(255,255,255,0.1) 1px, transparent 1px);
            background-size: 50px 50px;
            animation: moveBackground 20s linear infinite;
            opacity: 0.3;
        }

        @keyframes moveBackground {
            0% { transform: translate(0, 0); }
            100% { transform: translate(50px, 50px); }
        }

        .container {
            width: 100%;
            height: 100%;
            display: flex;
            justify-content: center;
            align-items: center;
            position: relative;
            z-index: 1;
        }

        /* Login Screen */
        .login-screen {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.95);
            backdrop-filter: blur(20px);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 2000;
        }

        .login-card {
            background: white;
            border-radius: 30px;
            padding: 50px;
            width: 90%;
            max-width: 450px;
            text-align: center;
        }

        .login-card h2 {
            color: #667eea;
            margin-bottom: 20px;
        }

        .login-card input {
            width: 100%;
            padding: 14px;
            margin: 10px 0;
            border: 2px solid #e0e0e0;
            border-radius: 12px;
            font-size: 16px;
        }

        .login-card button {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            margin-top: 10px;
        }

        .error {
            color: red;
            font-size: 12px;
            margin-top: 10px;
            display: none;
        }

        /* Join Screen */
        .join-screen {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.85);
            backdrop-filter: blur(20px);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }

        .join-card {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 30px;
            padding: 50px;
            width: 90%;
            max-width: 450px;
            text-align: center;
            animation: slideUp 0.6s ease-out;
        }

        @keyframes slideUp {
            from { opacity: 0; transform: translateY(50px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .logo {
            font-size: 80px;
            margin-bottom: 20px;
            animation: bounce 2s infinite;
        }

        @keyframes bounce {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-10px); }
        }

        .join-card h1 {
            font-size: 32px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }

        .input-group {
            margin-bottom: 20px;
            text-align: left;
        }

        .input-group label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 600;
        }

        .input-group input {
            width: 100%;
            padding: 14px;
            border: 2px solid #e0e0e0;
            border-radius: 12px;
            font-size: 16px;
        }

        .join-btn {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            font-weight: 700;
            margin-top: 10px;
        }

        /* Chat Interface */
        .chat-container {
            width: 95%;
            max-width: 1400px;
            height: 90vh;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 30px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            animation: fadeIn 0.5s;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: scale(0.95); }
            to { opacity: 1; transform: scale(1); }
        }

        .chat-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .header-left {
            display: flex;
            align-items: center;
            gap: 15px;
        }

        .status-badge {
            display: flex;
            align-items: center;
            gap: 8px;
            background: rgba(255, 255, 255, 0.2);
            padding: 8px 16px;
            border-radius: 20px;
        }

        .status-dot {
            width: 10px;
            height: 10px;
            background: #2ecc71;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(1.2); }
            100% { opacity: 1; transform: scale(1); }
        }

        .messages-area {
            flex: 1;
            overflow-y: auto;
            padding: 30px;
            background: #f8f9fa;
            display: flex;
            flex-direction: column;
            gap: 15px;
        }

        .messages-area::-webkit-scrollbar {
            width: 6px;
        }

        .messages-area::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 10px;
        }

        .messages-area::-webkit-scrollbar-thumb {
            background: #667eea;
            border-radius: 10px;
        }

        .message {
            display: flex;
            animation: messageSlide 0.3s ease-out;
        }

        @keyframes messageSlide {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .message.system {
            justify-content: center;
        }

        .message.system .message-content {
            background: linear-gradient(135deg, #95a5a6 0%, #7f8c8d 100%);
            color: white;
            text-align: center;
            font-size: 12px;
            padding: 8px 20px;
            border-radius: 20px;
            max-width: 80%;
        }

        .message.chat {
            justify-content: flex-start;
        }

        .message.own {
            justify-content: flex-end;
        }

        .message-bubble {
            max-width: 70%;
            padding: 12px 18px;
            border-radius: 20px;
            position: relative;
        }

        .message.chat .message-bubble {
            background: white;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
            border-bottom-left-radius: 5px;
        }

        .message.own .message-bubble {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-bottom-right-radius: 5px;
        }

        .message-sender {
            font-size: 12px;
            font-weight: 600;
            margin-bottom: 5px;
            display: flex;
            justify-content: space-between;
        }

        .message-time {
            font-size: 10px;
            opacity: 0.7;
        }

        .input-area {
            padding: 20px 30px;
            background: white;
            border-top: 1px solid #e0e0e0;
        }

        .input-wrapper {
            display: flex;
            gap: 15px;
            align-items: center;
        }

        .message-input {
            flex: 1;
        }

        .message-input input {
            width: 100%;
            padding: 15px 20px;
            border: 2px solid #e0e0e0;
            border-radius: 25px;
            font-size: 15px;
            background: #f8f9fa;
        }

        .message-input input:focus {
            outline: none;
            border-color: #667eea;
            background: white;
        }

        .send-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 25px;
            cursor: pointer;
            font-weight: 600;
        }

        .admin-badge {
            background: #e74c3c;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            margin-left: 10px;
        }

        @media (max-width: 768px) {
            .chat-container {
                width: 100%;
                height: 100vh;
                border-radius: 0;
            }
            .message-bubble {
                max-width: 85%;
            }
            .join-card {
                padding: 30px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Admin Login Screen -->
        <div id="loginScreen" class="login-screen">
            <div class="login-card">
                <h2>Admin Login</h2>
                <input type="text" id="adminUser" placeholder="Username">
                <input type="password" id="adminPass" placeholder="Password">
                <button onclick="adminLogin()">Login as Admin</button>
                <div id="loginError" class="error"></div>
                <hr style="margin: 20px 0;">
                <button onclick="showJoinScreen()" style="background: #555;">Continue as Guest</button>
            </div>
        </div>
        
        <!-- User Join Screen -->
        <div id="joinScreen" class="join-screen" style="display: none;">
            <div class="join-card">
                <div class="logo">💬</div>
                <h1>NeoChat</h1>
                <p class="subtitle">Modern LAN Chat Experience</p>
                
                <div class="input-group">
                    <label>Your Name</label>
                    <input type="text" id="nickname" placeholder="Enter your nickname...">
                </div>
                
                <button class="join-btn" onclick="joinAsUser()">Join Conversation</button>
            </div>
        </div>
        
        <!-- Chat Interface -->
        <div id="chat" class="chat-container" style="display:none">
            <div class="chat-header">
                <div class="header-left">
                    <i class="fas fa-comment-dots"></i>
                    <div class="header-info">
                        <h2>NeoChat <span id="userName"></span><span id="adminBadge"></span></h2>
                        <p>Real-time LAN Messenger</p>
                    </div>
                </div>
                <div class="status-badge">
                    <div class="status-dot"></div>
                    <span>Connected</span>
                    <span class="online-count" id="onlineCount">0 online</span>
                </div>
            </div>
            
            <div class="messages-area" id="messages"></div>
            
            <div class="input-area">
                <div class="input-wrapper">
                    <div class="message-input">
                        <input type="text" id="message" placeholder="Type your message..." 
                               onkeypress="if(event.key==='Enter') send()">
                    </div>
                    <button class="send-btn" onclick="send()">Send</button>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let isAdmin = false;
        let nickname = '';
        let lastCount = 0;
        
        async function adminLogin() {
            const user = document.getElementById('adminUser').value;
            const pass = document.getElementById('adminPass').value;
            
            const res = await fetch('/api/admin/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({username: user, password: pass})
            });
            const data = await res.json();
            
            if (data.success) {
                isAdmin = true;
                nickname = 'Admin';
                document.getElementById('loginScreen').style.display = 'none';
                document.getElementById('chat').style.display = 'flex';
                document.getElementById('userName').innerHTML = '(Admin)';
                document.getElementById('adminBadge').innerHTML = '<span class="admin-badge">ADMIN</span>';
                document.getElementById('message').focus();
                startChat();
            } else {
                document.getElementById('loginError').innerText = 'Wrong credentials!';
                document.getElementById('loginError').style.display = 'block';
            }
        }
        
        function showJoinScreen() {
            document.getElementById('loginScreen').style.display = 'none';
            document.getElementById('joinScreen').style.display = 'flex';
        }
        
        function joinAsUser() {
            nickname = document.getElementById('nickname').value.trim();
            if (!nickname) {
                alert('Please enter your name');
                return;
            }
            isAdmin = false;
            document.getElementById('joinScreen').style.display = 'none';
            document.getElementById('chat').style.display = 'flex';
            document.getElementById('userName').innerHTML = `(${nickname})`;
            document.getElementById('message').focus();
            startChat();
        }
        
        async function send() {
            const input = document.getElementById('message');
            const msg = input.value.trim();
            if (!msg) return;
            
            await fetch('/api/send', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    nickname: nickname,
                    message: msg,
                    isAdmin: isAdmin
                })
            });
            input.value = '';
        }
        
        async function poll() {
            try {
                const res = await fetch('/api/messages');
                const data = await res.json();
                if (data.messages && data.messages.length > lastCount) {
                    data.messages.slice(lastCount).forEach(display);
                    lastCount = data.messages.length;
                }
            } catch(e) {}
        }
        
        async function updateOnlineCount() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                document.getElementById('onlineCount').innerHTML = `${data.clients} online`;
            } catch(e) {}
        }
        
        function display(msg) {
            const container = document.getElementById('messages');
            const div = document.createElement('div');
            div.className = 'message ' + msg.type;
            
            if (msg.type === 'chat') {
                const isOwn = (msg.sender === nickname || (msg.sender === 'Admin' && isAdmin));
                if (isOwn) div.classList.add('own');
                else div.classList.add('chat');
                
                div.innerHTML = `
                    <div class="message-bubble">
                        <div class="message-sender">
                            <span>${escape(msg.sender)}</span>
                            <span class="message-time">${msg.time}</span>
                        </div>
                        <div class="message-text">${escape(msg.content)}</div>
                    </div>
                `;
            } else {
                div.innerHTML = `<div class="message-content">${escape(msg.content)}</div>`;
            }
            
            container.appendChild(div);
            container.scrollTop = container.scrollHeight;
        }
        
        function escape(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        function startChat() {
            poll();
            setInterval(poll, 1000);
            setInterval(updateOnlineCount, 3000);
        }
    </script>
</body>
</html>
'''

def run_web():
    os.makedirs('static', exist_ok=True)
    server = HTTPServer(('localhost', WEB_PORT), WebHandler)
    print(f'Web Server: http://localhost:{WEB_PORT}')
    server.serve_forever()

async def main():
    print('=' * 50)
    print('NeoChat - Modern LAN Chat System with Admin')
    print('=' * 50)
    print(f'Admin Login: {ADMIN_USERNAME} / {ADMIN_PASSWORD}')
    print(f'Web Interface: http://localhost:{WEB_PORT}')
    print('=' * 50)
    
    web_thread = threading.Thread(target=run_web, daemon=True)
    web_thread.start()
    
    await asyncio.sleep(1)
    await ChatServer().start()

if __name__ == '__main__':
    print('Starting NeoChat...')
    print('Open browser: http://localhost:8080')
    print('Press Ctrl+C to stop\n')
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('\nNeoChat stopped')