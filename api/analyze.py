import os
import json
import requests
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            body = json.loads(post_data)

            # Pobieramy prompt i klucz API z ciała zapytania od użytkownika
            prompt = body.get('prompt')
            user_api_key = body.get('apiKey')

            if not prompt:
                self._send_error_response(400, "Brak promptu w zapytaniu.")
                return
            
            if not user_api_key:
                self._send_error_response(400, "Brak klucza API w zapytaniu. Upewnij się, że został dodany w ustawieniach.")
                return

            gemini_response = self._call_gemini_api(prompt, user_api_key)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            self.wfile.write(json.dumps(gemini_response, ensure_ascii=False).encode('utf-8'))

        except Exception as e:
            self._send_error_response(500, f"Błąd po stronie serwera: {e}")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def _send_error_response(self, code, message):
        self.send_response(code)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps({'error': message}, ensure_ascii=False).encode('utf-8'))

    def _call_gemini_api(self, prompt, api_key):
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
        payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
        response = requests.post(api_url, json=payload, headers={'Content-Type': 'application/json'})
        response.raise_for_status()
        data = response.json()
        if "candidates" in data and len(data["candidates"]) > 0:
            return data
        else:
            raise Exception(f"API nie zwróciło kandydatów. Powód: {data.get('promptFeedback', {}).get('blockReason', 'Nieznany')}")