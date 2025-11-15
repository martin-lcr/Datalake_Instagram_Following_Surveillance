# Guide Complet - Visualisation Instagram Surveillance

## 🎯 Vue d'Ensemble

Votre pipeline Instagram Surveillance dispose maintenant de **3 interfaces de visualisation** :

1. **Interface Web Personnalisée** (FastAPI + PostgreSQL)
2. **Kibana** (Elasticsearch + visualisations avancées)
3. **Airflow UI** (orchestration et monitoring)

---

## 📊 1. Interface Web Personnalisée

### Accès
🌐 **URL**: http://localhost:8000/dashboard

### Fonctionnalités
- ✅ Vue d'ensemble des followings par compte
- ✅ Statistiques en temps réel (Total, Nouveaux, Supprimés, Genre)
- ✅ Tableau interactif avec filtres
- ✅ Colonne "Status" (🆕 Nouveau, ❌ Supprimé, ✅ Présent)
- ✅ Recherche par username ou nom complet
- ✅ Filtres par genre et status
- ✅ Barres de confiance pour les prédictions ML

### Captures d'écran des données affichées
```
┌─────────────────────────────────────────────────┐
│  📊 Instagram Following Surveillance            │
├─────────────────────────────────────────────────┤
│  Compte: @mariadlaura (686 followings)          │
├──────────┬──────────┬──────────┬────────────────┤
│  Total   │ Nouveaux │ Supprimés│ Hommes/Femmes │
│   686    │   398    │    9     │  159 / 216    │
├──────────┴──────────┴──────────┴────────────────┤
│  🔍 Recherche: [_____________]                  │
│  Genre: [Tous ▼] Status: [Tous ▼]              │
├─────────────────────────────────────────────────┤
│  Username    │ Nom    │ Genre  │ Status │ Date │
│  @john_doe   │ John   │ ♂ 90%  │ 🆕     │ ...  │
│  @jane_smith │ Jane   │ ♀ 90%  │ ✅     │ ...  │
│  @old_user   │ Old    │ ? 50%  │ ❌     │ ...  │
└─────────────────────────────────────────────────┘
```

### Actualisation
- Auto-refresh toutes les 30 secondes
- Rechargement manuel en actualisant la page

---

## 🔍 2. Kibana - Visualisations Avancées

### Accès
🌐 **URL**: http://localhost:5601

### Configuration Initiale

#### Étape 1: Créer un Data View
1. Ouvrir Kibana: http://localhost:5601
2. Menu hamburger (☰) → **Stack Management** → **Data Views**
3. Cliquer sur **"Create data view"**
4. Configuration:
   - **Name**: `Instagram Followings`
   - **Index pattern**: `instagram-followings-*`
   - **Timestamp field**: `timestamp`
5. Cliquer **"Save data view to Kibana"**

#### Étape 2: Créer les Visualisations

##### A. Répartition par Genre (Pie Chart)
```
1. Menu → Visualize Library → Create visualization
2. Type: Pie
3. Data view: Instagram Followings
4. Metrics: Count
5. Slice by: predicted_gender.keyword
6. Save: "Genre Répartition"
```

##### B. Nouveaux vs Supprimés (Metric + Pie)
```
Index pattern: instagram-followings-*-comparatif
1. Type: Pie
2. Slice by: change.keyword
3. Save: "Changements Followings"
```

##### C. Confidence Distribution (Histogram)
```
1. Type: Vertical bar
2. X-axis: Histogram on "confidence" (interval: 0.1)
3. Y-axis: Count
4. Save: "Distribution Confiance ML"
```

##### D. Timeline des Scrapings
```
1. Type: Line
2. X-axis: Date Histogram on @timestamp
3. Y-axis: Count
4. Save: "Evolution Followings"
```

##### E. Top 50 Followings (Table)
```
1. Type: Table
2. Rows per page: 50
3. Columns:
   - username.keyword
   - full_name.keyword
   - predicted_gender.keyword
   - confidence
4. Sort by: timestamp DESC
5. Save: "Liste Followings"
```

#### Étape 3: Créer le Dashboard
1. Menu → Dashboard → Create dashboard
2. Add from library → Sélectionner toutes les visualisations créées
3. Arranger les visualisations:

```
┌─────────────────────────────────────────────────────┐
│ 📊 Instagram Surveillance - @mariadlaura           │
├─────────────┬───────────────┬───────────────────────┤
│ Total: 686  │ Nouveaux: 398 │ Supprimés: 9          │
├─────────────┴───────────────┴───────────────────────┤
│ 🎯 Genre (Pie)       │ 📈 Timeline (Line)          │
│                      │                              │
├──────────────────────┴──────────────────────────────┤
│ 📊 Confiance ML (Histogram)                         │
├─────────────────────────────────────────────────────┤
│ 📋 Top 50 Followings (Table)                        │
│ ┌──────────┬────────────┬────────┬──────────┐      │
│ │ Username │ Nom        │ Genre  │ Conf.    │      │
│ └──────────┴────────────┴────────┴──────────┘      │
└─────────────────────────────────────────────────────┘
```

4. Save dashboard: "Instagram Surveillance Dashboard"

### Requêtes Utiles Kibana

#### Recherche par username
```
username: "maria*"
```

#### Followings masculins avec haute confiance
```
predicted_gender: "male" AND confidence > 0.8
```

#### Nouveaux followings uniquement
```
change: "added"
```

#### Followings supprimés
```
change: "deleted"
```

---

## ⚙️ 3. Airflow UI - Orchestration

### Accès
🌐 **URL**: http://localhost:8080
- **Username**: airflow
- **Password**: airflow

### Fonctionnalités
- Monitoring des DAGs
- Historique des exécutions
- Logs détaillés
- Planification automatique

---

## 🚀 Workflow Complet

### 1. Lancer un Scraping

#### Via Airflow
```bash
cd /home/timor/Datalake_Instagram_Following_Surveillance/docker
docker compose exec airflow-webserver airflow dags trigger instagram_surveillance
```

#### Directement
```bash
docker compose exec airflow-webserver python3 /opt/airflow/scripts/instagram_scraping_ml_pipeline.py mariadlaura
```

### 2. Vérifier les Résultats

#### A. PostgreSQL (pour l'interface web)
```bash
docker compose exec postgres psql -U airflow -d airflow -c "
SELECT COUNT(*) FROM instagram_data_mariadlaura;
SELECT COUNT(*) FROM instagram_data_mariadlaura_comparatif;
"
```

#### B. Elasticsearch (pour Kibana)
```bash
curl -s http://localhost:9200/instagram-followings-mariadlaura/_count
curl -s http://localhost:9200/instagram-followings-mariadlaura-comparatif/_count
```

### 3. Visualiser

1. **Vue Rapide** → Interface Web (http://localhost:8000/dashboard)
2. **Analyse Avancée** → Kibana (http://localhost:5601)
3. **Monitoring** → Airflow (http://localhost:8080)

---

## 📊 Données Disponibles

### Index Elasticsearch

#### 1. `instagram-followings-mariadlaura`
Données principales avec prédictions ML :
```json
{
  "username": "john_doe",
  "full_name": "John Doe",
  "predicted_gender": "male",
  "confidence": 0.9,
  "scraped_at": "2025-11-15T00:00:00",
  "target_account": "mariadlaura",
  "timestamp": "2025-11-15T02:45:00"
}
```

#### 2. `instagram-followings-mariadlaura-comparatif`
Changements détectés :
```json
{
  "username": "new_user",
  "full_name": "New User",
  "predicted_gender": "female",
  "confidence": 0.9,
  "change": "added",  // ou "deleted"
  "timestamp": "2025-11-15T02:45:00"
}
```

### Tables PostgreSQL

#### 1. `instagram_data_mariadlaura`
```sql
username | full_name | predicted_gender | confidence | scraped_at | target_account
```

#### 2. `instagram_data_mariadlaura_comparatif`
```sql
username | full_name | predicted_gender | confidence | change
```

---

## 🔄 Scraping Multi-Pass Quotidien

### Configuration Airflow DAG
Le scraping s'exécute automatiquement selon la planification définie dans le DAG.

### Détection des Changements
À chaque exécution :
- **Nouveaux followings** : `change = "added"`
- **Followings supprimés** : `change = "deleted"`
- **Followings inchangés** : pas dans la table comparatif

### Visualisation des Changements

#### Interface Web
- Filtrer par Status: "🆕 Nouveaux" ou "❌ Supprimés"

#### Kibana
- Index: `instagram-followings-*-comparatif`
- Filtre: `change: "added"` ou `change: "deleted"`

---

## 🛠️ Maintenance

### Réindexer les Données dans Elasticsearch
```bash
docker compose exec airflow-webserver python3 /opt/airflow/scripts/index_to_elasticsearch.py mariadlaura 20251115 0109
```

### Vider un Index Elasticsearch
```bash
curl -X DELETE "localhost:9200/instagram-followings-mariadlaura"
```

### Redémarrer les Services
```bash
docker compose restart
```

---

## 📈 Métriques Clés Disponibles

### Interface Web
- Total followings
- Nouveaux followings (dernières 24h)
- Followings supprimés
- Répartition homme/femme
- Confiance des prédictions ML

### Kibana
- Timeline d'évolution
- Distribution par genre
- Distribution de confiance ML
- Taux de changement (nouveaux/supprimés)
- Recherche full-text avancée
- Agrégations personnalisées

---

## 🎨 Personnalisation

### Ajouter un Nouveau Compte
1. Modifier le DAG Airflow
2. Lancer le scraping avec le nouveau username
3. Les index Elasticsearch seront créés automatiquement

### Modifier les Seuils de Confiance
Éditer le fichier : `scripts/instagram_scraping_ml_pipeline.py`
```python
# Ligne ~550
if pred_full in ["male", "mostly_male"]:
    gender_full = "male"
    conf_full = 0.9  # ← Modifier ici
```

---

## 🐛 Troubleshooting

### Interface Web ne charge pas
```bash
# Vérifier PostgreSQL
docker compose ps postgres

# Redémarrer l'API
pkill -f "python3 -m api.main"
nohup python3 -m api.main > /tmp/api.log 2>&1 &
```

### Kibana ne se connecte pas
```bash
# Vérifier Elasticsearch
curl http://localhost:9200/_cluster/health

# Redémarrer Kibana
docker compose restart kibana
```

### Données non indexées
```bash
# Vérifier les index
curl http://localhost:9200/_cat/indices?v

# Réindexer manuellement
docker compose exec airflow-webserver python3 /opt/airflow/scripts/index_to_elasticsearch.py mariadlaura <date> <time>
```

---

## 📚 Ressources

- **Elasticsearch Query DSL**: https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl.html
- **Kibana Visualizations**: https://www.elastic.co/guide/en/kibana/current/dashboard.html
- **FastAPI Docs**: https://fastapi.tiangolo.com/

---

**Dernière mise à jour** : 2025-11-15
**Version** : 2.0 (avec Elasticsearch + Kibana + Interface Web)
