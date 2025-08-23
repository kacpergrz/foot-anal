import os
import json
import requests
from http.server import BaseHTTPRequestHandler
from datetime import date, datetime

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

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        all_matches = []
        session = requests.Session()
        session.headers.update({'User-Agent': 'Vercel-Function-Football-Scraper/1.0'})

        # --- 1. football-data.org (z kluczem API) ---
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
        else:
            print("INFO: Zmienna FOOTBALL_DATA_API_KEY nie jest ustawiona.")

        # --- 2. OpenLigaDB (bez klucza) ---
        apis_no_key = {
            'Bundesliga': f"https://api.openligadb.de/getmatchdata/bl1/{date.today().year}",
        }
        for league_name, api_url in apis_no_key.items():
            try:
                response = session.get(api_url)
                response.raise_for_status()
                all_matches.extend(_parse_openligadb_response(response.json(), league_name))
            except Exception as e:
                print(f"Error fetching {league_name}: {e}")

        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(all_matches, ensure_ascii=False).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()