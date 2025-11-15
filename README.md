# 🔍 Instagram Following Surveillance Pipeline

> Pipeline automatisé 100% GRATUIT avec scraping multi-passes, détection de genre par IA et stockage multi-couches

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Airflow](https://img.shields.io/badge/Airflow-2.8+-orange.svg)](https://airflow.apache.org/)
[![Selenium](https://img.shields.io/badge/Selenium-4.0+-green.svg)](https://www.selenium.dev/)
[![Spark](https://img.shields.io/badge/Spark-3.5+-red.svg)](https://spark.apache.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 📋 Table des matières

- [Fonctionnalités](#-fonctionnalités)
- [Architecture](#-architecture)
- [Prérequis](#-prérequis)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Utilisation](#-utilisation)
- [API](#-api)
- [Dashboards Kibana](#-dashboards-kibana)
- [Troubleshooting](#-troubleshooting)

---

## ✨ Fonctionnalités

- ✅ **Scraping multi-passes** avec Selenium (5 passes, déduplication automatique, 698+ followings uniques)
- ✅ **Extraction robuste** des fullnames (4 méthodes de fallback, taux 85-95%)
- ✅ **Automatisation** avec Apache Airflow (exécution parallèle multi-comptes)
- ✅ **Détection de genre par IA** (gender-guesser avec confiance 0-1)
- ✅ **Comparaisons temporelles** (détection ajouts/suppressions entre exécutions)
- ✅ **Stockage multi-couches** : RAW (JSON) → FORMATTED (Parquet) → USAGE (horodaté) → COMBINED (agrégé)
- ✅ **Base de données** PostgreSQL + Elasticsearch
- ✅ **Dashboards Kibana** pour visualisation analytics
- ✅ **Traitement Big Data** avec Apache Spark + PySpark

---

## 🏗️ Architecture

```
instagram_accounts_to_scrape.txt (mariadlaura, le.corre_en.longueur)
                    │
                    ▼
┌────────────────────────────────────────────────────────┐
│         AIRFLOW DAG (Orchestration quotidienne)        │
│      scraping_surveillance_dag.py - @daily             │
└────────────────────────────────────────────────────────┘
                    │
    ┌───────────────┴───────────────┐
    │ 1. Génération Scripts         │ (Un script par compte)
    └───────────────┬───────────────┘
                    │
    ┌───────────────┴───────────────┐
    │ 2. Scraping Multi-Passes      │ (Parallèle - 5 passes chacun)
    │    scrape_user_multipass_v2   │
    │    ├─ Selenium Stealth         │
    │    ├─ 4 méthodes extraction    │
    │    └─ Déduplication Set Union  │
    └───────────────┬───────────────┘
                    │
    ┌───────────────┴───────────────┐
    │ 3. Traitement + ML + Stockage │ (Spark-submit)
    │    script_scraping_to_spark    │
    │    ├─ Détection Genre (ML)     │
    │    ├─ RAW (JSON)               │
    │    ├─ FORMATTED (Parquet)      │
    │    ├─ USAGE (Parquet horodaté) │
    │    └─ Comparaison temporelle   │
    └───────────────┬───────────────┘
                    │
    ┌───────────────┴───────────────┐
    │ 4. Agrégation Multi-Comptes   │
    │    ├─ final_aggregated         │
    │    ├─ final_comparatif         │
    │    └─ final_global_comparatif  │
    └───────────────┬───────────────┘
                    │
         ┌──────────┴──────────┐
         ▼                     ▼
┌─────────────────┐  ┌─────────────────┐
│   PostgreSQL    │  │ Elasticsearch   │
│  ├─ final_      │  │  ├─ instagram_  │
│  │  aggregated  │  │  │  scraping_   │
│  └─ final_      │  │  │  aggregated  │
│     comparatif  │  │  └─ instagram_  │
│                 │  │     scraping_   │
│                 │  │     comparatif  │
└────────┬────────┘  └────────┬────────┘
         │                    │
         └──────────┬─────────┘
                    ▼
         ┌─────────────────┐
         │     Kibana      │
         │   Dashboards    │
         │  ├─ Overview    │
         │  ├─ Changes     │
         │  └─ Gender ML   │
         └─────────────────┘
```

---

## 📦 Prérequis

### Logiciels nécessaires

- **Python 3.8+**
- **Apache Airflow 2.8+**
- **PostgreSQL 12+**
- **Elasticsearch 8.x**
- **Kibana 8.x**
- **Apache Spark 3.5+** (avec PySpark)
- **Java 8+** (pour Spark)

### Compte Instagram

Vous avez besoin d'un compte Instagram (gratuit) pour effectuer le scraping. **Recommandation** : Utilisez un compte secondaire pour éviter tout blocage.

---

## 🚀 Installation

### 1. Cloner le projet

```bash
cd /home/timor/Datalake_Instagram_Following_Surveillance
```

### 2. Installer les dépendances Python

```bash
pip install -r requirements.txt
```

### 3. Configuration de l'environnement

```bash
# Copier le fichier d'exemple
cp .env.example .env

# Éditer le fichier .env avec vos credentials
nano .env
```

**Fichier `.env` à compléter :**

```bash
INSTAGRAM_USERNAME=votre_username
INSTAGRAM_PASSWORD=votre_password
TARGET_INSTAGRAM_ACCOUNT=mariadlaura

POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=airflow
POSTGRES_USER=airflow
POSTGRES_PASSWORD=airflow

ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200
```

### 4. Télécharger les JARs nécessaires

```bash
mkdir -p jars
cd jars

# PostgreSQL JDBC Driver
wget https://jdbc.postgresql.org/download/postgresql-42.2.27.jar

# Elasticsearch-Spark Connector
wget https://repo1.maven.org/maven2/org/elasticsearch/elasticsearch-spark-30_2.12/8.5.3/elasticsearch-spark-30_2.12-8.5.3.jar

cd ..
```

### 5. Configurer les bases de données

```bash
# Lancer PostgreSQL (si pas déjà lancé)
sudo systemctl start postgresql

# Lancer Elasticsearch
sudo systemctl start elasticsearch

# Créer les tables et index
python scripts/setup_database.py
```

### 6. Initialiser Airflow

```bash
# Initialiser la base de données Airflow
airflow db init

# Créer un utilisateur admin
airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password admin

# Copier le DAG dans le dossier Airflow
cp airflow/dags/instagram_surveillance_dag.py ~/airflow/dags/
```

---

## ⚙️ Configuration

### Modifier le compte cible

Pour surveiller un autre compte Instagram, modifiez la variable `TARGET_INSTAGRAM_ACCOUNT` dans le fichier `.env` :

```bash
TARGET_INSTAGRAM_ACCOUNT=autre_compte
```

### Modifier la fréquence de scraping

Éditez le fichier [airflow/dags/instagram_surveillance_dag.py](airflow/dags/instagram_surveillance_dag.py:54) :

```python
schedule_interval='0 2 * * *',  # Tous les jours à 2h du matin
```

Exemples de schedule :
- `'0 */6 * * *'` : Toutes les 6 heures
- `'0 0 * * 0'` : Tous les dimanches à minuit
- `'@daily'` : Une fois par jour

---

## 🎯 Utilisation

### Lancer le pipeline complet

#### 1. Démarrer les services

```bash
# Terminal 1 : Airflow Webserver
airflow webserver --port 8080

# Terminal 2 : Airflow Scheduler
airflow scheduler

# Terminal 3 : API FastAPI
cd api
python main.py
```

#### 2. Activer le DAG

1. Ouvrez `http://localhost:8080` dans votre navigateur
2. Connectez-vous avec `admin` / `admin`
3. Activez le DAG `instagram_surveillance_pipeline`
4. (Optionnel) Cliquez sur "Trigger DAG" pour lancer immédiatement

#### 3. Vérifier l'exécution

Les logs sont disponibles dans :
- **Airflow UI** : `http://localhost:8080`
- **Fichiers logs** : `~/airflow/logs/`

### Tester le scraping manuellement

```bash
# Scraper uniquement les followers
python scripts/instagram_scraper.py mariadlaura --type followers

# Scraper uniquement les following
python scripts/instagram_scraper.py mariadlaura --type following

# Scraper les deux
python scripts/instagram_scraper.py mariadlaura --type both
```

### Tester la détection de genre

```bash
python scripts/gender_detector.py
```

---

## 🌐 API

L'API FastAPI expose les données via REST.

### Démarrer l'API

```bash
cd api
python main.py
```

L'API sera accessible sur `http://localhost:8000`

### Documentation interactive

- **Swagger UI** : `http://localhost:8000/docs`
- **ReDoc** : `http://localhost:8000/redoc`

### Endpoints principaux

#### Followers

```bash
# Liste des followers
GET /api/followers?limit=100&gender=female

# Détails d'un follower
GET /api/followers/{username}
```

#### Following

```bash
# Liste des following
GET /api/following?limit=100&gender=male

# Détails d'un following
GET /api/following/{username}
```

#### Changements quotidiens

```bash
# Derniers changements
GET /api/diff/latest?data_type=followers

# Changements par période
GET /api/diff/daily?date_from=2025-01-01&date_to=2025-01-31
```

#### Statistiques

```bash
# Vue d'ensemble
GET /api/stats/overview

# Stats par genre
GET /api/stats/gender?data_type=followers

# Évolution temporelle
GET /api/stats/timeline?days=30
```

#### Recherche

```bash
# Rechercher un utilisateur
GET /api/search?query=marie&data_type=followers
```

### Exemples avec curl

```bash
# Obtenir les statistiques globales
curl http://localhost:8000/api/stats/overview

# Filtrer les followers féminins
curl "http://localhost:8000/api/followers?gender=female&limit=50"

# Voir les derniers ajouts
curl "http://localhost:8000/api/diff/latest?data_type=followers"
```

---

## 📊 Dashboards Kibana

### Accéder à Kibana

```bash
# Démarrer Kibana
sudo systemctl start kibana

# Ou avec Docker
docker run -p 5601:5601 -e "ELASTICSEARCH_HOSTS=http://localhost:9200" kibana:8.11.0
```

Accédez à `http://localhost:5601`

### Configuration des dashboards

Suivez le guide détaillé : [kibana/setup_kibana.md](kibana/setup_kibana.md)

### Dashboards disponibles

1. **Vue d'ensemble** : Métriques clés, évolution temporelle
2. **Changements quotidiens** : Ajouts/suppressions par jour
3. **Analyse de genre** : Répartition et statistiques par genre

---

## 🔧 Troubleshooting

### Erreur de connexion Instagram

**Problème** : `LoginRequiredException` ou blocage temporaire

**Solutions** :
1. Utilisez un compte secondaire
2. Attendez quelques heures avant de réessayer
3. Activez l'authentification à deux facteurs sur Instagram
4. Utilisez le fichier de session pour éviter de se reconnecter

```bash
# Réutiliser la session
python scripts/instagram_scraper.py mariadlaura --session ~/.instagram_session
```

### Erreur PostgreSQL

**Problème** : `psycopg2.OperationalError: could not connect`

**Solutions** :
```bash
# Vérifier que PostgreSQL est lancé
sudo systemctl status postgresql

# Redémarrer PostgreSQL
sudo systemctl restart postgresql

# Vérifier les credentials dans .env
```

### Erreur Elasticsearch

**Problème** : `ConnectionError: Connection refused`

**Solutions** :
```bash
# Vérifier qu'Elasticsearch est lancé
curl http://localhost:9200

# Redémarrer Elasticsearch
sudo systemctl restart elasticsearch

# Vérifier les logs
tail -f /var/log/elasticsearch/elasticsearch.log
```

### Erreur Spark

**Problème** : `java.lang.OutOfMemoryError`

**Solutions** :
```bash
# Augmenter la mémoire Spark
export SPARK_DRIVER_MEMORY=4g
export SPARK_EXECUTOR_MEMORY=4g
```

### Airflow DAG ne se lance pas

**Solutions** :
1. Vérifiez les logs : `tail -f ~/airflow/logs/scheduler/latest/*.log`
2. Testez le DAG : `airflow dags test instagram_surveillance_pipeline`
3. Vérifiez les paths dans le DAG (BASE_DIR, etc.)

---

## 📁 Structure du projet

```
.
├── airflow/
│   └── dags/
│       └── instagram_surveillance_dag.py  # DAG principal
├── api/
│   ├── main.py                            # API FastAPI
│   ├── models.py                          # Modèles Pydantic
│   └── database.py                        # Gestionnaire DB
├── scripts/
│   ├── instagram_scraper.py               # Scraper Instagram
│   ├── gender_detector.py                 # Détection de genre ML
│   ├── data_processor.py                  # Traitement Spark
│   └── setup_database.py                  # Setup DB
├── kibana/
│   ├── dashboards_config.json             # Config dashboards
│   └── setup_kibana.md                    # Guide Kibana
├── data/                                  # Données (généré auto)
│   ├── raw/                               # Données brutes
│   ├── formatted/                         # Données formatées
│   └── usage/                             # Données finales
├── jars/                                  # JARs Spark
├── config.py                              # Configuration globale
├── .env.example                           # Template variables env
├── requirements.txt                       # Dépendances Python
└── README.md                              # Ce fichier
```

---

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à :
- Ouvrir une issue pour signaler un bug
- Proposer de nouvelles fonctionnalités
- Soumettre des pull requests

---

## 📝 License

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

---

## ⚠️ Avertissements

- **Respect des CGU Instagram** : Ce projet est à usage éducatif. Respectez les conditions d'utilisation d'Instagram.
- **Rate Limiting** : Ne scrapez pas trop fréquemment pour éviter les blocages.
- **Données personnelles** : Traitez les données conformément au RGPD.
- **Sécurité** : Ne commitez JAMAIS vos credentials Instagram dans Git.

---

## 📧 Contact

Pour toute question ou suggestion, ouvrez une issue sur GitHub.

---

**Bon scraping ! 🚀**
