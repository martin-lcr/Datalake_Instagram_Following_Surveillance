# 📊 Instagram Following Surveillance Pipeline

> Pipeline automatisé de surveillance des abonnements Instagram avec détection des changements, prédictions ML et visualisations en temps réel.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-required-blue.svg)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![Airflow](https://img.shields.io/badge/airflow-2.10.3-orange.svg)](https://airflow.apache.org/)

## 🎯 À propos

Ce projet permet de surveiller automatiquement les abonnements (followings) de comptes Instagram publics. Il détecte les nouveaux followings et unfollows, prédit le genre via Machine Learning, et stocke tout l'historique dans un Data Lake structuré.

**Caractéristiques principales** :
- 🔄 Scraping automatique horaire (24 fois/jour)
- 📊 Dashboard web moderne (port 8000)
- 🤖 Prédiction de genre par ML
- 📈 Visualisations Kibana avancées
- 💾 Data Lake structuré (RAW → FORMATTED → USAGE)
- 🐳 100% Dockerisé (aucune installation Python requise)

---

## ✨ Installation rapide (10 minutes)

### Prérequis

- ✅ **Docker Desktop** installé et lancé
- ✅ **Git** installé

**C'est tout !** Python, Make, Airflow, PostgreSQL, Elasticsearch sont tous conteneurisés.

### 1️⃣ Cloner le projet

```bash
git clone https://github.com/YOUR_USERNAME/Datalake_Instagram_Following_Surveillance.git
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

**C'est terminé !** 🎉 Le pipeline se lance automatiquement toutes les heures.

---

## 📋 Fonctionnalités

### Scraping et surveillance
- ✅ **Scraping automatique** toutes les heures (24 fois/jour)
- ✅ **Multi-comptes** : Surveillez autant de comptes que vous voulez
- ✅ **Détection des changements** : Nouveaux followings et unfollows
- ✅ **Prédiction de genre** : ML automatique (male/female/unknown avec % de confiance)
- ✅ **Historique complet** : Tous les scrapings sont conservés

### Dashboards et visualisations
- 📊 **Dashboard Web moderne** (port 8000) :
  - Vue globale : Tous vos comptes surveillés en un coup d'œil
  - Vue détaillée : Liste complète avec filtres (recherche, genre, statut)
  - Stats en temps réel : Total, ajouts/suppressions du jour, distribution genre

- 📈 **Kibana** (port 5601) :
  - Visualisations avancées
  - Graphiques de tendances
  - Recherche full-text

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
│            AIRFLOW SCHEDULER (Europe/Paris)              │
│         Exécution automatique toutes les heures          │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────┐
│  ÉTAPE 1-6 : SCRAPING HORAIRE (Selenium + Chrome)       │
│  • Extraction des followings Instagram                  │
│  • Prédiction de genre (ML)                              │
│  • Stockage Data Lake (RAW → FORMATTED → USAGE)         │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────┐
│  ÉTAPE 7 : AGRÉGATION QUOTIDIENNE (23h00)               │
│  • Fusion des 24 scrapings horaires                     │
│  • Déduplication par username                            │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────┐
│  ÉTAPE 8 : COMPARAISON J vs J-1 (23h00)                 │
│  • Détection nouveaux followings (added)                │
│  • Détection unfollows (deleted)                         │
└──────────────────────────────────────────────────────────┘
                          │
           ┌──────────────┼──────────────┐
           ▼              ▼              ▼
    ┌──────────┐   ┌─────────────┐   ┌──────────┐
    │PostgreSQL│   │Elasticsearch│   │ Dashboard│
    │  (SQL)   │   │  (Search)   │   │  (Web)   │
    └──────────┘   └─────────────┘   └──────────┘
```

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
- Scraping horaire : 00h00 à 23h00 (heure de Paris)
- Agrégation quotidienne : 23h00 (heure de Paris)
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
│   ├── instagram_scraping_ml_pipeline.py  # Script principal
│   └── setup_auto_open.sh       # Configuration auto-open 09h00
├── data/                        # Data Lake (généré automatiquement)
│   ├── raw/
│   ├── formatted/
│   └── usage/
├── instagram_accounts_to_scrape.txt  # Liste des comptes à surveiller
├── Makefile                     # Commandes d'automatisation
├── README.md                    # Ce fichier
└── QUICKSTART.md                # Guide rapide 3 minutes
```

---

## 📚 Documentation supplémentaire

- **[QUICKSTART.md](QUICKSTART.md)** - Guide de démarrage ultra-rapide (3 minutes)
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

Développé par [@YOUR_GITHUB_USERNAME](https://github.com/YOUR_GITHUB_USERNAME)

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

![GitHub stars](https://img.shields.io/github/stars/YOUR_USERNAME/Datalake_Instagram_Following_Surveillance?style=social)
![GitHub forks](https://img.shields.io/github/forks/YOUR_USERNAME/Datalake_Instagram_Following_Surveillance?style=social)
![GitHub issues](https://img.shields.io/github/issues/YOUR_USERNAME/Datalake_Instagram_Following_Surveillance)

---

**Dernière mise à jour** : Janvier 2025
