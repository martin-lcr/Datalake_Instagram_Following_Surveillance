#!/bin/bash

# =====================================================================
# Script de démarrage complet du projet Instagram Surveillance
# =====================================================================
# Ce script lance tous les services nécessaires et configure X11
# =====================================================================

set -e

# Couleurs pour l'affichage
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}🚀 Instagram Following Surveillance${NC}"
echo -e "${BLUE}📊 Démarrage complet du projet${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# Répertoire du projet (détecté automatiquement)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/.."
cd "$PROJECT_DIR"

# Étape 1 : Configuration X11 pour le mode visuel
echo -e "${YELLOW}[1/4]${NC} Configuration X11 pour le mode visuel..."
echo ""

if [ -f "scripts/setup_x11_visual_mode.sh" ]; then
    ./scripts/setup_x11_visual_mode.sh
else
    echo -e "${YELLOW}⚠️  Script X11 non trouvé, passage à l'étape suivante${NC}"
fi

echo ""

# Étape 2 : Vérification de l'environnement Docker
echo -e "${YELLOW}[2/4]${NC} Vérification de l'environnement Docker..."
echo ""

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker n'est pas installé${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ Docker Compose n'est pas installé${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker et Docker Compose installés${NC}"
echo ""

# Étape 3 : Lancement des services Docker
echo -e "${YELLOW}[3/4]${NC} Démarrage des services Docker..."
echo ""

cd docker

# Vérifier si les conteneurs tournent déjà
RUNNING_CONTAINERS=$(docker-compose ps --services --filter "status=running" 2>/dev/null | wc -l)

if [ "$RUNNING_CONTAINERS" -gt 0 ]; then
    echo -e "${BLUE}Conteneurs déjà en cours d'exécution${NC}"
    echo -e "${YELLOW}Voulez-vous les redémarrer ? (o/n)${NC}"
    read -r RESTART_CHOICE

    if [ "$RESTART_CHOICE" = "o" ] || [ "$RESTART_CHOICE" = "O" ]; then
        echo -e "${BLUE}Redémarrage des conteneurs...${NC}"
        docker-compose restart
    fi
else
    echo -e "${BLUE}Lancement des conteneurs...${NC}"
    docker-compose up -d

    echo ""
    echo -e "${YELLOW}⏳ Attente du démarrage des services (30s)...${NC}"
    sleep 30
fi

echo ""
echo -e "${GREEN}✅ Services Docker démarrés${NC}"
echo ""

# Étape 4 : Vérification de l'état des services
echo -e "${YELLOW}[4/4]${NC} Vérification de l'état des services..."
echo ""

# Vérifier PostgreSQL
if docker exec instagram-postgres pg_isready -U airflow > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PostgreSQL : OK${NC}"
else
    echo -e "${RED}❌ PostgreSQL : Erreur${NC}"
fi

# Vérifier Airflow Webserver
if curl -s http://localhost:8082/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Airflow Webserver : OK${NC}"
else
    echo -e "${YELLOW}⚠️  Airflow Webserver : En cours de démarrage...${NC}"
fi

# Vérifier Airflow Scheduler
if docker ps | grep -q instagram-airflow-scheduler; then
    echo -e "${GREEN}✅ Airflow Scheduler : OK${NC}"
else
    echo -e "${RED}❌ Airflow Scheduler : Erreur${NC}"
fi

# Vérifier Dashboard
if curl -s http://localhost:8000/ > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Dashboard Flask : OK${NC}"
else
    echo -e "${YELLOW}⚠️  Dashboard Flask : En cours de démarrage...${NC}"
fi

# Vérifier Elasticsearch
if curl -s http://localhost:9200/_cluster/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Elasticsearch : OK${NC}"
else
    echo -e "${YELLOW}⚠️  Elasticsearch : En cours de démarrage...${NC}"
fi

# Vérifier Kibana
if curl -s http://localhost:5601/api/status > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Kibana : OK${NC}"
else
    echo -e "${YELLOW}⚠️  Kibana : En cours de démarrage...${NC}"
fi

echo ""
echo -e "${BLUE}=========================================${NC}"
echo -e "${GREEN}✅ Projet démarré avec succès !${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# Afficher les URLs d'accès
echo -e "${YELLOW}📋 URLs d'accès :${NC}"
echo ""
echo -e "  ${BLUE}Dashboard Principal :${NC}     http://localhost:8000/"
echo -e "  ${BLUE}Airflow Web UI :${NC}          http://localhost:8082/"
echo -e "  ${BLUE}Kibana :${NC}                  http://localhost:5601/"
echo -e "  ${BLUE}Elasticsearch :${NC}           http://localhost:9200/"
echo ""

# Afficher les comptes surveillés
echo -e "${YELLOW}👥 Comptes surveillés :${NC}"
echo ""
if [ -f "../instagram_accounts_to_scrape.txt" ]; then
    while IFS= read -r account; do
        # Ignorer les lignes vides et les commentaires
        if [ -n "$account" ] && [[ ! "$account" =~ ^# ]]; then
            echo -e "  • ${GREEN}$account${NC}"
        fi
    done < "../instagram_accounts_to_scrape.txt"
else
    echo -e "  ${YELLOW}Fichier instagram_accounts_to_scrape.txt non trouvé${NC}"
fi

echo ""

# Instructions pour le mode visuel
echo -e "${YELLOW}🎮 Mode visuel :${NC}"
echo ""
echo "1. Accédez au dashboard : ${BLUE}http://localhost:8000/${NC}"
echo "2. Cliquez sur le bouton ${GREEN}'Lancer scraping'${NC}"
echo "3. Cochez ${BLUE}'Mode visuel'${NC}"
echo "4. Cliquez sur ${GREEN}'Lancer'${NC}"
echo "5. Chrome s'affichera automatiquement !"
echo ""

# Instructions pour les logs
echo -e "${YELLOW}📜 Suivre les logs :${NC}"
echo ""
echo "  ${BLUE}Tous les services :${NC}        docker-compose logs -f"
echo "  ${BLUE}Airflow scheduler :${NC}        docker logs -f instagram-airflow-scheduler"
echo "  ${BLUE}Dashboard :${NC}                docker logs -f instagram-dashboard"
echo ""

# Instructions pour arrêter
echo -e "${YELLOW}🛑 Arrêter le projet :${NC}"
echo ""
echo "  ${BLUE}Arrêt :${NC}                    cd docker && docker-compose stop"
echo "  ${BLUE}Arrêt + suppression :${NC}      cd docker && docker-compose down"
echo ""

echo -e "${GREEN}✨ Tout est prêt ! Bon scraping !${NC}"
