#!/bin/bash

# =====================================================================
# Script d'installation sur Hetzner Cloud
# =====================================================================
# Automatise le déploiement du projet Instagram Surveillance sur Hetzner
# =====================================================================

set -e

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}🚀 Installation Hetzner Cloud${NC}"
echo -e "${BLUE}Instagram Following Surveillance${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# Fonction pour vérifier si on est root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo -e "${RED}❌ Ce script doit être exécuté en tant que root${NC}"
        echo "Utilisez: sudo $0"
        exit 1
    fi
}

# Fonction pour installer Docker
install_docker() {
    echo -e "${YELLOW}[1/5]${NC} Installation de Docker..."

    # Mettre à jour les packages
    apt-get update
    apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release

    # Ajouter la clé GPG officielle de Docker
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

    # Ajouter le repository Docker
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Installer Docker Engine
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Démarrer Docker
    systemctl start docker
    systemctl enable docker

    echo -e "${GREEN}✅ Docker installé${NC}"
}

# Fonction pour installer Docker Compose V2
install_docker_compose() {
    echo -e "${YELLOW}[2/5]${NC} Installation de Docker Compose..."

    # Docker Compose V2 est déjà installé avec docker-compose-plugin
    # Créer un alias pour la compatibilité
    echo 'alias docker-compose="docker compose"' >> /root/.bashrc

    # Vérifier l'installation
    docker compose version

    echo -e "${GREEN}✅ Docker Compose installé${NC}"
}

# Fonction pour configurer le firewall
configure_firewall() {
    echo -e "${YELLOW}[3/5]${NC} Configuration du firewall..."

    # Installer UFW si pas déjà installé
    apt-get install -y ufw

    # Règles de base
    ufw default deny incoming
    ufw default allow outgoing

    # Autoriser SSH (important!)
    ufw allow 22/tcp

    # Autoriser les ports du projet
    ufw allow 8000/tcp  # Dashboard
    ufw allow 8082/tcp  # Airflow
    ufw allow 5601/tcp  # Kibana (optionnel - commenter si non exposé)

    # Activer le firewall
    ufw --force enable

    echo -e "${GREEN}✅ Firewall configuré${NC}"
}

# Fonction pour cloner le projet
clone_project() {
    echo -e "${YELLOW}[4/5]${NC} Clonage du projet..."

    # Installer git si nécessaire
    apt-get install -y git

    # Demander l'URL du repository
    echo ""
    echo -e "${BLUE}Entrez l'URL de votre repository GitHub:${NC}"
    read -p "URL: " REPO_URL

    # Répertoire de destination
    PROJECT_DIR="/opt/instagram-surveillance"

    # Cloner le projet
    if [ -d "$PROJECT_DIR" ]; then
        echo -e "${YELLOW}⚠️  Le répertoire $PROJECT_DIR existe déjà${NC}"
        read -p "Voulez-vous le supprimer et recloner? (o/n): " choice
        if [ "$choice" = "o" ] || [ "$choice" = "O" ]; then
            rm -rf "$PROJECT_DIR"
            git clone "$REPO_URL" "$PROJECT_DIR"
        fi
    else
        git clone "$REPO_URL" "$PROJECT_DIR"
    fi

    cd "$PROJECT_DIR"

    echo -e "${GREEN}✅ Projet cloné dans $PROJECT_DIR${NC}"
}

# Fonction pour configurer les variables d'environnement
configure_env() {
    echo -e "${YELLOW}[5/5]${NC} Configuration des variables d'environnement..."

    PROJECT_DIR="/opt/instagram-surveillance"
    cd "$PROJECT_DIR"

    # Créer le fichier .env si il n'existe pas
    if [ ! -f "docker/.env" ]; then
        cat > docker/.env << 'EOF'
# Configuration Airflow
AIRFLOW_UID=50000
AIRFLOW_SECRET_KEY=change-this-secret-key-in-production

# Mode visuel (désactivé par défaut sur serveur)
VISUAL_MODE=false
DISPLAY=:0

# PostgreSQL
POSTGRES_USER=airflow
POSTGRES_PASSWORD=airflow
POSTGRES_DB=airflow

# Elasticsearch
ELASTIC_PASSWORD=changeme
EOF
        echo -e "${GREEN}✅ Fichier .env créé${NC}"
    else
        echo -e "${BLUE}ℹ️  Fichier .env déjà existant${NC}"
    fi

    # Créer le fichier de comptes si il n'existe pas
    if [ ! -f "instagram_accounts_to_scrape.txt" ]; then
        cat > instagram_accounts_to_scrape.txt << 'EOF'
# Ajoutez ici les comptes Instagram à surveiller (un par ligne)
# Exemple:
# nike
# adidas
# puma
EOF
        echo -e "${GREEN}✅ Fichier instagram_accounts_to_scrape.txt créé${NC}"
    fi

    echo ""
    echo -e "${BLUE}📝 Configuration terminée${NC}"
    echo -e "${YELLOW}⚠️  IMPORTANT: Éditez les fichiers suivants:${NC}"
    echo "   1. docker/.env - Changez les secrets et mots de passe"
    echo "   2. instagram_accounts_to_scrape.txt - Ajoutez vos comptes à surveiller"
}

# Fonction pour démarrer le projet
start_project() {
    echo ""
    echo -e "${BLUE}=========================================${NC}"
    echo -e "${GREEN}✅ Installation terminée !${NC}"
    echo -e "${BLUE}=========================================${NC}"
    echo ""

    echo -e "${YELLOW}📋 Prochaines étapes:${NC}"
    echo ""
    echo "1. Configurez vos variables d'environnement:"
    echo -e "   ${BLUE}nano /opt/instagram-surveillance/docker/.env${NC}"
    echo ""
    echo "2. Ajoutez vos comptes à surveiller:"
    echo -e "   ${BLUE}nano /opt/instagram-surveillance/instagram_accounts_to_scrape.txt${NC}"
    echo ""
    echo "3. Démarrez le projet:"
    echo -e "   ${BLUE}cd /opt/instagram-surveillance/docker${NC}"
    echo -e "   ${BLUE}docker compose up -d${NC}"
    echo ""
    echo "4. Surveillez les logs:"
    echo -e "   ${BLUE}docker compose logs -f${NC}"
    echo ""

    echo -e "${YELLOW}🌐 URLs d'accès:${NC}"
    echo ""
    SERVER_IP=$(curl -s ifconfig.me)
    echo -e "  Dashboard:     ${BLUE}http://$SERVER_IP:8000/${NC}"
    echo -e "  Airflow:       ${BLUE}http://$SERVER_IP:8082/${NC}"
    echo -e "  Kibana:        ${BLUE}http://$SERVER_IP:5601/${NC}"
    echo ""

    echo -e "${YELLOW}🔐 Credentials Airflow par défaut:${NC}"
    echo "  Username: airflow"
    echo "  Password: airflow"
    echo ""

    echo -e "${YELLOW}📊 Commandes utiles:${NC}"
    echo "  Arrêter:       docker compose stop"
    echo "  Redémarrer:    docker compose restart"
    echo "  Logs:          docker compose logs -f [service]"
    echo "  Status:        docker compose ps"
    echo ""
}

# Menu principal
main() {
    check_root

    echo -e "${YELLOW}Ce script va installer:${NC}"
    echo "  • Docker & Docker Compose"
    echo "  • Configuration du firewall (UFW)"
    echo "  • Clonage du projet Instagram Surveillance"
    echo "  • Configuration initiale"
    echo ""

    read -p "Continuer? (o/n): " confirm
    if [ "$confirm" != "o" ] && [ "$confirm" != "O" ]; then
        echo "Installation annulée"
        exit 0
    fi

    install_docker
    install_docker_compose
    configure_firewall
    clone_project
    configure_env
    start_project
}

# Lancer le script
main
