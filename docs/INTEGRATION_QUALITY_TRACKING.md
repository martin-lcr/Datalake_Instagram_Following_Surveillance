# Guide d'intégration du Quality Tracking

## 🎯 Objectif

Améliorer la détection des nouveaux followings en tenant compte de la qualité/complétude des scrapings pour éviter les faux positifs lors de scrapings incomplets.

**Nouveauté ✨** : Le système extrait automatiquement le **nombre total réel de followings** directement depuis Instagram (valeur affichée sur le profil) et l'utilise comme référence pour calculer des scores de complétude précis.

## 📋 Étapes d'installation

### 1. Lancer le script d'installation automatique

```bash
# Depuis la racine du projet
cd scripts
./install_quality_tracking.sh
```

**Ce script va automatiquement** :
- ✅ Créer les tables et fonctions SQL dans PostgreSQL
- ✅ Migrer les données historiques existantes
- ✅ Recalculer les scores de complétude
- ✅ Tester le système avec le tracker Python

**Alternative manuelle** (si vous préférez) :
```bash
# Se connecter au container PostgreSQL
docker exec -i instagram-postgres psql -U airflow -d airflow < sql/create_scraping_metadata.sql
docker exec -i instagram-postgres psql -U airflow -d airflow < sql/detect_truly_new_followings.sql
```

### 2. Modifier le pipeline Python

Dans `scripts/instagram_scraping_ml_pipeline.py`, ajouter après l'import des modules :

```python
from scraping_quality_tracker import ScrapingQualityTracker
from datetime import datetime
import time

# Configuration PostgreSQL
POSTGRES_CONFIG = {
    'host': 'postgres',
    'port': '5432',
    'database': 'airflow',
    'user': 'airflow',
    'password': 'airflow'
}
```

### 3. Ajouter le tracking après chaque scraping

Localiser la section où les données sont écrites dans PostgreSQL (environ ligne 630), et ajouter APRÈS :

```python
# ============================================================================
# ÉTAPE 11 : ENREGISTRER LA QUALITÉ DU SCRAPING
# ============================================================================

try:
    print("=" * 80)
    print("ÉTAPE 11 : ENREGISTREMENT QUALITÉ SCRAPING")
    print("=" * 80)

    tracker = ScrapingQualityTracker(POSTGRES_CONFIG)

    # Compter le nombre de followings scrapés
    scraping_count = df_spark.count()

    # Enregistrer avec métadonnées (inclut instagram_reported_total automatiquement)
    completeness_score, is_complete = tracker.record_scraping(
        target_account=normalized_username,
        scraping_date=datetime.now(),
        total_followings=scraping_count,
        scraping_duration_seconds=int(time.time() - start_time) if 'start_time' in locals() else None,
        instagram_reported_total=instagram_reported_total,  # ✨ NOUVEAU: Valeur extraite depuis Instagram
        notes=f"Multipass scraping V2 - {scraping_count} followings captured"
    )

    # Afficher le résultat
    status_icon = "✅" if is_complete else "⚠️"
    print(f"{status_icon} Score de qualité: {completeness_score:.1f}%")
    print(f"{status_icon} Scraping {'COMPLET' if is_complete else 'INCOMPLET'}")

    # Si scraping incomplet, avertir
    if not is_complete:
        print(f"⚠️  ATTENTION: Ce scraping est incomplet ({completeness_score:.1f}%)")
        print(f"   Les comparaisons utiliseront le dernier scraping complet comme référence")

    # Obtenir les VRAIS nouveaux followings (si scraping complet)
    if is_complete:
        truly_new = tracker.get_truly_new_followings(
            target_account=normalized_username,
            scraping_date=datetime.now()
        )

        print(f"🆕 Vrais nouveaux followings détectés: {len(truly_new)}")
        if truly_new:
            print(f"   Premiers nouveaux:")
            for following in truly_new[:5]:
                print(f"     - @{following['username']} ({following['full_name'] or 'N/A'})")

    print("✅ Qualité du scraping enregistrée avec succès")

except Exception as e:
    print(f"⚠️  Erreur enregistrement qualité (non-bloquant): {e}")
    # Ne pas bloquer le pipeline si le tracking échoue

print("=" * 80)
```

### 4. Ajouter un chrono au début du script

Au tout début de la fonction `main()` ou du script, ajouter :

```python
start_time = time.time()
```

## 🔧 Modifications du Dashboard

### Nouvelle API pour les vrais nouveaux

Dans `dashboard/app.py`, ajouter :

```python
@app.route('/api/account/<account_name>/truly-new')
def api_truly_new_followings(account_name):
    """API: Vrais nouveaux followings (robuste aux scrapings incomplets)"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Paramètre de date optionnel
        date_filter = request.args.get('date', None)

        if date_filter:
            query = """
            SELECT * FROM get_new_followings_for_date(%s, %s)
            """
            cursor.execute(query, (account_name, date_filter))
        else:
            # Dernière date complète
            query = """
            SELECT * FROM get_new_followings_for_date(
                %s,
                (SELECT MAX(scraping_date) FROM scraping_metadata
                 WHERE target_account = %s AND is_complete = TRUE)
            )
            """
            cursor.execute(query, (account_name, account_name))

        results = []
        for row in cursor.fetchall():
            results.append({
                'username': row[0],
                'full_name': row[1],
                'predicted_gender': row[2],
                'is_truly_new': row[3],
                'confidence_score': float(row[4]) if row[4] else 0.0
            })

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'account': account_name,
            'truly_new': results,
            'count': len(results)
        })

    except Exception as e:
        logger.error(f"Erreur API truly_new: {e}")
        if conn:
            conn.close()
        return jsonify({'error': str(e)}), 500


@app.route('/api/scraping-quality/<account_name>')
def api_scraping_quality(account_name):
    """API: Qualité des scrapings pour un compte"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = """
        SELECT
            scraping_date,
            total_followings,
            completeness_score,
            is_complete,
            scraping_duration_seconds,
            notes
        FROM scraping_metadata
        WHERE target_account = %s
        ORDER BY scraping_date DESC
        LIMIT 30
        """

        cursor.execute(query, (account_name,))
        quality_history = cursor.fetchall()

        # Formater les dates
        for row in quality_history:
            if row['scraping_date']:
                row['scraping_date'] = row['scraping_date'].strftime('%Y-%m-%d')

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'account': account_name,
            'quality_history': quality_history
        })

    except Exception as e:
        logger.error(f"Erreur API quality: {e}")
        if conn:
            conn.close()
        return jsonify({'error': str(e)}), 500
```

## 📊 Exemple d'utilisation

### Dans le terminal

```python
from scraping_quality_tracker import ScrapingQualityTracker
from datetime import datetime

postgres_config = {
    'host': 'postgres',
    'port': '5432',
    'database': 'airflow',
    'user': 'airflow',
    'password': 'airflow'
}

tracker = ScrapingQualityTracker(postgres_config)

# Comparer intelligemment 22/11 vs 24/11
comparison = tracker.compare_scrapings(
    target_account='mariadlaura',
    date1=datetime(2025, 11, 22),
    date2=datetime(2025, 11, 24)
)

print(f"Ajoutés: {comparison['added_count']}")
print(f"Confiance: {comparison['confidence']}")

# Obtenir le dernier scraping complet
last_complete = tracker.get_last_complete_scraping('mariadlaura')
print(f"Dernier scraping complet: {last_complete['scraping_date']}")
print(f"Total: {last_complete['total_followings']} followings")
```

## 🎨 Avantages de cette approche

### ✅ Résout le problème des scrapings incomplets

- **Avant**: 663 → 505 → 651 = Détecte 146 "ajouts" fantômes
- **Après**: Compare seulement les scrapings "complets" (score ≥ 90%)
  - 663 (complet) → 651 (complet) = Détecte seulement les VRAIS changements

### ✅ Fournit un niveau de confiance

- **High**: Les deux scrapings sont ≥ 95% complets
- **Medium**: Les deux scrapings sont ≥ 80% complets
- **Low**: Au moins un scraping < 80% complet

### ✅ Traçabilité complète

- Historique de qualité de tous les scrapings
- Notes pour documenter les problèmes (cookies expirés, etc.)
- Durée de scraping trackée

### ✅ Rétrocompatible

- Les anciennes API continuent de fonctionner
- Les nouvelles API (`/truly-new`, `/scraping-quality`) sont additionnelles
- Si le tracking échoue, le pipeline continue (non-bloquant)

## 🚀 Migration des données existantes

Pour remplir la table `scraping_metadata` avec l'historique existant :

```sql
INSERT INTO scraping_metadata (
    target_account,
    scraping_date,
    scraping_timestamp,
    total_followings,
    completeness_score,
    is_complete
)
SELECT
    target_account,
    aggregation_date::date as scraping_date,
    MAX(scraped_at) as scraping_timestamp,
    COUNT(DISTINCT username) as total_followings,
    100.0 as completeness_score,  -- On suppose que les anciens sont complets
    TRUE as is_complete
FROM final_aggregated_scraping
WHERE aggregation_date IS NOT NULL
GROUP BY target_account, aggregation_date::date
ON CONFLICT (target_account, scraping_date, scraping_timestamp) DO NOTHING;
```

Ensuite, recalculer les scores de complétude :

```sql
UPDATE scraping_metadata sm
SET completeness_score = calculate_completeness_score(sm.target_account, sm.total_followings),
    is_complete = (completeness_score >= 90.0);
```

---

## ✨ Extraction automatique du nombre total Instagram

### 🎯 Fonctionnement

Le système extrait **automatiquement** le nombre total de followings directement depuis la page profil Instagram (valeur affichée comme "357 suivi(e)s") **avant** d'ouvrir la modal de scraping.

### 📍 Localisation dans le code

La fonction `extract_instagram_reported_total()` est appelée dans `instagram_scraping_ml_pipeline.py` :

```python
# scripts/instagram_scraping_ml_pipeline.py - Lignes 340-344

# Extraire le nombre total reporté par Instagram (avant d'ouvrir la modal)
instagram_reported_total = None
if pass_number == 1:  # Extraire seulement à la première passe
    print("📊 Extraction du nombre total depuis Instagram...")
    instagram_reported_total = extract_instagram_reported_total(driver, username)
```

### 🔧 Méthodes d'extraction (3 fallbacks)

La fonction utilise 3 méthodes avec fallback automatique :

1. **Méthode XPath** : Recherche via XPath le lien contenant `/following/`
2. **Méthode Text Search** : Recherche le texte "suivi(e)s" dans la page
3. **Méthode JavaScript** ✅ : Parse le DOM avec JavaScript (la plus fiable)

**Exemple de sortie** :
```
📊 Extraction du nombre total depuis Instagram...
   ⚠️  Méthode 1 échouée: invalid literal for int() with base 10: '357following'
✅ Instagram reported total extrait (JavaScript): 357 followings
```

### 📊 Utilisation dans le calcul de complétude

Le `ScrapingQualityTracker` utilise cette valeur comme **référence prioritaire** :

```python
# scripts/scraping_quality_tracker.py - Lignes 57-66

if instagram_reported_total and instagram_reported_total > 0:
    # Utiliser le nombre réel d'Instagram comme référence (GROUND TRUTH)
    completeness_score = round((total_followings / instagram_reported_total) * 100, 2)
    logger.info(f"Score basé sur Instagram reported: {total_followings}/{instagram_reported_total} = {completeness_score:.1f}%")
else:
    # Fallback: Utiliser la fonction SQL basée sur l'historique
    cursor.execute("""
        SELECT calculate_completeness_score(%s, %s)
    """, (target_account, total_followings))
    completeness_score = cursor.fetchone()[0] or 100.0
```

### 💡 Avantages

| Critère | Avant (historique) | Après (Instagram reported) |
|---------|-------------------|---------------------------|
| **Précision** | ±5% (basé sur max historique) | **100% précis** (valeur réelle Instagram) |
| **Nouveaux comptes** | Impossible (pas d'historique) | ✅ Fonctionne dès le 1er scraping |
| **Croissance rapide** | Score faussement bas | ✅ Score exact |
| **Fiabilité** | Dépend de l'historique | ✅ Ground truth Instagram |

### 📈 Exemple concret

**Compte mariadlaura - 25/11/2025** :

```
Instagram affiche: 665 suivi(e)s
Scrapé: 650 followings (1ère passe)

Score de complétude = (650 / 665) × 100 = 97.74% ✅
```

Sans l'extraction automatique, le score aurait été calculé par rapport au max historique (moins précis).

### 🔍 Vérification dans la base de données

```sql
SELECT
    target_account,
    scraping_date,
    total_followings,
    instagram_reported_total,
    completeness_score,
    CASE
        WHEN instagram_reported_total IS NOT NULL
        THEN '✅ Score basé sur Instagram'
        ELSE '⚠️ Score basé sur historique'
    END as score_method
FROM scraping_metadata
WHERE target_account = 'mariadlaura'
ORDER BY scraping_date DESC
LIMIT 5;
```

**Résultat attendu** :
```
 target_account | scraping_date | total_followings | instagram_reported_total | completeness_score | score_method
----------------+---------------+------------------+--------------------------+--------------------+-----------------------------
 mariadlaura    | 2025-11-25    | 650              | 665                      | 97.74              | ✅ Score basé sur Instagram
 mariadlaura    | 2025-11-24    | 651              | 665                      | 97.89              | ✅ Score basé sur Instagram
 mariadlaura    | 2025-11-23    | 505              | NULL                     | 76.10              | ⚠️ Score basé sur historique
```
