#!/usr/bin/env python3
"""
Pipeline complet intégré : Scraping Instagram Multi-Passes + ML + Stockage Multi-couches
Script fusionné combinant scrape_user_multipass_v2.py et script_scraping_to_spark.py
"""

import os
import sys
import re
import json
import time
import random
import glob
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

# Spark imports
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, FloatType
from pyspark.sql.functions import udf, col, lit

# Elasticsearch imports
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

# ML imports
import gender_guesser.detector as gender

# Quality tracking import
from scraping_quality_tracker import ScrapingQualityTracker

# =============================================================================
# CONFIGURATION
# =============================================================================

# Paramètres du script
if len(sys.argv) < 2:
    print("Usage: python3 instagram_scraping_ml_pipeline.py <username>")
    sys.exit(1)

account = sys.argv[1]
normalized_account = account.replace(".", "-").replace("_", "-")

# Configuration scraping
NUM_PASSES = 3  # 3 passes de scraping pour récupérer plus de followings et éviter la détection
COOKIES_FILE = "/opt/airflow/cookies/www.instagram.com_cookies.txt"
SCRAPING_OUTPUT_DIR = f"/tmp/scraping_output_{normalized_account}"

# Configuration stockage
DATA_BASE_PATH = "/sources/instagram_surveillance/data"
JARS_PATH = "/opt/airflow/jars/postgresql-42.2.27.jar,/opt/airflow/jars/elasticsearch-spark-30_2.12-8.11.0.jar"

# Configuration base de données
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")  # Nom du service Docker
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "airflow")
POSTGRES_USER = os.getenv("POSTGRES_USER", "airflow")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "airflow")

# Configuration pour le Quality Tracker
POSTGRES_CONFIG = {
    'host': POSTGRES_HOST,
    'port': POSTGRES_PORT,
    'database': POSTGRES_DB,
    'user': POSTGRES_USER,
    'password': POSTGRES_PASSWORD
}

# Configuration Elasticsearch
ELASTICSEARCH_HOST = os.getenv("ELASTICSEARCH_HOST", "elasticsearch")
ELASTICSEARCH_PORT = os.getenv("ELASTICSEARCH_PORT", "9200")

current_date = datetime.now().strftime("%Y%m%d")
current_time = datetime.now().strftime("%H%M")

# Vérification du fichier cookies
if not os.path.exists(COOKIES_FILE):
    print(f"❌ ERREUR CRITIQUE : Fichier cookies introuvable : {COOKIES_FILE}")
    print(f"   Veuillez copier votre fichier de cookies Instagram vers ce chemin.")
    sys.exit(1)

# =============================================================================
# PARTIE 1 : FONCTIONS DE SCRAPING (de scrape_user_multipass_v2.py)
# =============================================================================

def load_cookies(driver, cookies_file):
    """Charge les cookies depuis un fichier Netscape"""
    driver.get("https://www.instagram.com")
    time.sleep(2)

    with open(cookies_file, 'r') as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                parts = line.strip().split('\t')
                if len(parts) >= 7:
                    cookie = {
                        'name': parts[5],
                        'value': parts[6],
                        'domain': parts[0],
                        'path': parts[2],
                        'secure': parts[3] == 'TRUE',
                        'httpOnly': parts[4] == 'TRUE'
                    }
                    try:
                        driver.add_cookie(cookie)
                    except:
                        pass

    driver.get("https://www.instagram.com")
    time.sleep(3)


def extract_fullname_robust(link_element, username):
    """
    Extraction robuste du fullname - utilise plusieurs méthodes
    Ne dépend pas des classes CSS spécifiques
    """
    try:
        # Méthode 1: Chercher dans les parents jusqu'à trouver un texte qui contient le username
        current = link_element
        for _ in range(5):  # Remonter jusqu'à 5 niveaux
            try:
                parent = current.find_element(By.XPATH, './..')
                parent_text = parent.text.strip()

                # Si le texte du parent contient le username
                if username in parent_text:
                    # Le fullname est probablement le reste du texte
                    lines = parent_text.split('\n')

                    # Chercher une ligne qui n'est pas le username
                    for line in lines:
                        line_clean = line.strip()
                        # Ignorer les lignes vides, le username lui-même, et les boutons communs
                        if (line_clean and
                            line_clean != username and
                            line_clean.lower() not in ['follow', 'suivre', 'following', 'abonné', 'remove', 'supprimer'] and
                            not line_clean.startswith('@')):
                            return line_clean

                current = parent
            except:
                break

        # Méthode 2: Chercher tous les spans dans le grand-parent
        try:
            grandparent = link_element.find_element(By.XPATH, './../../..')
            spans = grandparent.find_elements(By.TAG_NAME, "span")

            for span in spans:
                span_text = span.text.strip()
                # Le fullname est un span non-vide qui n'est pas le username
                if (span_text and
                    span_text != username and
                    span_text.lower() not in ['follow', 'suivre', 'following', 'abonné'] and
                    not span_text.startswith('@')):
                    return span_text
        except:
            pass

        # Méthode 3: Utiliser le texte du lien lui-même s'il contient plus que le username
        link_text = link_element.text.strip()
        if link_text and link_text != username:
            # Parfois le texte du lien contient "username\nfullname"
            if '\n' in link_text:
                parts = link_text.split('\n')
                for part in parts:
                    if part.strip() and part.strip() != username:
                        return part.strip()

        # Méthode 4: Chercher via XPath les éléments contenant du texte
        try:
            # Chercher les divs/spans frères du lien
            parent = link_element.find_element(By.XPATH, './..')
            all_elements = parent.find_elements(By.XPATH, ".//*[text()]")

            for elem in all_elements:
                elem_text = elem.text.strip()
                if (elem_text and
                    elem_text != username and
                    len(elem_text) > 2 and
                    elem_text.lower() not in ['follow', 'suivre', 'following', 'abonné']):
                    return elem_text
        except:
            pass

        return None

    except Exception as e:
        return None


def extract_instagram_reported_total(driver, username):
    """
    Extrait le nombre total réel de followings depuis la page Instagram
    avant d'ouvrir la modal. Ce nombre est le "ground truth" visible sur Instagram.

    Args:
        driver: Instance Selenium WebDriver
        username: Nom du compte Instagram

    Returns:
        int: Nombre total de followings reporté par Instagram, ou None si extraction échoue
    """
    try:
        # Le nombre total est dans un lien avec href="/username/following/"
        # Format HTML: <a href="/username/following/"><span>357</span> suivi(e)s</a>

        # Méthode 1: Chercher via XPath le span contenant le nombre dans le lien "following"
        try:
            following_link = driver.find_element(
                By.XPATH,
                f"//a[contains(@href, '/{username}/following/')]"
            )
            # Le premier span dans ce lien contient le nombre
            number_span = following_link.find_element(By.TAG_NAME, "span")
            total_text = number_span.text.strip()

            # Nettoyer le texte (enlever les espaces, convertir en int)
            total = int(total_text.replace(" ", "").replace(",", ""))
            print(f"✅ Instagram reported total extrait: {total} followings")
            return total

        except Exception as e:
            print(f"   ⚠️  Méthode 1 échouée: {e}")

        # Méthode 2: Chercher via le texte "suivi(e)s" ou "following"
        try:
            # Chercher tous les éléments contenant "suivi(e)s" ou "following"
            following_elements = driver.find_elements(
                By.XPATH,
                "//a[contains(@href, '/following/')]//span[contains(text(), 'suivi') or contains(text(), 'following')]"
            )

            for elem in following_elements:
                # Le nombre est dans le span précédent ou parent
                parent = elem.find_element(By.XPATH, "./..")
                spans = parent.find_elements(By.TAG_NAME, "span")

                for span in spans:
                    text = span.text.strip()
                    # Vérifier si c'est un nombre
                    if text and text.replace(" ", "").replace(",", "").isdigit():
                        total = int(text.replace(" ", "").replace(",", ""))
                        print(f"✅ Instagram reported total extrait (méthode 2): {total} followings")
                        return total

        except Exception as e:
            print(f"   ⚠️  Méthode 2 échouée: {e}")

        # Méthode 3: JavaScript pour parser la page
        try:
            total = driver.execute_script("""
                // Chercher le lien "following"
                const followingLink = document.querySelector('a[href*="/following/"]');
                if (followingLink) {
                    // Extraire tous les spans
                    const spans = followingLink.querySelectorAll('span');
                    for (let span of spans) {
                        const text = span.textContent.trim();
                        // Si c'est un nombre (peut contenir des espaces ou virgules)
                        const cleaned = text.replace(/[\s,]/g, '');
                        if (/^\d+$/.test(cleaned)) {
                            return parseInt(cleaned, 10);
                        }
                    }
                }
                return null;
            """)

            if total:
                print(f"✅ Instagram reported total extrait (JavaScript): {total} followings")
                return total

        except Exception as e:
            print(f"   ⚠️  Méthode JavaScript échouée: {e}")

        print("⚠️  Impossible d'extraire le nombre total depuis Instagram")
        return None

    except Exception as e:
        print(f"❌ Erreur extraction instagram_reported_total: {e}")
        return None


def scrape_single_pass(username, pass_number, total_passes, cookies_file, scroll_delay=1.6, patience=10):
    """
    Effectue une passe de scraping avec extraction améliorée des fullnames
    """
    # Mode visuel contrôlé par variable d'environnement
    visual_mode = os.getenv('VISUAL_MODE', 'false').lower() == 'true'

    options = Options()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--remote-debugging-port=9222')

    # Mode headless uniquement si VISUAL_MODE n'est pas activé
    if not visual_mode:
        options.add_argument('--headless=new')
        options.add_argument('--disable-gpu')

    options.add_argument('--window-size=1920,1080')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    if visual_mode:
        print("🖥️  MODE VISUEL ACTIVÉ - Navigateur visible")

    driver = None

    try:
        print("\n" + "="*80)
        print(f"🔄 PASSE {pass_number}/{total_passes} - @{username}")
        print("="*80)

        driver = webdriver.Chrome(options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        print("🍪 Chargement cookies...")
        load_cookies(driver, cookies_file)
        print("✅ Connecté avec succès")

        print(f"🔍 Navigation vers @{username}...")
        driver.get(f"https://www.instagram.com/{username}/")
        time.sleep(3)

        # Extraire le nombre total reporté par Instagram (avant d'ouvrir la modal)
        instagram_reported_total = None
        if pass_number == 1:  # Extraire seulement à la première passe
            print("📊 Extraction du nombre total depuis Instagram...")
            instagram_reported_total = extract_instagram_reported_total(driver, username)

        print("🖱️  Clic sur 'following'...")
        following_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/following')]"))
        )
        following_button.click()
        time.sleep(3)

        print("✅ Modal ouverte")

        # Trouver la modal
        modal = driver.find_element(By.CSS_SELECTOR, "div[role='dialog']")

        # Trouver l'élément scrollable - DEBUG approfondi
        print("🔍 Recherche élément scrollable avec DEBUG...")
        scrollable = None

        # DEBUG: Afficher TOUS les divs avec overflow
        try:
            all_candidates = driver.execute_script("""
                const modal = arguments[0];
                const allDivs = modal.querySelectorAll('div');
                const results = [];

                for (let div of allDivs) {
                    const style = window.getComputedStyle(div);
                    const overflowY = style.overflowY;
                    const overflow = style.overflow;

                    // Afficher tout div avec overflow != visible
                    if ((overflowY !== 'visible' && overflowY !== '') ||
                        (overflow !== 'visible' && overflow !== '')) {
                        results.push({
                            scrollHeight: div.scrollHeight,
                            clientHeight: div.clientHeight,
                            overflowY: overflowY,
                            overflow: overflow,
                            links: div.querySelectorAll('a').length,
                            scrollable: div.scrollHeight > div.clientHeight
                        });
                    }
                }

                return results;
            """, modal)

            print(f"   📊 DEBUG: {len(all_candidates)} divs avec overflow trouvés:")
            for i, cand in enumerate(all_candidates[:10]):  # Afficher max 10 premiers
                print(f"      [{i}] scrollH={cand['scrollHeight']}, clientH={cand['clientHeight']}, " +
                      f"overflowY={cand['overflowY']}, liens={cand['links']}, scrollable={cand['scrollable']}")

        except Exception as e:
            print(f"   ⚠️  DEBUG échoué: {e}")

        # Méthode 1 : Chercher l'élément avec le plus de liens ET scrollable
        try:
            scrollable = driver.execute_script("""
                const modal = arguments[0];
                const allDivs = modal.querySelectorAll('div');
                let bestDiv = null;
                let maxLinks = 0;

                for (let div of allDivs) {
                    const style = window.getComputedStyle(div);
                    const overflowY = style.overflowY;

                    // Doit avoir overflowY auto/scroll ET être scrollable
                    if ((overflowY === 'auto' || overflowY === 'scroll') &&
                        div.scrollHeight > div.clientHeight + 10) {

                        const linkCount = div.querySelectorAll('a').length;
                        if (linkCount > maxLinks) {
                            maxLinks = linkCount;
                            bestDiv = div;
                        }
                    }
                }

                if (bestDiv) {
                    return {
                        element: bestDiv,
                        scrollHeight: bestDiv.scrollHeight,
                        clientHeight: bestDiv.clientHeight,
                        overflowY: window.getComputedStyle(bestDiv).overflowY,
                        links: maxLinks
                    };
                }
                return null;
            """, modal)

            if scrollable and scrollable.get('element'):
                print(f"   ✅ Scrollable trouvé: scrollH={scrollable['scrollHeight']}, " +
                      f"clientH={scrollable['clientHeight']}, liens={scrollable['links']}, overflowY={scrollable['overflowY']}")
                scrollable = scrollable['element']
        except Exception as e:
            print(f"   ⚠️  Méthode 1 échouée: {e}")
            scrollable = None

        # Méthode 2 : Fallback sur la modal
        if not scrollable:
            scrollable = modal
            print(f"   ⚠️  Utilisation de la modal comme fallback")

        # Scroll comme trackpad : grands mouvements répétés
        print(f"📜 Scroll TRACKPAD (100 scrolls max, délai={scroll_delay}s)...")
        last_count = 0
        no_change = 0
        max_scrolls = 100  # Nombre de scrolls à effectuer
        scroll_distance = 800  # Grand mouvement de 800px (comme swipe trackpad)

        for scroll_num in range(1, max_scrolls + 1):
            # Effectuer un GRAND scroll vers le bas avec scrollBy
            driver.execute_script("""
                arguments[0].scrollBy({
                    top: arguments[1],
                    behavior: 'smooth'
                });
            """, scrollable, scroll_distance)

            # Délai court pour le mouvement smooth
            time.sleep(0.8)

            # Attendre que Instagram charge le nouveau contenu
            time.sleep(scroll_delay)

            # Compter les nouveaux liens
            new_count = len(modal.find_elements(By.TAG_NAME, "a"))

            # Vérifier si de nouveaux éléments sont apparus
            if new_count == last_count:
                no_change += 1
                # Pour la première passe, on fait tous les scrolls sans arrêt anticipé
                if pass_number > 1 and no_change >= patience:
                    print(f"   ✅ Fin après {scroll_num} scrolls (pas de nouveau contenu)")
                    break
                # Pour la première passe, afficher le progrès même sans nouveaux liens
                elif pass_number == 1 and scroll_num % 10 == 0:
                    print(f"   📊 Scroll {scroll_num}/{max_scrolls}: {new_count} liens (=)")
            else:
                # Du nouveau contenu est apparu
                added = new_count - last_count
                if added > 0:
                    print(f"   📊 Scroll {scroll_num}/{max_scrolls}: {new_count} liens (+{added})")
                no_change = 0

            last_count = new_count

        # Message de fin de la boucle de scroll
        if pass_number == 1:
            print(f"   ✅ Passe 1 terminée: {max_scrolls} scrolls effectués, {new_count} liens trouvés")

        # Extraction AMÉLIORÉE avec méthodes robustes
        print("📊 Extraction AMÉLIORÉE avec méthodes robustes...")

        user_data = {}
        all_links = modal.find_elements(By.TAG_NAME, "a")

        extracted = 0
        with_fullname = 0

        for link in all_links:
            try:
                href = link.get_attribute('href')
                if not href or '/' not in href:
                    continue

                # Filtrer les URLs non-profil
                if any(x in href for x in ['/explore', '/reels', '/stories', '/p/', '/reel/', 'instagram.com/?', '/direct/', '/accounts/']):
                    continue

                # Extraire username
                parts = href.rstrip('/').split('/')
                profile_username = parts[-1]

                # Filtrer les mots-clés réservés
                if not profile_username or profile_username in ['explore', 'reels', 'stories', 'direct', 'accounts', 'following', 'followers', 'p', 'tv'] or '?' in profile_username:
                    continue

                # Extraire le fullname avec méthodes robustes
                fullname = extract_fullname_robust(link, profile_username)

                # Ajouter au dictionnaire
                if profile_username:
                    user_data[profile_username] = fullname
                    extracted += 1
                    if fullname:
                        with_fullname += 1

            except:
                continue

        print(f"   ✅ {extracted} profils extraits")
        print(f"   ✅ {with_fullname} avec fullname ({100*with_fullname/extracted if extracted > 0 else 0:.1f}%)")

        usernames = set(user_data.keys())
        fullnames_dict = user_data

        return usernames, fullnames_dict, instagram_reported_total

    except Exception as e:
        print(f"❌ Erreur passe {pass_number}: {e}")
        import traceback
        traceback.print_exc()
        return set(), {}, None

    finally:
        if driver:
            driver.quit()


def scrape_multipass(username, num_passes, output_dir, cookies_file):
    """
    Effectue le scraping multi-passes et retourne les données combinées
    """
    # Vérification des cookies
    if not os.path.exists(cookies_file):
        print(f"❌ Fichier cookies introuvable: {cookies_file}")
        return None

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    print("\n" + "="*80)
    print(f"🚀 SCRAPING MULTI-PASSES V2 (AMÉLIORÉ) : @{username}")
    print(f"   Nombre de passes: {num_passes}")
    print(f"   Répertoire de sortie: {output_dir}")
    print("="*80)

    all_usernames = set()
    all_fullnames_dict = {}
    pass_results = []
    instagram_reported_total = None  # Sera extrait à la première passe

    for pass_num in range(1, num_passes + 1):
        usernames, fullnames_dict, reported_total = scrape_single_pass(username, pass_num, num_passes, cookies_file)
        pass_results.append(len(usernames))
        all_usernames.update(usernames)

        # Capturer le nombre total reporté par Instagram (extrait à la première passe)
        if pass_num == 1 and reported_total is not None:
            instagram_reported_total = reported_total

        # Fusionner les dictionnaires (privilégier les fullnames non-None)
        for user, fname in fullnames_dict.items():
            if user not in all_fullnames_dict or (fname and not all_fullnames_dict.get(user)):
                all_fullnames_dict[user] = fname

        print(f"\n📊 Après passe {pass_num}:")
        print(f"   Cette passe: {len(usernames)} followings")
        print(f"   Total cumulé: {len(all_usernames)} followings uniques")

        # Compter les fullnames
        with_fullname = sum(1 for u in all_usernames if all_fullnames_dict.get(u))
        print(f"   Fullnames: {with_fullname}/{len(all_usernames)} ({100*with_fullname/len(all_usernames) if all_usernames else 0:.1f}%)")

        # Sauvegarder résultat de cette passe
        pass_data = {
            "account": username,
            "scraped_at": datetime.now().isoformat(),
            "pass_number": pass_num,
            "count": len(usernames),
            "data": [
                {
                    "username": u,
                    "fullname": fullnames_dict.get(u)
                } for u in sorted(usernames)
            ]
        }
        pass_file = f"{output_dir}/{username}_pass{pass_num}.json"
        with open(pass_file, 'w', encoding='utf-8') as f:
            json.dump(pass_data, f, indent=2, ensure_ascii=False)

        # Pause aléatoire entre les passes pour éviter la détection
        if pass_num < num_passes:
            wait_time = random.randint(60, 120)  # Entre 1 et 2 minutes
            print(f"\n⏳ Attente {wait_time}s avant la prochaine passe (délai aléatoire pour éviter détection)...")
            time.sleep(wait_time)

    # Résultats finaux
    final_list = sorted(list(all_usernames))
    fullnames_with_data = sum(1 for u in final_list if all_fullnames_dict.get(u))

    print("\n" + "="*80)
    print("📊 RÉSULTATS FINAUX COMBINÉS")
    print("="*80)
    print(f"Total usernames uniques: {len(all_usernames)}")
    print(f"Avec fullname: {fullnames_with_data} ({100*fullnames_with_data/len(all_usernames) if all_usernames else 0:.1f}%)")
    print(f"Sans fullname: {len(all_usernames) - fullnames_with_data}")
    print("="*80)

    # Créer fichier COMBINED avec timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    combined_file = f"{output_dir}/{username}_followings_MULTIPASS_V2_{timestamp}.json"

    combined_data = {
        "account": username,
        "scraped_at": datetime.now().isoformat(),
        "source": f"multipass scraping V2 ({num_passes} passes)",
        "version": "2.0 - improved fullname extraction",
        "total_passes": num_passes,
        "count": len(all_usernames),
        "fullnames_count": fullnames_with_data,
        "instagram_reported_total": instagram_reported_total,  # Nombre réel vu sur Instagram
        "data": [
            {
                "username": u,
                "fullname": all_fullnames_dict.get(u)
            } for u in final_list
        ]
    }

    with open(combined_file, 'w', encoding='utf-8') as f:
        json.dump(combined_data, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Fichier combiné créé: {combined_file}")
    print(f"✅ {len(all_usernames)} usernames uniques")
    print(f"✅ {fullnames_with_data} fullnames capturés")
    if instagram_reported_total:
        print(f"📊 Instagram reported total: {instagram_reported_total} followings")
    print()

    return combined_data, combined_file, instagram_reported_total


# =============================================================================
# PARTIE 2 : ML - Prédiction du genre
# =============================================================================

d = gender.Detector()

def guess_gender_best(full_name, username):
    """
    Prédit le genre en se basant sur 'full_name' et 'username'.
    """
    # Prédiction basée sur full_name
    if full_name and full_name.strip():
        first_name = full_name.split()[0].capitalize()
        pred_full = d.get_gender(first_name)
        if pred_full in ["male", "mostly_male"]:
            gender_full = "male"
            conf_full = 0.9 if pred_full == "male" else 0.8
        elif pred_full in ["female", "mostly_female"]:
            gender_full = "female"
            conf_full = 0.9 if pred_full == "female" else 0.8
        elif pred_full == "andy":
            # Prénom androgyne - essayer avec des variantes connues
            gender_full = "unknown"
            conf_full = 0.6
        else:
            gender_full = "unknown"
            conf_full = 0.5
    else:
        gender_full = "unknown"
        conf_full = 0.0

    # Prédiction basée sur username
    if username and username.strip():
        cleaned_username = re.sub(r'[^A-Za-z]', '', username)
        if cleaned_username:
            # Essayer d'extraire un prénom du username
            pred_user = d.get_gender(cleaned_username.capitalize())
            if pred_user in ["male", "mostly_male"]:
                gender_user = "male"
                conf_user = 0.7 if pred_user == "male" else 0.6
            elif pred_user in ["female", "mostly_female"]:
                gender_user = "female"
                conf_user = 0.7 if pred_user == "female" else 0.6
            elif pred_user == "andy":
                gender_user = "unknown"
                conf_user = 0.5
            else:
                gender_user = "unknown"
                conf_user = 0.4
        else:
            gender_user = "unknown"
            conf_user = 0.0
    else:
        gender_user = "unknown"
        conf_user = 0.0

    # On sélectionne la meilleure prédiction
    if conf_full >= conf_user:
        return (gender_full, float(conf_full))
    else:
        return (gender_user, float(conf_user))


# =============================================================================
# PARTIE 3 : PIPELINE PRINCIPAL
# =============================================================================

def main():
    # Chronomètre pour mesurer la durée du scraping
    start_time = time.time()

    print(f"🌀 [INFO] Lancement du pipeline pour le compte : {account} (normalisé : {normalized_account})")

    # =============================================================================
    # ÉTAPE 1 : SCRAPING MULTI-PASSES
    # =============================================================================

    print("\n" + "="*80)
    print("ÉTAPE 1 : SCRAPING MULTI-PASSES")
    print("="*80)

    scraped_data, json_file, instagram_reported_total = scrape_multipass(
        username=account,
        num_passes=NUM_PASSES,
        output_dir=SCRAPING_OUTPUT_DIR,
        cookies_file=COOKIES_FILE
    )

    if not scraped_data:
        print("❌ [ERREUR] Le scraping a échoué")
        sys.exit(1)

    # =============================================================================
    # ÉTAPE 2 : INITIALISATION SPARK
    # =============================================================================

    print("\n" + "="*80)
    print("ÉTAPE 2 : INITIALISATION SPARK")
    print("="*80)

    spark = SparkSession.builder \
        .appName("InstagramScrapingMLPipeline") \
        .config("spark.jars", JARS_PATH) \
        .getOrCreate()

    print("✅ Spark session créée")

    # Déclarer l'UDF pour Spark
    gender_udf = udf(
        guess_gender_best,
        StructType([
            StructField("predicted_gender", StringType(), True),
            StructField("confidence", FloatType(), True)
        ])
    )

    # =============================================================================
    # ÉTAPE 3 : STOCKAGE RAW
    # =============================================================================

    print("\n" + "="*80)
    print("ÉTAPE 3 : STOCKAGE RAW")
    print("="*80)

    raw_layer = os.path.join(DATA_BASE_PATH, "raw")
    raw_group = "scraping"
    raw_table_name = f"instagram_data_{normalized_account}"
    raw_filename = "raw.json"
    raw_output_path = os.path.join(raw_layer, raw_group, raw_table_name, current_date)
    os.makedirs(raw_output_path, exist_ok=True)
    raw_file_path = os.path.join(raw_output_path, raw_filename)

    with open(raw_file_path, "w", encoding="utf-8") as f:
        json.dump(scraped_data, f, ensure_ascii=False, indent=2)
    print(f"✅ [INFO] Données RAW enregistrées dans '{raw_file_path}'.")

    # =============================================================================
    # ÉTAPE 4 : TRANSFORMATION + ML
    # =============================================================================

    print("\n" + "="*80)
    print("ÉTAPE 4 : TRANSFORMATION + ML")
    print("="*80)

    items = scraped_data["data"]
    print(f"🔎 [INFO] Nombre d'éléments : {len(items)}")

    # Conversion en DataFrame Pandas
    df_pd = pd.DataFrame(items)

    if not df_pd.empty:
        # Renommer 'fullname' en 'full_name' si nécessaire
        if 'fullname' in df_pd.columns and 'full_name' not in df_pd.columns:
            df_pd = df_pd.rename(columns={'fullname': 'full_name'})

        # Garder uniquement les colonnes nécessaires
        columns_kept = ["username", "full_name"]
        df_pd = df_pd[columns_kept]

        # Ajouter les métadonnées du scraping
        df_pd['scraped_at'] = scraped_data.get('scraped_at', datetime.now().isoformat())
        df_pd['scraping_source'] = scraped_data.get('source', 'multipass scraping V2')
        df_pd['target_account'] = account

    # Schéma pour Spark
    schema = StructType([
        StructField("username", StringType(), True),
        StructField("full_name", StringType(), True),
        StructField("scraped_at", StringType(), True),
        StructField("scraping_source", StringType(), True),
        StructField("target_account", StringType(), True)
    ])
    df_spark = spark.createDataFrame(df_pd, schema=schema)

    row_count = df_spark.count()
    print(f"🔎 [INFO] Nombre de lignes dans df_spark : {row_count}")
    df_spark.show(5, truncate=False)

    # Application du modèle ML
    print("🤖 [INFO] Application du modèle ML pour prédiction du genre...")

    df_with_ml = df_spark.withColumn("gender_info", gender_udf(col("full_name"), col("username")))
    df_with_ml = df_with_ml \
        .withColumn("predicted_gender", col("gender_info.predicted_gender")) \
        .withColumn("confidence", col("gender_info.confidence")) \
        .drop("gender_info")

    print("🔎 [INFO] Exemples après application du modèle ML :")
    df_with_ml.show(5, truncate=False)

    # Statistiques sur les prédictions
    gender_counts = df_with_ml.groupBy("predicted_gender").count().collect()
    print("📊 [INFO] Répartition des genres prédits :")
    for row in gender_counts:
        print(f"   - {row['predicted_gender']}: {row['count']} ({100*row['count']/row_count:.1f}%)")

    # =============================================================================
    # ÉTAPE 5 : STOCKAGE FORMATTED
    # =============================================================================

    print("\n" + "="*80)
    print("ÉTAPE 5 : STOCKAGE FORMATTED")
    print("="*80)

    formatted_layer = os.path.join(DATA_BASE_PATH, "formatted")
    formatted_group = "scraping"
    formatted_table_name = f"instagram_data_{normalized_account}"
    formatted_filename = "formatted_parquet_with_ML.parquet"
    formatted_output_path = os.path.join(formatted_layer, formatted_group, formatted_table_name, current_date)
    os.makedirs(formatted_output_path, exist_ok=True)
    formatted_parquet_file = os.path.join(formatted_output_path, formatted_filename)

    df_with_ml.write.mode("append").parquet(formatted_parquet_file)
    print(f"✅ [INFO] Données formatées => '{formatted_parquet_file}'.")

    # =============================================================================
    # ÉTAPE 6 : STOCKAGE USAGE
    # =============================================================================

    print("\n" + "="*80)
    print("ÉTAPE 6 : STOCKAGE USAGE")
    print("="*80)

    usage_layer = os.path.join(DATA_BASE_PATH, "usage")
    usage_group = "scraping"
    usage_table_name = f"instagram_data_{normalized_account}"
    usage_filename = "formatted_parquet_with_ML.parquet"
    usage_output_path = os.path.join(usage_layer, usage_group, usage_table_name, current_date, current_time)
    os.makedirs(usage_output_path, exist_ok=True)
    usage_parquet_file = os.path.join(usage_output_path, usage_filename)

    df_with_ml.write.mode("overwrite").parquet(usage_parquet_file)
    print(f"✅ [INFO] Données usage final => '{usage_parquet_file}' ({df_with_ml.count()} lignes).")

    # =============================================================================
    # ÉTAPE 7 : AGRÉGATION QUOTIDIENNE (uniquement à 23h00)
    # =============================================================================

    print("\n" + "="*80)
    print("ÉTAPE 7 : AGRÉGATION QUOTIDIENNE")
    print("="*80)

    df_aggregated = None
    aggregated_parquet_file = None

    # Agrégation uniquement à 23h00
    if current_time == "2300":
        print("⏰ Heure d'agrégation (23:00) détectée - Début de l'agrégation des 24 scrapings horaires...")

        base_usage_path = os.path.join(usage_layer, usage_group, usage_table_name, current_date)

        if os.path.exists(base_usage_path):
            # Lister tous les répertoires horaires (0000, 0100, ..., 2300)
            hourly_dirs = [d for d in os.listdir(base_usage_path) if os.path.isdir(os.path.join(base_usage_path, d))]
            hourly_dirs_sorted = sorted(hourly_dirs)

            print(f"📂 Répertoires horaires trouvés : {len(hourly_dirs_sorted)}")
            print(f"   {hourly_dirs_sorted}")

            # Charger tous les fichiers horaires
            all_hourly_dfs = []
            for hour_dir in hourly_dirs_sorted:
                hourly_file = os.path.join(base_usage_path, hour_dir, usage_filename)
                if os.path.exists(hourly_file):
                    try:
                        df_hour = spark.read.parquet(hourly_file)
                        all_hourly_dfs.append(df_hour)
                        print(f"   ✅ Chargé : {hour_dir} ({df_hour.count()} lignes)")
                    except Exception as e:
                        print(f"   ❌ Erreur lecture {hour_dir}: {e}")

            if all_hourly_dfs:
                # Union de tous les DataFrames horaires
                from functools import reduce
                df_all_hours = reduce(lambda df1, df2: df1.unionByName(df2), all_hourly_dfs)
                print(f"📊 Total avant déduplication : {df_all_hours.count()} lignes")

                # Déduplication par username (garder la dernière occurrence)
                # On utilise dropDuplicates avec subset=["username"] pour garder une seule ligne par username
                df_aggregated = df_all_hours.dropDuplicates(["username"])
                print(f"✅ Total après déduplication : {df_aggregated.count()} lignes uniques")

                # Sauvegarder l'agrégation quotidienne
                aggregated_filename = "daily_aggregated.parquet"
                aggregated_output_path = os.path.join(usage_layer, usage_group, usage_table_name, current_date)
                aggregated_parquet_file = os.path.join(aggregated_output_path, aggregated_filename)

                df_aggregated.write.mode("overwrite").parquet(aggregated_parquet_file)
                print(f"💾 Agrégation quotidienne sauvegardée : '{aggregated_parquet_file}'")
            else:
                print("❌ Aucun fichier horaire trouvé pour l'agrégation")
        else:
            print(f"❌ Répertoire {base_usage_path} introuvable")
    else:
        print(f"⏭️  Heure actuelle : {current_time} - Agrégation uniquement à 23:00")

    # =============================================================================
    # ÉTAPE 8 : COMPARAISON QUOTIDIENNE J vs J-1 (uniquement à 23h00)
    # =============================================================================

    print("\n" + "="*80)
    print("ÉTAPE 8 : COMPARAISON QUOTIDIENNE")
    print("="*80)

    df_comparatif = None

    # Comparaison uniquement à 23h00
    if current_time == "2300" and df_aggregated is not None:
        print("⏰ Heure de comparaison (23:00) détectée - Comparaison J vs J-1...")

        # Calculer la date d'hier
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        yesterday_aggregated_path = os.path.join(usage_layer, usage_group, usage_table_name, yesterday, "daily_aggregated.parquet")

        print(f"🔍 Recherche de l'agrégation d'hier : {yesterday_aggregated_path}")

        if os.path.exists(yesterday_aggregated_path):
            try:
                df_yesterday = spark.read.parquet(yesterday_aggregated_path)
                print(f"✅ Données d'hier chargées : {df_yesterday.count()} lignes")

                # Sélection des colonnes pour comparaison
                df_today_sel = df_aggregated.select("username", "full_name", "predicted_gender", "confidence")
                df_yesterday_sel = df_yesterday.select("username", "full_name", "predicted_gender", "confidence")

                # Détection des ajouts (présents aujourd'hui, absents hier)
                df_added = (df_today_sel
                            .join(df_yesterday_sel, on=["username"], how="leftanti")
                            .withColumn("change", lit("added")))

                # Détection des suppressions (présents hier, absents aujourd'hui)
                df_deleted = (df_yesterday_sel
                              .join(df_today_sel, on=["username"], how="leftanti")
                              .withColumn("change", lit("deleted")))

                # Union des ajouts et suppressions
                df_comparatif = df_added.unionByName(df_deleted)

                print("🔎 Résultats de la comparaison quotidienne :")
                print(f"   ➕ Nouveaux followings : {df_added.count()}")
                print(f"   ➖ Followings supprimés : {df_deleted.count()}")
                df_comparatif.show(10, truncate=False)

                # Sauvegarde du comparatif
                comparatif_filename = "daily_comparatif.parquet"
                comparatif_output_path = os.path.join(usage_layer, usage_group, usage_table_name, current_date)
                comparatif_parquet_file = os.path.join(comparatif_output_path, comparatif_filename)

                df_comparatif.write.mode("overwrite").parquet(comparatif_parquet_file)
                print(f"💾 Comparatif quotidien sauvegardé : '{comparatif_parquet_file}' ({df_comparatif.count()} lignes)")

            except Exception as e:
                print(f"❌ Erreur lors de la comparaison : {e}")
                df_comparatif = None
        else:
            print(f"💡 Pas d'agrégation trouvée pour hier ({yesterday}) - Première exécution ?")
    else:
        if current_time != "2300":
            print(f"⏭️  Heure actuelle : {current_time} - Comparaison uniquement à 23:00")
        else:
            print("⏭️  Pas d'agrégation disponible pour la comparaison")

    # =============================================================================
    # ÉTAPE 9 : POSTGRESQL
    # =============================================================================

    print("\n" + "="*80)
    print("ÉTAPE 9 : POSTGRESQL")
    print("="*80)

    table_name_for_db = formatted_table_name.replace("-", "_")
    postgres_url = f"jdbc:postgresql://{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

    try:
        df_with_ml.write \
            .format("jdbc") \
            .option("url", postgres_url) \
            .option("dbtable", table_name_for_db) \
            .option("user", POSTGRES_USER) \
            .option("password", POSTGRES_PASSWORD) \
            .option("driver", "org.postgresql.Driver") \
            .mode("append") \
            .save()
        print(f"✅ [INFO] Données écrites dans PostgreSQL ({postgres_url}), table: {table_name_for_db}")
    except Exception as e:
        print(f"❌ [ERREUR] Écriture PostgreSQL : {e}")

    # Stocker également les données comparatives (avec colonne "change") dans PostgreSQL
    if df_comparatif is not None:
        comparatif_table_name = f"{table_name_for_db}_comparatif"
        try:
            df_comparatif.write \
                .format("jdbc") \
                .option("url", postgres_url) \
                .option("dbtable", comparatif_table_name) \
                .option("user", POSTGRES_USER) \
                .option("password", POSTGRES_PASSWORD) \
                .option("driver", "org.postgresql.Driver") \
                .mode("overwrite") \
                .save()
            print(f"✅ [INFO] Données comparatives écrites dans PostgreSQL, table: {comparatif_table_name}")
        except Exception as e:
            print(f"❌ [ERREUR] Écriture comparatif PostgreSQL : {e}")

    # =============================================================================
    # ÉTAPE 10 : ELASTICSEARCH
    # =============================================================================

    print("\n" + "="*80)
    print("ÉTAPE 10 : ELASTICSEARCH")
    print("="*80)

    try:
        # Connexion à Elasticsearch
        es = Elasticsearch([f"http://{ELASTICSEARCH_HOST}:{ELASTICSEARCH_PORT}"])

        if es.ping():
            print("✅ Connexion Elasticsearch établie")

            # Index des données principales
            index_name = f"instagram-followings-{normalized_account}"

            # Convertir le DataFrame en liste de documents
            docs = df_with_ml.toPandas().to_dict('records')

            # Préparer les actions bulk
            actions = []
            for doc in docs:
                action = {
                    "_index": index_name,
                    "_source": {
                        "username": doc.get("username"),
                        "full_name": doc.get("full_name"),
                        "predicted_gender": doc.get("predicted_gender"),
                        "confidence": float(doc.get("confidence")) if doc.get("confidence") else 0.5,
                        "scraped_at": doc.get("scraped_at"),
                        "scraping_source": doc.get("scraping_source"),
                        "target_account": doc.get("target_account"),
                        "timestamp": datetime.now().isoformat()
                    }
                }
                actions.append(action)

            # Indexer les documents
            if actions:
                success, failed = bulk(es, actions, raise_on_error=False)
                print(f"✅ [INFO] {success} documents indexés dans Elasticsearch (index: {index_name})")
                if failed:
                    print(f"⚠️  {len(failed)} documents ont échoué")

            # Index des données comparatives
            if df_comparatif is not None:
                comparatif_index_name = f"instagram-followings-{normalized_account}-comparatif"

                # Convertir le DataFrame comparatif
                comparatif_docs = df_comparatif.toPandas().to_dict('records')

                # Préparer les actions bulk pour comparatif
                comparatif_actions = []
                for doc in comparatif_docs:
                    action = {
                        "_index": comparatif_index_name,
                        "_source": {
                            "username": doc.get("username"),
                            "full_name": doc.get("full_name"),
                            "predicted_gender": doc.get("predicted_gender"),
                            "confidence": float(doc.get("confidence")) if doc.get("confidence") else 0.5,
                            "change": doc.get("change"),
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                    comparatif_actions.append(action)

                # Indexer les documents comparatifs
                if comparatif_actions:
                    success, failed = bulk(es, comparatif_actions, raise_on_error=False)
                    print(f"✅ [INFO] {success} documents comparatifs indexés (index: {comparatif_index_name})")
                    if failed:
                        print(f"⚠️  {len(failed)} documents ont échoué")

        else:
            print("❌ [ERREUR] Impossible de se connecter à Elasticsearch")

    except Exception as e:
        print(f"❌ [ERREUR] Indexation Elasticsearch : {e}")

    # =============================================================================
    # ÉTAPE 11 : ENREGISTREMENT QUALITÉ SCRAPING
    # =============================================================================

    print("\n" + "="*80)
    print("ÉTAPE 11 : ENREGISTREMENT QUALITÉ SCRAPING")
    print("="*80)

    try:
        tracker = ScrapingQualityTracker(POSTGRES_CONFIG)

        # Compter le nombre de followings scrapés
        scraping_count = df_with_ml.count()

        # Calculer la durée du scraping
        scraping_duration = int(time.time() - start_time)

        # Enregistrer avec métadonnées
        completeness_score, is_complete = tracker.record_scraping(
            target_account=normalized_account,
            scraping_date=datetime.now(),
            total_followings=scraping_count,
            scraping_duration_seconds=scraping_duration,
            instagram_reported_total=instagram_reported_total,  # Nombre réel vu sur Instagram
            notes=f"Multipass scraping V2 ({NUM_PASSES} passes) - {scraping_count} followings captured"
        )

        # Afficher le résultat
        status_icon = "✅" if is_complete else "⚠️"
        print(f"{status_icon} Score de qualité: {completeness_score:.1f}%")
        print(f"{status_icon} Scraping {'COMPLET' if is_complete else 'INCOMPLET'}")
        print(f"⏱️  Durée du scraping: {scraping_duration}s ({scraping_duration//60}m {scraping_duration%60}s)")

        # Si scraping incomplet, avertir
        if not is_complete:
            print(f"⚠️  ATTENTION: Ce scraping est incomplet ({completeness_score:.1f}%)")
            print(f"   Les comparaisons utiliseront le dernier scraping complet comme référence")

        # Obtenir les VRAIS nouveaux followings (si scraping complet)
        if is_complete:
            truly_new = tracker.get_truly_new_followings(
                target_account=normalized_account,
                scraping_date=datetime.now()
            )

            print(f"🆕 Vrais nouveaux followings détectés: {len(truly_new)}")
            if truly_new:
                print(f"   Premiers nouveaux:")
                for following in truly_new[:5]:
                    print(f"     - @{following['username']} ({following['full_name'] or 'N/A'})")
        else:
            # Afficher le dernier scraping complet pour référence
            last_complete = tracker.get_last_complete_scraping(normalized_account)
            if last_complete:
                print(f"📊 Dernier scraping complet: {last_complete['scraping_date']}")
                print(f"   Total: {last_complete['total_followings']} followings")
                print(f"   Score: {last_complete['completeness_score']:.1f}%")

        print("✅ Qualité du scraping enregistrée avec succès")

    except Exception as e:
        print(f"⚠️  Erreur enregistrement qualité (non-bloquant): {e}")
        import traceback
        traceback.print_exc()
        # Ne pas bloquer le pipeline si le tracking échoue

    # =============================================================================
    # FIN
    # =============================================================================

    spark.stop()

    print("\n" + "="*80)
    print("🎉 PIPELINE TERMINÉ AVEC SUCCÈS")
    print("="*80)
    print(f"✅ {row_count} followings scrapés")
    print(f"✅ Stockés dans : {usage_parquet_file}")
    print(f"✅ Base PostgreSQL : {table_name_for_db}")
    print(f"🔚 [INFO] Fin du script pour {account} (normalisé: {normalized_account}).")


if __name__ == '__main__':
    main()
