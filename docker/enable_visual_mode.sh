#!/bin/bash
# Script pour activer le mode visuel et lancer Docker

echo "🖥️  Configuration du MODE VISUEL pour Instagram Scraping"
echo "=========================================================="
echo ""

# Détecter IP Windows pour WSL2
WINDOWS_IP=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}')
export DISPLAY="${WINDOWS_IP}:0"

echo "✅ DISPLAY configuré: $DISPLAY"
echo ""
echo "⚠️  PRÉREQUIS:"
echo "   1. VcXsrv doit être lancé sur Windows"
echo "   2. XLaunch configuré avec 'Disable access control'"
echo ""
echo "📝 Télécharger VcXsrv: https://sourceforge.net/projects/vcxsrv/"
echo ""

# Tester X11
echo "🔍 Test de la connexion X11..."
if command -v xeyes &> /dev/null; then
    timeout 2 xeyes &
    PID=$!
    sleep 1
    if kill -0 $PID 2>/dev/null; then
        kill $PID
        echo "✅ X11 fonctionne! (xeyes a pu se lancer)"
    else
        echo "⚠️  X11 peut ne pas fonctionner (xeyes n'a pas répondu)"
    fi
else
    echo "⚠️  xeyes non installé, test X11 ignoré"
fi
echo ""

# Autoriser connexions X11 depuis Docker
echo "🔓 Autorisation des connexions X11 depuis Docker..."
xhost +local:docker 2>/dev/null || echo "⚠️  xhost non disponible"
echo ""

# Activer mode visuel dans .env
echo "📝 Activation VISUAL_MODE dans .env..."
cd "$(dirname "$0")"

if grep -q "^VISUAL_MODE=" .env; then
    sed -i 's/^VISUAL_MODE=.*/VISUAL_MODE=true/' .env
else
    echo "VISUAL_MODE=true" >> .env
fi

if grep -q "^DISPLAY=" .env; then
    sed -i "s|^DISPLAY=.*|DISPLAY=$DISPLAY|" .env
else
    echo "DISPLAY=$DISPLAY" >> .env
fi

echo "✅ Configuration mise à jour"
echo ""

# Rebuild et restart Docker
echo "🔨 Rebuild de l'image Docker..."
docker compose build

echo ""
echo "🚀 Redémarrage des services..."
docker compose down
docker compose up -d

echo ""
echo "⏳ Attente que les services soient healthy..."
sleep 20

echo ""
echo "✅ MODE VISUEL ACTIVÉ!"
echo ""
echo "📌 Pour lancer un scraping:"
echo "   docker compose exec airflow-webserver airflow dags trigger instagram_scraping_surveillance_pipeline"
echo ""
echo "🖥️  Les fenêtres Chrome devraient apparaître sur votre écran Windows!"
echo ""
