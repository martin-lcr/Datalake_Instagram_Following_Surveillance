from airflow import DAG
from airflow.decorators import task
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from datetime import datetime, timedelta
import pendulum
import os
import re
import subprocess
import glob

# -------------------------------------------------------------------------
# Configuration et constantes
# -------------------------------------------------------------------------

# Répertoire de travail Airflow (où sont montés les volumes Docker)
BASE_DIR = "/opt/airflow"
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
ACCOUNTS_FILE = os.path.join(BASE_DIR, "instagram_accounts_to_scrape.txt")  # Fichier à la racine
UNIFIED_SCRIPT = os.path.join(SCRIPTS_DIR, "instagram_scraping_ml_pipeline.py")
JARS_PATH = "/opt/airflow/jars/postgresql-42.2.27.jar"  # Jar PostgreSQL
ES_SPARK_JAR = "/opt/airflow/jars/elasticsearch-spark-30_2.12-8.11.0.jar"  # Jar ES (Scala 2.12)
DATA_DIR = os.path.join(BASE_DIR, "data")  # Répertoire de données

# Configuration base de données (Docker-compatible)
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")  # Nom du service Docker
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "airflow")
POSTGRES_USER = os.getenv("POSTGRES_USER", "airflow")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "airflow")

# Configuration Elasticsearch (Docker-compatible)
ELASTICSEARCH_HOST = os.getenv("ELASTICSEARCH_HOST", "elasticsearch")
ELASTICSEARCH_PORT = os.getenv("ELASTICSEARCH_PORT", "9200")

# Exemple d'ancien snapshot pour comparaison globale (optionnel)
OLD_PARQUET_PATH = os.path.join(
    DATA_DIR,
    "usage_to_combined",
    "scraping",
    "instagram_data",
    "20250228",
    "1243",
    "final_aggregated.parquet"
)

default_args = {
    'owner': 'instagram_surveillance',
    'start_date': days_ago(1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Note: Le timezone Europe/Paris est configuré via AIRFLOW__CORE__DEFAULT_TIMEZONE dans docker-compose.yml
dag = DAG(
    'instagram_scraping_surveillance_pipeline',
    default_args=default_args,
    description='Pipeline de surveillance Instagram ~4h (6x/jour) avec 3 passes + délais aléatoires + agrégation à 23h',
    schedule_interval='0 2,6,10,14,18,23 * * *',  # Déclenchement à 2h, 6h, 10h, 14h, 18h, 23h puis délai aléatoire pour variation quotidienne
    catchup=False,
    tags=['instagram', 'scraping', 'ml', 'surveillance']
)

# -------------------------------------------------------------------------
# Tâche 1 : LECTURE DES COMPTES À SCRAPER (TaskFlow)
# -------------------------------------------------------------------------
@task
def read_accounts():
    """
    Lit le fichier ACCOUNTS_FILE et retourne une liste de dictionnaires
    contenant les informations de compte pour chaque username à scraper.
    """
    # Vérifier que le script unifié existe
    if not os.path.exists(UNIFIED_SCRIPT):
        raise FileNotFoundError(f"Script unifié introuvable : {UNIFIED_SCRIPT}")

    # Lire les comptes à scraper
    if not os.path.exists(ACCOUNTS_FILE):
        raise FileNotFoundError(f"Fichier des comptes introuvable : {ACCOUNTS_FILE}")

    with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
        accounts = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    if not accounts:
        raise ValueError(f"Aucun compte trouvé dans {ACCOUNTS_FILE}")

    print(f"📋 [read_accounts] Comptes détectés : {accounts}")

    account_list = []
    for account in accounts:
        # Normalisation du nom de compte (remplacer . et _ par -)
        normalized = account.replace(".", "-").replace("_", "-")

        account_list.append({
            "account": account,
            "normalized": normalized
        })

        print(f"✅ [read_accounts] Compte ajouté : @{account} (normalisé: {normalized})")

    print(f"✅ [read_accounts] {len(account_list)} comptes à scraper")
    return account_list

# -------------------------------------------------------------------------
# Tâche 2 : EXÉCUTION DU SCRAPING EN PARALLÈLE (TaskFlow avec Mapping)
# -------------------------------------------------------------------------
@task(max_active_tis_per_dag=1)  # Une seule tâche à la fois pour éviter conflits Selenium
def run_single_account_scraping(account_info: dict):
    """
    Exécute le script unifié de scraping pour un compte Instagram.
    Le script intègre : scraping multi-passes + ML + stockage multi-couches.

    ⚠️ Délai aléatoire de 0-45min ajouté au démarrage pour éviter la détection Instagram
    """
    import sys
    import time
    import random

    account = account_info['account']

    # Délai aléatoire de 0 à 45 minutes pour éviter détection Instagram
    random_delay_seconds = random.randint(0, 45 * 60)  # 0 à 2700 secondes (45 minutes)
    random_delay_minutes = random_delay_seconds // 60
    random_delay_remaining = random_delay_seconds % 60

    print(f"⏰ [Anti-détection] Délai aléatoire appliqué : {random_delay_minutes}min {random_delay_remaining}s")
    print(f"⏰ [Anti-détection] Démarrage réel prévu à : {datetime.now() + timedelta(seconds=random_delay_seconds)}")
    time.sleep(random_delay_seconds)

    print(f"🌀 [run_single_account_scraping] Démarrage scraping pour @{account}...")

    # Commande pour exécuter le script unifié avec l'account en paramètre
    command = f"{sys.executable} {UNIFIED_SCRIPT} {account}"
    print(f"🌀 [run_single_account_scraping] Commande : {command}")
    print(f"🐍 [run_single_account_scraping] Python: {sys.executable} (version {sys.version.split()[0]})")

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=7200  # Timeout 2 heures (scraping peut être long)
        )

        print(f"📊 [run_single_account_scraping] Sortie pour @{account} :")
        print(result.stdout)

        if result.returncode != 0:
            print(f"❌ [run_single_account_scraping] Erreur pour @{account}")
            print(f"❌ Stderr : {result.stderr}")
            raise Exception(f"Scraping failed for {account} with return code {result.returncode}")

        print(f"✅ [run_single_account_scraping] Scraping terminé avec succès pour @{account}")

    except subprocess.TimeoutExpired:
        print(f"❌ [run_single_account_scraping] Timeout dépassé pour @{account}")
        raise
    except Exception as e:
        print(f"❌ [run_single_account_scraping] Erreur pour @{account} : {e}")
        raise

    return account_info

# -------------------------------------------------------------------------
# Tâche 3 : AGRÉGATION DES RÉSULTATS + CHARGEMENT EN BDD (PythonOperator)
# -------------------------------------------------------------------------
def aggregate_results(**kwargs):
    """
    1) Lit pour chaque compte :
         - "formatted_parquet_with_ML.parquet" (tables finales)
         - "comparatif_parquet_with_ML.parquet" (tables comparatives) si elles existent
    2) Agrège et écrit deux Parquets dans usage_to_combined :
         - final_aggregated.parquet
         - final_comparatif.parquet
    3) Compare le final agrégé avec OLD_PARQUET_PATH si présent.
    4) Insère ces Parquets dans PostgreSQL.
    5) Push les chemins des Parquets via XCom pour la tâche d'indexation.

    ⚠️ Cette tâche ne s'exécute qu'à 23h00 (agrégation quotidienne uniquement)
    """
    import glob
    import os
    from datetime import datetime
    from pyspark.sql import SparkSession
    from pyspark.sql.functions import lit

    # Vérification horaire : utiliser l'heure de déclenchement PRÉVUE, pas l'heure actuelle
    # (important car le scraping peut avoir un délai aléatoire de 0-45min)
    ti = kwargs['ti']
    execution_date = kwargs['execution_date']
    scheduled_hour = execution_date.hour

    print(f"⏰ [aggregate_results] Heure de déclenchement prévue : {scheduled_hour}h")
    print(f"⏰ [aggregate_results] Heure actuelle : {datetime.now().strftime('%H:%M:%S')}")

    if scheduled_hour != 23:
        print(f"⏭️ [aggregate_results] Agrégation uniquement pour l'exécution de 23h00")
        print(f"⏭️ [aggregate_results] Tâche skippée")
        return

    spark = SparkSession.builder \
        .appName("Aggregation_Scraping") \
        .config("spark.jars", JARS_PATH) \
        .getOrCreate()

    ti = kwargs['ti']
    account_list = ti.xcom_pull(key="return_value", task_ids="read_accounts")
    if not account_list:
        print("💡 [aggregate_results] Aucune donnée à agréger (pas de comptes).")
        spark.stop()
        return

    aggregated_final_df = None
    aggregated_comp_df = None
    current_date = datetime.now().strftime("%Y%m%d")
    current_time = datetime.now().strftime("%H%M")

    # Parcours des comptes pour lire "final" et "comparatif"
    for info in account_list:
        norm = info["normalized"]
        account = info["account"]

        print(f"📂 [aggregate_results] Traitement du compte @{account} (normalisé: {norm})")

        usage_final_pattern = os.path.join(
            DATA_DIR, "usage", "scraping",
            f"instagram_data_{norm}",
            current_date,
            "*",
            "formatted_parquet_with_ML.parquet"
        )
        final_files = glob.glob(usage_final_pattern)

        if final_files:
            for fpath in final_files:
                print(f"🔎 [aggregate_results] Lecture FINAL {fpath} pour {norm}")
                try:
                    df_final = spark.read.parquet(fpath)
                    df_final = df_final.withColumn("username_scraped", lit(account))
                    aggregated_final_df = df_final if aggregated_final_df is None else aggregated_final_df.unionByName(df_final, allowMissingColumns=True)
                except Exception as e:
                    print(f"❌ [aggregate_results] Erreur lecture finale {fpath} : {e}")
        else:
            print(f"💡 [aggregate_results] Aucune table finale trouvée pour {norm} avec pattern {usage_final_pattern}")

        usage_comp_pattern = os.path.join(
            DATA_DIR, "usage", "scraping",
            f"instagram_data_{norm}",
            current_date,
            "*",
            "comparatif_parquet_with_ML.parquet"
        )
        comp_files = glob.glob(usage_comp_pattern)

        if comp_files:
            for fpath in comp_files:
                print(f"🔎 [aggregate_results] Lecture COMPARATIF {fpath} pour {norm}")
                try:
                    df_comp = spark.read.parquet(fpath)
                    df_comp = df_comp.withColumn("username_scraped", lit(account))
                    aggregated_comp_df = df_comp if aggregated_comp_df is None else aggregated_comp_df.unionByName(df_comp, allowMissingColumns=True)
                except Exception as e:
                    print(f"❌ [aggregate_results] Erreur lecture comparatif {fpath} : {e}")
        else:
            print(f"💡 [aggregate_results] Aucune table comparatif trouvée pour {norm}")

    # Écriture des fichiers agrégés
    combined_path = os.path.join(
        DATA_DIR, "usage_to_combined", "scraping",
        "instagram_data", current_date, current_time
    )
    os.makedirs(combined_path, exist_ok=True)
    final_aggregated_file = os.path.join(combined_path, "final_aggregated.parquet")
    final_comp_file = os.path.join(combined_path, "final_comparatif.parquet")

    if aggregated_final_df is not None:
        aggregated_final_df.write.mode("append").parquet(final_aggregated_file)
        print(f"✅ [aggregate_results] final_aggregated.parquet => {final_aggregated_file}")
        print(f"📊 [aggregate_results] Nombre total de lignes : {aggregated_final_df.count()}")
        aggregated_final_df.show(10, truncate=False)
    else:
        print("💡 [aggregate_results] Aucun DF final agrégé à écrire.")

    if aggregated_comp_df is not None:
        aggregated_comp_df.write.mode("append").parquet(final_comp_file)
        print(f"✅ [aggregate_results] final_comparatif.parquet => {final_comp_file}")
        print(f"📊 [aggregate_results] Nombre total de changements : {aggregated_comp_df.count()}")
        aggregated_comp_df.show(10, truncate=False)
    else:
        print("💡 [aggregate_results] Aucun DF comparatif agrégé à écrire.")

    # Comparaison globale (optionnel)
    if aggregated_final_df is not None and os.path.exists(OLD_PARQUET_PATH):
        print("📌 [aggregate_results] Ancien snapshot détecté, comparaison globale en cours ...")
        try:
            oldDF = spark.read.parquet(OLD_PARQUET_PATH)
            join_cols = ["username", "full_name"]
            added = aggregated_final_df.join(oldDF, join_cols, "left_anti").withColumn("change", lit("added_global"))
            deleted = oldDF.join(aggregated_final_df, join_cols, "left_anti").withColumn("change", lit("deleted_global"))
            global_compDF = added.unionByName(deleted, allowMissingColumns=True)
            global_comp_file = os.path.join(combined_path, "final_global_comparatif.parquet")
            global_compDF.write.mode("append").parquet(global_comp_file)
            print(f"✅ [aggregate_results] final_global_comparatif.parquet => {global_comp_file}")
            global_compDF.show(20, truncate=False)
        except Exception as e:
            print(f"❌ [aggregate_results] Erreur comparaison globale : {e}")
    else:
        print("🛑 [aggregate_results] Pas d'ancien snapshot ou pas de DF final, pas de comparaison globale.")

    # Insertion en PostgreSQL
    postgres_url = f"jdbc:postgresql://{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

    if aggregated_final_df is not None:
        try:
            print(f"🔵 [aggregate_results] Insertion du Parquet final_aggregated dans PostgreSQL ({postgres_url}) ...")
            aggregated_final_df.write \
                .format("jdbc") \
                .option("url", postgres_url) \
                .option("dbtable", "final_aggregated_scraping") \
                .option("user", POSTGRES_USER) \
                .option("password", POSTGRES_PASSWORD) \
                .option("driver", "org.postgresql.Driver") \
                .mode("append") \
                .save()
            print("✅ [aggregate_results] final_aggregated.parquet inséré dans 'final_aggregated_scraping'.")
        except Exception as e:
            print(f"❌ [aggregate_results] Erreur lors de l'insertion final_aggregated : {e}")

    if aggregated_comp_df is not None:
        try:
            print(f"🔵 [aggregate_results] Insertion du Parquet final_comparatif dans PostgreSQL ({postgres_url}) ...")
            aggregated_comp_df.write \
                .format("jdbc") \
                .option("url", postgres_url) \
                .option("dbtable", "final_comparatif_scraping") \
                .option("user", POSTGRES_USER) \
                .option("password", POSTGRES_PASSWORD) \
                .option("driver", "org.postgresql.Driver") \
                .mode("append") \
                .save()
            print("✅ [aggregate_results] final_comparatif.parquet inséré dans 'final_comparatif_scraping'.")
        except Exception as e:
            print(f"❌ [aggregate_results] Erreur lors de l'insertion final_comparatif : {e}")

    # Push des chemins pour la tâche 4
    ti.xcom_push(key="final_aggregated_file", value=final_aggregated_file)
    ti.xcom_push(key="final_comparatif_file", value=final_comp_file)

    spark.stop()

aggregate_task = PythonOperator(
    task_id="aggregate_results",
    python_callable=aggregate_results,
    provide_context=True,
    dag=dag
)

# -------------------------------------------------------------------------
# Tâche 4 : INDEXATION ELASTICSEARCH (PythonOperator)
# -------------------------------------------------------------------------
def index_to_elasticsearch(**kwargs):
    """
    Lit final_aggregated.parquet et final_comparatif.parquet (via XCom)
    et les envoie dans Elasticsearch.

    ⚠️ Cette tâche ne s'exécute qu'à 23h00 (indexation quotidienne uniquement)
    """
    from pyspark.sql import SparkSession
    from pyspark.sql.functions import lit
    from datetime import datetime

    # Vérification horaire : utiliser l'heure de déclenchement PRÉVUE, pas l'heure actuelle
    # (important car le scraping peut avoir un délai aléatoire de 0-45min)
    execution_date = kwargs['execution_date']
    scheduled_hour = execution_date.hour

    print(f"⏰ [index_to_elasticsearch] Heure de déclenchement prévue : {scheduled_hour}h")
    print(f"⏰ [index_to_elasticsearch] Heure actuelle : {datetime.now().strftime('%H:%M:%S')}")

    if scheduled_hour != 23:
        print(f"⏭️ [index_to_elasticsearch] Indexation uniquement pour l'exécution de 23h00")
        print(f"⏭️ [index_to_elasticsearch] Tâche skippée")
        return

    ti = kwargs['ti']
    final_aggregated_file = ti.xcom_pull(task_ids="aggregate_results", key="final_aggregated_file")
    final_comparatif_file = ti.xcom_pull(task_ids="aggregate_results", key="final_comparatif_file")

    if not final_aggregated_file:
        print("💡 [index_to_elasticsearch] Pas de chemin parquet reçu, indexation annulée.")
        return

    # Concaténation des jars PostgreSQL et Elasticsearch-Spark
    jars_list = f"{JARS_PATH},{ES_SPARK_JAR}"
    spark = SparkSession.builder \
        .appName("IndexationElasticsearch_Scraping") \
        .config("spark.jars", jars_list) \
        .getOrCreate()

    # Indexation final_aggregated
    if final_aggregated_file and os.path.exists(final_aggregated_file):
        try:
            df_final = spark.read.parquet(final_aggregated_file)
            df_final = df_final.withColumn("indexed_at", lit(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

            df_final.write \
                .format("org.elasticsearch.spark.sql") \
                .option("es.nodes", ELASTICSEARCH_HOST) \
                .option("es.port", ELASTICSEARCH_PORT) \
                .option("es.nodes.wan.only", "true") \
                .option("es.resource", "instagram_scraping_aggregated") \
                .option("es.mapping.id", "username") \
                .mode("append") \
                .save()
            print(f"✅ [Elasticsearch] final_aggregated.parquet indexé dans 'instagram_scraping_aggregated' ({ELASTICSEARCH_HOST}:{ELASTICSEARCH_PORT}).")
        except Exception as e:
            print(f"❌ [Elasticsearch] Erreur indexation final_aggregated : {e}")

    # Indexation final_comparatif
    if final_comparatif_file and os.path.exists(final_comparatif_file):
        try:
            df_comp = spark.read.parquet(final_comparatif_file)
            df_comp = df_comp.withColumn("indexed_at", lit(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

            df_comp.write \
                .format("org.elasticsearch.spark.sql") \
                .option("es.nodes", ELASTICSEARCH_HOST) \
                .option("es.port", ELASTICSEARCH_PORT) \
                .option("es.nodes.wan.only", "true") \
                .option("es.resource", "instagram_scraping_comparatif") \
                .option("es.mapping.id", "username") \
                .mode("append") \
                .save()
            print(f"✅ [Elasticsearch] final_comparatif.parquet indexé dans 'instagram_scraping_comparatif' ({ELASTICSEARCH_HOST}:{ELASTICSEARCH_PORT}).")
        except Exception as e:
            print(f"❌ [Elasticsearch] Erreur indexation final_comparatif : {e}")

    spark.stop()

index_task = PythonOperator(
    task_id="index_to_elasticsearch",
    python_callable=index_to_elasticsearch,
    provide_context=True,
    dag=dag
)

# -------------------------------------------------------------------------
# ORDONNANCEMENT
# -------------------------------------------------------------------------
with dag:
    accounts = read_accounts()
    run_all_accounts = run_single_account_scraping.expand(account_info=accounts)
    accounts >> run_all_accounts >> aggregate_task >> index_task
