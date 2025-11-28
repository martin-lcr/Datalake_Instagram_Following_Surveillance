# Déploiement sur Hetzner Cloud

Guide complet pour déployer le projet Instagram Following Surveillance sur Hetzner Cloud.

## 🎯 Pourquoi Hetzner Cloud ?

- ✅ **Excellent rapport qualité/prix** : À partir de 3,79€/mois
- ✅ **Bande passante généreuse** : 20 TB/mois inclus
- ✅ **Performance** : Serveurs en Allemagne, faible latence Europe
- ✅ **Simplicité** : Interface intuitive, API bien documentée
- ✅ **Fiabilité** : Provider européen établi depuis 1997

## 📋 Prérequis

- Un compte Hetzner Cloud ([inscription ici](https://www.hetzner.com/cloud))
- Méthode de paiement (carte bancaire ou PayPal)
- Votre projet Git poussé sur GitHub/GitLab

## 💰 Choix du serveur

### Recommandé : **CX21** (4,90€/mois)

```
2 vCPU
4 GB RAM
40 GB SSD
20 TB de trafic/mois
```

**Parfait pour :**
- 3-10 comptes Instagram
- Scrapings toutes les 4h
- Historique 3-6 mois

### Alternative : **CX31** (8,90€/mois)

```
2 vCPU
8 GB RAM
80 GB SSD
20 TB de trafic/mois
```

**Recommandé si :**
- Plus de 10 comptes
- Historique > 6 mois
- Analyses intensives

### Budget serré : **CX11** (3,79€/mois)

```
1 vCPU
2 GB RAM
20 GB SSD
20 TB de trafic/mois
```

**Limitation :**
- Maximum 3-5 comptes
- Scrapings moins fréquents recommandés

## 🚀 Déploiement en 5 minutes

### Étape 1 : Créer le serveur

#### Via l'interface web

1. Connexion à [Hetzner Cloud Console](https://console.hetzner.cloud)
2. Créer un nouveau projet : "Instagram Surveillance"
3. Cliquer sur "Add Server"

**Configuration :**
- **Location** : Nuremberg (de préférence, le plus proche)
- **Image** : Ubuntu 22.04
- **Type** : Standard - CX21 (recommandé)
- **Networking** :
  - IPv4 : ✅
  - IPv6 : ✅ (optionnel)
- **SSH Key** : Ajouter votre clé publique SSH
- **Name** : `instagram-scraper-prod`

4. Cliquer sur "Create & Buy now"

#### Via CLI (alternatif)

```bash
# Installer hcloud CLI
brew install hcloud  # macOS
# ou
snap install hcloud  # Linux

# Authentification
hcloud context create instagram-project

# Créer le serveur
hcloud server create \
  --name instagram-scraper-prod \
  --type cx21 \
  --image ubuntu-22.04 \
  --ssh-key your-ssh-key-name \
  --location nbg1
```

### Étape 2 : Connexion SSH

```bash
# Récupérer l'IP du serveur (affichée après création)
ssh root@<SERVER_IP>
```

### Étape 3 : Exécution du script d'installation

```bash
# Télécharger et exécuter le script
curl -fsSL https://raw.githubusercontent.com/VOTRE-USERNAME/Datalake_Instagram_Following_Surveillance/main/scripts/install_hetzner_cloud.sh -o install.sh

chmod +x install.sh
sudo ./install.sh
```

**Le script va automatiquement :**
1. ✅ Installer Docker & Docker Compose
2. ✅ Configurer le firewall (UFW)
3. ✅ Cloner votre projet
4. ✅ Créer les fichiers de configuration

### Étape 4 : Configuration

#### 1. Variables d'environnement

```bash
nano /opt/instagram-surveillance/docker/.env
```

**À modifier obligatoirement :**
```bash
# Générer une clé secrète unique
AIRFLOW_SECRET_KEY=$(openssl rand -hex 32)

# PostgreSQL (changez les mots de passe !)
POSTGRES_PASSWORD=votre-mot-de-passe-fort

# Elasticsearch
ELASTIC_PASSWORD=votre-autre-mot-de-passe-fort
```

#### 2. Comptes à surveiller

```bash
nano /opt/instagram-surveillance/instagram_accounts_to_scrape.txt
```

Ajoutez vos comptes (un par ligne) :
```
nike
adidas
mariadlaura
```

### Étape 5 : Démarrage du projet

```bash
cd /opt/instagram-surveillance/docker
docker compose up -d
```

**Attendre ~2 minutes** que tous les services démarrent.

#### Vérifier le statut

```bash
docker compose ps
```

Tous les services doivent être "Up" et "healthy".

## 🌐 Accès aux interfaces

Remplacez `<SERVER_IP>` par l'IP de votre serveur :

- **Dashboard** : http://&lt;SERVER_IP&gt;:8000
- **Airflow** : http://&lt;SERVER_IP&gt;:8082
  - Username : `airflow`
  - Password : `airflow`
- **Kibana** : http://&lt;SERVER_IP&gt;:5601

## 🔐 Sécurité

### 1. Changer les mots de passe Airflow

```bash
docker exec instagram-airflow-webserver airflow users create \
  --username admin \
  --firstname Admin \
  --lastname User \
  --role Admin \
  --email admin@example.com \
  --password VOTRE_MOT_DE_PASSE
```

### 2. Configurer HTTPS (optionnel mais recommandé)

#### Installer Nginx + Certbot

```bash
apt-get install -y nginx certbot python3-certbot-nginx

# Configurer un nom de domaine (ex: scraper.votredomaine.com)
# Pointer le DNS A record vers l'IP du serveur

# Obtenir un certificat SSL gratuit
certbot --nginx -d scraper.votredomaine.com
```

#### Configuration Nginx

```bash
nano /etc/nginx/sites-available/instagram-dashboard
```

```nginx
server {
    server_name scraper.votredomaine.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/scraper.votredomaine.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/scraper.votredomaine.com/privkey.pem;
}

server {
    listen 80;
    server_name scraper.votredomaine.com;
    return 301 https://$server_name$request_uri;
}
```

```bash
ln -s /etc/nginx/sites-available/instagram-dashboard /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx
```

### 3. Restreindre les accès par IP (optionnel)

```bash
# Autoriser seulement votre IP
ufw delete allow 8000
ufw delete allow 8082
ufw allow from VOTRE_IP to any port 8000
ufw allow from VOTRE_IP to any port 8082
```

## 📊 Monitoring

### Logs en temps réel

```bash
# Tous les services
docker compose logs -f

# Service spécifique
docker compose logs -f airflow-scheduler
docker compose logs -f dashboard
```

### Espace disque

```bash
# Vérifier l'espace
df -h

# Nettoyer les anciennes images Docker
docker system prune -a
```

### Mémoire et CPU

```bash
# Installer htop
apt-get install -y htop

# Monitoring
htop
```

## 🔄 Maintenance

### Mettre à jour le projet

```bash
cd /opt/instagram-surveillance
git pull origin main
docker compose down
docker compose build
docker compose up -d
```

### Sauvegardes automatiques

#### 1. Sauvegarder la base de données

```bash
# Créer un script de backup
nano /opt/backup-db.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup PostgreSQL
docker exec instagram-postgres pg_dump -U airflow airflow | gzip > $BACKUP_DIR/db_backup_$DATE.sql.gz

# Garder seulement les 7 derniers jours
find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR/db_backup_$DATE.sql.gz"
```

```bash
chmod +x /opt/backup-db.sh
```

#### 2. Automatiser avec cron

```bash
crontab -e
```

Ajouter :
```cron
# Backup quotidien à 3h du matin
0 3 * * * /opt/backup-db.sh >> /var/log/backup.log 2>&1
```

### Restaurer une sauvegarde

```bash
# Copier le backup dans le container
docker cp /opt/backups/db_backup_XXXXXXXX.sql.gz instagram-postgres:/tmp/

# Restaurer
docker exec instagram-postgres bash -c "gunzip < /tmp/db_backup_XXXXXXXX.sql.gz | psql -U airflow airflow"
```

## 📈 Optimisation des coûts

### Snapshots Hetzner

Créer un snapshot du serveur configuré (1€/mois pour 20GB) :

```bash
hcloud server create-image instagram-scraper-prod --description "Configured Instagram Scraper"
```

**Avantage** : Recréer rapidement un nouveau serveur identique

### Arrêter temporairement

Si vous n'avez pas besoin du scraping pendant une période :

```bash
# Arrêter les services
docker compose stop

# Shutdown du serveur (Hetzner ne facture pas les serveurs éteints)
shutdown -h now
```

**Note** : Le stockage reste facturé (~0,10€/GB/mois)

## ❓ Dépannage

### Services qui ne démarrent pas

```bash
# Vérifier les logs
docker compose logs

# Redémarrer un service spécifique
docker compose restart airflow-scheduler

# Rebuild complet
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Manque de mémoire

```bash
# Vérifier la RAM
free -h

# Si < 500MB libre, upgrader vers CX31 (8GB RAM)
```

### Espace disque plein

```bash
# Nettoyer Docker
docker system prune -a --volumes

# Nettoyer les logs Airflow
rm -rf /opt/instagram-surveillance/airflow/logs/*

# Analyser l'espace
du -sh /opt/instagram-surveillance/* | sort -h
```

## 📞 Support

### Hetzner Cloud

- **Documentation** : https://docs.hetzner.com/cloud/
- **Status** : https://status.hetzner.com/
- **Support** : Via console Hetzner (réponse < 24h)

### Ressources

- [Hetzner Community](https://community.hetzner.com/)
- [Documentation Docker](https://docs.docker.com/)
- [Airflow Documentation](https://airflow.apache.org/)

## 🎉 Félicitations !

Votre système de surveillance Instagram est maintenant déployé sur Hetzner Cloud !

**Prochaines étapes :**
1. Configurez vos cookies Instagram (voir README.md)
2. Lancez votre premier scraping depuis le dashboard
3. Configurez les sauvegardes automatiques
4. Optionnel : Configurez HTTPS avec Nginx

---

**Auteur** : Claude Code
**Date** : 27 novembre 2025
**Version** : 1.0
