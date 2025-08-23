import json
from dotenv import load_dotenv

# Załaduj zmienne z pliku .env na samym początku
load_dotenv() 
print("--- Test lokalny aplikacji Flask ---")

# Importujemy aplikację 'app' z Twojego pliku api/index.py
try:
    from api.index import app
    print("✅ Aplikacja Flask została poprawnie zaimportowana.")
except ImportError as e:
    print(f"❌ BŁĄD: Nie udało się zaimportować aplikacji. Sprawdź, czy plik api/index.py istnieje. Błąd: {e}")
    exit()

# Używamy wbudowanego klienta testowego Flask
with app.test_client() as client:
    print("\n--- Uruchamiam test dla endpointu /api/get-matches ---")
    
    # Wysyłamy zapytanie GET do Twojego API
    response = client.get('/api/get-matches')
    
    print(f"Status odpowiedzi: {response.status_code}")
    
    # Sprawdzamy, czy odpowiedź jest poprawna
    if response.status_code == 200:
        print("✅ Otrzymano poprawną odpowiedź od serwera.")
        # Dekodujemy odpowiedź JSON
        data = response.get_json()
        print(f"Znaleziono {len(data)} meczów.")
        
        # Opcjonalnie: wyświetl kilka pierwszych meczów
        if data:
            print("\nPrzykładowe dane (pierwsze 3 mecze):")
            for match in data[:3]:
                print(f" - {match['home_team']} vs {match['away_team']} ({match['league']})")
    else:
        print("❌ BŁĄD: Serwer zwrócił błąd. Treść odpowiedzi:")
        # Próbujemy odczytać odpowiedź jako tekst w razie błędu
        try:
            print(response.get_data(as_text=True))
        except Exception as e:
            print(f"Nie można było odczytać odpowiedzi: {e}")

print("\n--- Koniec testu ---")