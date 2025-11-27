#!/bin/bash

# Script d'installation automatique pour Oracle Cloud Free Tier
# Usage: ./install_oracle_cloud.sh

set -e  # Arrêter en cas d'erreur

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}Installation Instagram Surveillance${NC}"
echo -e "${BLUE}Oracle Cloud Free Tier${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""

# Vérifier qu'on est sur Oracle Cloud (Ubuntu)
if [ ! -f /etc/lsb-release ]; then
    echo -e "${RED}❌ Ce script doit être exécuté sur Ubuntu${NC}"
    exit 1
fi

echo -e "${YELLOW}[1/10]${NC} Vérification de l'environnement..."
echo "OS: $(lsb_release -ds)"
echo "Kernel: $(uname -r)"
echo "Architecture: $(uname -m)"
echo ""

# Vérifier si c'est une VM ARM
if [ "$(uname -m)" != "aarch64" ]; then
    echo -e "${YELLOW}⚠️  Attention: Architecture $(uname -m) détectée${NC}"
    echo -e "${YELLOW}   Oracle Cloud Free Tier recommande ARM64 (aarch64)${NC}"
fi

echo -e "${GREEN}✅ Environnement vérifié${NC}"
echo ""

# Mise à jour du système
echo -e "${YELLOW}[2/10]${NC} Mise à jour du système..."
sudo apt update -qq
sudo apt upgrade -y -qq
echo -e "${GREEN}✅ Système mis à jour${NC}"
echo ""

# Installation de Docker
echo -e "${YELLOW}[3/10]${NC} Installation de Docker..."
if command -v docker &> /dev/null; then
    echo -e "${GREEN}✅ Docker déjà installé: $(docker --version)${NC}"
else
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo -e "${GREEN}✅ Docker installé${NC}"
fi
echo ""

# Installation de Docker Compose
echo -e "${YELLOW}[4/10]${NC} Installation de Docker Compose..."
if command -v docker-compose &> /dev/null; then
    echo -e "${GREEN}✅ Docker Compose déjà installé: $(docker-compose --version)${NC}"
else
    sudo apt install -y docker-compose
    echo -e "${GREEN}✅ Docker Compose installé${NC}"
fi
echo ""

# Installation des outils
echo -e "${YELLOW}[5/10]${NC} Installation des outils nécessaires..."
sudo apt install -y git make curl wget net-tools htop
echo -e "${GREEN}✅ Outils installés${NC}"
echo ""

# Configuration du pare-feu
echo -e "${YELLOW}[6/10]${NC} Configuration du pare-feu Ubuntu (ufw)..."
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 8000/tcp  # Dashboard
sudo ufw allow 8082/tcp  # Airflow
sudo ufw allow 5601/tcp  # Kibana
sudo ufw --force enable
echo -e "${GREEN}✅ Pare-feu configuré${NC}"
sudo ufw status
echo ""

# Configuration Elasticsearch
echo -e "${YELLOW}[7/10]${NC} Configuration système pour Elasticsearch..."
sudo sysctl -w vm.max_map_count=262144
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf > /dev/null
echo -e "${GREEN}✅ Configuration Elasticsearch appliquée${NC}"
echo ""

# Vérifier si le projet est déjà cloné
if [ -d "$HOME/Datalake_Instagram_Following_Surveillance" ]; then
    echo -e "${YELLOW}[8/10]${NC} Projet déjà cloné, mise à jour..."
    cd $HOME/Datalake_Instagram_Following_Surveillance
    git pull
else
    echo -e "${YELLOW}[8/10]${NC} Clonage du projet..."
    read -p "URL du repository Git (ou ENTER pour passer): " REPO_URL
    if [ -n "$REPO_URL" ]; then
        cd $HOME
        git clone $REPO_URL
        cd Datalake_Instagram_Following_Surveillance
    else
        echo -e "${YELLOW}⚠️  Clonage sauté - assurez-vous que le projet est présent${NC}"
    fi
fi
echo -e "${GREEN}✅ Projet prêt${NC}"
echo ""

# Créer les répertoires nécessaires
echo -e "${YELLOW}[9/10]${NC} Création des répertoires..."
mkdir -p docker/cookies
mkdir -p data/{raw,formatted,usage}
mkdir -p airflow/logs
echo -e "${GREEN}✅ Répertoires créés${NC}"
echo ""

# Génération des variables d'environnement
echo -e "${YELLOW}[10/10]${NC} Génération des variables d'environnement..."
AIRFLOW_SECRET=$(openssl rand -hex 32)
cat > docker/.env << EOF
AIRFLOW_UID=50000
AIRFLOW_SECRET_KEY=$AIRFLOW_SECRET
VISUAL_MODE=false
EOF
echo -e "${GREEN}✅ Fichier .env créé${NC}"
echo ""

# Vérifier si docker-compose.cloud.yml existe
if [ ! -f "docker/docker-compose.cloud.yml" ]; then
    echo -e "${RED}❌ Fichier docker-compose.cloud.yml manquant${NC}"
    echo -e "${YELLOW}Veuillez copier docker-compose.cloud.yml depuis la documentation${NC}"
    echo -e "${YELLOW}Voir: docs/DEPLOIEMENT_ORACLE_CLOUD.md${NC}"
fi

echo ""
echo -e "${BLUE}==========================================${NC}"
echo -e "${GREEN}✅ Installation terminée avec succès!${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""
echo -e "${YELLOW}📋 Prochaines étapes:${NC}"
echo ""
echo "1️⃣  Transférer les cookies Instagram:"
echo "   ${BLUE}scp cookies.txt ubuntu@<PUBLIC_IP>:~/Datalake_Instagram_Following_Surveillance/docker/cookies/www.instagram.com_cookies.txt${NC}"
echo ""
echo "2️⃣  Éditer la liste des comptes à surveiller:"
echo "   ${BLUE}nano instagram_accounts_to_scrape.txt${NC}"
echo ""
echo "3️⃣  Vérifier docker-compose.cloud.yml:"
echo "   ${BLUE}cat docker/docker-compose.cloud.yml${NC}"
echo ""
echo "4️⃣  Construire les images Docker:"
echo "   ${BLUE}cd docker && docker-compose -f docker-compose.cloud.yml build${NC}"
echo ""
echo "5️⃣  Démarrer les services:"
echo "   ${BLUE}docker-compose -f docker-compose.cloud.yml up -d${NC}"
echo ""
echo "6️⃣  Vérifier le statut:"
echo "   ${BLUE}docker ps${NC}"
echo ""
echo "7️⃣  Accéder aux interfaces depuis votre navigateur:"
echo "   📊 Dashboard: ${BLUE}http://$(curl -s ifconfig.me):8000${NC}"
echo "   🚀 Airflow:   ${BLUE}http://$(curl -s ifconfig.me):8082${NC}"
echo "   📈 Kibana:    ${BLUE}http://$(curl -s ifconfig.me):5601${NC}"
echo ""
echo -e "${GREEN}🎉 Bon déploiement sur Oracle Cloud !${NC}"
echo ""
