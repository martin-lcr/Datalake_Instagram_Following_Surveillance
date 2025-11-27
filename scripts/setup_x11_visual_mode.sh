#!/bin/bash

# =====================================================================
# Script de configuration X11 pour le mode visuel
# =====================================================================
# Configure automatiquement X11/DISPLAY pour permettre au scraper
# Instagram d'afficher Chrome en mode visuel
# =====================================================================

set -e

# Couleurs pour l'affichage
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Configuration X11 pour mode visuel${NC}"
echo -e "${BLUE}Instagram Following Surveillance${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# 1. Vérifier que X11 est disponible sur l'hôte
echo -e "${YELLOW}[1/5]${NC} Vérification du serveur X11..."

if [ -z "$DISPLAY" ]; then
    echo -e "${RED}❌ Variable DISPLAY non définie${NC}"
    echo -e "${YELLOW}Solution: Exporter DISPLAY${NC}"
    echo "export DISPLAY=:0"
    exit 1
fi

if [ ! -d "/tmp/.X11-unix" ]; then
    echo -e "${RED}❌ Répertoire /tmp/.X11-unix introuvable${NC}"
    echo -e "${YELLOW}Solution: Installer et démarrer un serveur X11${NC}"
    echo "Pour WSL2: Installer VcXsrv ou X410 sur Windows"
    exit 1
fi

echo -e "${GREEN}✅ DISPLAY=$DISPLAY${NC}"
echo -e "${GREEN}✅ Socket X11 trouvé${NC}"
echo ""

# 2. Vérifier que xhost est installé
echo -e "${YELLOW}[2/5]${NC} Vérification de xhost..."

if ! command -v xhost &> /dev/null; then
    echo -e "${RED}❌ xhost non installé${NC}"
    echo -e "${YELLOW}Solution:${NC}"
    echo "sudo apt-get update && sudo apt-get install -y x11-xserver-utils"
    exit 1
fi

echo -e "${GREEN}✅ xhost installé${NC}"
echo ""

# 3. Configurer xhost pour autoriser les connexions locales
echo -e "${YELLOW}[3/5]${NC} Configuration des permissions X11..."

# Autoriser les connexions locales
xhost +local: > /dev/null 2>&1 || {
    echo -e "${RED}❌ Impossible de configurer xhost${NC}"
    echo -e "${YELLOW}Vérifiez que le serveur X11 est démarré${NC}"
    exit 1
}

echo -e "${GREEN}✅ xhost configuré: connexions locales autorisées${NC}"

# Afficher l'état actuel de xhost
echo -e "${BLUE}État xhost:${NC}"
xhost | head -5
echo ""

# 4. Vérifier les permissions du socket X11
echo -e "${YELLOW}[4/5]${NC} Vérification des permissions..."

SOCKET_FILE="/tmp/.X11-unix/X${DISPLAY#:}"
if [ ! -S "$SOCKET_FILE" ]; then
    echo -e "${RED}❌ Socket X11 introuvable: $SOCKET_FILE${NC}"
    exit 1
fi

# Donner les bonnes permissions (lecture/écriture pour tous)
sudo chmod 777 /tmp/.X11-unix/X* 2>/dev/null || {
    echo -e "${YELLOW}⚠️  Impossible de modifier les permissions (sudo requis)${NC}"
}

ls -la /tmp/.X11-unix/
echo ""

# 5. Tester la connexion X11 depuis un conteneur Docker
echo -e "${YELLOW}[5/5]${NC} Test de connexion X11 depuis Docker..."

# Vérifier si les conteneurs sont lancés
if ! docker ps | grep -q "instagram-airflow-scheduler"; then
    echo -e "${YELLOW}⚠️  Conteneurs Airflow non démarrés${NC}"
    echo -e "${BLUE}Démarrer avec: cd docker && docker-compose up -d${NC}"
else
    # Test simple : vérifier que DISPLAY et le socket sont accessibles
    echo -e "${BLUE}Test dans le conteneur Airflow:${NC}"
    docker exec instagram-airflow-scheduler bash -c "
        echo 'DISPLAY='\$DISPLAY
        ls -la /tmp/.X11-unix/
    " || {
        echo -e "${RED}❌ Le conteneur ne peut pas accéder au socket X11${NC}"
        exit 1
    }

    echo -e "${GREEN}✅ Conteneur Airflow a accès au socket X11${NC}"
fi

echo ""
echo -e "${BLUE}=========================================${NC}"
echo -e "${GREEN}✅ Configuration X11 terminée !${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

echo -e "${YELLOW}📋 Utilisation:${NC}"
echo ""
echo "1. Le mode visuel est maintenant prêt"
echo "2. Accédez au dashboard: ${BLUE}http://localhost:8000/${NC}"
echo "3. Cliquez sur '${GREEN}Lancer scraping${NC}'"
echo "4. Cochez '${BLUE}Mode visuel${NC}'"
echo "5. Chrome s'affichera pendant le scraping !"
echo ""

echo -e "${YELLOW}🔧 Configuration persistante:${NC}"
echo ""
echo "Pour que xhost soit toujours configuré au démarrage, ajoutez à ~/.bashrc:"
echo -e "${BLUE}xhost +local: > /dev/null 2>&1${NC}"
echo ""

echo -e "${YELLOW}🐛 Dépannage:${NC}"
echo ""
echo "Si Chrome ne s'affiche pas:"
echo "1. Vérifiez que le serveur X11 est démarré (VcXsrv/X410 sous Windows)"
echo "2. Relancez ce script: ${BLUE}./scripts/setup_x11_visual_mode.sh${NC}"
echo "3. Redémarrez les conteneurs: ${BLUE}cd docker && docker-compose restart${NC}"
echo ""

echo -e "${GREEN}✨ Configuration réussie !${NC}"
