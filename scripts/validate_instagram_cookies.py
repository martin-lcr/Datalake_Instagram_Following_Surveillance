#!/usr/bin/env python3
"""
Script de validation et gestion des cookies Instagram
Vérifie la validité des cookies et alerte en cas d'expiration
"""

import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

def parse_netscape_cookies(cookie_file):
    """Parse le fichier de cookies au format Netscape"""
    cookies = []

    if not os.path.exists(cookie_file):
        print(f"❌ Fichier de cookies introuvable : {cookie_file}")
        return None

    with open(cookie_file, 'r') as f:
        for line in f:
            # Ignorer les commentaires et lignes vides
            if line.startswith('#') or not line.strip():
                continue

            parts = line.strip().split('\t')
            if len(parts) >= 7:
                cookie = {
                    'domain': parts[0],
                    'flag': parts[1],
                    'path': parts[2],
                    'secure': parts[3],
                    'expiration': int(parts[4]) if parts[4] != '0' else 0,
                    'name': parts[5],
                    'value': parts[6]
                }
                cookies.append(cookie)

    return cookies

def check_cookie_expiration(cookies):
    """Vérifie l'expiration des cookies critiques"""
    critical_cookies = ['sessionid', 'csrftoken', 'ds_user_id']
    now = int(time.time())

    results = {
        'valid': [],
        'expiring_soon': [],
        'expired': [],
        'missing': []
    }

    found_cookies = {name: False for name in critical_cookies}

    for cookie in cookies:
        if cookie['name'] in critical_cookies:
            found_cookies[cookie['name']] = True

            if cookie['expiration'] == 0:
                # Cookie de session (pas d'expiration)
                results['valid'].append(cookie)
            elif cookie['expiration'] < now:
                # Cookie expiré
                results['expired'].append(cookie)
            elif cookie['expiration'] < now + (7 * 24 * 3600):  # Expire dans moins de 7 jours
                results['expiring_soon'].append(cookie)
            else:
                results['valid'].append(cookie)

    # Vérifier les cookies manquants
    for name, found in found_cookies.items():
        if not found:
            results['missing'].append(name)

    return results

def format_expiration(timestamp):
    """Formatte la date d'expiration"""
    if timestamp == 0:
        return "Session (pas d'expiration)"

    dt = datetime.fromtimestamp(timestamp)
    now = datetime.now()
    delta = dt - now

    if delta.days < 0:
        return f"⚠️ EXPIRÉ le {dt.strftime('%Y-%m-%d %H:%M:%S')}"
    elif delta.days < 7:
        return f"⚠️ Expire dans {delta.days} jours ({dt.strftime('%Y-%m-%d')})"
    else:
        return f"✅ Expire le {dt.strftime('%Y-%m-%d')} (dans {delta.days} jours)"

def display_report(cookies, results):
    """Affiche un rapport détaillé"""
    print("\n" + "="*80)
    print("📊 RAPPORT DE VALIDATION DES COOKIES INSTAGRAM")
    print("="*80)

    # Statistiques globales
    print(f"\n📈 Statistiques :")
    print(f"  - Total cookies : {len(cookies)}")
    print(f"  - Cookies valides : {len(results['valid'])}")
    print(f"  - Cookies expirant bientôt : {len(results['expiring_soon'])}")
    print(f"  - Cookies expirés : {len(results['expired'])}")
    print(f"  - Cookies critiques manquants : {len(results['missing'])}")

    # Cookies critiques
    print(f"\n🔑 Cookies Critiques :")
    critical_cookies = ['sessionid', 'csrftoken', 'ds_user_id']

    all_cookies_dict = {c['name']: c for c in cookies}

    for name in critical_cookies:
        if name in all_cookies_dict:
            cookie = all_cookies_dict[name]
            exp_str = format_expiration(cookie['expiration'])
            print(f"  ✅ {name:15} : {exp_str}")
        else:
            print(f"  ❌ {name:15} : MANQUANT")

    # Cookies expirés
    if results['expired']:
        print(f"\n❌ Cookies Expirés ({len(results['expired'])}) :")
        for cookie in results['expired']:
            print(f"  - {cookie['name']:20} (expiré le {datetime.fromtimestamp(cookie['expiration']).strftime('%Y-%m-%d')})")

    # Cookies expirant bientôt
    if results['expiring_soon']:
        print(f"\n⚠️ Cookies Expirant Bientôt ({len(results['expiring_soon'])}) :")
        for cookie in results['expiring_soon']:
            days_left = (datetime.fromtimestamp(cookie['expiration']) - datetime.now()).days
            print(f"  - {cookie['name']:20} (expire dans {days_left} jours)")

    # Cookies manquants
    if results['missing']:
        print(f"\n❌ Cookies Critiques Manquants ({len(results['missing'])}) :")
        for name in results['missing']:
            print(f"  - {name}")

    # Verdict final
    print("\n" + "="*80)
    if results['expired'] or results['missing']:
        print("❌ VERDICT : Cookies INVALIDES - Mettre à jour requis")
        print("\n💡 Actions recommandées :")
        print("   1. Ouvrir Instagram dans Chrome")
        print("   2. Se connecter à votre compte")
        print("   3. Utiliser l'extension 'Get cookies.txt LOCALLY'")
        print("   4. Remplacer le fichier : docker/cookies/www.instagram.com_cookies.txt")
        return False
    elif results['expiring_soon']:
        print("⚠️ VERDICT : Cookies VALIDES mais expirent bientôt")
        print("\n💡 Prévoir un renouvellement dans les prochains jours")
        return True
    else:
        print("✅ VERDICT : Cookies VALIDES - Tout est OK !")
        return True

def main():
    """Fonction principale"""
    # Chemin du fichier de cookies (relatif, portable)
    script_dir = Path(__file__).parent
    cookie_file = script_dir.parent / "docker" / "cookies" / "www.instagram.com_cookies.txt"

    print(f"\n🍪 Validation des cookies Instagram")
    print(f"📁 Fichier : {cookie_file}\n")

    # Parser les cookies
    cookies = parse_netscape_cookies(cookie_file)

    if cookies is None:
        sys.exit(1)

    # Vérifier l'expiration
    results = check_cookie_expiration(cookies)

    # Afficher le rapport
    is_valid = display_report(cookies, results)

    print("\n" + "="*80 + "\n")

    # Code de sortie
    sys.exit(0 if is_valid else 1)

if __name__ == "__main__":
    main()
