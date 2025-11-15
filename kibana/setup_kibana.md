# Configuration des Dashboards Kibana

## 📋 Vue d'ensemble

Ce guide vous aide à configurer les dashboards Kibana pour visualiser les données de surveillance Instagram.

## 🚀 Étapes de configuration

### 1. Vérifier qu'Elasticsearch et Kibana sont lancés

```bash
# Vérifier Elasticsearch
curl http://localhost:9200

# Vérifier Kibana (par défaut sur le port 5601)
curl http://localhost:5601
```

### 2. Accéder à Kibana

Ouvrez votre navigateur et allez sur : `http://localhost:5601`

### 3. Créer les Index Patterns

#### a) Index Pattern pour Followers

1. Allez dans **Stack Management** → **Index Patterns**
2. Cliquez sur **Create index pattern**
3. Entrez : `instagram_followers*`
4. Sélectionnez **scraped_at** comme champ de temps
5. Cliquez sur **Create index pattern**

#### b) Index Pattern pour Following

1. Répétez les étapes ci-dessus avec : `instagram_following*`
2. Sélectionnez **scraped_at** comme champ de temps

#### c) Index Pattern pour Daily Diff

1. Répétez les étapes ci-dessus avec : `instagram_daily_diff*`
2. Sélectionnez **comparison_date** comme champ de temps (ou laissez vide si non disponible)

---

## 📊 Dashboards à créer

### Dashboard 1 : Vue d'ensemble (Overview)

#### Visualisation 1 : Total Followers (Metric)
```
Type: Metric
Index: instagram_followers*
Aggregation: Unique Count sur "username"
```

#### Visualisation 2 : Total Following (Metric)
```
Type: Metric
Index: instagram_following*
Aggregation: Unique Count sur "username"
```

#### Visualisation 3 : Répartition par Genre - Followers (Pie Chart)
```
Type: Pie Chart
Index: instagram_followers*
Buckets:
  - Type: Terms
  - Field: predicted_gender
  - Order By: Metric: Count
  - Order: Descending
  - Size: 10
```

#### Visualisation 4 : Répartition par Genre - Following (Pie Chart)
```
Type: Pie Chart
Index: instagram_following*
Buckets:
  - Type: Terms
  - Field: predicted_gender
  - Order By: Metric: Count
  - Order: Descending
  - Size: 10
```

#### Visualisation 5 : Évolution Temporelle (Line Chart)
```
Type: Line Chart
Index: instagram_followers*
X-Axis:
  - Aggregation: Date Histogram
  - Field: scraped_at
  - Interval: Daily

Y-Axis:
  - Aggregation: Count

Split Series:
  - Sub-aggregation: Terms
  - Field: data_type
```

---

### Dashboard 2 : Changements Quotidiens (Daily Changes)

#### Visualisation 1 : Ajouts/Suppressions par Jour (Bar Chart)
```
Type: Vertical Bar Chart
Index: instagram_daily_diff*
X-Axis:
  - Aggregation: Terms
  - Field: comparison_date
  - Order By: Custom
  - Size: 30

Y-Axis:
  - Aggregation: Count

Split Series:
  - Sub-aggregation: Terms
  - Field: change_type
```

#### Visualisation 2 : Derniers Ajouts (Data Table)
```
Type: Data Table
Index: instagram_daily_diff*
Filters:
  - change_type: "added"
  - data_type: "followers"

Columns:
  - username
  - full_name
  - predicted_gender
  - confidence
  - comparison_date

Rows: 20
Sort: comparison_date DESC
```

#### Visualisation 3 : Dernières Suppressions (Data Table)
```
Type: Data Table
Index: instagram_daily_diff*
Filters:
  - change_type: "deleted"
  - data_type: "followers"

Columns:
  - username
  - full_name
  - predicted_gender
  - confidence
  - comparison_date

Rows: 20
Sort: comparison_date DESC
```

#### Visualisation 4 : Genre des Nouveaux Ajouts (Pie Chart)
```
Type: Pie Chart
Index: instagram_daily_diff*
Filter:
  - change_type: "added"

Buckets:
  - Type: Terms
  - Field: predicted_gender
```

---

### Dashboard 3 : Analyse de Genre (Gender Analysis)

#### Visualisation 1 : Distribution de Genre (Horizontal Bar Chart)
```
Type: Horizontal Bar Chart
Index: instagram_followers*,instagram_following*

Y-Axis:
  - Aggregation: Terms
  - Field: predicted_gender

X-Axis:
  - Aggregation: Count

Split Chart:
  - Sub-aggregation: Terms
  - Field: data_type
```

#### Visualisation 2 : Confiance Moyenne par Genre (Metric)
```
Type: Metric
Index: instagram_followers*,instagram_following*

Metrics:
  - Aggregation: Average
  - Field: confidence

Bucket:
  - Type: Terms
  - Field: predicted_gender
```

#### Visualisation 3 : Évolution de la Répartition (Area Chart)
```
Type: Area Chart
Index: instagram_followers*

X-Axis:
  - Aggregation: Date Histogram
  - Field: scraped_at
  - Interval: Daily

Y-Axis:
  - Aggregation: Count

Split Series:
  - Sub-aggregation: Terms
  - Field: predicted_gender
```

---

## 🎨 Personnalisation

### Couleurs suggérées
- **Hommes** : Bleu (#3498db)
- **Femmes** : Rose (#e91e63)
- **Inconnu** : Gris (#95a5a6)
- **Ajouts** : Vert (#2ecc71)
- **Suppressions** : Rouge (#e74c3c)

### Time Range
Pour tous les dashboards, configurez le time picker sur :
- Par défaut : **Last 30 days**
- Refresh : **Every 5 minutes** (optionnel)

---

## 🔍 Requêtes KQL utiles

### Filtrer les followers féminins
```
predicted_gender: "female"
```

### Filtrer les ajouts récents avec haute confiance
```
change_type: "added" AND confidence > 0.8
```

### Filtrer les comptes vérifiés
```
is_verified: true
```

### Comptes avec plus de 10k followers
```
follower_count > 10000
```

---

## 💡 Tips

1. **Sauvegarder régulièrement** : Sauvegardez vos dashboards après chaque modification
2. **Dupliquer avant modification** : Créez une copie avant de modifier un dashboard existant
3. **Utiliser les filtres** : Ajoutez des filtres globaux pour faciliter l'exploration
4. **Drilldown** : Activez le drilldown sur les visualisations pour explorer les détails

---

## 📚 Ressources

- [Documentation Kibana](https://www.elastic.co/guide/en/kibana/current/index.html)
- [Kibana Lens](https://www.elastic.co/guide/en/kibana/current/lens.html) - Pour créer des visualisations rapidement
- [Dashboard Best Practices](https://www.elastic.co/guide/en/kibana/current/dashboard.html)

---

## 🆘 Dépannage

### Les index n'apparaissent pas
1. Vérifiez qu'Elasticsearch contient des données :
   ```bash
   curl -X GET "localhost:9200/instagram_followers/_count"
   ```
2. Rafraîchissez les index patterns dans Kibana

### Erreurs de mapping
- Supprimez l'index pattern et recréez-le
- Vérifiez que les champs de temps sont correctement formatés

### Performance lente
- Limitez la période de temps affichée
- Réduisez le nombre de visualisations par dashboard
- Utilisez des agrégations au lieu de recherches complètes
