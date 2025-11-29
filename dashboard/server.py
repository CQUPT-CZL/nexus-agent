import http.server
import socketserver
import json
import os
import sys
import urllib.request
import urllib.error
from urllib.parse import urlparse, parse_qs
from datetime import datetime

# 配置端口
PORT = 3000
CONFIG_FILE = 'config.json'

class ConfigHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # 1. 获取配置接口
        if self.path == '/api/config':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self.wfile.write(f.read().encode('utf-8'))
            else:
                self.wfile.write(b'[]')
            return

        # 2. [关键补全] 代理接口: /api/proxy?url=http://...
        # 这是 FRP 穿透能看到数据的核心，没有它外网无法访问内网 Agent
        if self.path.startswith('/api/proxy'):
            try:
                query = parse_qs(urlparse(self.path).query)
                target_url = query.get('url', [None])[0]

                if not target_url:
                    raise ValueError("Missing 'url' parameter")

                # 设置 3 秒超时，防止内网不通导致卡死
                with urllib.request.urlopen(target_url, timeout=3) as response:
                    self.send_response(response.status)
                    # 转发 Content-Type (application/json)
                    content_type = response.getheader('Content-Type')
                    if content_type:
                        self.send_header('Content-type', content_type)
                    self.end_headers()
                    self.wfile.write(response.read())
            except Exception as e:
                # 代理失败返回 502 Bad Gateway
                self.send_response(502)
                self.end_headers()
                error_msg = {"error": str(e)}
                self.wfile.write(json.dumps(error_msg).encode('utf-8'))
            return
        
        # 其他静态文件请求 (html/css/js)
        super().do_GET()

    def do_POST(self):
        # 保存配置接口
        if self.path == '/api/config':
            # 1. 密码校验 (PIN 必须是 MMDD，例如 1124)
            pin = self.headers.get('X-PIN')
            today_pin = datetime.now().strftime('%m%d')
            
            if pin != today_pin:
                self.send_response(403)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"error":"invalid_pin"}')
                print(f"❌ Invalid PIN attempt: {pin} (Expected: {today_pin})")
                return

            # 2. 保存文件
            content_length = int(self.headers.get('Content-Length') or 0)
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"status": "success"}')
                print(f"✅ Configuration saved to {CONFIG_FILE}")
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"error":"server_error"}')
                print(f"❌ Error saving config: {e}")
            return

# 允许地址重用，防止重启时报端口占用
socketserver.TCPServer.allow_reuse_address = True

print(f"🚀 Nexus Gateway running at http://0.0.0.0:{PORT}")
print(f"📂 Configuration will be saved to: {os.path.abspath(CONFIG_FILE)}")

with socketserver.TCPServer(("", PORT), ConfigHandler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped.")
        httpd.server_close()