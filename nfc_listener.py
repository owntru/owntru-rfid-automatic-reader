from http.server import BaseHTTPRequestHandler, HTTPServer
import pyautogui
import time
import json

PORT = 5005


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8', errors='ignore')

        # Accept either raw text or JSON like {"id": "04A1B2C3"}
        card_id = body.strip()
        try:
            data = json.loads(body)
            if isinstance(data, dict) and 'id' in data:
                card_id = str(data['id']).strip()
        except (json.JSONDecodeError, ValueError):
            pass

        print(f"[{time.strftime('%H:%M:%S')}] Received card ID: {card_id}")

        if card_id:
            time.sleep(0.2)  # tiny delay so focus settles
            pyautogui.write(card_id, interval=0.01)

        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'OK')

    def log_message(self, format, *args):
        pass  # keep console clean


if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', PORT), Handler)
    print(f"Listening for NFC scans on port {PORT}... (Ctrl+C to stop)")
    print("Click into the app where you want the ID typed, then scan your card.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")