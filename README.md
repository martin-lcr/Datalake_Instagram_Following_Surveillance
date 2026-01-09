# 📊 Instagram Following Surveillance Pipeline

> Pipeline automatisé de surveillance des abonnements Instagram avec détection des changements, prédictions ML et visualisations en temps réel.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-required-blue.svg)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![Airflow](https://img.shields.io/badge/airflow-2.10.3-orange.svg)](https://airflow.apache.org/)

## 🎯 À propos

Ce projet permet de surveiller automatiquement les abonnements (followings) de comptes Instagram publics. Il détecte les nouveaux followings et unfollows, prédit le genre via Machine Learning, et stocke tout l'historique dans un Data Lake structuré.

**Caractéristiques principales** :
- 🔄 Scraping automatique toutes les ~4h (6 fois/jour) avec délais aléatoires anti-détection
- 📊 Dashboard web moderne avec filtres avancés (port 8000)
- 🖥️ Mode visuel optionnel pour voir Chrome naviguer en temps réel (X11/VNC)
- 🤖 Prédiction de genre par ML avec % de confiance
- 📈 Visualisations Kibana avancées (port 5601)
- 💾 Data Lake structuré (RAW → FORMATTED → USAGE)
- 🐳 100% Dockerisé - Automatisation complète 24/7
- 🛡️ Stratégie anti-détection Instagram (intervalles irréguliers, délais aléatoires)

---

## ✨ Installation rapide

### Option 1 : Installation locale (10 minutes)

**Prérequis** :
- ✅ **Docker Desktop** installé et lancé
- ✅ **Git** installé

**C'est tout !** Python, Make, Airflow, PostgreSQL, Elasticsearch sont tous conteneurisés.

### Option 2 : Déploiement Cloud (20 minutes) ☁️

**Déploiement gratuit 24/7 sur Oracle Cloud Free Tier** :
- ✅ VM ARM 4 OCPU + 24 GB RAM (Always Free)
- ✅ 200 GB Storage
- ✅ IP publique statique
- ✅ Disponibilité 24/7

📖 **Guide complet** : [docs/DEPLOIEMENT_ORACLE_CLOUD.md](docs/DEPLOIEMENT_ORACLE_CLOUD.md)

### 1️⃣ Cloner le projet

```bash
git clone https://github.com/martin-lcr/Datalake_Instagram_Following_Surveillance.git
cd Datalake_Instagram_Following_Surveillance
```

### 2️⃣ Obtenir les cookies Instagram

**Installer l'extension Chrome** : [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)

**Étapes** :
1. Connectez-vous à [Instagram](https://www.instagram.com)
2. Cliquez sur l'extension "Get cookies.txt LOCALLY"
3. Téléchargez le fichier `www.instagram.com_cookies.txt`

**Placer les cookies** :
```bash
mkdir -p docker/cookies
cp ~/Downloads/www.instagram.com_cookies.txt docker/cookies/
```

### 3️⃣ Configurer les comptes à surveiller

Ouvrez le fichier `instagram_accounts_to_scrape.txt` :
```bash
nano instagram_accounts_to_scrape.txt
```

Ajoutez les comptes Instagram (un par ligne) :
```
nike
adidas
puma
```

### 4️⃣ Lancer l'installation automatique

```bash
make install
```

**Cette commande va automatiquement** :
- ✅ Détecter votre système (Linux/macOS/Windows WSL)
- ✅ Générer les secrets Airflow
- ✅ Créer tous les répertoires nécessaires
- ✅ Valider vos cookies Instagram
- ✅ Construire toutes les images Docker
- ✅ Démarrer tous les services (Airflow, PostgreSQL, Elasticsearch, Kibana, Dashboard)

**Durée** : 5-7 minutes (téléchargement + build des images Docker)

### 5️⃣ Accéder aux interfaces

Les dashboards s'ouvrent automatiquement dans votre navigateur ! 🎉

Ou accédez manuellement :

| Interface | URL | Login |
|-----------|-----|-------|
| 📊 **Dashboard Instagram** | http://localhost:8000 | - |
| 🚀 **Airflow** | http://localhost:8082 | airflow / airflow |
| 📈 **Kibana** | http://localhost:5601 | - |

**Ouverture automatique** :
```bash
make open  # Ouvre les 3 dashboards dans le navigateur
```

**C'est terminé !** 🎉 Le pipeline tourne maintenant automatiquement 24/7.

**📍 Important** : Tant que Docker Desktop est lancé, le système est 100% autonome :
- ✅ Scrapings automatiques 6 fois/jour (2h, 6h, 10h, 14h, 18h, 23h + délais aléatoires 0-45min)
- ✅ Agrégation et comparaison quotidienne à 23h
- ✅ Pas besoin de garder VS Code ou Chrome ouverts
- ✅ Redémarrage automatique des services (restart: always)
- ⚠️ Cookies Instagram à renouveler tous les 1-3 mois (vous recevrez des erreurs dans les logs)

---

## 📋 Fonctionnalités

### Scraping et surveillance
- ✅ **Scraping automatique** 6 fois/jour (2h, 6h, 10h, 14h, 18h, 23h)
- ✅ **Anti-détection Instagram** : Délais aléatoires 0-45min + 3 passes par scraping
- ✅ **Multi-comptes** : Surveillez autant de comptes que vous voulez
- ✅ **Détection des changements** : Nouveaux followings et unfollows (comparaison quotidienne à 23h)
- ✅ **Prédiction de genre** : ML automatique (male/female/unknown avec % de confiance)
- ✅ **Historique complet** : Tous les scrapings sont conservés
- ✅ **Fonctionnement 24/7** : Autonomie totale tant que Docker Desktop tourne

### Dashboards et visualisations
- 📊 **Dashboard Web moderne** (port 8000) :
  - Vue globale : Tous vos comptes surveillés en un coup d'œil
  - Vue détaillée : Liste complète avec filtres avancés (recherche, genre, statut, tri)
  - Stats quotidiennes : Total, ajouts/suppressions, distribution genre
  - **Qualité du scraping** : Score de complétude basé sur le nombre réel Instagram
  - **Mise à jour quotidienne à 23h** (affiche le snapshot quotidien après agrégation)
  - Affichage de la date de scraping pour chaque following

- 📈 **Kibana** (port 5601) :
  - Visualisations avancées
  - Graphiques de tendances
  - Recherche full-text

### Quality Tracking (Suivi de qualité)
- ✅ **Extraction automatique** : Récupération du nombre total réel depuis Instagram
- ✅ **Score de complétude** : Calcul précis du % de couverture de chaque scraping
- ✅ **Détection des vrais nouveaux** : Ignore les scrapings incomplets dans les comparaisons
- ✅ **Niveau de confiance** : HIGH/MEDIUM/LOW selon la qualité des données
- ✅ **Historique de qualité** : Traçabilité complète de tous les scrapings
- ✅ **Robustesse** : Évite les faux positifs dus aux scrapings partiels

### Architecture Data Lake
```
data/
├── raw/         # Données brutes JSON du scraping
├── formatted/   # Données nettoyées avec prédictions ML
└── usage/       # Agrégations quotidiennes et comparatifs
```

---

## 🎯 Utilisation quotidienne

### Démarrer les services
```bash
make start
```

### Ouvrir les dashboards
```bash
make open
```

### Voir le statut
```bash
make status
```

### Arrêter les services
```bash
make stop
```

### Consulter les logs
```bash
make logs              # Tous les logs
make logs-airflow      # Logs Airflow uniquement
```

### Déclencher un scraping manuel
```bash
make trigger-dag
```

### Valider les cookies
```bash
make validate-cookies
```

### Mode Visuel (voir Chrome en action)
Activez le mode visuel pour voir Chrome naviguer sur Instagram en temps réel :
```bash
# Via le Dashboard (recommandé)
# 1. Aller sur http://localhost:8000
# 2. Cliquer sur "Lancer scraping"
# 3. Cocher "Mode visuel"

# Ou en ligne de commande
make test-visual-mode  # Tester l'affichage X11
```

📖 **Guide complet** : [docs/X11_VISUAL_MODE_SETUP.md](docs/X11_VISUAL_MODE_SETUP.md)

---

## 🔧 Commandes Make disponibles

| Commande | Description |
|----------|-------------|
| `make install` | Installation complète automatique |
| `make start` | Démarrer tous les services |
| `make stop` | Arrêter tous les services |
| `make restart` | Redémarrer tous les services |
| `make status` | Afficher le statut des services |
| `make logs` | Voir les logs en temps réel |
| `make open` | Ouvrir les dashboards dans le navigateur |
| `make validate-cookies` | Valider les cookies Instagram |
| `make trigger-dag` | Déclencher un scraping manuel |
| `make clean` | Supprimer les volumes et données |
| `make rebuild` | Reconstruire les images sans cache |
| `make help` | Liste complète des commandes |

---

## 📊 Architecture du système

```
┌──────────────────────────────────────────────────────────┐
│         AIRFLOW SCHEDULER (Europe/Paris) 24/7            │
│     6 exécutions/jour : 2h, 6h, 10h, 14h, 18h, 23h       │
│           + Délai aléatoire 0-45min (anti-détection)     │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────┐
│  SCRAPINGS ~4h (Selenium Chrome headless)                │
│  • 3 passes par scraping (avec délais 60-120s)          │
│  • Extraction followings Instagram                       │
│  • Prédiction genre ML (confidence %)                    │
│  • Stockage tables individuelles PostgreSQL              │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────┐
│  AGRÉGATION QUOTIDIENNE (23h uniquement)                 │
│  • Fusion des 6 scrapings de la journée                 │
│  • Déduplication par username (DISTINCT ON)             │
│  • → final_aggregated_scraping                          │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────┐
│  COMPARAISON J vs J-1 (23h uniquement)                   │
│  • Détection nouveaux followings (added)                │
│  • Détection unfollows (deleted)                         │
│  • → final_comparatif_scraping                          │
└──────────────────────────────────────────────────────────┘
                          │
           ┌──────────────┼──────────────┐
           ▼              ▼              ▼
    ┌──────────┐   ┌─────────────┐   ┌──────────┐
    │PostgreSQL│   │Elasticsearch│   │ Dashboard│
    │  (Vues)  │   │  (Index)    │   │ (Flask)  │
    │Màj 23h   │   │  Màj 23h    │   │ Màj 23h  │
    └──────────┘   └─────────────┘   └──────────┘
```

---

## 🤖 Fonctionnement Automatique 24/7

### ✅ Autonomie Totale

Une fois Docker Desktop lancé, **le système tourne entièrement en autonomie** :

- **Pas besoin de VS Code ouvert** - Les containers tournent en arrière-plan
- **Pas besoin de Chrome ouvert** - Les dashboards sont accessibles quand vous voulez
- **Pas besoin de votre session utilisateur** - Les services sont gérés par Docker
- **Redémarrage automatique** - Tous les services ont `restart: always`

### 🔄 Planning Automatique

| Heure | Action | Détails |
|-------|--------|---------|
| **02:00** + 0-45min | 🔍 Scraping | 3 passes + délais aléatoires 60-120s |
| **06:00** + 0-45min | 🔍 Scraping | 3 passes + délais aléatoires 60-120s |
| **10:00** + 0-45min | 🔍 Scraping | 3 passes + délais aléatoires 60-120s |
| **14:00** + 0-45min | 🔍 Scraping | 3 passes + délais aléatoires 60-120s |
| **18:00** + 0-45min | 🔍 Scraping | 3 passes + délais aléatoires 60-120s |
| **23:00** + 0-45min | 🔍 Scraping + 📊 **Agrégation** + 🔄 **Comparaison** | Mise à jour dashboard |

**Tous les horaires sont en heure locale (Europe/Paris)**

### 📊 Mises à Jour du Dashboard

Le dashboard (http://localhost:8000) **se met à jour une fois par jour à 23h** :

**Pourquoi** ?
- Les scrapings de 2h, 6h, 10h, 14h, 18h stockent dans des tables individuelles
- L'agrégation de 23h fusionne tous les scrapings du jour
- Les vues PostgreSQL lisent depuis les tables agrégées
- **Résultat** : Le dashboard affiche un snapshot quotidien consolidé

**Avantages** :
- ✅ Données déduplicées et nettoyées
- ✅ Comparaison précise J vs J-1
- ✅ Moins de charge sur la base de données
- ✅ Cohérence des données affichées

### ⚠️ Maintenance Nécessaire

**Seule intervention requise** : Renouveler les cookies Instagram tous les **1-3 mois**

**Comment savoir que les cookies ont expiré** ?
```bash
make logs-airflow
# Vous verrez : ❌ [ERREUR] Authentification Instagram échouée
```

**Solution** :
1. Reconnectez-vous à Instagram dans Chrome
2. Téléchargez les nouveaux cookies (extension Get cookies.txt LOCALLY)
3. Remplacez `docker/cookies/www.instagram.com_cookies.txt`
4. Redémarrez : `make restart`

### 🔒 Stratégie Anti-Détection Instagram

Pour éviter que Instagram détecte le scraping automatique :

1. **Fréquence réduite** : 6x/jour au lieu de 24x/jour
2. **Intervalles irréguliers** : 3h, 4h, 4h, 4h, 4h, 5h (non prévisible)
3. **Délais aléatoires au démarrage** : 0-45 minutes (exécution jamais à heure fixe)
4. **Multi-passes** : 3 passes par scraping (comportement plus humain)
5. **Délais entre passes** : 60-120 secondes aléatoires
6. **Cookies persistants** : Même session Instagram réutilisée

**Résultat** : Pattern de scraping imprévisible et similaire au comportement humain

---

## 🛠️ Stack technique

- **Orchestration** : Apache Airflow 2.10.3 (LocalExecutor)
- **Scraping** : Selenium 4.36 + Chrome headless
- **Processing** : PySpark 4.0.1
- **ML** : Gender-guesser 0.4.0 + Scikit-learn 1.6.0
- **Storage** : PostgreSQL 14 + Elasticsearch 8.11
- **Visualization** : Flask + Kibana 8.11
- **Containerization** : Docker + Docker Compose

---

## ⚙️ Configuration

### Timezone
Le pipeline fonctionne en **Europe/Paris (UTC+1)** :
- Scrapings : 02h00, 06h00, 10h00, 14h00, 18h00, 23h00 (+ délai aléatoire 0-45min)
- Agrégation quotidienne : 23h00 uniquement
- Le changement d'heure été/hiver est automatique

### Ports utilisés
| Service | Port |
|---------|------|
| Dashboard Flask | 8000 |
| Airflow Web UI | 8082 |
| Kibana | 5601 |
| Elasticsearch | 9200 |
| PostgreSQL | 5433 |

### Comptes surveillés
Éditez simplement le fichier `instagram_accounts_to_scrape.txt` :
```bash
nano instagram_accounts_to_scrape.txt
```

Puis redémarrez :
```bash
make restart
```

### Quality Tracking (Système de suivi de qualité)

Le système de quality tracking est **déjà intégré** dans le pipeline et s'active automatiquement à chaque scraping.

**Fonctionnalités automatiques** :
- ✅ Extraction du nombre total réel depuis Instagram (valeur "357 suivi(e)s")
- ✅ Calcul du score de complétude : `(scrapé / total_instagram) × 100`
- ✅ Stockage dans `scraping_metadata` avec historique complet
- ✅ Comparaisons intelligentes (ignore les scrapings incomplets)

**Consultation** :
- **Dashboard** : http://localhost:8000 → Section "Qualité du scraping"
- **PostgreSQL** :
  ```bash
  docker exec -it instagram-postgres psql -U airflow -d airflow
  ```
  ```sql
  SELECT * FROM scraping_metadata ORDER BY scraping_date DESC LIMIT 10;
  ```

**Documentation complète** :
- [Guide d'intégration](docs/INTEGRATION_QUALITY_TRACKING.md) - Détails techniques
- [Solution aux scrapings incomplets](docs/SOLUTION_SCRAPINGS_INCOMPLETS.md) - Problème résolu

---

## 🐛 Troubleshooting

### ❌ Erreur "Login required" lors du scraping

**Cause** : Cookies expirés ou invalides

**Solution** :
```bash
# 1. Télécharger de nouveaux cookies depuis Instagram
# 2. Remplacer le fichier
cp ~/Downloads/www.instagram.com_cookies.txt docker/cookies/

# 3. Valider
make validate-cookies

# 4. Redémarrer
make restart
```

### ❌ Services ne démarrent pas

**Solution** :
```bash
# Vérifier que Docker Desktop est lancé
docker ps

# Voir les logs d'erreur
make logs

# Rebuild complet
make rebuild
make start
```

### ❌ Port déjà utilisé (8000, 8082, etc.)

**Solution** :
```bash
# Voir quel processus utilise le port
lsof -i :8000

# Tuer le processus
kill -9 <PID>

# Ou modifier les ports dans docker/docker-compose.yml
```

### ❌ Le DAG ne s'affiche pas dans Airflow

**Solution** :
```bash
# Vérifier les erreurs de parsing
docker compose exec airflow-scheduler airflow dags list-import-errors

# Redémarrer le scheduler
make restart
```

### ❌ Elasticsearch refuse les connexions

**Solution** :
```bash
# Attendre que le service soit healthy
make status

# Elasticsearch doit afficher "Up (healthy)"
# Cela peut prendre 1-2 minutes au démarrage
```

---

## 🔐 Sécurité et bonnes pratiques

### Fichiers sensibles (dans .gitignore)
- ✅ `docker/cookies/` - Ne jamais commit les cookies Instagram
- ✅ `docker/.env` - Variables d'environnement et secrets
- ✅ `data/` - Données du Data Lake
- ✅ `airflow/logs/` - Logs Airflow

### Recommandations
1. **Renouvelez les cookies** régulièrement (tous les 15-30 jours)
2. **Vérifiez la validité** avec `make validate-cookies` chaque semaine
3. **Ne partagez jamais** vos cookies Instagram
4. **Utilisez des mots de passe forts** pour PostgreSQL en production
5. **Limitez le nombre de comptes** surveillés pour éviter le rate-limiting Instagram

---

## 📁 Structure du projet

```
.
├── airflow/
│   ├── dags/                    # DAGs Airflow
│   └── logs/                    # Logs Airflow
├── dashboard/                   # Application Flask (port 8000)
│   ├── app.py                   # API REST
│   ├── templates/               # Templates HTML
│   └── Dockerfile
├── docker/
│   ├── docker-compose.yml       # Services Docker
│   ├── Dockerfile               # Image Airflow custom
│   ├── cookies/                 # Cookies Instagram (à placer ici)
│   └── .env                     # Variables d'environnement
├── scripts/
│   ├── instagram_scraping_ml_pipeline.py   # Script principal de scraping
│   ├── scraping_quality_tracker.py         # Module de suivi de qualité
│   ├── install_quality_tracking.sh         # Installation du quality tracking
│   ├── install_oracle_cloud.sh             # Installation automatique Oracle Cloud
│   └── setup_auto_open.sh                  # Configuration auto-open 09h00
├── data/                        # Data Lake (généré automatiquement)
│   ├── raw/
│   ├── formatted/
│   └── usage/
├── sql/                         # Scripts SQL pour quality tracking
│   ├── create_scraping_metadata.sql      # Tables de métadonnées
│   └── detect_truly_new_followings.sql   # Fonctions de détection
├── docs/                        # Documentation technique
│   ├── DEPLOIEMENT_ORACLE_CLOUD.md       # Guide déploiement Oracle Cloud
│   ├── INTEGRATION_QUALITY_TRACKING.md   # Guide quality tracking
│   └── SOLUTION_SCRAPINGS_INCOMPLETS.md  # Résolution problèmes
├── instagram_accounts_to_scrape.txt  # Liste des comptes à surveiller
├── Makefile                     # Commandes d'automatisation
├── README.md                    # Ce fichier
└── QUICKSTART.md                # Guide rapide 3 minutes
```

---

## 📚 Documentation supplémentaire

### Guides d'installation
- **[QUICKSTART.md](QUICKSTART.md)** - Guide de démarrage ultra-rapide (10 minutes)
- **[Déploiement Oracle Cloud](docs/DEPLOIEMENT_ORACLE_CLOUD.md)** ☁️ - Déploiement gratuit 24/7 sur Oracle Cloud Free Tier

### Guides techniques
- **[Quality Tracking Integration](docs/INTEGRATION_QUALITY_TRACKING.md)** - Guide technique complet du système de suivi de qualité
- **[Solution Scrapings Incomplets](docs/SOLUTION_SCRAPINGS_INCOMPLETS.md)** - Résolution du problème des scrapings partiels

### Références
- **Commandes Make** - `make help` pour la liste complète
- **Airflow UI** - http://localhost:8082 (documentation intégrée)

---

## ⚠️ Avertissement légal

Ce projet est fourni **à des fins éducatives et de recherche uniquement**.

L'utilisation de ce pipeline doit respecter :
- Les [Conditions d'Utilisation d'Instagram](https://help.instagram.com/581066165581870)
- Les lois sur la protection des données (RGPD en Europe)
- Le respect de la vie privée des utilisateurs

⚠️ **Le scraping massif peut entraîner la suspension de votre compte Instagram.**

**Utilisez ce projet de manière responsable** :
- Ne surveillez que des comptes publics
- Limitez le nombre de requêtes
- Respectez les délais entre les scrapings
- N'utilisez pas les données à des fins commerciales

---

## 🤝 Contribution

Les contributions sont les bienvenues ! Pour contribuer :

1. **Fork** le projet
2. Créez une **branche** pour votre feature (`git checkout -b feature/AmazingFeature`)
3. **Commit** vos changements (`git commit -m 'Add AmazingFeature'`)
4. **Push** vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrez une **Pull Request**

**Guidelines** :
- Suivez le style de code existant (commentaires en français)
- Testez vos changements avec `make install`
- Documentez les nouvelles fonctionnalités dans le README

---

## 📞 Support et Questions

### Pour les problèmes techniques

1. **Vérifiez les commandes** : `make help`
2. **Consultez les logs** : `make logs`
3. **Validez les cookies** : `make validate-cookies`
4. **Lisez le guide** : [QUICKSTART.md](QUICKSTART.md)
5. **Ouvrez une issue** sur GitHub avec :
   - Description du problème
   - Logs d'erreur (`make logs`)
   - Système d'exploitation
   - Version de Docker

### FAQ

**Q : Le scraping échoue avec "Login required"**
R : Vos cookies ont expiré. Téléchargez-en de nouveaux depuis Instagram et exécutez `make restart`.

**Q : Les services ne démarrent pas**
R : Vérifiez que Docker Desktop est lancé avec `docker ps`. Si problème, exécutez `make rebuild`.

**Q : Puis-je surveiller des comptes privés ?**
R : Non, seuls les comptes publics sont supportés. Vous devez aussi être connecté à Instagram via les cookies.

---

## 📄 License

Ce projet est sous licence **MIT** - voir le fichier [LICENSE](LICENSE) pour plus de détails.

### Utilisation responsable

⚠️ **IMPORTANT** : Ce projet est fourni **à des fins éducatives et de recherche uniquement**.

**Vous devez** :
- ✅ Respecter les [Conditions d'Utilisation d'Instagram](https://help.instagram.com/581066165581870)
- ✅ Respecter les lois sur la protection des données (RGPD en Europe)
- ✅ Ne surveiller que des comptes publics
- ✅ Limiter le nombre de requêtes pour éviter le rate-limiting
- ✅ Utiliser vos propres cookies Instagram
- ✅ Ne pas revendre ou exploiter commercialement les données

**Vous ne devez pas** :
- ❌ Scraper massivement (risque de suspension de compte)
- ❌ Utiliser à des fins commerciales sans autorisation
- ❌ Partager vos cookies Instagram
- ❌ Violer la vie privée des utilisateurs

**Disclaimer** : Les auteurs ne sont pas responsables de l'utilisation que vous faites de ce projet. Utilisez-le de manière éthique et responsable.

---

## 👨‍💻 Auteur

Développé par Martin Le Corre

**Stack technique** :
- Apache Airflow 2.10.3
- PySpark 4.0.1
- Selenium 4.36
- PostgreSQL 14
- Elasticsearch 8.11
- Flask + Tailwind CSS

---

## ⭐ Remerciements

Si ce projet vous a été utile, n'hésitez pas à lui donner une étoile ⭐ sur GitHub !

**Ressources utiles** :
- [Documentation Airflow](https://airflow.apache.org/docs/)
- [Docker Documentation](https://docs.docker.com/)
- [Selenium Documentation](https://selenium-python.readthedocs.io/)
- [PySpark Documentation](https://spark.apache.org/docs/latest/api/python/)

---

## 📊 Statistiques du projet

![GitHub stars](https://img.shields.io/github/stars/martin-lcr/Datalake_Instagram_Following_Surveillance?style=social)
![GitHub forks](https://img.shields.io/github/forks/martin-lcr/Datalake_Instagram_Following_Surveillance?style=social)
![GitHub issues](https://img.shields.io/github/issues/martin-lcr/Datalake_Instagram_Following_Surveillance)

---

**Dernière mise à jour** : Janvier 2025
