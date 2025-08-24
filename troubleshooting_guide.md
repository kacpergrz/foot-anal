# 🔧 VERCEL TROUBLESHOOTING GUIDE

## Krok po kroku rozwiązywanie błędu FUNCTION_INVOCATION_FAILED

### 1. 🧪 **TESTUJ PODSTAWOWĄ FUNKCJONALNOŚĆ**

Najpierw sprawdź czy podstawowe endpointy działają:

```bash
# Test 1: Minimal endpoint
curl https://your-app.vercel.app/api/minimal

# Test 2: Health check
curl https://your-app.vercel.app/api/health

# Test 3: Debug imports
curl https://your-app.vercel.app/api/debug
```

### 2. 📋 **SPRAWDŹ LOGI VERCEL**

1. Idź do Vercel Dashboard
2. Wybierz swój projekt
3. Kliknij "Functions" tab
4. Kliknij "View Function Logs"
5. Sprawdź błędy w czasie rzeczywistym

### 3. 🔍 **TYPOWE PRZYCZYNY BŁĘDÓW**

#### A) **Import Errors**
```python
# Sprawdź czy wszystkie biblioteki są w requirements.txt
pip freeze > requirements_current.txt
# Porównaj z requirements.txt
```

#### B) **Timeout Issues**
- Vercel Hobby: 10s limit
- Vercel Pro: 60s limit
- Sprawdź czy API calls nie trwają za długo

#### C) **Memory Issues**
- Vercel Hobby: 1024MB limit
- Sprawdź czy nie ładujesz za dużo danych

#### D) **Environment Variables**
```bash
# W Vercel Dashboard → Settings → Environment Variables
FOOTBALL_DATA_API_KEY=your_key_here
```

### 4. 🛠️ **KROKI NAPRAWCZE**

#### Krok 1: Test minimalnej aplikacji
```bash
# Zmień vercel.json na minimal.py
{
  "builds": [{"src": "api/minimal.py", "use": "@vercel/python"}],
  "routes": [{"src": "/(.*)", "dest": "/api/minimal.py"}]
}
```

#### Krok 2: Stopniowo dodawaj funkcjonalność
1. Minimal → Health → Debug → Full app
2. Po każdym kroku testuj deployment

#### Krok 3: Sprawdź requirements.txt
```txt
flask==2.3.3
requests==2.31.0
python-dotenv==1.0.0
flask-cors==4.0.0
google-generativeai==0.3.2
google-api-core==2.14.0
```

### 5. 📊 **MONITORING I DEBUGGING**

#### A) Dodaj logging do kodu:
```python
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/api/test')
def test():
    logger.info("Test endpoint called")
    try:
        # your code
        logger.info("Success")
        return jsonify({'status': 'ok'})
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({'error': str(e)}), 500
```

#### B) Sprawdź metryki w Vercel:
- Response time
- Error rate
- Memory usage

### 6. 🚨 **EMERGENCY FIXES**

Jeśli nic nie działa:

1. **Rollback do working version**
2. **Deploy minimal app**
3. **Sprawdź Vercel status page**
4. **Kontakt z Vercel support**

### 7. 📞 **GDZIE SZUKAĆ POMOCY**

- Vercel Discord: https://discord.gg/vercel
- Vercel Docs: https://vercel.com/docs
- GitHub Issues: Sprawdź czy inni mają podobny problem

---

## 🌐 **GROUNDING SEARCH TROUBLESHOOTING**

### Problem: "module 'google.generativeai' has no attribute 'GoogleSearchRetrieval'"

#### Rozwiązanie 1: Aktualizuj bibliotekę
```bash
# Uruchom skrypt aktualizacji
python update_dependencies.py

# Lub ręcznie:
pip install --upgrade google-generativeai>=0.3.0
```

#### Rozwiązanie 2: Sprawdź wersję
```bash
pip show google-generativeai
# Powinna być >= 0.3.0
```

#### Rozwiązanie 3: Użyj Perplexity jako alternatywy
- Perplexity ma wbudowane wyszukiwanie internetowe
- Nie wymaga dodatkowych bibliotek
- Zawsze aktualne dane

#### Rozwiązanie 4: Wyłącz grounding
- Idź do Ustawienia → Wyłącz "Wyszukiwanie internetowe"
- Używaj szybkich analiz bez internetu

### Problem: Grounding search trwa za długo

#### Rozwiązania:
1. **Użyj Perplexity** - szybsze wyszukiwanie (5-15s)
2. **Wyłącz grounding** dla szybkich analiz
3. **Sprawdź połączenie** internetowe
4. **Poczekaj do 60 sekund** - to normalny czas dla grounding

### Problem: "Failed to fetch" z grounding

#### Przyczyny i rozwiązania:
- **Timeout** → Zwiększ cierpliwość lub użyj Perplexity
- **Błąd API** → Sprawdź klucz Gemini API
- **Połączenie** → Sprawdź internet

---

## 🎯 **QUICK CHECKLIST**

- [ ] Requirements.txt zawiera wszystkie zależności
- [ ] Vercel.json ma poprawną konfigurację
- [ ] Environment variables są ustawione
- [ ] Kod nie ma syntax errors
- [ ] Import statements działają lokalnie
- [ ] Funkcje nie przekraczają timeout limits
- [ ] Memory usage jest w limitach
- [ ] Logi Vercel pokazują konkretny błąd