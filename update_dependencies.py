#!/usr/bin/env python3
"""
Skrypt do aktualizacji zależności dla grounding search
"""

import subprocess
import sys

def run_command(command):
    """Uruchamia komendę i wyświetla wynik"""
    print(f"Wykonuję: {command}")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ Sukces: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Błąd: {e.stderr}")
        return False

def main():
    print("🔄 Aktualizacja zależności dla grounding search...")
    
    # Aktualizuj google-generativeai
    if run_command("pip install --upgrade google-generativeai>=0.3.0"):
        print("✅ google-generativeai zaktualizowane")
    else:
        print("❌ Błąd aktualizacji google-generativeai")
        return False
    
    # Sprawdź wersję
    if run_command("pip show google-generativeai"):
        print("✅ Sprawdzenie wersji zakończone")
    
    print("\n🎉 Aktualizacja zakończona!")
    print("💡 Teraz możesz używać grounding search w Gemini")
    print("💡 Jeśli nadal są problemy, użyj Perplexity (ma wbudowane wyszukiwanie)")

if __name__ == "__main__":
    main()