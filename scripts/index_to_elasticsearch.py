#!/usr/bin/env python3
"""
Script pour indexer les données Instagram dans Elasticsearch
Usage: python3 index_to_elasticsearch.py <account_name> <data_date> <data_time>
Exemple: python3 index_to_elasticsearch.py mariadlaura 20251115 0109
"""

import sys
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from pyspark.sql import SparkSession
from datetime import datetime

if len(sys.argv) < 4:
    print("Usage: python3 index_to_elasticsearch.py <account_name> <data_date> <data_time>")
    print("Exemple: python3 index_to_elasticsearch.py mariadlaura 20251115 0109")
    sys.exit(1)

account = sys.argv[1]
data_date = sys.argv[2]
data_time = sys.argv[3]

normalized_account = account.replace(".", "-").replace("_", "-")

# Chemins des données
base_path = f"/sources/instagram_surveillance/data/usage/scraping/instagram_data_{normalized_account}/{data_date}/{data_time}"
formatted_parquet = f"{base_path}/formatted_parquet_with_ML.parquet"
comparatif_parquet = f"{base_path}/comparatif_parquet_with_ML.parquet"

print(f"📊 Indexation Elasticsearch pour @{account}")
print(f"Date: {data_date} - Heure: {data_time}")
print("="*80)

# Connexion à Elasticsearch
es = Elasticsearch(['http://elasticsearch:9200'])

if not es.ping():
    print("❌ Impossible de se connecter à Elasticsearch")
    sys.exit(1)

print("✅ Connexion Elasticsearch établie")

# Initialiser Spark
spark = SparkSession.builder \
    .appName(f"Index_{account}") \
    .getOrCreate()

# ============================================================================
# Index des données principales
# ============================================================================

print("\n📥 Chargement des données principales...")
try:
    df = spark.read.parquet(formatted_parquet)
    count = df.count()
    print(f"✅ {count} followings chargés")

    # Convertir en documents
    docs = df.toPandas().to_dict('records')

    # Index name
    index_name = f"instagram-followings-{normalized_account}"

    # Préparer les actions bulk
    actions = []
    for doc in docs:
        action = {
            "_index": index_name,
            "_source": {
                "username": doc.get("username"),
                "full_name": doc.get("full_name"),
                "predicted_gender": doc.get("predicted_gender"),
                "confidence": float(doc.get("confidence")) if doc.get("confidence") else 0.5,
                "scraped_at": doc.get("scraped_at"),
                "scraping_source": doc.get("scraping_source"),
                "target_account": doc.get("target_account"),
                "timestamp": datetime.now().isoformat()
            }
        }
        actions.append(action)

    # Indexer
    if actions:
        print(f"📤 Indexation de {len(actions)} documents...")
        success, failed = bulk(es, actions, raise_on_error=False)
        print(f"✅ {success} documents indexés dans '{index_name}'")
        if failed:
            print(f"⚠️  {len(failed)} documents ont échoué")

except Exception as e:
    print(f"❌ Erreur lors de l'indexation principale: {e}")

# ============================================================================
# Index des données comparatives
# ============================================================================

print("\n📥 Chargement des données comparatives...")
try:
    df_comp = spark.read.parquet(comparatif_parquet)
    count_comp = df_comp.count()
    print(f"✅ {count_comp} changements chargés")

    # Convertir en documents
    docs_comp = df_comp.toPandas().to_dict('records')

    # Index name
    comparatif_index_name = f"instagram-followings-{normalized_account}-comparatif"

    # Préparer les actions bulk
    comparatif_actions = []
    for doc in docs_comp:
        action = {
            "_index": comparatif_index_name,
            "_source": {
                "username": doc.get("username"),
                "full_name": doc.get("full_name"),
                "predicted_gender": doc.get("predicted_gender"),
                "confidence": float(doc.get("confidence")) if doc.get("confidence") else 0.5,
                "change": doc.get("change"),
                "target_account": normalized_account,
                "timestamp": datetime.now().isoformat()
            }
        }
        comparatif_actions.append(action)

    # Indexer
    if comparatif_actions:
        print(f"📤 Indexation de {len(comparatif_actions)} changements...")
        success, failed = bulk(es, comparatif_actions, raise_on_error=False)
        print(f"✅ {success} changements indexés dans '{comparatif_index_name}'")
        if failed:
            print(f"⚠️  {len(failed)} documents ont échoué")

except Exception as e:
    print(f"❌ Erreur lors de l'indexation comparatif: {e}")

# Arrêter Spark
spark.stop()

print("\n" + "="*80)
print("🎉 Indexation terminée!")
print("\n📊 Accédez à Kibana: http://localhost:5601")
print("💡 Créez un Data View avec le pattern: instagram-followings-*")
