#!/usr/bin/env python3
import requests
import os
from dotenv import load_dotenv

load_dotenv()

def test_football_data_api():
    """Test football-data.org API z nowymi kodami lig"""
    
    api_key = os.environ.get('FOOTBALL_DATA_API_KEY')
    if not api_key:
        print("❌ Brak FOOTBALL_DATA_API_KEY w zmiennych środowiskowych")
        return
    
    # Nowe kody lig
    competitions = {
        'Premier League': 'PL',
        'La Liga': 'PD', 
        'Serie A': 'SA',
        'Bundesliga': 'BL1'
    }
    
    headers = {'X-Auth-Token': api_key}
    
    for league_name, code in competitions.items():
        url = f"https://api.football-data.org/v4/competitions/{code}/matches?status=SCHEDULED"
        print(f"\n🔍 Testowanie {league_name} ({code})...")
        print(f"URL: {url}")
        
        try:
            response = requests.get(url, headers=headers)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                matches_count = len(data.get('matches', []))
                print(f"✅ {league_name}: Znaleziono {matches_count} meczów")
                
                # Pokaż pierwszy mecz jako przykład
                if matches_count > 0:
                    first_match = data['matches'][0]
                    home_team = first_match.get('homeTeam', {}).get('name', 'N/A')
                    away_team = first_match.get('awayTeam', {}).get('name', 'N/A')
                    date = first_match.get('utcDate', 'N/A')
                    print(f"   Przykład: {home_team} vs {away_team} ({date})")
            else:
                print(f"❌ Błąd {response.status_code}: {response.text}")
                
        except Exception as e:
            print(f"❌ Wyjątek: {e}")

if __name__ == "__main__":
    test_football_data_api()