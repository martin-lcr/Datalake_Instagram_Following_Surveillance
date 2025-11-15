#!/usr/bin/env python3
"""
API FastAPI pour exposer les données de surveillance Instagram
100% GRATUIT - Pas de services payants
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Optional
from datetime import datetime, date
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.models import (
    FollowerRecord,
    FollowingRecord,
    DailyDiffRecord,
    StatsResponse,
    GenderStatsResponse
)
# Utiliser la version MySQL au lieu de PostgreSQL
from api.database_mysql import DatabaseManager

# Initialisation de l'API
app = FastAPI(
    title="Instagram Surveillance API",
    description="API gratuite pour surveiller les followers/following Instagram",
    version="1.0.0"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gestionnaire de base de données
db = DatabaseManager()

# Monter le répertoire static pour servir le dashboard
static_path = Path(__file__).parent / "static"
static_path.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


@app.on_event("startup")
async def startup_event():
    """Initialisation au démarrage"""
    db.connect()


@app.on_event("shutdown")
async def shutdown_event():
    """Nettoyage à l'arrêt"""
    db.close()


# =========================================================================
# Endpoints - Followers
# =========================================================================

@app.get("/api/followers", response_model=List[FollowerRecord])
async def get_followers(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    gender: Optional[str] = Query(None, regex="^(male|female|unknown)$"),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None
):
    """
    Récupère la liste des followers

    - **limit**: Nombre de résultats (max 1000)
    - **offset**: Décalage pour la pagination
    - **gender**: Filtrer par genre (male, female, unknown)
    - **date_from**: Date de début (YYYY-MM-DD)
    - **date_to**: Date de fin (YYYY-MM-DD)
    """
    return db.get_followers(
        limit=limit,
        offset=offset,
        gender=gender,
        date_from=date_from,
        date_to=date_to
    )


@app.get("/api/followers/{username}", response_model=FollowerRecord)
async def get_follower(username: str):
    """Récupère les informations d'un follower spécifique"""
    follower = db.get_follower_by_username(username)
    if not follower:
        raise HTTPException(status_code=404, detail="Follower non trouvé")
    return follower


# =========================================================================
# Endpoints - Following
# =========================================================================

@app.get("/api/following", response_model=List[FollowingRecord])
async def get_following(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    gender: Optional[str] = Query(None, regex="^(male|female|unknown)$"),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None
):
    """
    Récupère la liste des following (comptes suivis)

    - **limit**: Nombre de résultats (max 1000)
    - **offset**: Décalage pour la pagination
    - **gender**: Filtrer par genre (male, female, unknown)
    - **date_from**: Date de début (YYYY-MM-DD)
    - **date_to**: Date de fin (YYYY-MM-DD)
    """
    return db.get_following(
        limit=limit,
        offset=offset,
        gender=gender,
        date_from=date_from,
        date_to=date_to
    )


@app.get("/api/following/{username}", response_model=FollowingRecord)
async def get_following_user(username: str):
    """Récupère les informations d'un compte suivi spécifique"""
    following = db.get_following_by_username(username)
    if not following:
        raise HTTPException(status_code=404, detail="Compte suivi non trouvé")
    return following


# =========================================================================
# Endpoints - Daily Diff (Changements quotidiens)
# =========================================================================

@app.get("/api/diff/daily", response_model=List[DailyDiffRecord])
async def get_daily_diff(
    data_type: Optional[str] = Query(None, regex="^(followers|following)$"),
    change_type: Optional[str] = Query(None, regex="^(added|deleted)$"),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """
    Récupère les changements quotidiens (ajouts/suppressions)

    - **data_type**: Type de données (followers ou following)
    - **change_type**: Type de changement (added ou deleted)
    - **date_from**: Date de début
    - **date_to**: Date de fin
    - **limit**: Nombre de résultats
    - **offset**: Décalage pour la pagination
    """
    return db.get_daily_diff(
        data_type=data_type,
        change_type=change_type,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset
    )


@app.get("/api/diff/latest", response_model=List[DailyDiffRecord])
async def get_latest_diff(
    data_type: Optional[str] = Query(None, regex="^(followers|following)$"),
    limit: int = Query(50, ge=1, le=500)
):
    """
    Récupère les derniers changements

    - **data_type**: Type de données (followers ou following)
    - **limit**: Nombre de résultats
    """
    return db.get_latest_diff(data_type=data_type, limit=limit)


# =========================================================================
# Endpoints - Statistiques
# =========================================================================

@app.get("/api/stats/overview", response_model=StatsResponse)
async def get_stats_overview():
    """
    Récupère les statistiques globales

    Retourne le nombre total de followers, following, et les changements récents
    """
    return db.get_overview_stats()


@app.get("/api/stats/gender", response_model=GenderStatsResponse)
async def get_gender_stats(
    data_type: str = Query("followers", regex="^(followers|following)$")
):
    """
    Récupère les statistiques par genre

    - **data_type**: Type de données (followers ou following)

    Retourne la répartition par genre et les statistiques associées
    """
    return db.get_gender_stats(data_type)


@app.get("/api/stats/timeline")
async def get_timeline_stats(
    days: int = Query(30, ge=1, le=365)
):
    """
    Récupère l'évolution du nombre de followers/following sur une période

    - **days**: Nombre de jours à afficher (max 365)

    Retourne les données pour créer des graphiques d'évolution
    """
    return db.get_timeline_stats(days)


# =========================================================================
# Endpoints - Recherche
# =========================================================================

@app.get("/api/search")
async def search_users(
    query: str = Query(..., min_length=2),
    data_type: Optional[str] = Query(None, regex="^(followers|following)$"),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Recherche des utilisateurs par nom ou username

    - **query**: Texte à rechercher (min 2 caractères)
    - **data_type**: Limiter à followers ou following
    - **limit**: Nombre de résultats
    """
    return db.search_users(query, data_type, limit)


# =========================================================================
# Endpoint - Health Check
# =========================================================================

@app.get("/health")
async def health_check():
    """Vérification de l'état de l'API"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": "connected" if db.is_connected() else "disconnected"
    }


@app.get("/")
async def root():
    """Redirection vers le dashboard"""
    return RedirectResponse(url="/dashboard")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Page du dashboard visuel"""
    dashboard_file = Path(__file__).parent / "static" / "surveillance_dashboard.html"
    if dashboard_file.exists():
        with open(dashboard_file, 'r', encoding='utf-8') as f:
            return f.read()
    return """
    <html>
        <body>
            <h1>Dashboard non trouvé</h1>
            <p>Veuillez vérifier que le fichier surveillance_dashboard.html existe dans api/static/</p>
            <p><a href="/docs">Documentation API</a></p>
        </body>
    </html>
    """


@app.get("/api/accounts")
async def get_accounts():
    """Liste des comptes surveillés avec statistiques"""
    try:
        # Lire les comptes depuis le fichier
        accounts_file = Path(__file__).parent.parent / "scripts" / "instagram_accounts_to_scrape.txt"

        if not accounts_file.exists():
            print(f"Fichier non trouvé: {accounts_file}")
            return []

        with open(accounts_file, 'r') as f:
            account_names = [line.strip() for line in f if line.strip()]

        if not account_names:
            print("Aucun compte trouvé dans le fichier")
            return []

        # Connexion à PostgreSQL (Docker)
        import psycopg2
        conn = psycopg2.connect(
            host="localhost",
            port=5433,
            database="airflow",
            user="airflow",
            password="airflow"
        )
        cursor = conn.cursor()

        accounts = []
        for account_name in account_names:
            # Normaliser le nom du compte pour le nom de table
            normalized_account = account_name.replace(".", "-").replace("_", "-")
            table_name = f"instagram_data_{normalized_account}"

            # Vérifier si la table existe
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = %s
                )
            """, (table_name,))

            table_exists = cursor.fetchone()[0]

            if table_exists:
                # Compter les followings pour ce compte
                cursor.execute(f"""
                    SELECT COUNT(DISTINCT username)
                    FROM {table_name}
                """)
                total = cursor.fetchone()[0]
            else:
                total = 0

            accounts.append({
                "name": account_name,
                "total_followings": total
            })

        cursor.close()
        conn.close()

        return accounts
    except Exception as e:
        print(f"Erreur: {e}")
        import traceback
        traceback.print_exc()
        return []


@app.get("/api/account/{account_name}/comparatif")
async def get_account_comparatif(account_name: str):
    """Récupère les données comparatives pour un compte (avec status)"""
    try:
        import psycopg2

        # Normaliser le nom du compte
        normalized_account = account_name.replace(".", "-").replace("_", "-")

        conn = psycopg2.connect(
            host="localhost",
            port=5433,
            database="airflow",
            user="airflow",
            password="airflow"
        )
        cursor = conn.cursor()

        # Vérifier si la table comparatif existe
        table_name_comparatif = f"instagram_data_{normalized_account}_comparatif"
        table_name_main = f"instagram_data_{normalized_account}"

        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = %s
            )
        """, (table_name_comparatif,))

        table_exists = cursor.fetchone()[0]

        if table_exists:
            # Récupérer TOUS les followings avec leur status (un seul enregistrement par username)
            # Combine la table principale (followings actuels) avec la table comparatif (changements)
            cursor.execute(f"""
                WITH latest_followings AS (
                    -- Obtenir la ligne la plus récente pour chaque username
                    SELECT DISTINCT ON (username)
                        username,
                        full_name,
                        predicted_gender,
                        confidence,
                        scraped_at
                    FROM {table_name_main}
                    ORDER BY username, scraped_at DESC
                )
                -- Tous les followings actuels avec leur status
                SELECT
                    m.username,
                    m.full_name,
                    m.predicted_gender,
                    m.confidence,
                    COALESCE(c.change, 'present') as status,
                    m.scraped_at
                FROM latest_followings m
                LEFT JOIN {table_name_comparatif} c
                    ON m.username = c.username

                UNION ALL

                -- Les followings supprimés (uniquement dans comparatif)
                SELECT
                    c.username,
                    c.full_name,
                    c.predicted_gender,
                    c.confidence,
                    c.change as status,
                    NULL as scraped_at
                FROM {table_name_comparatif} c
                WHERE c.change = 'deleted'
                    AND c.username NOT IN (SELECT username FROM {table_name_main})

                ORDER BY username
            """)

            data = []
            for row in cursor.fetchall():
                # Gérer scraped_at qui peut être une string, datetime ou None
                scraped_at = row[5]
                if scraped_at is None:
                    scraped_at_str = "2025-11-15T00:00:00"
                elif isinstance(scraped_at, str):
                    scraped_at_str = scraped_at
                else:
                    scraped_at_str = scraped_at.isoformat()

                data.append({
                    "username": row[0],
                    "fullname": row[1] if row[1] else "",
                    "gender": row[2] if row[2] else "unknown",
                    "confidence": float(row[3]) if row[3] else 0.5,
                    "status": row[4] if row[4] else "present",
                    "scraped_at": scraped_at_str
                })
        else:
            # Fallback sur la table principale sans status
            cursor.execute(f"""
                SELECT DISTINCT username, full_name, predicted_gender, confidence, scraped_at
                FROM {table_name_main}
                ORDER BY username
            """)

            data = []
            for row in cursor.fetchall():
                data.append({
                    "username": row[0],
                    "fullname": row[1] if row[1] else "",
                    "gender": row[2] if row[2] else "unknown",
                    "confidence": float(row[3]) if row[3] else 0.5,
                    "status": "present",
                    "scraped_at": row[4].isoformat() if row[4] else "2025-11-15T00:00:00"
                })

        cursor.close()
        conn.close()

        return data
    except Exception as e:
        print(f"Erreur: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    from config import API_CONFIG

    uvicorn.run(
        app,
        host=API_CONFIG['host'],
        port=API_CONFIG['port'],
        log_level="info"
    )
