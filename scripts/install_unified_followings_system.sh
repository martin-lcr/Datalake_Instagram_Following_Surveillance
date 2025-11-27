#!/bin/bash

# =====================================================================
# Script d'installation du système de fusion intelligente des scrapings
# =====================================================================
# Ce script installe le système qui fusionne automatiquement tous les
# scrapings du jour pour obtenir la liste la plus complète possible.
#
# Résultat attendu: Amélioration de la couverture de ~92% à ~100%
# Exemple mariadlaura: 611 → 665 followings (+54, +8.8%)
# =====================================================================

set -e  # Arrêter en cas d'erreur

# Couleurs pour l'affichage
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Installation du système de fusion${NC}"
echo -e "${BLUE}Instagram Following Surveillance${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# Configuration PostgreSQL (depuis variables d'environnement ou valeurs par défaut)
POSTGRES_HOST="${POSTGRES_HOST:-postgres}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:-airflow}"
POSTGRES_USER="${POSTGRES_USER:-airflow}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-airflow}"

# Vérifier si on est dans un conteneur Docker ou sur l'hôte
if [ -f /.dockerenv ]; then
    echo -e "${YELLOW}Détection: Environnement Docker${NC}"
    PSQL_CMD="psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB"
else
    echo -e "${YELLOW}Détection: Environnement hôte${NC}"
    # Utiliser docker exec pour exécuter psql dans le conteneur PostgreSQL
    PSQL_CMD="docker exec -i instagram-postgres psql -U $POSTGRES_USER -d $POSTGRES_DB"
fi

echo ""
echo -e "${YELLOW}[1/3]${NC} Installation du système SQL..."
echo -e "${BLUE}       - Table daily_unified_followings${NC}"
echo -e "${BLUE}       - Fonctions de fusion et détection${NC}"

# Chemin du fichier SQL (relatif au script)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SQL_FILE="$SCRIPT_DIR/../sql/unified_followings_system.sql"

# Vérifier que le fichier SQL existe
if [ ! -f "$SQL_FILE" ]; then
    echo -e "${RED}❌ Fichier SQL manquant: $SQL_FILE${NC}"
    exit 1
fi

# Installer le système SQL
if [ -f /.dockerenv ]; then
    PGPASSWORD=$POSTGRES_PASSWORD $PSQL_CMD < "$SQL_FILE"
else
    docker exec -i instagram-postgres psql -U $POSTGRES_USER -d $POSTGRES_DB < "$SQL_FILE"
fi

echo -e "${GREEN}✅ Système SQL installé${NC}"
echo ""

echo -e "${YELLOW}[2/3]${NC} Vérification du système..."

# Vérifier que la table existe
TABLE_CHECK=$(echo "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'daily_unified_followings';" | $PSQL_CMD -t)

if [ "$TABLE_CHECK" -eq 1 ]; then
    echo -e "${GREEN}✅ Table daily_unified_followings créée${NC}"
else
    echo -e "${RED}❌ Erreur: Table daily_unified_followings non créée${NC}"
    exit 1
fi

# Vérifier que les fonctions existent
FUNCTION_CHECK=$(echo "SELECT COUNT(*) FROM pg_proc WHERE proname = 'rebuild_unified_followings_for_day';" | $PSQL_CMD -t)

if [ "$FUNCTION_CHECK" -ge 1 ]; then
    echo -e "${GREEN}✅ Fonctions SQL créées${NC}"
else
    echo -e "${RED}❌ Erreur: Fonctions SQL non créées${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}[3/3]${NC} Récupération de la liste des comptes surveillés..."

# Récupérer la liste des comptes
ACCOUNTS=$(echo "SELECT DISTINCT table_name FROM information_schema.tables WHERE table_name LIKE 'instagram_data_%';" | $PSQL_CMD -t | sed 's/instagram_data_//' | tr -d ' ')

if [ -z "$ACCOUNTS" ]; then
    echo -e "${YELLOW}⚠️  Aucun compte trouvé${NC}"
    echo -e "${YELLOW}   Le système est installé et prêt à l'emploi${NC}"
else
    echo -e "${GREEN}✅ Comptes détectés:${NC}"
    for account in $ACCOUNTS; do
        echo -e "   • $account"
    done
fi

echo ""
echo -e "${BLUE}=========================================${NC}"
echo -e "${GREEN}✅ Installation terminée avec succès!${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

echo -e "${YELLOW}📊 Fonctionnement du système:${NC}"
echo ""
echo "Le dashboard utilise maintenant automatiquement le système de fusion."
echo "Pour chaque compte, tous les scrapings valides du jour sont fusionnés"
echo "pour obtenir la liste la plus complète possible des followings."
echo ""
echo -e "${YELLOW}📈 Amélioration de la couverture:${NC}"
echo ""
echo "Exemple pour mariadlaura:"
echo "  • Avant (1 scraping):  611 followings (92.18%)"
echo "  • Après (4 scrapings): 665 followings (100.00%)"
echo "  • Amélioration:        +54 followings (+8.8%)"
echo ""

echo -e "${YELLOW}🔧 Utilisation:${NC}"
echo ""
echo "Le dashboard affiche automatiquement les followings fusionnés."
echo "Accédez simplement à: ${BLUE}http://localhost:8000/account/NOM_COMPTE${NC}"
echo ""
echo "Les informations de fusion sont visibles dans l'API:"
echo "  ${BLUE}curl http://localhost:8000/api/account/NOM_COMPTE/followings${NC}"
echo ""
echo "Résultat JSON contient:"
echo "  • fusion_info.total_unique:       Nombre de followings uniques"
echo "  • fusion_info.scrapings_used:     Nombre de scrapings fusionnés"
echo "  • fusion_info.coverage_percent:   % de couverture vs Instagram"
echo "  • fusion_info.instagram_reported: Total reporté par Instagram"
echo ""

echo -e "${YELLOW}🛠️  Fonctions SQL disponibles (optionnel):${NC}"
echo ""
echo "Si vous souhaitez utiliser les fonctions SQL directement:"
echo ""
echo "1. Reconstruire la fusion pour un compte:"
echo "   ${BLUE}SELECT * FROM rebuild_unified_followings_for_day('NOM_COMPTE', '2025-11-26');${NC}"
echo ""
echo "2. Détecter les ajouts/suppressions:"
echo "   ${BLUE}SELECT * FROM detect_changes_with_confidence('NOM_COMPTE', '2025-11-26');${NC}"
echo ""
echo "3. Obtenir la vue fusionnée:"
echo "   ${BLUE}SELECT * FROM get_unified_view_for_day('NOM_COMPTE');${NC}"
echo ""
echo "4. Obtenir les statistiques:"
echo "   ${BLUE}SELECT * FROM get_daily_stats('NOM_COMPTE');${NC}"
echo ""

echo -e "${GREEN}🎉 Le système de fusion est maintenant opérationnel !${NC}"
echo ""
