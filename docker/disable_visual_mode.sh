#!/bin/bash
# Script pour désactiver le mode visuel

echo "🔒 Désactivation du MODE VISUEL"
echo "================================"
echo ""

cd "$(dirname "$0")"

# Désactiver mode visuel dans .env
echo "📝 Désactivation VISUAL_MODE dans .env..."

if grep -q "^VISUAL_MODE=" .env; then
    sed -i 's/^VISUAL_MODE=.*/VISUAL_MODE=false/' .env
else
    echo "VISUAL_MODE=false" >> .env
fi

echo "✅ Configuration mise à jour"
echo ""

# Restart Docker
echo "🚀 Redémarrage des services..."
docker compose restart airflow-scheduler airflow-webserver

echo ""
echo "✅ Mode headless réactivé (Chrome invisible)"
echo ""
