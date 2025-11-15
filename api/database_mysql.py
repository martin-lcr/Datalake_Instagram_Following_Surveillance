"""
Gestionnaire de base de données MySQL pour l'API
Adapté pour utiliser MySQL au lieu de PostgreSQL
"""

import sys
from pathlib import Path
from typing import List, Optional
from datetime import datetime, date, timedelta
import logging

import mysql.connector
from mysql.connector import Error

sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Gestionnaire de connexions MySQL"""

    def __init__(self):
        self.conn = None

    def connect(self):
        """Établit la connexion MySQL"""
        try:
            self.conn = mysql.connector.connect(
                host='localhost',
                user='airflow_user',
                password='airflow_password',
                database='instagram_surveillance'
            )
            logger.info("✅ Connexion MySQL établie")
        except Error as e:
            logger.error(f"❌ Erreur connexion MySQL : {e}")

    def close(self):
        """Ferme la connexion"""
        if self.conn and self.conn.is_connected():
            self.conn.close()

    def is_connected(self) -> bool:
        """Vérifie si la connexion est active"""
        return self.conn is not None and self.conn.is_connected()

    # =====================================================================
    # Méthodes pour les Following (table followings dans MySQL)
    # =====================================================================

    def get_following(
        self,
        limit: int = 100,
        offset: int = 0,
        gender: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> List[dict]:
        """Récupère les following avec filtres"""
        query = "SELECT * FROM followings WHERE 1=1"
        params = []

        if gender:
            query += " AND gender = %s"
            params.append(gender)

        if date_from:
            query += " AND DATE(scraped_at) >= %s"
            params.append(date_from)

        if date_to:
            query += " AND DATE(scraped_at) <= %s"
            params.append(date_to)

        query += " ORDER BY scraped_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        return self._execute_query(query, params)

    def get_following_by_username(self, username: str) -> Optional[dict]:
        """Récupère un following par username"""
        query = """
            SELECT * FROM followings
            WHERE follower_username = %s
            ORDER BY scraped_at DESC
            LIMIT 1
        """
        results = self._execute_query(query, [username])
        return results[0] if results else None

    # Alias pour l'API
    def get_followers(self, *args, **kwargs):
        """Alias pour get_following (dans ce cas, followings = les comptes suivis)"""
        return self.get_following(*args, **kwargs)

    def get_follower_by_username(self, username: str):
        """Alias pour get_following_by_username"""
        return self.get_following_by_username(username)

    # =====================================================================
    # Méthodes pour les Daily Diff (non implémenté pour l'instant)
    # =====================================================================

    def get_daily_diff(
        self,
        data_type: Optional[str] = None,
        change_type: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[dict]:
        """Récupère les changements quotidiens (non implémenté)"""
        return []

    def get_latest_diff(self, data_type: Optional[str] = None, limit: int = 50) -> List[dict]:
        """Récupère les derniers changements (non implémenté)"""
        return []

    # =====================================================================
    # Méthodes pour les Statistiques
    # =====================================================================

    def get_overview_stats(self) -> dict:
        """Récupère les statistiques globales"""
        stats = {
            'total_followers': 0,
            'total_following': 0,
            'latest_followers_added': 0,
            'latest_followers_deleted': 0,
            'latest_following_added': 0,
            'latest_following_deleted': 0,
            'last_update': None
        }

        # Total following (tous les comptes suivis)
        query = """
            SELECT COUNT(DISTINCT follower_username) as count, MAX(scraped_at) as last_update
            FROM followings
            WHERE target_account = 'mariadlaura'
        """
        result = self._execute_query_raw(query)
        if result:
            stats['total_following'] = result[0]['count']
            stats['last_update'] = result[0]['last_update']

        return stats

    def get_gender_stats(self, data_type: str = 'following') -> dict:
        """Récupère les statistiques par genre"""
        query = """
            SELECT gender, COUNT(*) as count
            FROM followings
            WHERE target_account = 'mariadlaura'
            GROUP BY gender
        """

        # Utiliser _execute_query_raw pour éviter le mapping
        results = self._execute_query_raw(query)

        stats = {
            'data_type': data_type,
            'total': 0,
            'by_gender': {'male': 0, 'female': 0, 'unknown': 0},
            'percentages': {}
        }

        for row in results:
            gender = row['gender']
            count = row['count']
            stats['by_gender'][gender] = count
            stats['total'] += count

        # Calculer les pourcentages
        if stats['total'] > 0:
            for gender, count in stats['by_gender'].items():
                stats['percentages'][gender] = round((count / stats['total']) * 100, 2)

        return stats

    def get_timeline_stats(self, days: int = 30) -> dict:
        """Récupère l'évolution sur une période"""
        start_date = (datetime.now() - timedelta(days=days)).date()

        # Évolution des following
        query = """
            SELECT DATE(scraped_at) as date, COUNT(DISTINCT follower_username) as count
            FROM followings
            WHERE target_account = 'mariadlaura' AND DATE(scraped_at) >= %s
            GROUP BY DATE(scraped_at)
            ORDER BY date
        """
        following_timeline = self._execute_query_raw(query, [start_date])

        return {
            'followers': [],
            'following': following_timeline
        }

    # =====================================================================
    # Méthode de recherche
    # =====================================================================

    def search_users(self, query: str, data_type: Optional[str] = None, limit: int = 20) -> dict:
        """Recherche des utilisateurs"""
        sql = """
            SELECT * FROM followings
            WHERE (follower_username LIKE %s OR follower_fullname LIKE %s)
                AND target_account = 'mariadlaura'
            ORDER BY follower_username
            LIMIT %s
        """
        search_pattern = f"%{query}%"
        results = self._execute_query(sql, [search_pattern, search_pattern, limit])

        return {
            'followers': [],
            'following': results
        }

    # =====================================================================
    # Méthodes utilitaires
    # =====================================================================

    def _execute_query_raw(self, query: str, params: list = None) -> List[dict]:
        """Exécute une requête SQL et retourne les résultats bruts (sans mapping)"""
        try:
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute(query, params or [])
            results = cursor.fetchall()
            cursor.close()
            return results
        except Error as e:
            logger.error(f"❌ Erreur requête SQL : {e}")
            return []

    def _execute_query(self, query: str, params: list = None) -> List[dict]:
        """Exécute une requête SQL et retourne les résultats"""
        try:
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute(query, params or [])
            results = cursor.fetchall()
            cursor.close()

            # Mapper les colonnes MySQL vers les noms attendus par l'API
            mapped_results = []
            for row in results:
                mapped_row = {
                    'username': row.get('follower_username'),
                    'full_name': row.get('follower_fullname'),
                    'predicted_gender': row.get('gender', 'unknown'),
                    'confidence': row.get('gender_confidence', 0.0),
                    'scraped_at': row.get('scraped_at'),
                    'target_account': row.get('target_account'),
                    'is_private': None,  # Pas dans la base MySQL
                    'is_verified': None,  # Pas dans la base MySQL
                    'follower_count': None  # Pas dans la base MySQL
                }
                mapped_results.append(mapped_row)

            return mapped_results
        except Error as e:
            logger.error(f"❌ Erreur requête SQL : {e}")
            return []
