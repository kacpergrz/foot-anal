#!/usr/bin/env python3
"""
Alternative Football Scraper using web scraping
Scrapes from ESPN or other free sources
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, date
import json
from typing import List, Dict
import time
import re

class AlternativeFootballScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        # API keys for different services. Get your key from https://www.football-data.org
        self.api_keys = {
            'football-data.org': '8d42bbb4f8c14761a44d6262373c5a08'
        }
    
    def get_free_api_matches(self) -> List[Dict]:
        """Uses free football API"""
        matches = []
        
        # Free API endpoint (no auth required but limited)
        today_str = date.today().strftime('%Y-%m-%d')
        
        # --- 1. APIs that DO NOT require a key (like OpenLigaDB) ---
        apis_to_try = {
            'Bundesliga': f"https://api.openligadb.de/getmatchdata/bl1/{date.today().year}",
            '2. Bundesliga': f"https://api.openligadb.de/getmatchdata/bl2/{date.today().year}",
        }
        
        # --- 2. APIs that DO require a key (like football-data.org) ---
        # League codes for football-data.org: PL (Premier League), PD (La Liga), SA (Serie A), BL1 (Bundesliga)
        apis_with_key = {
            'Premier League': 'https://api.football-data.org/v4/competitions/PL/matches?status=SCHEDULED',
            'La Liga': 'https://api.football-data.org/v4/competitions/PD/matches?status=SCHEDULED',
        }
        
        # Process APIs with keys
        api_key = self.api_keys.get('football-data.org')
        if api_key and api_key != 'YOUR_API_KEY_HERE':
            headers = {'X-Auth-Token': api_key}
            for league_name, api_url in apis_with_key.items():
                try:
                    response = self.session.get(api_url, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    parsed_matches = self._parse_footballdata_org_response(data, league_name)
                    matches.extend(parsed_matches)
                    time.sleep(1) # Be nice to the API
                except Exception as e:
                    print(f"Błąd API (z kluczem) dla {league_name}: {e}")
        else:
            print("INFO: Klucz API dla football-data.org nie jest skonfigurowany. Pomijam to źródło.")

        # Process APIs without keys
        print("Sprawdzanie OpenLigaDB dla lig niemieckich...")
        for league_name, api_url in apis_to_try.items():
            try:
                response = self.session.get(api_url)
                if response.status_code == 200:
                    data = response.json()
                    # Parse the response based on API structure
                    parsed_matches = self._parse_free_api_response(data, league_name)
                    matches.extend(parsed_matches)
                    
                time.sleep(1)  # Rate limiting
                
            except Exception as e:
                print(f"Błąd API dla {league_name} ({api_url}): {e}")
        
        return matches
    
    def _parse_footballdata_org_response(self, data: Dict, league_name: str) -> List[Dict]:
        """Parse response from football-data.org API"""
        matches = []
        today = date.today()
        api_matches = data.get('matches', [])

        for match in api_matches:
            utc_date_str = match.get('utcDate')
            if not utc_date_str:
                continue
            
            try:
                # Check if the match date is today
                match_date = datetime.fromisoformat(utc_date_str.replace('Z', '+00:00')).date()
                if match_date == today:
                    matches.append({
                        'league': league_name,
                        'date': utc_date_str,
                        'home_team': match.get('homeTeam', {}).get('name', 'N/A'),
                        'away_team': match.get('awayTeam', {}).get('name', 'N/A'),
                        'status': match.get('status', 'SCHEDULED'),
                        'source': 'Football-Data.org'
                    })
            except (ValueError, TypeError):
                continue
        
        return matches
    
    def _parse_free_api_response(self, data, league_name: str) -> List[Dict]:
        """Parse response from free APIs (like OpenLigaDB)"""
        matches = []
        
        # Parse OpenLigaDB format
        for match in data:
            if isinstance(match, dict):
                match_date_str = match.get('matchDateTime', '')
                
                # Check if match is today
                try:
                    match_dt = datetime.fromisoformat(match_date_str.replace('Z', '+00:00'))
                    if match_dt.date() == date.today():
                        matches.append({
                            'league': league_name,
                            'date': match_date_str,
                            'home_team': match.get('team1', {}).get('teamName', ''),
                            'away_team': match.get('team2', {}).get('teamName', ''),
                            'status': 'Scheduled',
                            'source': 'OpenLigaDB'
                        })
                except (ValueError, TypeError):
                    continue
        
        return matches
    
    def get_all_matches(self) -> List[Dict]:
        """Fetches matches from all configured APIs."""
        print("Pobieranie meczów z darmowych API...")
        api_matches = self.get_free_api_matches()
        print(f"-> Znaleziono {len(api_matches)} meczów z API.")
        return api_matches
    
    def save_matches(self, matches: List[Dict], filename: str = None):
        """Save matches to JSON file"""
        if filename is None:
            filename = f"football_matches_{date.today().strftime('%Y%m%d')}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(matches, f, ensure_ascii=False, indent=2)
        
        print(f"Zapisano {len(matches)} meczów do {filename}")
    
    def print_matches(self, matches: List[Dict]):
        """Print matches to console"""
        if not matches:
            print("Nie znaleziono meczów na dzisiaj.")
            return
        
        print(f"\n=== MECZE PIŁKARSKIE - {date.today().strftime('%Y-%m-%d')} ===\n")
        
        # Sort matches by league
        matches.sort(key=lambda x: x.get('league', ''))
        
        current_league = None
        for match in matches:
            league = match.get('league', 'Unknown')
            if league != current_league:
                print(f"\n--- {league.upper()} ---")
                current_league = league

            home = match.get('home_team', 'Unknown')
            away = match.get('away_team', 'Unknown')
            
            # Format time nicely
            time_info = "N/A"
            date_str = match.get('date', '')
            try:
                dt_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                time_info = dt_obj.strftime('%H:%M')
            except (ValueError, TypeError):
                # If date string is invalid or not present, time_info remains "N/A"
                pass

            source = match.get('source', '')
            
            print(f"{time_info} | {home:<25} vs  {away:<25} ({source})")


def main():
    scraper = AlternativeFootballScraper()
    
    print("Alternative Football Scraper")
    print("=" * 40)
    
    matches = scraper.get_all_matches()
    scraper.print_matches(matches)
    scraper.save_matches(matches)


if __name__ == "__main__":
    main()