import http.server
import socketserver
import json
import os
import sys

# 配置端口
PORT = 3000
CONFIG_FILE = 'config.json'

class ConfigHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # 如果请求是获取配置
        if self.path == '/api/config':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # 读取本地 JSON 文件，如果不存在则返回空数组
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self.wfile.write(f.read().encode('utf-8'))
            else:
                self.wfile.write(b'[]')
            return
        
        # 其他请求照常处理（返回 html/css/js）
        super().do_GET()

    def do_POST(self):
        # 如果请求是保存配置
        if self.path == '/api/config':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                # 验证 JSON 格式
                data = json.loads(post_data.decode('utf-8'))
                
                # 写入本地文件
                with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"status": "success"}')
                print(f"✅ Configuration saved to {CONFIG_FILE}")
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                print(f"❌ Error saving config: {e}")
            return

# 允许地址重用，防止重启时报端口占用
socketserver.TCPServer.allow_reuse_address = True

print(f"🚀 Nexus Dashboard running at http://0.0.0.0:{PORT}")
print(f"📂 Configuration will be saved to: {os.path.abspath(CONFIG_FILE)}")

with socketserver.TCPServer(("", PORT), ConfigHandler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped.")
        httpd.server_close()