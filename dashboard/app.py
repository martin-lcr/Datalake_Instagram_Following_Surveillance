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


@app.route('/api/accounts')
def api_accounts():
    """API: Liste de tous les comptes surveillés avec leurs stats"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Récupérer tous les comptes distincts avec leurs stats
        query = """
        SELECT
            target_account,
            COUNT(*) as total_followings,
            COUNT(CASE WHEN predicted_gender = 'male' THEN 1 END) as male_count,
            COUNT(CASE WHEN predicted_gender = 'female' THEN 1 END) as female_count,
            COUNT(CASE WHEN predicted_gender = 'unknown' THEN 1 END) as unknown_count,
            MAX(scraping_date) as last_scraping_date
        FROM instagram_followings
        GROUP BY target_account
        ORDER BY target_account
        """
        cursor.execute(query)
        accounts = cursor.fetchall()

        # Pour chaque compte, récupérer les changements récents (aujourd'hui)
        today = datetime.now().strftime('%Y-%m-%d')
        for account in accounts:
            # Récupérer les added/deleted d'aujourd'hui
            query_changes = """
            SELECT
                action_type,
                COUNT(*) as count
            FROM instagram_comparatif
            WHERE target_account = %s
            AND comparison_date = %s
            GROUP BY action_type
            """
            cursor.execute(query_changes, (account['target_account'], today))
            changes = cursor.fetchall()

            account['added_today'] = 0
            account['deleted_today'] = 0

            for change in changes:
                if change['action_type'] == 'added':
                    account['added_today'] = change['count']
                elif change['action_type'] == 'deleted':
                    account['deleted_today'] = change['count']

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
    """API: Changements récents (added/deleted) pour un compte"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        today = datetime.now().strftime('%Y-%m-%d')

        query = """
        SELECT
            username,
            full_name,
            predicted_gender,
            confidence,
            action_type,
            comparison_date
        FROM instagram_comparatif
        WHERE target_account = %s
        AND comparison_date = %s
        AND action_type IN ('added', 'deleted')
        ORDER BY action_type, username
        LIMIT 50
        """
        cursor.execute(query, (account_name, today))
        changes = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'account': account_name,
            'changes': changes,
            'date': today
        })

    except Exception as e:
        logger.error(f"Erreur API recent_changes: {e}")
        if conn:
            conn.close()
        return jsonify({'error': str(e)}), 500


@app.route('/api/account/<account_name>/followings')
def api_followings(account_name):
    """API: Liste complète des followings d'un compte avec pagination"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        # Paramètres de pagination
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        offset = (page - 1) * per_page

        # Filtres
        search = request.args.get('search', '')
        gender_filter = request.args.get('gender', '')
        status_filter = request.args.get('status', '')  # added/present/deleted

        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Construire la requête avec filtres
        where_clauses = ["f.target_account = %s"]
        params = [account_name]

        if search:
            where_clauses.append("(f.username ILIKE %s OR f.full_name ILIKE %s)")
            params.extend([f'%{search}%', f'%{search}%'])

        if gender_filter:
            where_clauses.append("f.predicted_gender = %s")
            params.append(gender_filter)

        # Requête principale avec jointure pour récupérer le status (added/deleted)
        query = f"""
        SELECT
            f.username,
            f.full_name,
            f.predicted_gender,
            f.confidence,
            f.scraping_date,
            COALESCE(c.action_type, 'present') as status
        FROM instagram_followings f
        LEFT JOIN (
            SELECT DISTINCT ON (target_account, username)
                target_account, username, action_type, comparison_date
            FROM instagram_comparatif
            WHERE comparison_date >= (CURRENT_DATE - INTERVAL '7 days')
            ORDER BY target_account, username, comparison_date DESC
        ) c ON f.target_account = c.target_account AND f.username = c.username
        WHERE {' AND '.join(where_clauses)}
        """

        if status_filter:
            if status_filter == 'present':
                query += " AND COALESCE(c.action_type, 'present') = 'present'"
            else:
                query += " AND c.action_type = %s"
                params.append(status_filter)

        query += " ORDER BY f.username LIMIT %s OFFSET %s"
        params.extend([per_page, offset])

        cursor.execute(query, params)
        followings = cursor.fetchall()

        # Compter le total pour la pagination
        count_query = f"""
        SELECT COUNT(*) as total
        FROM instagram_followings f
        LEFT JOIN (
            SELECT DISTINCT ON (target_account, username)
                target_account, username, action_type
            FROM instagram_comparatif
            WHERE comparison_date >= (CURRENT_DATE - INTERVAL '7 days')
            ORDER BY target_account, username, comparison_date DESC
        ) c ON f.target_account = c.target_account AND f.username = c.username
        WHERE {' AND '.join(where_clauses)}
        """

        cursor.execute(count_query, params[:-2])  # Sans LIMIT et OFFSET
        total = cursor.fetchone()['total']

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'account': account_name,
            'followings': followings,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        })

    except Exception as e:
        logger.error(f"Erreur API followings: {e}")
        if conn:
            conn.close()
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats')
def api_stats():
    """API: Statistiques globales"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database connection failed'}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Stats globales
        query = """
        SELECT
            COUNT(DISTINCT target_account) as total_accounts,
            COUNT(*) as total_followings,
            COUNT(CASE WHEN predicted_gender = 'male' THEN 1 END) as total_male,
            COUNT(CASE WHEN predicted_gender = 'female' THEN 1 END) as total_female,
            COUNT(CASE WHEN predicted_gender = 'unknown' THEN 1 END) as total_unknown
        FROM instagram_followings
        """
        cursor.execute(query)
        stats = cursor.fetchone()

        # Changements aujourd'hui (tous comptes confondus)
        today = datetime.now().strftime('%Y-%m-%d')
        query_changes = """
        SELECT
            action_type,
            COUNT(*) as count
        FROM instagram_comparatif
        WHERE comparison_date = %s
        GROUP BY action_type
        """
        cursor.execute(query_changes, (today,))
        changes = cursor.fetchall()

        stats['added_today'] = 0
        stats['deleted_today'] = 0

        for change in changes:
            if change['action_type'] == 'added':
                stats['added_today'] = change['count']
            elif change['action_type'] == 'deleted':
                stats['deleted_today'] = change['count']

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
