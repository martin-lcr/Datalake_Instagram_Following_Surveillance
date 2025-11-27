#!/usr/bin/env python3
"""
Script de test rapide pour vérifier l'extraction du nombre total depuis Instagram
"""
import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Configuration
COOKIES_FILE = "/opt/airflow/cookies/www.instagram.com_cookies.txt"
TEST_ACCOUNTS = ["le.corre_en.longueur", "mariadlaura"]

def load_cookies(driver, cookies_file):
    """Charge les cookies depuis un fichier Netscape"""
    driver.get("https://www.instagram.com")
    time.sleep(2)

    with open(cookies_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            parts = line.split('\t')
            if len(parts) >= 7:
                domain, _, path, secure, expiry, name, value = parts[:7]
                cookie = {
                    'name': name,
                    'value': value,
                    'path': path,
                    'domain': domain,
                    'secure': secure == 'TRUE',
                }
                if expiry != '0':
                    cookie['expiry'] = int(expiry)
                driver.add_cookie(cookie)

    driver.refresh()
    time.sleep(2)

def extract_instagram_reported_total(driver, username):
    """Extrait le nombre total de followings depuis la page Instagram"""
    try:
        # Méthode 1: XPath direct
        try:
            following_link = driver.find_element(
                By.XPATH,
                f"//a[contains(@href, '/{username}/following/')]"
            )
            number_span = following_link.find_element(By.TAG_NAME, "span")
            total_text = number_span.text.strip()
            total = int(total_text.replace(" ", "").replace(",", ""))
            print(f"✅ Méthode 1 réussie: {total} followings")
            return total
        except Exception as e:
            print(f"   ⚠️  Méthode 1 échouée: {e}")

        # Méthode 2: JavaScript
        try:
            total = driver.execute_script("""
                const followingLink = document.querySelector('a[href*="/following/"]');
                if (followingLink) {
                    const spans = followingLink.querySelectorAll('span');
                    for (let span of spans) {
                        const text = span.textContent.trim();
                        const cleaned = text.replace(/[\\s,]/g, '');
                        if (/^\\d+$/.test(cleaned)) {
                            return parseInt(cleaned, 10);
                        }
                    }
                }
                return null;
            """)

            if total:
                print(f"✅ Méthode 2 (JavaScript) réussie: {total} followings")
                return total
        except Exception as e:
            print(f"   ⚠️  Méthode 2 échouée: {e}")

        print("❌ Impossible d'extraire le nombre total")
        return None

    except Exception as e:
        print(f"❌ Erreur: {e}")
        return None

def test_extraction():
    """Test l'extraction pour tous les comptes"""
    print("="*80)
    print("TEST D'EXTRACTION DU NOMBRE TOTAL DEPUIS INSTAGRAM")
    print("="*80)

    # Configuration Chrome
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

    driver = None
    results = {}

    try:
        driver = webdriver.Chrome(options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        print("\n🍪 Chargement des cookies...")
        load_cookies(driver, COOKIES_FILE)
        print("✅ Cookies chargés\n")

        for account in TEST_ACCOUNTS:
            print(f"\n{'='*80}")
            print(f"TEST: @{account}")
            print(f"{'='*80}")

            print(f"📍 Navigation vers https://www.instagram.com/{account}/")
            driver.get(f"https://www.instagram.com/{account}/")
            time.sleep(3)

            print(f"📊 Extraction du nombre total...")
            total = extract_instagram_reported_total(driver, account)

            if total:
                results[account] = total
                print(f"✅ SUCCÈS: {account} a {total} followings sur Instagram")
            else:
                results[account] = None
                print(f"❌ ÉCHEC: Impossible d'extraire pour {account}")

            time.sleep(2)

    except Exception as e:
        print(f"❌ Erreur générale: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if driver:
            driver.quit()

    # Résumé
    print("\n" + "="*80)
    print("RÉSUMÉ DES RÉSULTATS")
    print("="*80)
    for account, total in results.items():
        if total:
            print(f"✅ {account}: {total} followings")
        else:
            print(f"❌ {account}: Échec de l'extraction")
    print("="*80)

    return results

if __name__ == '__main__':
    test_extraction()
