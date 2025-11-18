#!/bin/bash
#
# Script d'installation d'un cron job pour ouvrir automatiquement
# les dashboards à 09h00 chaque matin
#
# Usage: ./scripts/setup_auto_open.sh
#

set -e

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Configuration Auto-Open des Dashboards à 09h00              ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Détecter le répertoire du projet
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo -e "${BLUE}📁 Répertoire du projet: ${PROJECT_DIR}${NC}"
echo ""

# Vérifier que Make est disponible
if ! command -v make >/dev/null 2>&1; then
    echo -e "${RED}❌ Make n'est pas installé. Installez-le d'abord.${NC}"
    exit 1
fi

# Créer le script d'ouverture
OPEN_SCRIPT="${PROJECT_DIR}/scripts/open_dashboards.sh"

echo -e "${YELLOW}📝 Création du script d'ouverture...${NC}"
cat > "${OPEN_SCRIPT}" << 'EOF'
#!/bin/bash
# Script automatique pour ouvrir les dashboards
# Généré automatiquement par setup_auto_open.sh

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_DIR}"

# Log
LOG_FILE="${PROJECT_DIR}/logs/auto_open.log"
mkdir -p "${PROJECT_DIR}/logs"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Ouverture automatique des dashboards" >> "${LOG_FILE}"

# Lancer make open
make open >> "${LOG_FILE}" 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Dashboards ouverts avec succès" >> "${LOG_FILE}"
EOF

# Rendre le script exécutable
chmod +x "${OPEN_SCRIPT}"
echo -e "${GREEN}✅ Script créé: ${OPEN_SCRIPT}${NC}"
echo ""

# Configurer le cron job
echo -e "${YELLOW}⚙️  Configuration du cron job...${NC}"

# Créer l'entrée cron (09h00 tous les jours)
CRON_ENTRY="0 9 * * * ${OPEN_SCRIPT}"

# Vérifier si le cron job existe déjà
if crontab -l 2>/dev/null | grep -q "${OPEN_SCRIPT}"; then
    echo -e "${YELLOW}⚠️  Le cron job existe déjà. Mise à jour...${NC}"
    # Supprimer l'ancienne entrée
    (crontab -l 2>/dev/null | grep -v "${OPEN_SCRIPT}") | crontab -
fi

# Ajouter le nouveau cron job
(crontab -l 2>/dev/null; echo "${CRON_ENTRY}") | crontab -

echo -e "${GREEN}✅ Cron job configuré avec succès !${NC}"
echo ""

# Afficher la configuration
echo -e "${BLUE}📅 Configuration actuelle:${NC}"
echo -e "  • Heure d'ouverture: ${GREEN}09h00${NC} (tous les jours)"
echo -e "  • Script: ${OPEN_SCRIPT}"
echo -e "  • Logs: ${PROJECT_DIR}/logs/auto_open.log"
echo ""

echo -e "${BLUE}🔍 Cron jobs actuels pour ce projet:${NC}"
crontab -l | grep "${PROJECT_DIR}" || echo "  (aucun)"
echo ""

# Instructions
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅ Configuration terminée !                                   ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}📋 Informations utiles:${NC}"
echo ""
echo -e "  ${BLUE}Tester manuellement:${NC}"
echo -e "    make open"
echo ""
echo -e "  ${BLUE}Voir les cron jobs:${NC}"
echo -e "    crontab -l"
echo ""
echo -e "  ${BLUE}Modifier l'heure d'ouverture:${NC}"
echo -e "    crontab -e"
echo -e "    Modifier: ${CRON_ENTRY}"
echo ""
echo -e "  ${BLUE}Supprimer le cron job:${NC}"
echo -e "    crontab -l | grep -v '${OPEN_SCRIPT}' | crontab -"
echo ""
echo -e "  ${BLUE}Voir les logs:${NC}"
echo -e "    tail -f ${PROJECT_DIR}/logs/auto_open.log"
echo ""
echo -e "${YELLOW}⚠️  Note: Les dashboards s'ouvriront automatiquement à 09h00${NC}"
echo -e "${YELLOW}   chaque matin si Docker est lancé.${NC}"
echo ""
