#!/usr/bin/env python3
"""
Module pour tracker la qualité des scrapings et détecter les vrais nouveaux followings
"""

import psycopg2
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class ScrapingQualityTracker:
    """Classe pour gérer la qualité des scrapings et détecter les vrais nouveaux"""

    def __init__(self, postgres_config: Dict[str, str]):
        """
        Args:
            postgres_config: Dict avec 'host', 'port', 'database', 'user', 'password'
        """
        self.config = postgres_config

    def get_connection(self):
        """Créer une connexion PostgreSQL"""
        return psycopg2.connect(
            host=self.config['host'],
            port=self.config['port'],
            database=self.config['database'],
            user=self.config['user'],
            password=self.config['password']
        )

    def record_scraping(
        self,
        target_account: str,
        scraping_date: datetime,
        total_followings: int,
        scraping_duration_seconds: Optional[int] = None,
        instagram_reported_total: Optional[int] = None,
        notes: Optional[str] = None
    ) -> Tuple[float, bool]:
        """
        Enregistrer un scraping et calculer son score de qualité

        Args:
            instagram_reported_total: Nombre réel de followings reporté par Instagram (ground truth)

        Returns:
            Tuple[completeness_score, is_complete]
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            # Calculer le score de complétude
            if instagram_reported_total and instagram_reported_total > 0:
                # Utiliser le nombre réel d'Instagram comme référence
                completeness_score = round((total_followings / instagram_reported_total) * 100, 2)
                logger.info(f"Score basé sur Instagram reported: {total_followings}/{instagram_reported_total} = {completeness_score:.1f}%")
            else:
                # Fallback: Utiliser la fonction SQL basée sur l'historique
                cursor.execute("""
                    SELECT calculate_completeness_score(%s, %s)
                """, (target_account, total_followings))
                completeness_score = cursor.fetchone()[0] or 100.0

            # Déterminer si c'est "complet" (>= 90%)
            is_complete = completeness_score >= 90.0

            # Insérer les métadonnées
            cursor.execute("""
                INSERT INTO scraping_metadata (
                    target_account,
                    scraping_date,
                    scraping_timestamp,
                    total_followings,
                    completeness_score,
                    is_complete,
                    scraping_duration_seconds,
                    instagram_reported_total,
                    notes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (target_account, scraping_date, scraping_timestamp)
                DO UPDATE SET
                    total_followings = EXCLUDED.total_followings,
                    completeness_score = EXCLUDED.completeness_score,
                    is_complete = EXCLUDED.is_complete,
                    scraping_duration_seconds = EXCLUDED.scraping_duration_seconds,
                    instagram_reported_total = EXCLUDED.instagram_reported_total,
                    notes = EXCLUDED.notes
            """, (
                target_account,
                scraping_date.date(),
                scraping_date,
                total_followings,
                completeness_score,
                is_complete,
                scraping_duration_seconds,
                instagram_reported_total,
                notes
            ))

            conn.commit()

            logger.info(
                f"📊 Scraping enregistré: {target_account} @ {scraping_date.date()} | "
                f"{total_followings} followings | Score: {completeness_score:.1f}% | "
                f"Complet: {'✅' if is_complete else '⚠️'}"
            )

            return completeness_score, is_complete

        except Exception as e:
            conn.rollback()
            logger.error(f"Erreur enregistrement scraping: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def get_truly_new_followings(
        self,
        target_account: str,
        scraping_date: datetime
    ) -> List[Dict]:
        """
        Obtenir les VRAIS nouveaux followings pour une date
        (robuste aux scrapings incomplets)

        Returns:
            List de dicts avec username, full_name, predicted_gender, is_truly_new, confidence_score
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT * FROM get_new_followings_for_date(%s, %s)
            """, (target_account, scraping_date.date()))

            results = []
            for row in cursor.fetchall():
                results.append({
                    'username': row[0],
                    'full_name': row[1],
                    'predicted_gender': row[2],
                    'is_truly_new': row[3],
                    'confidence_score': float(row[4]) if row[4] else 0.0
                })

            return results

        except Exception as e:
            logger.error(f"Erreur récupération nouveaux followings: {e}")
            return []
        finally:
            cursor.close()
            conn.close()

    def compare_scrapings(
        self,
        target_account: str,
        date1: datetime,
        date2: datetime
    ) -> Dict[str, List[Dict]]:
        """
        Comparer deux scrapings de manière intelligente

        Returns:
            Dict avec 'added', 'removed' et 'confidence'
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT * FROM compare_scrapings_smart(%s, %s, %s)
            """, (target_account, date1.date(), date2.date()))

            added = []
            removed = []
            confidence = None

            for row in cursor.fetchall():
                change = {
                    'username': row[0],
                    'full_name': row[1],
                    'predicted_gender': row[2]
                }

                if row[3] == 'added':
                    added.append(change)
                elif row[3] == 'removed':
                    removed.append(change)

                confidence = row[4]  # Tous ont la même confiance

            return {
                'added': added,
                'removed': removed,
                'confidence': confidence,
                'added_count': len(added),
                'removed_count': len(removed)
            }

        except Exception as e:
            logger.error(f"Erreur comparaison scrapings: {e}")
            return {'added': [], 'removed': [], 'confidence': 'unknown', 'added_count': 0, 'removed_count': 0}
        finally:
            cursor.close()
            conn.close()

    def get_last_complete_scraping(
        self,
        target_account: str,
        before_date: Optional[datetime] = None
    ) -> Optional[Dict]:
        """
        Obtenir les infos du dernier scraping complet

        Returns:
            Dict avec scraping_date, total_followings, completeness_score ou None
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            if before_date:
                cursor.execute("""
                    SELECT scraping_date, total_followings, completeness_score
                    FROM scraping_metadata
                    WHERE target_account = %s
                    AND scraping_date < %s
                    AND is_complete = TRUE
                    ORDER BY scraping_date DESC
                    LIMIT 1
                """, (target_account, before_date.date()))
            else:
                cursor.execute("""
                    SELECT scraping_date, total_followings, completeness_score
                    FROM scraping_metadata
                    WHERE target_account = %s
                    AND is_complete = TRUE
                    ORDER BY scraping_date DESC
                    LIMIT 1
                """, (target_account,))

            row = cursor.fetchone()
            if row:
                return {
                    'scraping_date': row[0],
                    'total_followings': row[1],
                    'completeness_score': float(row[2]) if row[2] else 0.0
                }
            return None

        except Exception as e:
            logger.error(f"Erreur récupération dernier scraping complet: {e}")
            return None
        finally:
            cursor.close()
            conn.close()

    def mark_complete_scrapings(self):
        """Marquer automatiquement les scrapings comme complets si score >= 90%"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT mark_complete_scrapings()")
            conn.commit()
            logger.info("✅ Scrapings complets marqués automatiquement")
        except Exception as e:
            conn.rollback()
            logger.error(f"Erreur marquage scrapings complets: {e}")
        finally:
            cursor.close()
            conn.close()


def example_usage():
    """Exemple d'utilisation du tracker"""

    # Configuration PostgreSQL
    postgres_config = {
        'host': 'postgres',
        'port': '5432',
        'database': 'airflow',
        'user': 'airflow',
        'password': 'airflow'
    }

    tracker = ScrapingQualityTracker(postgres_config)

    # 1. Enregistrer un scraping
    score, is_complete = tracker.record_scraping(
        target_account='mariadlaura',
        scraping_date=datetime.now(),
        total_followings=651,
        scraping_duration_seconds=1200,
        notes='Scraping réussi avec cookies renouvelés'
    )

    print(f"Score de qualité: {score:.1f}%")
    print(f"Complet: {is_complete}")

    # 2. Obtenir les vrais nouveaux
    new_followings = tracker.get_truly_new_followings(
        target_account='mariadlaura',
        scraping_date=datetime.now()
    )

    print(f"\nVrais nouveaux followings: {len(new_followings)}")
    for following in new_followings[:5]:  # Afficher les 5 premiers
        print(f"  - @{following['username']} (confiance: {following['confidence_score']:.1f}%)")

    # 3. Comparer deux scrapings
    comparison = tracker.compare_scrapings(
        target_account='mariadlaura',
        date1=datetime(2025, 11, 23),
        date2=datetime(2025, 11, 24)
    )

    print(f"\nComparaison 23/11 vs 24/11:")
    print(f"  Ajoutés: {comparison['added_count']}")
    print(f"  Supprimés: {comparison['removed_count']}")
    print(f"  Confiance: {comparison['confidence']}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    example_usage()
