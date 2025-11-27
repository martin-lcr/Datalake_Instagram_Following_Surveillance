#!/bin/bash

# Script d'installation du Quality Tracking pour Instagram Surveillance
# Usage: ./install_quality_tracking.sh

set -e  # Arrêter en cas d'erreur

echo "=========================================="
echo "Installation Quality Tracking System"
echo "=========================================="
echo ""

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Variables
POSTGRES_CONTAINER="instagram-postgres"
POSTGRES_USER="airflow"
POSTGRES_DB="airflow"
SQL_DIR="../sql"
SCRIPTS_DIR="."

echo -e "${YELLOW}[1/5]${NC} Vérification de l'environnement..."

# Vérifier que le container PostgreSQL est en cours d'exécution
if ! docker ps | grep -q $POSTGRES_CONTAINER; then
    echo -e "${RED}❌ Erreur: Le container PostgreSQL '$POSTGRES_CONTAINER' n'est pas en cours d'exécution${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Container PostgreSQL trouvé${NC}"

# Créer le répertoire SQL s'il n'existe pas
mkdir -p $SQL_DIR

echo ""
echo -e "${YELLOW}[2/5]${NC} Création des tables et fonctions SQL..."

# Installer les tables de métadonnées
if docker exec -i $POSTGRES_CONTAINER psql -U $POSTGRES_USER -d $POSTGRES_DB < $SQL_DIR/create_scraping_metadata.sql 2>&1 | grep -q "ERROR"; then
    echo -e "${RED}❌ Erreur lors de la création des tables de métadonnées${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Tables de métadonnées créées${NC}"

# Installer les fonctions de détection
if docker exec -i $POSTGRES_CONTAINER psql -U $POSTGRES_USER -d $POSTGRES_DB < $SQL_DIR/detect_truly_new_followings.sql 2>&1 | grep -q "ERROR"; then
    echo -e "${RED}❌ Erreur lors de la création des fonctions de détection${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Fonctions de détection créées${NC}"

echo ""
echo -e "${YELLOW}[3/5]${NC} Migration des données historiques..."

# Migrer les données existantes
docker exec -i $POSTGRES_CONTAINER psql -U $POSTGRES_USER -d $POSTGRES_DB <<EOF
-- Remplir la table avec l'historique existant
INSERT INTO scraping_metadata (
    target_account,
    scraping_date,
    scraping_timestamp,
    total_followings,
    completeness_score,
    is_complete
)
SELECT
    target_account,
    aggregation_date::date as scraping_date,
    MAX(scraped_at)::timestamp as scraping_timestamp,
    COUNT(DISTINCT username) as total_followings,
    100.0 as completeness_score,
    TRUE as is_complete
FROM final_aggregated_scraping
WHERE aggregation_date IS NOT NULL
GROUP BY target_account, aggregation_date::date
ON CONFLICT (target_account, scraping_date, scraping_timestamp) DO NOTHING;

-- Afficher le nombre de lignes migrées
SELECT
    target_account,
    COUNT(*) as scrapings_count,
    MIN(scraping_date) as first_date,
    MAX(scraping_date) as last_date
FROM scraping_metadata
GROUP BY target_account;
EOF

echo -e "${GREEN}✅ Données historiques migrées${NC}"

echo ""
echo -e "${YELLOW}[4/5]${NC} Recalcul des scores de complétude..."

# Recalculer les scores
docker exec -i $POSTGRES_CONTAINER psql -U $POSTGRES_USER -d $POSTGRES_DB <<EOF
UPDATE scraping_metadata sm
SET
    completeness_score = calculate_completeness_score(sm.target_account, sm.total_followings),
    is_complete = (calculate_completeness_score(sm.target_account, sm.total_followings) >= 90.0)
WHERE completeness_score = 100.0;  -- Seulement recalculer ceux qui étaient à 100%

-- Afficher le résumé
SELECT
    target_account,
    COUNT(*) as total_scrapings,
    COUNT(CASE WHEN is_complete THEN 1 END) as complete_scrapings,
    ROUND(AVG(completeness_score), 1) as avg_score
FROM scraping_metadata
GROUP BY target_account
ORDER BY target_account;
EOF

echo -e "${GREEN}✅ Scores recalculés${NC}"

echo ""
echo -e "${YELLOW}[5/5]${NC} Test du système..."

# Tester le tracker Python
python3 <<EOF
import sys
sys.path.append('$SCRIPTS_DIR')

try:
    from scraping_quality_tracker import ScrapingQualityTracker

    postgres_config = {
        'host': 'localhost',  # Depuis l'hôte
        'port': '5433',        # Port mappé
        'database': 'airflow',
        'user': 'airflow',
        'password': 'airflow'
    }

    tracker = ScrapingQualityTracker(postgres_config)

    # Test: obtenir le dernier scraping complet
    result = tracker.get_last_complete_scraping('mariadlaura')

    if result:
        print(f"✅ Test réussi!")
        print(f"   Dernier scraping complet: {result['scraping_date']}")
        print(f"   Total followings: {result['total_followings']}")
        print(f"   Score: {result['completeness_score']:.1f}%")
    else:
        print("⚠️  Aucun scraping complet trouvé pour mariadlaura")

except Exception as e:
    print(f"❌ Erreur test: {e}")
    sys.exit(1)
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Test du tracker Python réussi${NC}"
else
    echo -e "${RED}❌ Test du tracker Python échoué${NC}"
    exit 1
fi

echo ""
echo "=========================================="
echo -e "${GREEN}✅ Installation terminée avec succès!${NC}"
echo "=========================================="
echo ""
echo "📋 Prochaines étapes:"
echo ""
echo "1. Intégrer le tracker dans le pipeline:"
echo "   Modifier scripts/instagram_scraping_ml_pipeline.py"
echo "   Suivre les instructions dans INTEGRATION_QUALITY_TRACKING.md"
echo ""
echo "2. Tester avec un scraping:"
echo "   python3 scripts/scraping_quality_tracker.py"
echo ""
echo "3. Consulter la qualité des scrapings:"
echo "   docker exec -i $POSTGRES_CONTAINER psql -U $POSTGRES_USER -d $POSTGRES_DB -c \\"
echo "   \"SELECT * FROM scraping_metadata ORDER BY scraping_date DESC LIMIT 10;\""
echo ""
echo "4. Ajouter les nouvelles API au dashboard (voir INTEGRATION_QUALITY_TRACKING.md)"
echo ""
echo "🎯 Avantages:"
echo "  - Détection robuste des vrais nouveaux followings"
echo "  - Traçabilité de la qualité des scrapings"
echo "  - Comparaisons intelligentes même avec scrapings incomplets"
echo ""
