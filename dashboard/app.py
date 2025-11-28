"""
Dashboard Flask pour Instagram Following Surveillance
Port: 8000
"""
import os
from flask import Flask, render_template, jsonify, request
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import logging
from unified_followings_helper import (
    get_smart_unified_followings,
    get_smart_unified_stats_for_account,
    detect_changes_between_days
)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')

# Configuration PostgreSQL
DB_CONFIG = {
    'host': os.environ.get('POSTGRES_HOST', 'postgres'),
    'port': int(os.environ.get('POSTGRES_PORT', 5432)),
    'database': os.environ.get('POSTGRES_DB', 'airflow'),
    'user': os.environ.get('POSTGRES_USER', 'airflow'),
    'password': os.environ.get('POSTGRES_PASSWORD', 'airflow')
}

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_db_connection():
    """Créer une connexion à PostgreSQL"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"Erreur de connexion PostgreSQL: {e}")
        return None


@app.route('/')
def index():
    """Page d'accueil - Vue globale de tous les comptes"""
    return render_template('index.html')


@app.route('/account/<account_name>')
def account_detail(account_name):
    """Page de détail pour un compte spécifique"""
    return render_template('account.html', account_name=account_name)


@app.route('/history')
def history():
    """Page d'historique des changements par jour"""
    return render_template('history.html')


@app.route('/api/available-dates')
def api_available_dates():
    """API: Liste des dates d'agrégation disponibles (système de fusion)"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        # Utiliser scraping_metadata pour obtenir les dates avec scrapings valides
        query = """
        SELECT DISTINCT scraping_date::date as date
        FROM scraping_metadata
        WHERE completeness_score >= 50.0
        ORDER BY date DESC
        """
        cursor.execute(query)
        dates = [row['date'].strftime('%Y-%m-%d') for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'dates': dates})
    except Exception as e:
        logger.error(f"Erreur API available_dates: {e}")
        if conn:
            conn.close()
        return jsonify({'error': str(e)}), 500


@app.route('/api/history/daily-changes')
def api_daily_changes():
    """API: Historique des changements (ajouts/suppressions) par jour (système de fusion)"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Paramètres optionnels
        account_filter = request.args.get('account', None)
        date_filter = request.args.get('date', None)
        action_filter = request.args.get('action', None)  # 'added' or 'deleted'

        # Récupérer la liste des comptes
        if account_filter:
            accounts = [account_filter]
        else:
            cursor.execute("""
                SELECT DISTINCT table_name
                FROM information_schema.tables
                WHERE table_name LIKE 'instagram_data_%'
                AND table_schema = 'public'
            """)
            accounts = [row['table_name'].replace('instagram_data_', '') for row in cursor.fetchall()]

        # Récupérer les dates disponibles
        cursor.execute("""
            SELECT DISTINCT scraping_date::date as date
            FROM scraping_metadata
            WHERE completeness_score >= 50.0
            ORDER BY date DESC
        """)
        all_dates = [row['date'] for row in cursor.fetchall()]

        cursor.close()
        conn.close()

        # Collecter tous les changements
        all_changes = []

        for account in accounts:
            for i in range(len(all_dates) - 1):
                current_date = all_dates[i]
                previous_date = all_dates[i + 1]

                # Filtrer par date si spécifié
                if date_filter and current_date.strftime('%Y-%m-%d') != date_filter:
                    continue

                # Détecter les changements entre les deux jours
                changes_data = detect_changes_between_days(
                    DB_CONFIG,
                    account,
                    current_date.strftime('%Y-%m-%d'),
                    previous_date.strftime('%Y-%m-%d')
                )

                # Ajouter les followings ajoutés
                if not action_filter or action_filter == 'added':
                    for following in changes_data['added']:
                        all_changes.append({
                            'target_account': account,
                            'date': current_date.strftime('%Y-%m-%d'),
                            'username': following['username'],
                            'full_name': following.get('full_name'),
                            'predicted_gender': following.get('predicted_gender'),
                            'action': 'added'
                        })

                # Ajouter les followings supprimés
                if not action_filter or action_filter == 'deleted':
                    for following in changes_data['deleted']:
                        all_changes.append({
                            'target_account': account,
                            'date': current_date.strftime('%Y-%m-%d'),
                            'username': following['username'],
                            'full_name': following.get('full_name'),
                            'predicted_gender': following.get('predicted_gender'),
                            'action': 'deleted'
                        })

        # Trier par date décroissante
        all_changes.sort(key=lambda x: (x['date'], x['target_account'], x['action'], x['username']), reverse=True)

        # Limiter à 500 résultats
        all_changes = all_changes[:500]

        return jsonify({
            'success': True,
            'changes': all_changes,
            'filters': {
                'account': account_filter,
                'date': date_filter,
                'action': action_filter
            }
        })

    except Exception as e:
        logger.error(f"Erreur API daily_changes: {e}")
        if conn:
            conn.close()
        return jsonify({'error': str(e)}), 500


@app.route('/api/history/summary')
def api_history_summary():
    """API: Résumé des changements par jour (comptages) (système de fusion)"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        account_filter = request.args.get('account', None)

        # Récupérer la liste des comptes
        if account_filter:
            accounts = [account_filter]
        else:
            cursor.execute("""
                SELECT DISTINCT table_name
                FROM information_schema.tables
                WHERE table_name LIKE 'instagram_data_%'
                AND table_schema = 'public'
            """)
            accounts = [row['table_name'].replace('instagram_data_', '') for row in cursor.fetchall()]

        # Récupérer les dates disponibles
        cursor.execute("""
            SELECT DISTINCT scraping_date::date as date
            FROM scraping_metadata
            WHERE completeness_score >= 50.0
            ORDER BY date DESC
        """)
        all_dates = [row['date'] for row in cursor.fetchall()]

        cursor.close()
        conn.close()

        # Dictionnaire pour agréger les changements par (date, account)
        summary_dict = {}

        for account in accounts:
            for i in range(len(all_dates) - 1):
                current_date = all_dates[i]
                previous_date = all_dates[i + 1]

                # Détecter les changements entre les deux jours
                changes_data = detect_changes_between_days(
                    DB_CONFIG,
                    account,
                    current_date.strftime('%Y-%m-%d'),
                    previous_date.strftime('%Y-%m-%d')
                )

                # Obtenir le total de followings pour ce jour
                stats = get_smart_unified_stats_for_account(DB_CONFIG, account, current_date.strftime('%Y-%m-%d'))

                # Ajouter au dictionnaire
                key = (current_date.strftime('%Y-%m-%d'), account)
                summary_dict[key] = {
                    'target_account': account,
                    'date': current_date.strftime('%Y-%m-%d'),
                    'added_count': changes_data['added_count'],
                    'deleted_count': changes_data['deleted_count'],
                    'total_followings': stats['total']
                }

        # Convertir en liste et trier
        summary = list(summary_dict.values())
        summary.sort(key=lambda x: (x['date'], x['target_account']), reverse=True)

        return jsonify({
            'success': True,
            'summary': summary
        })

    except Exception as e:
        logger.error(f"Erreur API history_summary: {e}")
        if conn:
            conn.close()
        return jsonify({'error': str(e)}), 500


@app.route('/api/accounts')
def api_accounts():
    """API: Liste de tous les comptes surveillés avec leurs stats (système de fusion)"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Paramètre optionnel pour choisir la date
        selected_date = request.args.get('date', None)

        # Si aucune date n'est spécifiée, trouver la date la plus récente avec des scrapings valides
        if selected_date is None:
            cursor.execute("""
                SELECT scraping_date::text
                FROM scraping_metadata
                WHERE completeness_score >= 50.0
                ORDER BY scraping_date DESC
                LIMIT 1
            """)
            result = cursor.fetchone()
            if result:
                selected_date = result['scraping_date']
            else:
                # Fallback: utiliser aujourd'hui si aucun scraping valide n'existe
                from datetime import datetime
                selected_date = datetime.now().strftime('%Y-%m-%d')

        # Récupérer la liste des comptes à partir des tables instagram_data_*
        cursor.execute("""
            SELECT DISTINCT table_name
            FROM information_schema.tables
            WHERE table_name LIKE 'instagram_data_%'
            AND table_schema = 'public'
        """)
        tables = cursor.fetchall()

        accounts = []
        for table_row in tables:
            # Extraire le nom du compte depuis le nom de la table
            table_name = table_row['table_name']
            account_name = table_name.replace('instagram_data_', '')

            # Utiliser le système de fusion intelligente pour obtenir les stats
            # (la normalisation sera faite à l'intérieur du helper)
            stats = get_smart_unified_stats_for_account(DB_CONFIG, account_name, selected_date)

            # Récupérer la date du dernier scraping
            cursor.execute("""
                SELECT MAX(scraped_at::timestamp) as last_scraping_date
                FROM {}
            """.format(table_name))
            last_scraping = cursor.fetchone()

            # Calculer les changements par rapport au jour précédent
            from datetime import datetime, timedelta

            date_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()
            previous_date = (date_obj - timedelta(days=1)).strftime('%Y-%m-%d')

            changes = detect_changes_between_days(DB_CONFIG, account_name, selected_date, previous_date)

            # Construire l'objet account compatible avec l'ancien format
            account_data = {
                'target_account': account_name,
                'total_followings': stats['total'],
                'male_count': stats['male'],
                'female_count': stats['female'],
                'unknown_count': stats['unknown'],
                'added_today': changes['added_count'],
                'deleted_today': changes['deleted_count'],
                'last_scraping_date': last_scraping['last_scraping_date'] if last_scraping else None,
                'aggregation_date': datetime.now().date().isoformat(),
                'fusion_info': {
                    'coverage_percent': stats['coverage_percent'],
                    'instagram_reported': stats['instagram_reported'],
                    'base_scraping': stats['base_scraping'],
                    'completed_from_others': stats['completed_from_others']
                }
            }

            accounts.append(account_data)

        # Trier par nom de compte
        accounts.sort(key=lambda x: x['target_account'])

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'accounts': accounts,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Erreur API accounts: {e}")
        if conn:
            conn.close()
        return jsonify({'error': str(e)}), 500


@app.route('/api/account/<account_name>/recent-changes')
def api_recent_changes(account_name):
    """API: Changements récents (added/deleted) pour un compte - comparaison jour par jour"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Récupérer les ajoutés (dans aujourd'hui mais pas hier) et supprimés (dans hier mais pas aujourd'hui)
        query = """
        WITH latest_dates AS (
            SELECT DISTINCT aggregation_date::date as agg_date
            FROM current_followings_realtime
            WHERE target_account = %s AND aggregation_date IS NOT NULL
            ORDER BY agg_date DESC
            LIMIT 2
        ),
        today_data AS (
            SELECT DISTINCT ON (username)
                username, full_name, predicted_gender, confidence
            FROM current_followings_realtime
            WHERE target_account = %s
            AND aggregation_date::date = (SELECT MAX(agg_date) FROM latest_dates)
            ORDER BY username, scraped_at DESC
        ),
        yesterday_data AS (
            SELECT DISTINCT ON (username)
                username, full_name, predicted_gender, confidence
            FROM current_followings_realtime
            WHERE target_account = %s
            AND aggregation_date::date = (SELECT MIN(agg_date) FROM latest_dates WHERE agg_date < (SELECT MAX(agg_date) FROM latest_dates))
            ORDER BY username, scraped_at DESC
        ),
        added AS (
            SELECT username, full_name, predicted_gender, confidence, 'added' as action_type
            FROM today_data
            WHERE username NOT IN (SELECT username FROM yesterday_data)
        ),
        deleted AS (
            SELECT username, full_name, predicted_gender, confidence, 'deleted' as action_type
            FROM yesterday_data
            WHERE username NOT IN (SELECT username FROM today_data)
        )
        SELECT * FROM added
        UNION ALL
        SELECT * FROM deleted
        ORDER BY action_type, username
        LIMIT 100
        """
        cursor.execute(query, (account_name, account_name, account_name))
        changes = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'account': account_name,
            'changes': changes,
            'date': datetime.now().strftime('%Y-%m-%d')
        })

    except Exception as e:
        logger.error(f"Erreur API recent_changes: {e}")
        if conn:
            conn.close()
        return jsonify({'error': str(e)}), 500


@app.route('/api/account/<account_name>/day-to-day-stats')
def api_day_to_day_stats(account_name):
    """API: Statistiques jour-à-jour (nombre d'ajouts et suppressions) via fusion intelligente"""
    try:
        from datetime import datetime, timedelta

        # Récupérer la date ou utiliser la plus récente avec scrapings valides
        date_str = request.args.get('date', None)

        if date_str is None:
            conn = get_db_connection()
            if conn:
                try:
                    cursor = conn.cursor(cursor_factory=RealDictCursor)
                    cursor.execute("""
                        SELECT scraping_date::text
                        FROM scraping_metadata
                        WHERE completeness_score >= 50.0
                        ORDER BY scraping_date DESC
                        LIMIT 1
                    """)
                    result = cursor.fetchone()
                    if result:
                        date_str = result['scraping_date']
                    else:
                        date_str = datetime.now().strftime('%Y-%m-%d')
                    cursor.close()
                    conn.close()
                except Exception as e:
                    logger.error(f"Erreur lors de la récupération de la date: {e}")
                    if conn:
                        conn.close()
                    date_str = datetime.now().strftime('%Y-%m-%d')

        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        previous_date = (date_obj - timedelta(days=1)).strftime('%Y-%m-%d')

        # Utiliser la fonction de détection avec fusion intelligente
        changes = detect_changes_between_days(DB_CONFIG, account_name, date_str, previous_date)

        return jsonify({
            'success': True,
            'account': account_name,
            'added': changes['added_count'],
            'deleted': changes['deleted_count']
        })

    except Exception as e:
        logger.error(f"Erreur API day_to_day_stats: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/account/<account_name>/day-to-day-changes')
def api_day_to_day_changes(account_name):
    """API: Liste des changements jour-à-jour (ajouts ou suppressions) via fusion intelligente"""
    try:
        from datetime import datetime, timedelta

        action_filter = request.args.get('action', 'added')  # 'added' ou 'deleted'
        date_str = request.args.get('date', None)

        # Si aucune date n'est spécifiée, utiliser la plus récente avec scrapings valides
        if date_str is None:
            conn = get_db_connection()
            if conn:
                try:
                    cursor = conn.cursor(cursor_factory=RealDictCursor)
                    cursor.execute("""
                        SELECT scraping_date::text
                        FROM scraping_metadata
                        WHERE completeness_score >= 50.0
                        ORDER BY scraping_date DESC
                        LIMIT 1
                    """)
                    result = cursor.fetchone()
                    if result:
                        date_str = result['scraping_date']
                    else:
                        date_str = datetime.now().strftime('%Y-%m-%d')
                    cursor.close()
                    conn.close()
                except Exception as e:
                    logger.error(f"Erreur lors de la récupération de la date: {e}")
                    if conn:
                        conn.close()
                    date_str = datetime.now().strftime('%Y-%m-%d')

        # Calculer la date précédente
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        previous_date = (date_obj - timedelta(days=1)).strftime('%Y-%m-%d')

        # Utiliser la fonction de détection de changements avec fusion intelligente
        changes_data = detect_changes_between_days(DB_CONFIG, account_name, date_str, previous_date)

        # Sélectionner les changements selon le filtre
        if action_filter == 'added':
            changes = changes_data['added']
        else:  # deleted
            changes = changes_data['deleted']

        return jsonify({
            'success': True,
            'account': account_name,
            'action': action_filter,
            'changes': changes
        })

    except Exception as e:
        logger.error(f"Erreur API day_to_day_changes: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/account/<account_name>/followings')
def api_followings(account_name):
    """API: Liste complète des followings d'un compte avec pagination (système de fusion)"""
    try:
        # Paramètres de pagination
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        offset = (page - 1) * per_page

        # Filtres
        search = request.args.get('search', '')
        gender_filter = request.args.get('gender', '')
        status_filter = request.args.get('status', '')  # added/present/deleted (not yet implemented)
        sort_filter = request.args.get('sort', 'username_asc')  # tri

        # Récupérer les followings fusionnés via le helper
        date_param = request.args.get('date', None)  # Format YYYY-MM-DD

        # Si aucune date n'est spécifiée, utiliser la date la plus récente avec des scrapings valides
        if date_param is None:
            conn = get_db_connection()
            if conn:
                try:
                    cursor = conn.cursor(cursor_factory=RealDictCursor)
                    cursor.execute("""
                        SELECT scraping_date::text
                        FROM scraping_metadata
                        WHERE completeness_score >= 50.0
                        ORDER BY scraping_date DESC
                        LIMIT 1
                    """)
                    result = cursor.fetchone()
                    if result:
                        date_param = result['scraping_date']
                    cursor.close()
                    conn.close()
                except Exception as e:
                    logger.error(f"Erreur lors de la récupération de la date: {e}")
                    if conn:
                        conn.close()

        unified_data = get_smart_unified_followings(DB_CONFIG, account_name, date_param)

        if 'error' in unified_data:
            return jsonify({'error': unified_data['error']}), 500

        # Récupérer la liste des followings
        all_followings = unified_data['followings']

        # Appliquer les filtres
        filtered_followings = []
        for f in all_followings:
            # Filtre de recherche
            if search:
                search_lower = search.lower()
                username_match = search_lower in (f.get('username') or '').lower()
                fullname_match = search_lower in (f.get('full_name') or '').lower()
                if not (username_match or fullname_match):
                    continue

            # Filtre de genre
            if gender_filter and f.get('predicted_gender') != gender_filter:
                continue

            # Ajouter à la liste filtrée
            filtered_followings.append(f)

        # Appliquer le tri
        sort_key_map = {
            'username_asc': lambda x: (x.get('username') or '').lower(),
            'username_desc': lambda x: (x.get('username') or '').lower(),
            'date_desc': lambda x: x.get('last_seen') or '',
            'date_asc': lambda x: x.get('first_seen') or '',
            'confidence_desc': lambda x: x.get('confidence_score') or 0,
            'confidence_asc': lambda x: x.get('confidence_score') or 0
        }
        reverse_map = {
            'username_asc': False,
            'username_desc': True,
            'date_desc': True,
            'date_asc': False,
            'confidence_desc': True,
            'confidence_asc': False
        }

        sort_key = sort_key_map.get(sort_filter, lambda x: (x.get('username') or '').lower())
        reverse = reverse_map.get(sort_filter, False)
        filtered_followings.sort(key=sort_key, reverse=reverse)

        # Pagination
        total = len(filtered_followings)
        paginated_followings = filtered_followings[offset:offset + per_page]

        # Formater les données pour correspondre au format attendu par le frontend
        formatted_followings = []
        for f in paginated_followings:
            formatted_followings.append({
                'username': f.get('username'),
                'full_name': f.get('full_name'),
                'predicted_gender': f.get('predicted_gender'),
                'confidence': f.get('gender_confidence'),  # Confiance du genre
                'scraping_date': f.get('last_seen'),  # Dernière apparition
                'status': 'present',  # Status (détection added/removed via /day-to-day-changes)
                'appearances': f.get('appearances'),  # Nombre d'apparitions
                'confidence_score': f.get('confidence_score')  # Score de confiance de présence
            })

        return jsonify({
            'success': True,
            'account': account_name,
            'followings': formatted_followings,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            },
            'fusion_info': {
                'total_unique': unified_data['total_unique'],
                'coverage_percent': unified_data['coverage_percent'],
                'instagram_reported': unified_data['instagram_reported'],
                'base_scraping': unified_data['base_scraping'],
                'completed_from_others': unified_data['completed_from_others']
            }
        })

    except Exception as e:
        logger.error(f"Erreur API followings: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats')
def api_stats():
    """API: Statistiques globales (système de fusion)"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Paramètre optionnel pour choisir la date
        selected_date = request.args.get('date', None)

        # Si aucune date n'est spécifiée, trouver la date la plus récente avec des scrapings valides
        if selected_date is None:
            cursor.execute("""
                SELECT scraping_date::text
                FROM scraping_metadata
                WHERE completeness_score >= 50.0
                ORDER BY scraping_date DESC
                LIMIT 1
            """)
            result = cursor.fetchone()
            if result:
                selected_date = result['scraping_date']
            else:
                # Fallback: utiliser aujourd'hui si aucun scraping valide n'existe
                from datetime import datetime
                selected_date = datetime.now().strftime('%Y-%m-%d')

        # Récupérer la liste des comptes
        cursor.execute("""
            SELECT DISTINCT table_name
            FROM information_schema.tables
            WHERE table_name LIKE 'instagram_data_%'
            AND table_schema = 'public'
        """)
        tables = cursor.fetchall()

        # Agréger les stats de tous les comptes via le système de fusion
        stats = {
            'total_accounts': 0,
            'total_followings': 0,
            'total_male': 0,
            'total_female': 0,
            'total_unknown': 0,
            'added_today': 0,
            'deleted_today': 0
        }

        for table_row in tables:
            table_name = table_row['table_name']
            account_name = table_name.replace('instagram_data_', '')

            try:
                # Utiliser le système de fusion avec la date sélectionnée
                account_stats = get_smart_unified_stats_for_account(DB_CONFIG, account_name, selected_date)

                if account_stats['total'] > 0:
                    stats['total_accounts'] += 1
                    stats['total_followings'] += account_stats['total']
                    stats['total_male'] += account_stats['male']
                    stats['total_female'] += account_stats['female']
                    stats['total_unknown'] += account_stats['unknown']

                # Calculer les changements par rapport au jour précédent
                from datetime import datetime, timedelta
                date_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()
                previous_date = (date_obj - timedelta(days=1)).strftime('%Y-%m-%d')

                changes = detect_changes_between_days(DB_CONFIG, account_name, selected_date, previous_date)
                stats['added_today'] += changes['added_count']
                stats['deleted_today'] += changes['deleted_count']

            except Exception as e:
                logger.error(f"Erreur stats pour {account_name}: {e}")
                continue

        # Récupérer la date de dernière agrégation (même table que scraping, mais on cherche la plus récente)
        try:
            query_last_aggregation = """
            SELECT MAX(scraped_at::timestamp)::date as last_aggregation_date
            FROM current_followings_realtime
            """
            cursor.execute(query_last_aggregation)
            result = cursor.fetchone()
            stats['last_aggregation_date'] = str(result['last_aggregation_date']) if result and result['last_aggregation_date'] else None
        except Exception as e:
            logger.error(f"Error fetching last_aggregation_date: {e}")
            stats['last_aggregation_date'] = None

        # Récupérer si le comparatif existe (la table n'a pas de date)
        try:
            query_last_comparatif = """
            SELECT COUNT(*) as count FROM final_comparatif_scraping LIMIT 1
            """
            cursor.execute(query_last_comparatif)
            result = cursor.fetchone()
            # Utiliser la même date que l'agrégation si le comparatif existe
            stats['last_comparison_date'] = stats.get('last_aggregation_date') if result and result['count'] > 0 else None
        except Exception as e:
            conn.rollback()
            logger.error(f"Error fetching last_comparison_date: {e}")
            stats['last_comparison_date'] = None

        # Récupérer la date du dernier scraping
        try:
            query_last_scraping = """
            SELECT MAX(scraped_at::timestamp) as last_scraping_date
            FROM current_followings_realtime
            """
            cursor.execute(query_last_scraping)
            result = cursor.fetchone()
            stats['last_scraping_date'] = result['last_scraping_date'] if result else None
        except Exception as e:
            logger.error(f"Error fetching last_scraping_date: {e}")
            stats['last_scraping_date'] = None

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'stats': stats,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Erreur API stats: {e}")
        if conn:
            conn.close()
        return jsonify({'error': str(e)}), 500


@app.route('/api/global-visual-mode', methods=['GET'])
def api_get_global_visual_mode():
    """API: Récupère l'état du mode visuel global (pour les scrapings automatiques)"""
    try:
        env_file_path = '/app/docker/.env'

        if not os.path.exists(env_file_path):
            return jsonify({'success': False, 'error': 'Fichier .env non trouvé'}), 404

        # Lire le fichier .env et chercher VISUAL_MODE
        visual_mode = False
        with open(env_file_path, 'r') as f:
            for line in f:
                if line.strip().startswith('VISUAL_MODE='):
                    value = line.split('=')[1].strip()
                    visual_mode = value.lower() == 'true'
                    break

        return jsonify({
            'success': True,
            'visual_mode': visual_mode
        })

    except Exception as e:
        logger.error(f"Erreur lors de la lecture du mode visuel global: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/global-visual-mode', methods=['POST'])
def api_set_global_visual_mode():
    """API: Modifie l'état du mode visuel global (pour les scrapings automatiques)"""
    try:
        data = request.get_json() or {}
        visual_mode = data.get('visual_mode', False)

        env_file_path = '/app/docker/.env'

        if not os.path.exists(env_file_path):
            return jsonify({'success': False, 'error': 'Fichier .env non trouvé'}), 404

        # Lire le fichier .env
        with open(env_file_path, 'r') as f:
            lines = f.readlines()

        # Modifier la ligne VISUAL_MODE
        visual_mode_found = False
        for i, line in enumerate(lines):
            if line.strip().startswith('VISUAL_MODE='):
                lines[i] = f"VISUAL_MODE={'true' if visual_mode else 'false'}\n"
                visual_mode_found = True
                break

        # Si VISUAL_MODE n'existe pas, l'ajouter après AIRFLOW_SECRET_KEY
        if not visual_mode_found:
            for i, line in enumerate(lines):
                if line.strip().startswith('AIRFLOW_SECRET_KEY='):
                    lines.insert(i + 1, f"\nVISUAL_MODE={'true' if visual_mode else 'false'}\n")
                    break

        # Écrire le fichier .env modifié
        with open(env_file_path, 'w') as f:
            f.writelines(lines)

        return jsonify({
            'success': True,
            'visual_mode': visual_mode,
            'message': f"Mode visuel global {'activé' if visual_mode else 'désactivé'} pour les scrapings automatiques"
        })

    except Exception as e:
        logger.error(f"Erreur lors de la modification du mode visuel global: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/health')
def health():
    """Healthcheck endpoint"""
    conn = get_db_connection()
    if conn:
        conn.close()
        return jsonify({'status': 'healthy', 'database': 'connected'})
    else:
        return jsonify({'status': 'unhealthy', 'database': 'disconnected'}), 503


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)


@app.route('/api/account/<account_name>/truly-new')
def api_truly_new_followings(account_name):
    """API: Vrais nouveaux followings depuis le dernier scraping complet"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Récupérer les vrais nouveaux du dernier scraping complet (le meilleur du jour)
        query = """
        WITH best_scraping AS (
            SELECT target_account, scraping_date, completeness_score
            FROM scraping_metadata
            WHERE target_account = %s
            AND is_complete = TRUE
            AND scraping_date = (
                SELECT MAX(scraping_date)
                FROM scraping_metadata
                WHERE target_account = %s
                AND is_complete = TRUE
            )
            ORDER BY total_followings DESC, scraping_timestamp DESC
            LIMIT 1
        )
        SELECT DISTINCT
            tnf.username,
            tnf.full_name,
            tnf.predicted_gender,
            bs.completeness_score as confidence_score
        FROM truly_new_followings tnf
        JOIN best_scraping bs
            ON tnf.target_account = bs.target_account
            AND tnf.scraping_date = bs.scraping_date
        ORDER BY tnf.username;
        """
        
        cursor.execute(query, (account_name, account_name))
        truly_new = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'account': account_name,
            'truly_new': truly_new,
            'count': len(truly_new)
        })
    
    except Exception as e:
        logger.error(f"Erreur API truly_new: {e}")
        if conn:
            conn.close()
        return jsonify({'error': str(e)}), 500


@app.route('/api/account/<account_name>/scraping-quality')
def api_scraping_quality(account_name):
    """API: Historique de qualité des scrapings"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
        WITH daily_combined AS (
            -- Calculer le total combiné pour chaque jour
            SELECT
                target_account,
                aggregation_date::date as scraping_date,
                COUNT(DISTINCT username) as combined_total
            FROM current_followings_realtime
            WHERE target_account = %s
            GROUP BY target_account, aggregation_date::date
        )
        SELECT
            sm.scraping_date,
            sm.scraping_timestamp,
            sm.total_followings,
            sm.completeness_score as original_completeness_score,
            sm.is_complete,
            sm.scraping_duration_seconds,
            sm.notes,
            sm.instagram_reported_total,
            dc.combined_total,
            -- Vrai score de complétude (priorité à instagram_reported_total)
            CASE
                WHEN sm.instagram_reported_total IS NOT NULL AND sm.instagram_reported_total > 0 THEN
                    ROUND((sm.total_followings::numeric / sm.instagram_reported_total::numeric) * 100, 2)
                WHEN dc.combined_total > 0 THEN
                    ROUND((sm.total_followings::numeric / dc.combined_total::numeric) * 100, 2)
                ELSE
                    sm.completeness_score
            END as dynamic_completeness_score
        FROM scraping_metadata sm
        LEFT JOIN daily_combined dc
            ON sm.target_account = dc.target_account
            AND sm.scraping_date = dc.scraping_date
        WHERE sm.target_account = %s
        ORDER BY sm.scraping_date DESC, sm.scraping_timestamp DESC
        LIMIT 30
        """

        cursor.execute(query, (account_name, account_name))
        quality_history = cursor.fetchall()

        # Formater les dates et timestamps
        for row in quality_history:
            if row['scraping_date']:
                row['scraping_date'] = row['scraping_date'].strftime('%Y-%m-%d')
            if row['scraping_timestamp']:
                row['scraping_timestamp'] = row['scraping_timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        
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


@app.route('/api/target-accounts', methods=['GET'])
def api_get_target_accounts():
    """API: Récupère la liste des comptes ciblés"""
    try:
        accounts_file = '/app/instagram_accounts_to_scrape.txt'

        if not os.path.exists(accounts_file):
            return jsonify({
                'success': True,
                'accounts': []
            })

        with open(accounts_file, 'r') as f:
            accounts = [line.strip() for line in f if line.strip()]

        return jsonify({
            'success': True,
            'accounts': accounts
        })

    except Exception as e:
        logger.error(f"Erreur lors de la lecture des comptes: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/target-accounts', methods=['POST'])
def api_save_target_accounts():
    """API: Sauvegarde la liste des comptes ciblés"""
    try:
        data = request.get_json() or {}
        accounts_text = data.get('accounts', '')

        # Nettoyer la liste (enlever lignes vides, espaces)
        accounts = [line.strip() for line in accounts_text.split('\n') if line.strip()]

        # Valider que ce sont des usernames valides (optionnel)
        for account in accounts:
            if not account.replace('_', '').replace('.', '').isalnum():
                return jsonify({
                    'success': False,
                    'error': f'Nom de compte invalide: {account}'
                }), 400

        # Sauvegarder dans le fichier
        accounts_file = '/app/instagram_accounts_to_scrape.txt'
        with open(accounts_file, 'w') as f:
            for account in accounts:
                f.write(f"{account}\n")

        logger.info(f"Liste des comptes mise à jour: {len(accounts)} comptes")

        return jsonify({
            'success': True,
            'message': f'{len(accounts)} compte(s) sauvegardé(s)',
            'accounts': accounts
        })

    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde des comptes: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/trigger-dag', methods=['POST'])
def api_trigger_dag():
    """API: Déclenche manuellement le DAG Airflow avec option mode visuel"""
    try:
        import requests
        import json

        # Récupérer le paramètre visual_mode
        data = request.get_json() or {}
        visual_mode = data.get('visual_mode', False)

        # Mettre à jour VISUAL_MODE dans docker/.env si demandé
        if visual_mode:
            env_file_path = '/app/docker/.env'
            try:
                # Lire le fichier .env
                with open(env_file_path, 'r') as f:
                    lines = f.readlines()

                # Modifier la ligne VISUAL_MODE
                updated = False
                for i, line in enumerate(lines):
                    if line.startswith('VISUAL_MODE='):
                        lines[i] = 'VISUAL_MODE=true\n'
                        updated = True
                        break

                # Si VISUAL_MODE n'existe pas, l'ajouter
                if not updated:
                    lines.append('VISUAL_MODE=true\n')

                # Écrire le fichier .env
                with open(env_file_path, 'w') as f:
                    f.writelines(lines)

                logger.info("VISUAL_MODE activé dans docker/.env")
            except Exception as e:
                logger.error(f"Erreur lors de la mise à jour de VISUAL_MODE: {e}")
                return jsonify({
                    'success': False,
                    'error': f'Erreur mise à jour VISUAL_MODE: {str(e)}'
                }), 500

        # Déclencher le DAG via l'API Airflow
        # Note: Depuis le container dashboard, on accède à airflow-webserver via le nom du service Docker
        airflow_url = "http://airflow-webserver:8080/api/v1/dags/instagram_scraping_surveillance_pipeline/dagRuns"

        # Authentification Airflow (utiliser les credentials par défaut)
        airflow_user = os.environ.get('AIRFLOW_USER', 'admin')
        airflow_password = os.environ.get('AIRFLOW_PASSWORD', 'admin')

        # Payload pour déclencher le DAG
        payload = {
            "conf": {
                "manual_trigger": True,
                "visual_mode": visual_mode
            }
        }

        # Faire la requête POST vers Airflow
        response = requests.post(
            airflow_url,
            json=payload,
            auth=(airflow_user, airflow_password),
            headers={'Content-Type': 'application/json'},
            timeout=10
        )

        if response.status_code in [200, 201]:
            dag_run_data = response.json()
            return jsonify({
                'success': True,
                'message': 'DAG déclenché avec succès',
                'dag_run_id': dag_run_data.get('dag_run_id'),
                'visual_mode': visual_mode,
                'execution_date': dag_run_data.get('execution_date')
            })
        else:
            logger.error(f"Erreur Airflow API: {response.status_code} - {response.text}")
            return jsonify({
                'success': False,
                'error': f'Erreur Airflow: {response.status_code}',
                'details': response.text
            }), response.status_code

    except Exception as e:
        logger.error(f"Erreur lors du déclenchement du DAG: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)


