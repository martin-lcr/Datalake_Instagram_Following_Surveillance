"""
Helper pour récupérer les followings fusionnés de tous les scrapings du jour
Au lieu d'afficher seulement le dernier scraping (611 followings),
on fusionne tous les scrapings valides pour obtenir le maximum (664 followings)
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def get_unified_followings_for_account(db_config, account_name, date=None):
    """
    Récupère tous les followings uniques en fusionnant tous les scrapings du jour

    Args:
        db_config: Configuration PostgreSQL
        account_name: Nom du compte Instagram
        date: Date au format 'YYYY-MM-DD' (défaut: aujourd'hui)

    Returns:
        dict: {
            'followings': [...],  # Liste des followings
            'total_unique': int,  # Nombre total unique
            'scrapings_used': int,  # Nombre de scrapings fusionnés
            'coverage_percent': float,  # % de couverture vs Instagram
            'instagram_reported': int  # Nombre total Instagram
        }
    """
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')

    conn = None
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Nom de la table (format: instagram_data_XXX)
        table_name = f"instagram_data_{account_name}"

        # Vérifier que la table existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = %s
            )
        """, (table_name,))

        if not cursor.fetchone()['exists']:
            logger.warning(f"Table {table_name} n'existe pas")
            return {
                'followings': [],
                'total_unique': 0,
                'scrapings_used': 0,
                'coverage_percent': 0,
                'instagram_reported': None
            }

        # Récupérer le nombre Instagram reporté
        cursor.execute("""
            SELECT instagram_reported_total
            FROM scraping_metadata
            WHERE target_account = %s
              AND scraping_date = %s::date
              AND instagram_reported_total IS NOT NULL
            ORDER BY scraping_timestamp DESC
            LIMIT 1
        """, (normalized_account, date))

        result = cursor.fetchone()
        instagram_reported = result['instagram_reported_total'] if result else None

        # Compter le nombre de scrapings valides
        # Note: utilise une fenêtre temporelle de 2 minutes pour matcher les timestamps
        # car scraped_at (début) != scraping_timestamp (fin)
        cursor.execute("""
            SELECT COUNT(DISTINCT scraped_at::timestamp) as count
            FROM {} f
            WHERE scraped_at::timestamp::date = %s::date
              AND EXISTS (
                  SELECT 1 FROM scraping_metadata sm
                  WHERE sm.target_account = %s
                    AND sm.scraping_date = %s::date
                    AND ABS(EXTRACT(EPOCH FROM (sm.scraping_timestamp - f.scraped_at::timestamp))) < 120
                    AND sm.completeness_score >= 50.0
              )
        """.format(table_name), (date, normalized_account, date))

        scrapings_used = cursor.fetchone()['count']

        # Fusion de tous les scrapings valides
        query = """
            WITH valid_scrapings AS (
                SELECT DISTINCT scraped_at::timestamp as ts
                FROM {} f
                WHERE scraped_at::timestamp::date = %s::date
                  AND EXISTS (
                      SELECT 1 FROM scraping_metadata sm
                      WHERE sm.target_account = %s
                        AND sm.scraping_date = %s::date
                        AND ABS(EXTRACT(EPOCH FROM (sm.scraping_timestamp - f.scraped_at::timestamp))) < 120
                        AND sm.completeness_score >= 50.0
                  )
            )
            SELECT
                f.username,
                MAX(f.full_name) as full_name,
                MAX(f.predicted_gender) as predicted_gender,
                MAX(f.confidence) as gender_confidence,
                COUNT(DISTINCT f.scraped_at::timestamp) as appearances,
                MIN(f.scraped_at::timestamp) as first_seen,
                MAX(f.scraped_at::timestamp) as last_seen,
                ROUND((COUNT(DISTINCT f.scraped_at::timestamp)::NUMERIC / %s::NUMERIC) * 100, 2) as confidence_score
            FROM {} f
            WHERE f.scraped_at::timestamp IN (SELECT ts FROM valid_scrapings)
            GROUP BY f.username
            ORDER BY f.username
        """.format(table_name, table_name)

        cursor.execute(query, (date, account_name, date, scrapings_used))
        followings = cursor.fetchall()

        # Calculer la couverture
        total_unique = len(followings)
        coverage_percent = None
        if instagram_reported and instagram_reported > 0:
            coverage_percent = round((total_unique / instagram_reported) * 100, 2)

        return {
            'followings': [dict(f) for f in followings],
            'total_unique': total_unique,
            'scrapings_used': scrapings_used,
            'coverage_percent': coverage_percent,
            'instagram_reported': instagram_reported
        }

    except Exception as e:
        logger.error(f"Erreur lors de la fusion des followings pour {account_name}: {e}")
        return {
            'followings': [],
            'total_unique': 0,
            'scrapings_used': 0,
            'coverage_percent': 0,
            'instagram_reported': None,
            'error': str(e)
        }
    finally:
        if conn:
            conn.close()


def get_unified_stats_for_account(db_config, account_name, date=None):
    """
    Récupère les statistiques globales basées sur la fusion

    Returns:
        dict: {
            'total': int,
            'male': int,
            'female': int,
            'unknown': int,
            'coverage_percent': float,
            'scrapings_used': int
        }
    """
    data = get_unified_followings_for_account(db_config, account_name, date)

    followings = data['followings']

    stats = {
        'total': data['total_unique'],
        'male': sum(1 for f in followings if f.get('predicted_gender') == 'male'),
        'female': sum(1 for f in followings if f.get('predicted_gender') == 'female'),
        'unknown': sum(1 for f in followings if f.get('predicted_gender') in [None, 'unknown']),
        'coverage_percent': data['coverage_percent'],
        'scrapings_used': data['scrapings_used'],
        'instagram_reported': data['instagram_reported']
    }

    return stats


def get_smart_unified_followings(db_config, account_name, date=None, max_age_hours=12):
    """
    Fusion intelligente : prend le scraping complet récent comme base,
    puis complète avec les autres scrapings si nécessaire

    Args:
        db_config: Configuration PostgreSQL
        account_name: Nom du compte Instagram
        date: Date au format 'YYYY-MM-DD' (défaut: aujourd'hui)
        max_age_hours: Age maximum en heures pour le scraping de base (défaut: 12h)

    Returns:
        dict: {
            'followings': [...],
            'total_unique': int,
            'instagram_reported': int,
            'coverage_percent': float,
            'base_scraping': {...},  # Info sur le scraping de base utilisé
            'completed_from_others': int  # Nombre ajouté depuis autres scrapings
        }
    """
    from datetime import datetime, timedelta

    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')

    # Normaliser le nom du compte pour les requêtes metadata (même logique que le script de scraping)
    normalized_account = account_name.replace(".", "-").replace("_", "-")

    conn = None
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        table_name = f"instagram_data_{account_name}"

        # Vérifier que la table existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = %s
            )
        """, (table_name,))

        if not cursor.fetchone()['exists']:
            logger.warning(f"Table {table_name} n'existe pas")
            return {
                'followings': [],
                'total_unique': 0,
                'instagram_reported': None,
                'coverage_percent': 0,
                'base_scraping': None,
                'completed_from_others': 0
            }

        # Récupérer le nombre Instagram reporté le plus récent
        cursor.execute("""
            SELECT instagram_reported_total, scraping_timestamp
            FROM scraping_metadata
            WHERE target_account = %s
              AND scraping_date = %s::date
              AND instagram_reported_total IS NOT NULL
            ORDER BY scraping_timestamp DESC
            LIMIT 1
        """, (normalized_account, date))

        result = cursor.fetchone()
        instagram_reported = result['instagram_reported_total'] if result else None

        # Trouver le scraping complet le plus récent (dans la fenêtre de temps)
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

        cursor.execute("""
            SELECT
                sm.scraping_timestamp,
                sm.total_followings,
                sm.completeness_score,
                sm.instagram_reported_total
            FROM scraping_metadata sm
            WHERE sm.target_account = %s
              AND sm.scraping_date = %s::date
              AND sm.completeness_score >= 50.0
              AND sm.scraping_timestamp >= %s
            ORDER BY sm.completeness_score DESC, sm.scraping_timestamp DESC
            LIMIT 1
        """, (normalized_account, date, cutoff_time))

        base_scraping_meta = cursor.fetchone()

        if not base_scraping_meta:
            # Fallback : prendre le meilleur scraping du jour sans limite de temps
            cursor.execute("""
                SELECT
                    sm.scraping_timestamp,
                    sm.total_followings,
                    sm.completeness_score,
                    sm.instagram_reported_total
                FROM scraping_metadata sm
                WHERE sm.target_account = %s
                  AND sm.scraping_date = %s::date
                  AND sm.completeness_score >= 50.0
                ORDER BY sm.completeness_score DESC, sm.scraping_timestamp DESC
                LIMIT 1
            """, (normalized_account, date))
            base_scraping_meta = cursor.fetchone()

        if not base_scraping_meta:
            logger.warning(f"Aucun scraping valide trouvé pour {account_name} le {date}")
            return {
                'followings': [],
                'total_unique': 0,
                'instagram_reported': instagram_reported,
                'coverage_percent': 0,
                'base_scraping': None,
                'completed_from_others': 0
            }

        base_timestamp = base_scraping_meta['scraping_timestamp']

        # Récupérer les followings du scraping de base
        cursor.execute("""
            SELECT
                username,
                full_name,
                predicted_gender,
                confidence as gender_confidence
            FROM {}
            WHERE ABS(EXTRACT(EPOCH FROM (scraped_at::timestamp - %s))) < 120
        """.format(table_name), (base_timestamp,))

        base_followings = [dict(row) for row in cursor.fetchall()]
        base_usernames = {f['username'] for f in base_followings}

        # Calculer combien de followings manquent
        missing_count = 0
        if instagram_reported and instagram_reported > len(base_followings):
            missing_count = instagram_reported - len(base_followings)

        # Si des followings manquent, chercher dans les autres scrapings
        completed_from_others = 0
        if missing_count > 0:
            logger.info(f"Manque {missing_count} followings, recherche dans les autres scrapings...")

            # Récupérer tous les followings des autres scrapings valides
            cursor.execute("""
                SELECT DISTINCT
                    f.username,
                    MAX(f.full_name) as full_name,
                    MAX(f.predicted_gender) as predicted_gender,
                    MAX(f.confidence) as gender_confidence,
                    COUNT(DISTINCT f.scraped_at::timestamp) as appearances
                FROM {} f
                WHERE f.scraped_at::timestamp::date = %s::date
                  AND ABS(EXTRACT(EPOCH FROM (f.scraped_at::timestamp - %s))) >= 120
                  AND EXISTS (
                      SELECT 1 FROM scraping_metadata sm
                      WHERE sm.target_account = %s
                        AND sm.scraping_date = %s::date
                        AND ABS(EXTRACT(EPOCH FROM (sm.scraping_timestamp - f.scraped_at::timestamp))) < 120
                        AND sm.completeness_score >= 50.0
                  )
                GROUP BY f.username
                ORDER BY appearances DESC, f.username
            """.format(table_name), (date, base_timestamp, normalized_account, date))

            other_followings = cursor.fetchall()

            # Filtrer pour garder seulement ceux qui ne sont pas dans le scraping de base
            candidates = [f for f in other_followings if f['username'] not in base_usernames]

            # Prendre les N premiers candidats (ceux avec le plus d'apparitions)
            to_add = candidates[:missing_count]

            base_followings.extend([dict(f) for f in to_add])
            completed_from_others = len(to_add)

            logger.info(f"Ajouté {completed_from_others} followings depuis les autres scrapings")

        # Calculer la couverture
        total_unique = len(base_followings)
        coverage_percent = None
        if instagram_reported and instagram_reported > 0:
            coverage_percent = round((total_unique / instagram_reported) * 100, 2)

        cursor.close()
        conn.close()

        return {
            'followings': base_followings,
            'total_unique': total_unique,
            'instagram_reported': instagram_reported,
            'coverage_percent': coverage_percent,
            'base_scraping': {
                'timestamp': base_scraping_meta['scraping_timestamp'].isoformat(),
                'total_followings': base_scraping_meta['total_followings'],
                'completeness_score': float(base_scraping_meta['completeness_score'])
            },
            'completed_from_others': completed_from_others
        }

    except Exception as e:
        logger.error(f"Erreur lors de la fusion intelligente pour {account_name}: {e}")
        return {
            'followings': [],
            'total_unique': 0,
            'instagram_reported': None,
            'coverage_percent': 0,
            'base_scraping': None,
            'completed_from_others': 0,
            'error': str(e)
        }
    finally:
        if conn:
            conn.close()


def get_smart_unified_stats_for_account(db_config, account_name, date=None):
    """
    Récupère les statistiques basées sur la fusion intelligente

    Returns:
        dict: {
            'total': int,
            'male': int,
            'female': int,
            'unknown': int,
            'coverage_percent': float,
            'instagram_reported': int,
            'base_scraping': {...},
            'completed_from_others': int
        }
    """
    data = get_smart_unified_followings(db_config, account_name, date)

    followings = data['followings']

    stats = {
        'total': data['total_unique'],
        'male': sum(1 for f in followings if f.get('predicted_gender') == 'male'),
        'female': sum(1 for f in followings if f.get('predicted_gender') == 'female'),
        'unknown': sum(1 for f in followings if f.get('predicted_gender') in [None, 'unknown']),
        'coverage_percent': data['coverage_percent'],
        'instagram_reported': data['instagram_reported'],
        'base_scraping': data['base_scraping'],
        'completed_from_others': data['completed_from_others']
    }

    return stats


def detect_changes_between_days(db_config, account_name, date_current, date_previous):
    """
    Détecte les ajouts et suppressions en comparant deux jours de fusion

    Args:
        db_config: Configuration PostgreSQL
        account_name: Nom du compte Instagram
        date_current: Date actuelle au format 'YYYY-MM-DD'
        date_previous: Date précédente au format 'YYYY-MM-DD'

    Returns:
        dict: {
            'added': [...],  # Followings ajoutés
            'deleted': [...],  # Followings supprimés
            'date_current': str,
            'date_previous': str
        }
    """
    # Récupérer les followings des deux jours (fusion intelligente)
    current_data = get_smart_unified_followings(db_config, account_name, date_current)
    previous_data = get_smart_unified_followings(db_config, account_name, date_previous)

    # Créer des sets de usernames pour comparaison rapide
    current_usernames = {f['username'] for f in current_data['followings']}
    previous_usernames = {f['username'] for f in previous_data['followings']}

    # Détecter les ajouts (présents en current, absents en previous)
    added_usernames = current_usernames - previous_usernames
    added = [f for f in current_data['followings'] if f['username'] in added_usernames]

    # Détecter les suppressions (présents en previous, absents en current)
    deleted_usernames = previous_usernames - current_usernames
    deleted = [f for f in previous_data['followings'] if f['username'] in deleted_usernames]

    return {
        'added': added,
        'deleted': deleted,
        'date_current': date_current,
        'date_previous': date_previous,
        'added_count': len(added),
        'deleted_count': len(deleted)
    }
