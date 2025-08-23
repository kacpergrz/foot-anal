from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import requests
from datetime import date, datetime

# Utwórz aplikację Flask
app = Flask(__name__)
CORS(app) # Włącz CORS, aby przeglądarka mogła wysyłać zapytania

# --- Logika z get_matches.py ---
def _parse_footballdata_org_response(data: dict, league_name: str) -> list:
    matches = []
    for match in data.get('matches', []):
        utc_date_str = match.get('utcDate')
        if not utc_date_str: continue
        # Filtrowanie po dacie odbywa się teraz w zapytaniu API, więc sprawdzanie daty tutaj nie jest już potrzebne.
        matches.append({
            'league': league_name, 'date': utc_date_str,
            'home_team': match.get('homeTeam', {}).get('name', 'N/A'),
            'away_team': match.get('awayTeam', {}).get('name', 'N/A'),
            'status': match.get('status', 'SCHEDULED'), 'source': 'Football-Data.org'
        })
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
    today_iso = date.today().isoformat()

    FOOTBALL_DATA_API_KEY = os.environ.get('FOOTBALL_DATA_API_KEY')
    if FOOTBALL_DATA_API_KEY:
        apis_with_key = {
            # Użyj filtrowania po dacie, aby pobrać wszystkie mecze z danego dnia, niezależnie od statusu.
            'Premier League': f'https://api.football-data.org/v4/competitions/PL/matches?dateFrom={today_iso}&dateTo={today_iso}',
            'La Liga': f'https://api.football-data.org/v4/competitions/PD/matches?dateFrom={today_iso}&dateTo={today_iso}',
        }
        headers = {'X-Auth-Token': FOOTBALL_DATA_API_KEY}
        for league_name, api_url in apis_with_key.items():
            try:
                response = session.get(api_url, headers=headers)
                response.raise_for_status()
                all_matches.extend(_parse_footballdata_org_response(response.json(), league_name))
            except Exception as e:
                print(f"Error fetching {league_name}: {e}")

    # Pobierz dane dla bieżącej kolejki zamiast całego sezonu - jest to bardziej wydajne.
    apis_no_key = { 'Bundesliga': "https://api.openligadb.de/getmatchdata/bl1" }
    for league_name, api_url in apis_no_key.items():
        try:
            response = session.get(api_url)
            response.raise_for_status()
            all_matches.extend(_parse_openligadb_response(response.json(), league_name))
        except Exception as e:
            print(f"Error fetching {league_name}: {e}")

    return jsonify(all_matches)

# --- Logika z analyze.py ---
def _call_gemini_api(prompt, api_key):
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
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
        # Lepszą praktyką jest logowanie szczegółów błędu na serwerze i zwracanie ogólnej wiadomości do klienta.
        print(f"Server error during Gemini API call: {e}")
        return jsonify({"error": "Wystąpił błąd po stronie serwera podczas przetwarzania zapytania."}), 500
