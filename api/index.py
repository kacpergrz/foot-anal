from flask import Flask, jsonify, request, render_template, send_from_directory
from flask_cors import CORS
import os
import requests
from datetime import date, datetime
import json
try:
    import google.generativeai as genai
    from google.api_core import exceptions as google_exceptions
    from google.generativeai.types import generation_types
    GOOGLE_AI_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Google AI libraries not available: {e}")
    GOOGLE_AI_AVAILABLE = False
    # Fallback classes for error handling
    class MockGoogleExceptions:
        PermissionDenied = Exception
        NotFound = Exception
        InvalidArgument = Exception
    google_exceptions = MockGoogleExceptions()
    
    class MockGenerationTypes:
        class BlockedPromptException(Exception):
            pass
    generation_types = MockGenerationTypes()
from dotenv import load_dotenv
load_dotenv()

# --- Konfiguracja Aplikacji Flask ---
# Konfiguracja dla Vercel
template_dir = os.path.dirname(os.path.abspath(__file__))
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
            'Serie A': 'https://api.football-data.org/v4/competitions/SA/matches?status=SCHEDULED',
            'Bundesliga': 'https://api.football-data.org/v4/competitions/BL1/matches?status=SCHEDULED',
        }
        headers = {'X-Auth-Token': FOOTBALL_DATA_API_KEY}
        for league_name, api_url in apis_with_key.items():
            try:
                response = session.get(api_url, headers=headers)
                response.raise_for_status()
                all_matches.extend(_parse_footballdata_org_response(response.json(), league_name))
            except Exception as e:
                print(f"Error fetching {league_name}: {e}")
    apis_no_key = {}
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
    """Komunikuje się z API Gemini używając oficjalnej biblioteki Google."""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash') # Poprawiona nazwa modelu na 'gemini-1.5-flash'
        response = model.generate_content(prompt)

        # Sprawdzamy, czy odpowiedź nie została zablokowana
        if not response.candidates:
            reason = response.prompt_feedback.block_reason.name if response.prompt_feedback.block_reason else "Nieznany"
            raise generation_types.BlockedPromptException(f"API nie zwróciło odpowiedzi. Powód blokady: {reason}")

        # Zwracamy odpowiedź w formacie, którego oczekuje frontend
        # (naśladując strukturę JSON z oryginalnego API REST)
        return {"candidates": [{"content": {"parts": [{"text": response.text}]}}]}

    except ValueError as e:
        # Biblioteka rzuca ValueError, gdy nie może wyodrębnić .text (np. zablokowany prompt)
        raise generation_types.BlockedPromptException(f"Odpowiedź zablokowana lub pusta. {e}")

@app.route('/api/analyze', methods=['POST'])
def analyze():
    # Sprawdź czy Google AI jest dostępne
    if not GOOGLE_AI_AVAILABLE:
        return jsonify({"error": "Google AI libraries are not available. Please check server configuration."}), 503
    
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
    except google_exceptions.PermissionDenied:
        return jsonify({"error": "Błąd API Gemini: Nieprawidłowy klucz API lub brak uprawnień."}), 403
    except google_exceptions.NotFound as e:
        return jsonify({"error": f"Błąd API Gemini: Nie znaleziono zasobu (np. modelu). Sprawdź poprawność nazwy. Szczegóły: {e}"}), 404
    except google_exceptions.InvalidArgument:
         return jsonify({"error": "Błąd API Gemini: Nieprawidłowy argument, sprawdź poprawność promptu."}), 400
    except generation_types.BlockedPromptException as e:
        return jsonify({"error": f"Twoje zapytanie zostało zablokowane przez API. {e}"}), 400
    except Exception as e:
        return jsonify({"error": f"Wystąpił nieoczekiwany błąd serwera: {e}"}), 500

# --- Dodaj handler dla błędów ---
@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

# --- Blok do uruchamiania serwera deweloperskiego ---
if __name__ == '__main__':
    # Uruchamia wbudowany serwer Flask, idealny do lokalnego dewelopmentu.
    # debug=True sprawi, że serwer będzie się automatycznie restartował po każdej zmianie w kodzie.
    app.run(debug=True, port=5001)