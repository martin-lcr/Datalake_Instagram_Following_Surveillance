"""
Configuration centralisée pour le projet Instagram Surveillance
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Chemins de base
BASE_DIR = Path(__file__).parent
DATA_DIR = Path(os.getenv('DATA_DIR', BASE_DIR / 'data'))
LOGS_DIR = Path(os.getenv('LOGS_DIR', BASE_DIR / 'logs'))

# Créer les répertoires s'ils n'existent pas
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Configuration Instagram
INSTAGRAM_USERNAME = os.getenv('INSTAGRAM_USERNAME')
INSTAGRAM_PASSWORD = os.getenv('INSTAGRAM_PASSWORD')
TARGET_INSTAGRAM_ACCOUNT = os.getenv('TARGET_INSTAGRAM_ACCOUNT', 'mariadlaura')
SESSION_FILE = BASE_DIR / '.instagram_session'

# Configuration PostgreSQL
POSTGRES_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', 5432)),
    'database': os.getenv('POSTGRES_DB', 'airflow'),
    'user': os.getenv('POSTGRES_USER', 'airflow'),
    'password': os.getenv('POSTGRES_PASSWORD', 'airflow'),
}

POSTGRES_JDBC_URL = (
    f"jdbc:postgresql://{POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}"
    f"/{POSTGRES_CONFIG['database']}"
)

# Configuration Elasticsearch
ELASTICSEARCH_CONFIG = {
    'host': os.getenv('ELASTICSEARCH_HOST', 'localhost'),
    'port': int(os.getenv('ELASTICSEARCH_PORT', 9200)),
}

# Configuration de l'API
API_CONFIG = {
    'host': os.getenv('API_HOST', '0.0.0.0'),
    'port': int(os.getenv('API_PORT', 8000)),
}

# Noms des tables/index
TABLES = {
    'followers': 'instagram_followers',
    'following': 'instagram_following',
    'daily_diff': 'instagram_daily_diff',
}

# Index Elasticsearch
ES_INDICES = {
    'followers': 'instagram_followers',
    'following': 'instagram_following',
    'daily_diff': 'instagram_daily_diff',
}
