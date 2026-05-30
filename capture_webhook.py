from http.server import BaseHTTPRequestHandler, HTTPServer
import json

class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        print("\n=== PAYLOAD RECEBIDO ===")
        print(json.dumps(json.loads(post_data), indent=2))
        print("========================\n")
        
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', 8001), WebhookHandler)
    print("Servidor aguardando webhook na porta 8001...")
    server.serve_forever()
