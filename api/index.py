from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import requests
from datetime import date, datetime
import json
try:
    import google.generativeai as genai
    from google.api_core import exceptions as google_exceptions
    from google.generativeai.types import generation_types, Tool
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

# Konfiguracja dla Vercel
template_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=template_dir)
CORS(app)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    return send_from_directory(app.template_folder, 'index.html')

def _parse_footballdata_org_response(data: dict, league_name: str) -> list:
    matches = []
    for match in data.get('matches', []):
        utc_date_str = match.get('utcDate')
        if not utc_date_str: continue
        try:
            matches.append({
                'league': league_name, 'date': utc_date_str,
                'home_team': match.get('homeTeam', {}).get('name', 'N/A'),
                'away_team': match.get('awayTeam', {}).get('name', 'N/A'),
                'status': match.get('status', 'SCHEDULED'), 'source': 'Football-Data.org'
            })
        except (ValueError, TypeError): continue
    return matches

@app.route('/api/get-matches', methods=['GET'])
def get_matches():
    all_matches = []
    session = requests.Session()
    session.headers.update({'User-Agent': 'Vercel-Function-Football-Scraper/1.0'})
    today_str = date.today().strftime('%Y-%m-%d')

    FOOTBALL_DATA_API_KEY = os.environ.get('FOOTBALL_DATA_API_KEY')
    if FOOTBALL_DATA_API_KEY:
        competitions = {
            'Premier League': 'PL',
            'La Liga': 'PD',
            'Serie A': 'SA',
            'Bundesliga': 'BL1',
            'Ligue 1': 'FL1',
            'Primeira Liga': 'PPL'
        }
        headers = {'X-Auth-Token': FOOTBALL_DATA_API_KEY}
        for league_name, code in competitions.items():
            api_url = f"https://api.football-data.org/v4/competitions/{code}/matches?dateFrom={today_str}&dateTo={today_str}"
            try:
                response = session.get(api_url, headers=headers)
                response.raise_for_status()
                all_matches.extend(_parse_footballdata_org_response(response.json(), league_name))
            except Exception as e:
                print(f"Error fetching {league_name}: {e}")
    return jsonify(all_matches)

def _call_perplexity_api(prompt, api_key):
    """Komunikuje się z API Perplexity."""
    url = "https://api.perplexity.ai/chat/completions"
    # Używamy modelu 'sonar-medium-online', który ma dostęp do internetu i jest odpowiedni do analiz.
    payload = {
        "model": "sonar",
        # Cały prompt jest teraz kontrolowany przez frontend.
        "messages": [{"role": "user", "content": prompt}]
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    data = response.json()
    text_response = data.get('choices', [{}])[0].get('message', {}).get('content', '')
    if not text_response:
        raise Exception("API Perplexity zwróciło pustą odpowiedź.")
    # Ujednolicamy format odpowiedzi, aby pasował do tego z Gemini
    return {"candidates": [{"content": {"parts": [{"text": text_response}]}}]}

def should_use_grounding(prompt):
    """Sprawdza czy prompt wymaga aktualnych danych"""
    keywords = ['dzisiaj', 'obecnie', 'najnowsze', 'aktualne', 'ostatnie mecze', 'dzisiejsze', 'teraz']
    return any(keyword in prompt.lower() for keyword in keywords)

def _call_gemini_api(prompt, api_key, use_grounding=False):
    """Komunikuje się z API Gemini z opcjonalnym groundingiem."""
    try:
        genai.configure(api_key=api_key)
        
        # Użyj grounding jeśli włączony przez użytkownika
        if use_grounding:
            print("Używam grounding search (włączony przez użytkownika)...")
            try:
                # Próbuj nową składnię (v0.3.0+)
                tools = [{"google_search_retrieval": {}}]
                model = genai.GenerativeModel('gemini-1.5-flash', tools=tools)
            except Exception as e:
                print(f"Błąd z nową składnią grounding: {e}")
                try:
                    # Próbuj starszą składnię
                    model = genai.GenerativeModel(
                        'gemini-2.0-flash',
                        tools=[genai.Tool.from_google_search_retrieval(genai.GoogleSearchRetrieval())]
                    )
                except Exception as e2:
                    print(f"Błąd ze starszą składnią grounding: {e2}")
                    # Fallback - rzuć błąd z sugestią aktualizacji
                    raise Exception("Grounding search nie jest dostępny. Zaktualizuj bibliotekę google-generativeai do wersji >=0.3.0 lub użyj Perplexity, które ma wbudowane wyszukiwanie internetowe.")
            
            # Optymalizacja promptu dla grounding
            optimized_prompt = f"""
            {prompt}
            
            INSTRUKCJE WYSZUKIWANIA:
            - Szukaj tylko najważniejszych, aktualnych informacji
            - Ogranicz się do ostatnich 24 godzin
            - Skup się na konkretnych faktach, nie opiniach
            - Bądź zwięzły w odpowiedzi
            """
        else:
            print("Używam standardowego modelu bez grounding...")
            model = genai.GenerativeModel('gemini-2.0-flash')
            optimized_prompt = prompt

        # Konfiguracja generowania z timeoutem
        generation_config = genai.GenerationConfig(
            max_output_tokens=2000,  # Ograniczenie długości
            temperature=0.1,         # Mniej kreatywności = szybsza odpowiedź
        )
        
        response = model.generate_content(
            optimized_prompt,
            generation_config=generation_config,
            request_options={"timeout": 45}  # 45 sekund timeout
        )

        if not response.candidates:
            reason = response.prompt_feedback.block_reason.name if response.prompt_feedback.block_reason else "Nieznany"
            raise generation_types.BlockedPromptException(f"API nie zwróciło odpowiedzi. Powód blokady: {reason}")

        return {"candidates": [{"content": {"parts": [{"text": response.text}]}}]}

    except Exception as e:
        if "timeout" in str(e).lower():
            raise Exception("Zapytanie przekroczyło limit czasu. Spróbuj ponownie lub użyj Perplexity.")
        raise e

@app.route('/api/analyze', methods=['POST'])
def analyze():
    body = request.get_json()
    if not body:
        return jsonify({'error': 'Brak danych w zapytaniu.'}), 400

    # Przywracamy oczekiwanie na gotowy 'prompt' z frontendu.
    prompt = body.get('prompt')
    model_choice = body.get('model')

    if not prompt or not model_choice:
        return jsonify({"error": "Brakujące dane w zapytaniu (wymagane: prompt, model)."}), 400

    try:
        print(f"Rozpoczynam analizę z modelem: {model_choice}")
        
        if model_choice == 'gemini':
            user_api_key = body.get('geminiApiKey')
            if not user_api_key:
                return jsonify({"error": "Brak klucza API dla Gemini. Upewnij się, że został dodany w ustawieniach."}), 400
            if not GOOGLE_AI_AVAILABLE:
                return jsonify({"error": "Biblioteki Google AI nie są dostępne. Sprawdź konfigurację serwera."}), 503
            
            # Sprawdź czy grounding jest włączony przez użytkownika
            use_grounding = body.get('useGrounding', False)
            if use_grounding:
                print("UWAGA: Grounding search włączony - może to potrwać do 60 sekund")
            
            response_data = _call_gemini_api(prompt, user_api_key, use_grounding)
            
        elif model_choice == 'perplexity':
            # Najpierw spróbuj pobrać klucz API z zmiennych środowiskowych Vercel
            perplexity_api_key = os.environ.get('PERPLEXITY_API_KEY')
            if not perplexity_api_key:
                # Jeśli klucz nie jest ustawiony w zmiennych środowiskowych, pobierz go z frontendu
                perplexity_api_key = body.get('perplexityApiKey')
                if not perplexity_api_key:
                    return jsonify({"error": "Brak klucza API dla Perplexity. Upewnij się, że został dodany w ustawieniach lub w zmiennych środowiskowych Vercel."}), 400
            response_data = _call_perplexity_api(prompt, perplexity_api_key)
        else:
            return jsonify({"error": "Nieprawidłowy model. Dostępne opcje: 'gemini', 'perplexity'."}), 400
            
        print("Analiza zakończona pomyślnie")
        return jsonify(response_data)

    except google_exceptions.PermissionDenied:
        return jsonify({"error": "Błąd API Gemini: Nieprawidłowy klucz API lub brak uprawnień."}), 403
    except google_exceptions.NotFound as e:
        return jsonify({"error": f"Błąd API Gemini: Nie znaleziono zasobu (np. modelu). Sprawdź poprawność nazwy. Szczegóły: {e}"}), 404
    except google_exceptions.InvalidArgument:
         return jsonify({"error": "Błąd API Gemini: Nieprawidłowy argument, sprawdź poprawność promptu."}), 400
    except requests.exceptions.Timeout:
        return jsonify({"error": "Zapytanie przekroczyło limit czasu. Spróbuj ponownie lub użyj Perplexity dla szybszej odpowiedzi."}), 408
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Błąd połączenia z API. Sprawdź połączenie internetowe i spróbuj ponownie."}), 503
    except requests.exceptions.HTTPError as e:
        if e.response.status_code in [401, 403]:
            return jsonify({"error": "Błąd API Perplexity: Nieprawidłowy klucz API lub brak uprawnień."}), 403
        return jsonify({"error": f"Błąd API Perplexity: {e.response.status_code} - {e.response.text}"}), e.response.status_code
    except generation_types.BlockedPromptException as e:
        return jsonify({"error": f"Twoje zapytanie zostało zablokowane przez API. {e}"}), 400
    except Exception as e:
        error_msg = str(e)
        if "timeout" in error_msg.lower():
            return jsonify({"error": "Zapytanie przekroczyło limit czasu. Spróbuj ponownie lub użyj Perplexity dla szybszej odpowiedzi."}), 408
        elif "failed to fetch" in error_msg.lower():
            return jsonify({"error": "Błąd połączenia. Sprawdź połączenie internetowe i spróbuj ponownie."}), 503
        print(f"Nieoczekiwany błąd: {error_msg}")
        return jsonify({"error": f"Wystąpił nieoczekiwany błąd serwera: {error_msg}"}), 500

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

if __name__ == '__main__':
    app.run(debug=True, port=5001)
