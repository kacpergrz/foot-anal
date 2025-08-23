from flask import Flask, jsonify, request, render_template, send_from_directory
from flask_cors import CORS
import os
import requests
from datetime import date, datetime
import json

# --- Konfiguracja Aplikacji Flask ---
# Vercel umieszcza pliki statyczne (jak index.html) w folderze /tmp
# Musimy mu wskazać poprawną ścieżkę
template_dir = os.path.abspath('./api')
app = Flask(__name__, template_folder=template_dir)
CORS(app)

# --- Endpoint do serwowania strony głównej (index.html) ---
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    # Ta funkcja będzie serwować Twój plik index.html
    return send_from_directory(app.template_folder, 'index.html')

# --- Logika z get_matches.py (bez zmian) ---
def _parse_footballdata_org_response(data: dict, league_name: str) -> list:
    matches = []
    today = date.today()
    for match in data.get('matches', []):
        utc_date_str = match.get('utcDate')
        if not utc_date_str: continue
        try:
            match_date = datetime.fromisoformat(utc_date_str.replace('Z', '+00:00')).date()
            if match_date == today:
                matches.append({
                    'league': league_name, 'date': utc_date_str,
                    'home_team': match.get('homeTeam', {}).get('name', 'N/A'),
                    'away_team': match.get('awayTeam', {}).get('name', 'N/A'),
                    'status': match.get('status', 'SCHEDULED'), 'source': 'Football-Data.org'
                })
        except (ValueError, TypeError): continue
    return matches

def _parse_openligadb_response(data: list, league_name: str) -> list:
    matches = []
    for match in data:
        if not isinstance(match, dict): continue
        match_date_str = match.get('matchDateTime', '')
        try:
            match_dt = datetime.fromisoformat(match_date_str.replace('Z', '+00:00'))
            if match_dt.date() == date.today():
                matches.append({
                    'league': league_name, 'date': match_date_str,
                    'home_team': match.get('team1', {}).get('teamName', ''),
                    'away_team': match.get('team2', {}).get('teamName', ''),
                    'status': 'Scheduled', 'source': 'OpenLigaDB'
                })
        except (ValueError, TypeError): continue
    return matches

@app.route('/api/get-matches', methods=['GET'])
def get_matches():
    all_matches = []
    session = requests.Session()
    session.headers.update({'User-Agent': 'Vercel-Function-Football-Scraper/1.0'})
    FOOTBALL_DATA_API_KEY = os.environ.get('FOOTBALL_DATA_API_KEY')
    if FOOTBALL_DATA_API_KEY:
        apis_with_key = {
            'Premier League': 'https://api.football-data.org/v4/competitions/PL/matches?status=SCHEDULED',
            'La Liga': 'https://api.football-data.org/v4/competitions/PD/matches?status=SCHEDULED',
        }
        headers = {'X-Auth-Token': FOOTBALL_DATA_API_KEY}
        for league_name, api_url in apis_with_key.items():
            try:
                response = session.get(api_url, headers=headers)
                response.raise_for_status()
                all_matches.extend(_parse_footballdata_org_response(response.json(), league_name))
            except Exception as e:
                print(f"Error fetching {league_name}: {e}")
    apis_no_key = { 'Bundesliga': f"https://api.openligadb.de/getmatchdata/bl1/{date.today().year}" }
    for league_name, api_url in apis_no_key.items():
        try:
            response = session.get(api_url)
            response.raise_for_status()
            all_matches.extend(_parse_openligadb_response(response.json(), league_name))
        except Exception as e:
            print(f"Error fetching {league_name}: {e}")
    return jsonify(all_matches)

# --- Logika z analyze.py (bez zmian) ---
def _call_gemini_api(prompt, api_key):
    api_url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2-5:generateContent?key={api_key}"
    payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
    response = requests.post(api_url, json=payload, headers={'Content-Type': 'application/json'})
    response.raise_for_status()
    data = response.json()
    if "candidates" in data and len(data["candidates"]) > 0:
        return data
    else:
        raise Exception(f"API nie zwróciło kandydatów. Powód: {data.get('promptFeedback', {}).get('blockReason', 'Nieznany')}")

@app.route('/api/analyze', methods=['POST'])
def analyze():
    body = request.get_json()
    if not body:
        return jsonify({'error': 'Brak danych w zapytaniu.'}), 400
    prompt = body.get('prompt')
    user_api_key = body.get('apiKey')
    if not prompt:
        return jsonify({"error": "Brak promptu w zapytaniu."}), 400
    if not user_api_key:
        return jsonify({"error": "Brak klucza API w zapytaniu. Upewnij się, że został dodany w ustawieniach."}), 400
    try:
        gemini_response = _call_gemini_api(prompt, user_api_key)
        return jsonify(gemini_response)
    except Exception as e:
        return jsonify({"error": f"Błąd po stronie serwera: {e}"}), 500