# 🌩️ Déploiement sur Oracle Cloud Free Tier

> Guide complet pour déployer le pipeline Instagram Surveillance sur Oracle Cloud Infrastructure (OCI) Free Tier

## 📊 Analyse des ressources nécessaires

### Utilisation actuelle (locale)

| Service | RAM | CPU | Storage |
|---------|-----|-----|---------|
| PostgreSQL | ~65 MB | 0.5% | 500 MB |
| Elasticsearch | ~1.1 GB | 2% | 1 GB |
| Kibana | ~1.2 GB | 0.5% | 200 MB |
| Airflow Scheduler | ~800 MB | 2% | 500 MB |
| Airflow Webserver | ~520 MB | 0.6% | 200 MB |
| Dashboard Flask | ~70 MB | 0.1% | 50 MB |
| **TOTAL** | **~3.75 GB** | **~6%** | **~2.5 GB** |

### Oracle Cloud Free Tier - Limites

#### Option 1: VM x86 (Standard.E2.1.Micro) ❌
- **2 instances** × 1 GB RAM = **2 GB total**
- **1 OCPU** par instance
- **Verdict** : **Insuffisant** pour notre projet

#### Option 2: VM ARM (Standard.A1.Flex) ✅ **RECOMMANDÉ**
- **1 instance** avec jusqu'à :
  - **4 OCPU** (Always Free)
  - **24 GB RAM** (Always Free)
  - **200 GB Block Storage** (Always Free)
- **Verdict** : **Parfait !** Largement suffisant

---

## 🎯 Architecture de déploiement recommandée

### Configuration VM Oracle Cloud

```
┌─────────────────────────────────────────────────────┐
│  Oracle Cloud VM.Standard.A1.Flex (ARM64)           │
│  • Shape: VM.Standard.A1.Flex                       │
│  • OCPU: 4 (Always Free)                            │
│  • RAM: 6 GB (sur 24 GB disponibles)                │
│  • Storage: 50 GB Boot + 50 GB Block Volume         │
│  • OS: Ubuntu 22.04 LTS (ARM64)                     │
│  • Région: eu-paris-1 (Europe - Paris)              │
└─────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│  Services Docker avec limites de ressources         │
│  ┌─────────────────────────────────────────────┐   │
│  │ PostgreSQL      : 256 MB  |  0.5 OCPU       │   │
│  │ Elasticsearch   : 1.5 GB  |  1.0 OCPU       │   │
│  │ Kibana          : 1.5 GB  |  0.5 OCPU       │   │
│  │ Airflow Sched.  : 1.0 GB  |  1.0 OCPU       │   │
│  │ Airflow Web     : 768 MB  |  0.5 OCPU       │   │
│  │ Dashboard       : 256 MB  |  0.25 OCPU      │   │
│  │ Total           : 5.3 GB  |  3.75 OCPU      │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

---

## 🚀 Étapes de déploiement

### Prérequis

- ✅ Compte Oracle Cloud créé : https://cloud.oracle.com
- ✅ Tenancy : `pascal-obistro`
- ✅ Région : `eu-paris-1` (Europe - Paris)
- ✅ Cookies Instagram valides

### Étape 1 : Créer la VM Oracle Cloud

#### 1.1 Créer une instance Compute

1. **Connectez-vous** à Oracle Cloud Console : https://cloud.oracle.com
2. **Menu** → **Compute** → **Instances**
3. **Create Instance**

**Configuration** :
```
Name: instagram-surveillance-vm
Placement:
  - Availability Domain: Any
  - Fault Domain: Let Oracle choose

Image and Shape:
  - Image: Ubuntu 22.04 (Canonical)
  - Shape: VM.Standard.A1.Flex (ARM64)
    • OCPU: 4 (max Always Free)
    • Memory: 6 GB (ou plus si besoin)

Networking:
  - VCN: Create new VCN (default settings)
  - Subnet: Public Subnet
  - Assign public IPv4 address: YES

Add SSH keys:
  - Paste SSH public key (générer avec `ssh-keygen` si besoin)

Boot volume:
  - Size: 50 GB
```

4. **Create** → Attendre 2-3 minutes

#### 1.2 Configurer le pare-feu (Security List)

1. **Networking** → **Virtual Cloud Networks** → Votre VCN
2. **Security Lists** → **Default Security List**
3. **Add Ingress Rules** :

```
Ingress Rule 1 - SSH
Source CIDR: 0.0.0.0/0
IP Protocol: TCP
Destination Port: 22

Ingress Rule 2 - Dashboard
Source CIDR: 0.0.0.0/0
IP Protocol: TCP
Destination Port: 8000

Ingress Rule 3 - Airflow
Source CIDR: 0.0.0.0/0
IP Protocol: TCP
Destination Port: 8082

Ingress Rule 4 - Kibana
Source CIDR: 0.0.0.0/0
IP Protocol: TCP
Destination Port: 5601
```

#### 1.3 Noter l'adresse IP publique

```bash
# Exemple
Public IP: 152.70.123.45
```

---

### Étape 2 : Se connecter à la VM

```bash
# Depuis votre machine locale
ssh -i ~/.ssh/id_rsa ubuntu@<PUBLIC_IP>

# Exemple
ssh -i ~/.ssh/id_rsa ubuntu@152.70.123.45
```

---

### Étape 3 : Installer Docker sur la VM

```bash
# Se connecter en tant qu'ubuntu
sudo apt update
sudo apt upgrade -y

# Installer Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Ajouter l'utilisateur au groupe docker
sudo usermod -aG docker ubuntu

# Installer Docker Compose
sudo apt install docker-compose -y

# Vérifier l'installation
docker --version
docker-compose --version

# Redémarrer la session pour appliquer les permissions
exit
# Se reconnecter
ssh -i ~/.ssh/id_rsa ubuntu@<PUBLIC_IP>
```

---

### Étape 4 : Configurer le pare-feu Ubuntu (ufw)

```bash
# Autoriser les ports nécessaires
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 8000/tcp  # Dashboard
sudo ufw allow 8082/tcp  # Airflow
sudo ufw allow 5601/tcp  # Kibana

# Activer le pare-feu
sudo ufw --force enable

# Vérifier le statut
sudo ufw status
```

---

### Étape 5 : Cloner et configurer le projet

```bash
# Installer Git
sudo apt install git make -y

# Cloner le projet
git clone https://github.com/YOUR_USERNAME/Datalake_Instagram_Following_Surveillance.git
cd Datalake_Instagram_Following_Surveillance

# Créer les répertoires nécessaires
mkdir -p docker/cookies
mkdir -p data/{raw,formatted,usage}
mkdir -p airflow/logs
```

---

### Étape 6 : Transférer les cookies Instagram

**Depuis votre machine locale** :

```bash
# Copier les cookies vers la VM
scp -i ~/.ssh/id_rsa \
  ~/Downloads/www.instagram.com_cookies.txt \
  ubuntu@<PUBLIC_IP>:~/Datalake_Instagram_Following_Surveillance/docker/cookies/

# Vérifier
ssh -i ~/.ssh/id_rsa ubuntu@<PUBLIC_IP> \
  "ls -lh ~/Datalake_Instagram_Following_Surveillance/docker/cookies/"
```

---

### Étape 7 : Créer le docker-compose optimisé pour Oracle Cloud

**Sur la VM**, créer le fichier `docker/docker-compose.cloud.yml` :

```bash
cd ~/Datalake_Instagram_Following_Surveillance
cat > docker/docker-compose.cloud.yml << 'EOF'
version: '3.8'

x-airflow-common:
  &airflow-common
  build:
    context: .
    dockerfile: Dockerfile
  environment:
    &airflow-common-env
    AIRFLOW__CORE__EXECUTOR: LocalExecutor
    AIRFLOW__CORE__LOAD_EXAMPLES: 'false'
    AIRFLOW__CORE__DEFAULT_TIMEZONE: Europe/Paris
    AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://airflow:airflow@postgres:5432/airflow
    AIRFLOW__WEBSERVER__SECRET_KEY: '${AIRFLOW_SECRET_KEY}'
    VISUAL_MODE: 'false'
  volumes:
    - ../scripts:/opt/airflow/scripts
    - ../airflow/dags:/opt/airflow/dags
    - ../airflow/logs:/opt/airflow/logs
    - ../data:/opt/airflow/data
    - ./cookies:/opt/airflow/cookies
    - ../instagram_accounts_to_scrape.txt:/opt/airflow/instagram_accounts_to_scrape.txt
  user: "50000:0"
  depends_on:
    &airflow-common-depends-on
    postgres:
      condition: service_healthy
  # Limites de ressources
  deploy:
    resources:
      limits:
        cpus: '1.0'
        memory: 1024M
      reservations:
        cpus: '0.5'
        memory: 512M

services:
  # PostgreSQL Database
  postgres:
    image: postgres:14-alpine
    container_name: instagram-postgres
    environment:
      POSTGRES_USER: airflow
      POSTGRES_PASSWORD: airflow
      POSTGRES_DB: airflow
    volumes:
      - postgres-db-volume:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "airflow"]
      interval: 10s
      retries: 5
    restart: always
    ports:
      - "5433:5432"
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 256M
        reservations:
          cpus: '0.25'
          memory: 128M

  # Elasticsearch (optimisé)
  elasticsearch:
    image: elasticsearch:8.11.0
    container_name: instagram-elasticsearch
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms512m -Xmx1024m"  # Réduit pour Free Tier
      - bootstrap.memory_lock=true
    volumes:
      - elasticsearch-data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:9200/_cluster/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5
    restart: always
    ulimits:
      memlock:
        soft: -1
        hard: -1
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1536M
        reservations:
          cpus: '0.5'
          memory: 1024M

  # Kibana (optimisé)
  kibana:
    image: kibana:8.11.0
    container_name: instagram-kibana
    environment:
      ELASTICSEARCH_HOSTS: http://elasticsearch:9200
      NODE_OPTIONS: "--max-old-space-size=1024"  # Limite mémoire JS
    ports:
      - "5601:5601"
    depends_on:
      elasticsearch:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:5601/api/status || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5
    restart: always
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 1536M
        reservations:
          cpus: '0.25'
          memory: 1024M

  # Airflow Webserver
  airflow-webserver:
    <<: *airflow-common
    container_name: instagram-airflow-webserver
    command: webserver
    ports:
      - "8082:8080"
    healthcheck:
      test: ["CMD", "curl", "--fail", "http://localhost:8080/health"]
      interval: 15s
      timeout: 10s
      retries: 5
    restart: always
    depends_on:
      <<: *airflow-common-depends-on
      airflow-init:
        condition: service_completed_successfully
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 768M
        reservations:
          cpus: '0.25'
          memory: 512M

  # Airflow Scheduler
  airflow-scheduler:
    <<: *airflow-common
    container_name: instagram-airflow-scheduler
    command: scheduler
    healthcheck:
      test: ["CMD-SHELL", 'airflow jobs check --job-type SchedulerJob --hostname "$${HOSTNAME}"']
      interval: 15s
      timeout: 10s
      retries: 5
    restart: always
    depends_on:
      <<: *airflow-common-depends-on
      airflow-init:
        condition: service_completed_successfully

  # Airflow Initialization
  airflow-init:
    <<: *airflow-common
    container_name: instagram-airflow-init
    entrypoint: /bin/bash
    command:
      - -c
      - |
        mkdir -p /opt/airflow/logs /opt/airflow/dags /opt/airflow/data
        chown -R "50000:0" /opt/airflow/{logs,dags,data}
        exec /entrypoint airflow version
    environment:
      <<: *airflow-common-env
      _AIRFLOW_DB_MIGRATE: 'true'
      _AIRFLOW_WWW_USER_CREATE: 'true'
      _AIRFLOW_WWW_USER_USERNAME: airflow
      _AIRFLOW_WWW_USER_PASSWORD: airflow
    user: "0:0"
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M

  # Dashboard Flask
  dashboard:
    build:
      context: ../dashboard
      dockerfile: Dockerfile
    container_name: instagram-dashboard
    environment:
      POSTGRES_HOST: postgres
      POSTGRES_PORT: 5432
      POSTGRES_DB: airflow
      POSTGRES_USER: airflow
      POSTGRES_PASSWORD: airflow
      FLASK_SECRET_KEY: ${AIRFLOW_SECRET_KEY}
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "--fail", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: always
    deploy:
      resources:
        limits:
          cpus: '0.25'
          memory: 256M
        reservations:
          cpus: '0.1'
          memory: 128M

volumes:
  postgres-db-volume:
  elasticsearch-data:

networks:
  default:
    name: instagram-surveillance-network
EOF
```

---

### Étape 8 : Configurer les comptes à surveiller

```bash
# Éditer la liste des comptes
nano instagram_accounts_to_scrape.txt

# Ajouter vos comptes (un par ligne)
# Exemple:
# nike
# adidas
# le.corre_en.longueur
# mariadlaura
```

---

### Étape 9 : Générer les variables d'environnement

```bash
# Générer le secret Airflow
AIRFLOW_SECRET=$(openssl rand -hex 32)

# Créer le fichier .env
cat > docker/.env << EOF
AIRFLOW_UID=50000
AIRFLOW_SECRET_KEY=$AIRFLOW_SECRET
VISUAL_MODE=false
EOF

# Vérifier
cat docker/.env
```

---

### Étape 10 : Lancer l'installation

```bash
# Se placer dans le répertoire docker
cd ~/Datalake_Instagram_Following_Surveillance/docker

# Construire les images
docker-compose -f docker-compose.cloud.yml build

# Démarrer tous les services
docker-compose -f docker-compose.cloud.yml up -d

# Suivre les logs
docker-compose -f docker-compose.cloud.yml logs -f
```

**Durée estimée** : 10-15 minutes (build des images)

---

### Étape 11 : Vérifier que tout fonctionne

```bash
# Vérifier le statut des containers
docker ps

# Tous doivent être "Up (healthy)"

# Tester les endpoints
curl http://localhost:8000/health  # Dashboard
curl http://localhost:8082/health  # Airflow
curl http://localhost:9200         # Elasticsearch
curl http://localhost:5601/api/status  # Kibana
```

---

## 🌐 Accès aux interfaces

Depuis votre navigateur local :

| Interface | URL |
|-----------|-----|
| 📊 Dashboard | `http://<PUBLIC_IP>:8000` |
| 🚀 Airflow | `http://<PUBLIC_IP>:8082` (airflow / airflow) |
| 📈 Kibana | `http://<PUBLIC_IP>:5601` |

**Exemple** : `http://152.70.123.45:8000`

---

## 🔧 Maintenance et monitoring

### Voir les logs

```bash
cd ~/Datalake_Instagram_Following_Surveillance/docker

# Tous les services
docker-compose -f docker-compose.cloud.yml logs -f

# Un service spécifique
docker-compose -f docker-compose.cloud.yml logs -f airflow-scheduler
```

### Redémarrer les services

```bash
# Redémarrer tout
docker-compose -f docker-compose.cloud.yml restart

# Redémarrer un service
docker-compose -f docker-compose.cloud.yml restart airflow-scheduler
```

### Arrêter les services

```bash
docker-compose -f docker-compose.cloud.yml down

# Avec suppression des volumes (⚠️ SUPPRIME LES DONNÉES)
docker-compose -f docker-compose.cloud.yml down -v
```

### Monitoring des ressources

```bash
# Utilisation CPU/RAM en temps réel
docker stats

# Utilisation disque
df -h
du -sh ~/Datalake_Instagram_Following_Surveillance/data/*
```

---

## 💰 Coûts estimés

### Always Free (0€/mois)

- ✅ VM.Standard.A1.Flex : 4 OCPU + 24 GB RAM
- ✅ Boot Volume : 50 GB
- ✅ Block Volume : 50 GB
- ✅ Network : 10 TB sortant/mois

**Total** : **0€/mois** tant que vous restez dans les limites Always Free

---

## 🔐 Sécurité

### Recommandations de production

1. **Changer les mots de passe** :
   ```bash
   # Airflow : Modifier docker/.env
   # PostgreSQL : Modifier docker-compose.cloud.yml
   ```

2. **Configurer HTTPS** (optionnel) :
   ```bash
   sudo apt install certbot nginx -y
   # Configurer un reverse proxy Nginx avec Let's Encrypt
   ```

3. **Restreindre les accès** :
   - Modifier les Security Lists Oracle Cloud
   - Restreindre SSH à votre IP uniquement
   - Utiliser un VPN ou bastion host

4. **Sauvegardes régulières** :
   ```bash
   # Backup PostgreSQL
   docker exec instagram-postgres pg_dump -U airflow airflow > backup.sql

   # Backup données
   tar -czf data-backup.tar.gz ~/Datalake_Instagram_Following_Surveillance/data/
   ```

---

## 🐛 Troubleshooting

### Les containers ne démarrent pas (Out of Memory)

**Solution** : Réduire les limites de mémoire dans `docker-compose.cloud.yml`

```yaml
# Exemple pour Elasticsearch
deploy:
  resources:
    limits:
      memory: 1024M  # Au lieu de 1536M
```

### Elasticsearch ne démarre pas

**Vérifier** :
```bash
docker logs instagram-elasticsearch

# Si "max virtual memory areas vm.max_map_count [65530] is too low"
sudo sysctl -w vm.max_map_count=262144
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
```

### Cookies Instagram expirés

```bash
# Copier de nouveaux cookies depuis votre machine locale
scp -i ~/.ssh/id_rsa \
  ~/Downloads/www.instagram.com_cookies.txt \
  ubuntu@<PUBLIC_IP>:~/Datalake_Instagram_Following_Surveillance/docker/cookies/

# Redémarrer les services
docker-compose -f docker-compose.cloud.yml restart
```

---

## 📊 Comparaison Local vs Cloud

| Critère | Local (Dev) | Oracle Cloud (Prod) |
|---------|-------------|---------------------|
| **RAM** | 16 GB | 6 GB (optimisé) |
| **CPU** | 8 cores | 4 OCPU ARM |
| **Storage** | SSD local | 100 GB Block Storage |
| **Coût** | 0€ | 0€ (Always Free) |
| **Disponibilité** | 8h/jour | 24/7 |
| **IP publique** | Non | Oui |
| **Sauvegarde** | Manuelle | Automatique (Oracle) |

---

## ✅ Checklist de déploiement

- [ ] Compte Oracle Cloud créé
- [ ] VM ARM créée (4 OCPU, 6 GB RAM)
- [ ] Security Lists configurées (ports 22, 8000, 8082, 5601)
- [ ] SSH fonctionnel vers la VM
- [ ] Docker et Docker Compose installés
- [ ] Projet cloné sur la VM
- [ ] Cookies Instagram transférés
- [ ] `docker-compose.cloud.yml` créé
- [ ] Variables d'environnement configurées (`.env`)
- [ ] Comptes à surveiller ajoutés (`instagram_accounts_to_scrape.txt`)
- [ ] Services démarrés (`docker-compose up -d`)
- [ ] Dashboard accessible depuis le navigateur
- [ ] Airflow accessible et DAG activé
- [ ] Premier scraping exécuté avec succès

---

**Félicitations !** 🎉 Votre pipeline Instagram Surveillance est maintenant déployé sur Oracle Cloud et tourne 24/7 gratuitement.

**Dernière mise à jour** : Novembre 2025
