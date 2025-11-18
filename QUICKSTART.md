# ⚡ QUICKSTART - Démarrage en 10 minutes

Guide ultra-rapide pour lancer le pipeline de surveillance Instagram.

---

## 📋 Prérequis

Avant de commencer, assurez-vous d'avoir **uniquement** :

✅ **Docker Desktop** installé et **lancé**
✅ **Git** installé

**C'est tout !** Pas besoin de Python, Make, PostgreSQL, Elasticsearch... Tout est conteneurisé.

### Vérification rapide

```bash
# Vérifier Docker
docker --version
docker ps

# Vérifier Git
git --version
```

Si ces commandes fonctionnent, vous êtes prêt ! 🚀

---

## 🚀 Installation en 4 étapes

### **Étape 1 : Cloner le projet** (30 secondes)

```bash
git clone https://github.com/votre-username/Datalake_Instagram_Following_Surveillance.git
cd Datalake_Instagram_Following_Surveillance
```

---

### **Étape 2 : Obtenir les cookies Instagram** (2 minutes)

#### 2.1 Installer l'extension Chrome

Allez sur : https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc

Cliquez sur **"Ajouter à Chrome"**.

#### 2.2 Télécharger les cookies

1. Connectez-vous à **Instagram** : https://www.instagram.com
2. Cliquez sur l'icône de l'extension (en haut à droite)
3. Cliquez sur **"Get cookies.txt LOCALLY"**
4. Le fichier `www.instagram.com_cookies.txt` est téléchargé

#### 2.3 Placer les cookies dans le projet

```bash
# Créer le répertoire
mkdir -p docker/cookies

# Copier les cookies téléchargés
cp ~/Downloads/www.instagram.com_cookies.txt docker/cookies/
```

✅ **Vérification** :
```bash
ls -lh docker/cookies/www.instagram.com_cookies.txt
```

Vous devriez voir le fichier (environ 2-4 KB).

---

### **Étape 3 : Configurer les comptes à surveiller** (1 minute)

Ouvrez le fichier `instagram_accounts_to_scrape.txt` :

```bash
# Linux/macOS
nano instagram_accounts_to_scrape.txt

# Ou avec votre éditeur préféré
code instagram_accounts_to_scrape.txt
```

**Ajoutez les comptes Instagram** (un par ligne) :

```
nike
adidas
puma
```

Enregistrez et fermez (`Ctrl + X` puis `Y` pour nano).

✅ **Vérification** :
```bash
cat instagram_accounts_to_scrape.txt
```

---

### **Étape 4 : Lancer l'installation automatique** (5-7 minutes)

```bash
make install
```

**Cette commande va automatiquement** :

1. ✅ Détecter votre UID utilisateur : `id -u`
2. ✅ Générer le secret Airflow : `openssl rand -hex 32`
3. ✅ Créer automatiquement `docker/.env`
4. ✅ Créer les répertoires `data/`, `airflow/logs/`
5. ✅ Valider vos cookies Instagram
6. ✅ Construire les images Docker (Airflow, Dashboard, PostgreSQL, Elasticsearch, Kibana)
7. ✅ Démarrer tous les services

**Durée estimée** : 5-7 minutes (téléchargement + build Docker)

**Vous voyez** :
```
🔧 Installation complète du projet Instagram Surveillance...
✅ Configuration générée dans docker/.env
✅ Cookies Instagram valides
🐳 Construction des images Docker...
🚀 Démarrage des services...
✅ Tous les services sont démarrés !
```

---

## ✅ Vérification - Tout fonctionne ?

### Vérifier le statut des services

```bash
make status
```

**Attendu** :
```
NAME                        STATUS              PORTS
instagram-postgres          Up (healthy)        0.0.0.0:5433->5432/tcp
instagram-elasticsearch     Up (healthy)        0.0.0.0:9200->9200/tcp
instagram-kibana            Up (healthy)        0.0.0.0:5601->5601/tcp
instagram-airflow-scheduler Up (healthy)
instagram-airflow-webserver Up (healthy)        0.0.0.0:8082->8080/tcp
instagram-dashboard         Up (healthy)        0.0.0.0:8000->8000/tcp
```

**Tous doivent afficher** : `Up (healthy)` ✅

Si un service affiche `starting`, attendez 1-2 minutes et relancez `make status`.

---

## 🌐 Accéder aux interfaces

### Option A : Ouverture automatique

```bash
make open
```

Les 3 dashboards s'ouvrent automatiquement dans votre navigateur ! 🎉

### Option B : Ouverture manuelle

| Interface | URL | Credentials |
|-----------|-----|-------------|
| 📊 **Dashboard Instagram** | http://localhost:8000 | - |
| 🚀 **Airflow** | http://localhost:8082 | airflow / airflow |
| 📈 **Kibana** | http://localhost:5601 | - |

---

## 📊 Dashboard Instagram (http://localhost:8000)

**Attendu** :

- **Page d'accueil** : Vue globale avec cartes pour chaque compte
- **Stats globales** : Total followings, ajoutés/supprimés aujourd'hui
- **Distribution genre** : Hommes, femmes, inconnu
- **Cliquez sur un compte** pour voir la liste détaillée des followings

**Exemple** :
```
┌─────────────────────────────────────┐
│  📊 Instagram Surveillance          │
│                                     │
│  Total : 1,234 followings           │
│  Ajoutés aujourd'hui : 12           │
│  Supprimés aujourd'hui : 5          │
│                                     │
│  ┌─────────┐ ┌─────────┐ ┌────────┐│
│  │  nike   │ │ adidas  │ │ puma   ││
│  │  250    │ │  300    │ │  684   ││
│  └─────────┘ └─────────┘ └────────┘│
└─────────────────────────────────────┘
```

---

## 🚀 Airflow (http://localhost:8082)

**Login** : `airflow` / `airflow`

**Attendu** :

1. **DAG visible** : `instagram_scraping_surveillance_pipeline`
2. **Toggle ON** (vert) : Le DAG est activé
3. **Prochaine exécution** : Affichée automatiquement (dans l'heure)

**Le pipeline se lance automatiquement toutes les heures** !

---

## 🎯 Déclencher un scraping manuel (optionnel)

Pour tester immédiatement sans attendre l'exécution horaire :

```bash
make trigger-dag
```

**Attendu** :
```
🎯 Déclenchement manuel du DAG...
Created <DagRun instagram_scraping_surveillance_pipeline @ 2025-01-18 14:30:00>
✅ DAG déclenché
```

**Suivre l'exécution dans Airflow** :

1. Ouvrez http://localhost:8082
2. Cliquez sur le DAG `instagram_scraping_surveillance_pipeline`
3. Vous verrez les tâches en cours :
   - 🟢 = succès
   - 🔵 = en cours
   - 🔴 = échec

**Durée d'exécution** : 3-5 minutes (selon le nombre de followings)

---

## 📁 Vérifier les données scrapées

### Fichiers créés

```bash
# Voir les fichiers raw
ls -lh data/raw/instagram_followings/nike/

# Voir les fichiers formatted
ls -lh data/formatted/instagram_followings/nike/
```

**Attendu** :
```
data/raw/instagram_followings/nike/
└── 20250118/
    └── 1430/
        └── followings_pass_1.json

data/formatted/instagram_followings/nike/
└── 20250118/
    └── 1430/
        └── formatted_parquet_with_ML.parquet/
```

### PostgreSQL

```bash
# Se connecter à PostgreSQL
docker compose exec postgres psql -U airflow -d airflow

# Compter les followings
SELECT COUNT(*) FROM instagram_followings;

# Quitter
\q
```

### Elasticsearch

```bash
# Voir les index
curl http://localhost:9200/_cat/indices?v | grep instagram
```

**Attendu** :
```
instagram-followings
instagram-comparatif
```

---

## 🎉 C'est terminé !

**Félicitations !** Votre pipeline de surveillance Instagram est opérationnel.

### Ce qui se passe automatiquement

| Heure | Action |
|-------|--------|
| **00h00 - 22h00** | Scraping horaire (1 fois par heure) |
| **23h00** | Agrégation des 24 scrapings + Comparaison J vs J-1 |

**Vous n'avez rien à faire !** Le pipeline tourne 24/7.

---

## 🛠️ Commandes utiles

### Gestion quotidienne

```bash
make start              # Démarrer les services
make stop               # Arrêter les services
make status             # Voir le statut
make logs               # Voir les logs
make open               # Ouvrir les dashboards
```

### Maintenance

```bash
make validate-cookies   # Valider les cookies (à faire 1x/semaine)
make trigger-dag        # Forcer un scraping manuel
make restart            # Redémarrer après modification config
```

### Dépannage

```bash
make logs               # Tous les logs
make logs-airflow       # Logs Airflow uniquement
make rebuild            # Rebuild complet sans cache
make clean              # Supprimer volumes et données
make help               # Liste complète des commandes
```

---

## 🐛 Problèmes courants

### ❌ "Login required" lors du scraping

**Cause** : Cookies expirés

**Solution** :
```bash
# 1. Télécharger de nouveaux cookies depuis Instagram
# 2. Remplacer le fichier
cp ~/Downloads/www.instagram.com_cookies.txt docker/cookies/

# 3. Redémarrer
make restart
```

### ❌ Services ne démarrent pas (status "unhealthy")

**Solution** :
```bash
# Voir les logs
make logs

# Rebuild sans cache
make rebuild
make start
```

### ❌ Le DAG ne s'affiche pas dans Airflow

**Solution** :
```bash
# Vérifier les erreurs de parsing
docker compose exec airflow-scheduler airflow dags list-import-errors

# Redémarrer
make restart
```

### ❌ Port déjà utilisé (8000, 8082, etc.)

**Solution** :
```bash
# Voir quel processus utilise le port
lsof -i :8000

# Tuer le processus
kill -9 <PID>

# Ou relancer
make stop
make start
```

---

## 📚 Pour aller plus loin

- **Documentation complète** : [README.md](README.md)
- **Toutes les commandes** : `make help`
- **Timezone Europe/Paris** : Configuration automatique (UTC+1)
- **Auto-open à 09h00** : `make setup-auto-open` (optionnel)

---

## 📊 Checklist finale

- [ ] Docker Desktop lancé
- [ ] Cookies Instagram placés dans `docker/cookies/`
- [ ] Comptes ajoutés dans `instagram_accounts_to_scrape.txt`
- [ ] `make install` exécuté avec succès
- [ ] Tous les services : `Up (healthy)`
- [ ] Dashboard accessible : http://localhost:8000
- [ ] Airflow accessible : http://localhost:8082
- [ ] DAG activé dans Airflow
- [ ] Premier scraping déclenché (manuel ou auto)
- [ ] Données visibles dans le Dashboard

**Si tous les items sont cochés, vous êtes prêt ! 🎉**

---

## 🚀 Workflow optimal

### Jour 1 - Installation

```bash
git clone <repo>
cd Datalake_Instagram_Following_Surveillance
cp cookies.txt docker/cookies/www.instagram.com_cookies.txt
nano instagram_accounts_to_scrape.txt
make install
make open
```

### Jour 2-N - Utilisation normale

```bash
make start              # Matin : démarrer
make open               # Ouvrir les dashboards
make validate-cookies   # Vérifier les cookies (1x/semaine)
make stop               # Soir : arrêter (optionnel)
```

### Maintenance ponctuelle

```bash
make trigger-dag        # Forcer un scraping manuel
make restart            # Après modification config
make logs               # Debug
```

---

**Temps total d'installation** : **10 minutes** (dont 5-7 minutes de build Docker)

**Prêt à surveiller Instagram comme un pro !** 🚀
