# Configuration Dashboard Kibana - Instagram Surveillance

## Accès Kibana
URL: http://localhost:5601

## Étapes de Configuration

### 1. Créer un Data View
1. Ouvrir Kibana: http://localhost:5601
2. Menu hamburger → Stack Management → Data Views
3. Click "Create data view"
4. Configurer:
   - **Name**: `Instagram Followings`
   - **Index pattern**: `instagram-followings-*`
   - **Timestamp field**: `timestamp`
5. Click "Save data view to Kibana"

### 2. Créer un Dashboard

#### Visualisations à créer :

##### A. Répartition par Genre (Pie Chart)
- Type: Pie
- Data view: Instagram Followings
- Slice by: `predicted_gender.keyword`
- Metric: Count

##### B. Timeline des Scrapings (Area Chart)
- Type: Area
- Data view: Instagram Followings
- X-axis: Date Histogram on `@timestamp`
- Y-axis: Count

##### C. Confidence des Prédictions (Histogram)
- Type: Histogram
- Data view: Instagram Followings
- Horizontal axis: `confidence` (intervals of 0.1)
- Vertical axis: Count

##### D. Top 20 Followings Récents (Data Table)
- Type: Table
- Columns:
  - `username.keyword`
  - `full_name.keyword`
  - `predicted_gender.keyword`
  - `confidence`
  - `timestamp`
- Sortby: `timestamp` descending
- Rows: 20

##### E. Status Changes (si index comparatif existe)
- Index pattern: `instagram-followings-*-comparatif`
- Type: Pie
- Slice by: `change.keyword`
  - added (Nouveaux)
  - deleted (Supprimés)

##### F. Metric: Total Followings
- Type: Metric
- Metric: Count

## 3. Filtres Suggérés

### Par Genre
```json
{
  "query": {
    "match": {
      "predicted_gender.keyword": "male"
    }
  }
}
```

### Par Confiance Élevée (> 80%)
```json
{
  "range": {
    "confidence": {
      "gte": 0.8
    }
  }
}
```

### Dernières 24h
Time range: Last 24 hours

## 4. Structure du Dashboard

```
┌─────────────────────────────────────────────────────────┐
│  📊 Instagram Following Surveillance - @mariadlaura     │
├─────────────────────────────────────────────────────────┤
│  [Total Followings]  [Nouveaux]  [Supprimés]           │
├──────────────────┬──────────────────────────────────────┤
│  Genre (Pie)     │  Timeline (Area Chart)              │
│                  │                                      │
├──────────────────┴──────────────────────────────────────┤
│  Confiance (Histogram)                                  │
├─────────────────────────────────────────────────────────┤
│  Top 20 Followings (Table)                              │
└─────────────────────────────────────────────────────────┘
```

## 5. Requêtes Utiles

### Recherche par username
```
username: "john*"
```

### Followings masculins avec haute confiance
```
predicted_gender: "male" AND confidence > 0.8
```

### Nouveaux followings
```
change: "added"
```

## 6. Export/Import Dashboard

Une fois le dashboard créé, vous pouvez l'exporter :
1. Menu hamburger → Stack Management → Saved Objects
2. Sélectionner le dashboard
3. Export → Download as JSON

Le fichier JSON peut être importé sur d'autres instances Kibana.
