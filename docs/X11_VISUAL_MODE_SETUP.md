# Configuration X11 pour le Mode Visuel

## 🎯 Objectif

Permettre au scraper Instagram d'afficher le navigateur Chrome en temps réel pendant le scraping, pour observer le comportement et déboguer facilement.

## ✅ Pré-requis

### Sous WSL2 (Windows)

Vous avez besoin d'un serveur X11 fonctionnel sur Windows :

**Option 1 : VcXsrv (Gratuit)** ⭐ Recommandé
1. Télécharger : https://sourceforge.net/projects/vcxsrv/
2. Installer VcXsrv
3. Lancer XLaunch avec les paramètres :
   - Display number : `0`
   - Start no client : ✅
   - Clipboard : ✅
   - **Disable access control : ✅ IMPORTANT**
   - Native opengl : ❌
   - **Additional parameters : `-ac`**

**Option 2 : X410 (Payant - Microsoft Store)**
1. Installer depuis le Microsoft Store
2. Lancer X410
3. X410 configure automatiquement le DISPLAY

**Option 3 : WSLg (Intégré à Windows 11)**
- WSL2 sous Windows 11 inclut WSLg (serveur X11 intégré)
- Aucune installation requise
- Détecté automatiquement

### Sous Linux natif

X11 est déjà installé et configuré automatiquement.

## 🚀 Installation automatique

### Étape 1 : Exécuter le script de configuration

```bash
cd /path/to/Datalake_Instagram_Following_Surveillance
./scripts/setup_x11_visual_mode.sh
```

Ce script va automatiquement :
- ✅ Vérifier que X11 est disponible
- ✅ Configurer xhost pour autoriser Docker
- ✅ Tester la connexion depuis les conteneurs
- ✅ Afficher un guide d'utilisation

**Sortie attendue :**
```
=========================================
✅ Configuration X11 terminée !
=========================================
```

### Étape 2 : Rendre la configuration persistante (optionnel)

Pour que xhost soit automatiquement configuré au démarrage de WSL :

```bash
echo 'xhost +local: > /dev/null 2>&1' >> ~/.bashrc
source ~/.bashrc
```

## 📊 Vérification manuelle

### Vérifier que DISPLAY est défini

```bash
echo $DISPLAY
# Doit afficher: :0
```

### Vérifier que le socket X11 existe

```bash
ls -la /tmp/.X11-unix/
# Doit montrer: X0
```

### Vérifier que les conteneurs ont accès

```bash
docker exec instagram-airflow-scheduler bash -c "echo \$DISPLAY"
# Doit afficher: :0

docker exec instagram-airflow-scheduler ls -la /tmp/.X11-unix/
# Doit montrer le socket X0
```

### Test complet avec xeyes

```bash
# Sur l'hôte
docker run --rm -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix fr3nd/xeyes
```

Si une fenêtre avec des yeux s'affiche, X11 fonctionne parfaitement ! ✅

## 🎮 Utilisation du mode visuel

### Via le Dashboard (Recommandé)

1. Ouvrir http://localhost:8000/
2. Cliquer sur le bouton vert **"Lancer scraping"**
3. Cocher **"Mode visuel"**
4. Cliquer sur **"Lancer"**
5. Une fenêtre Chrome s'ouvrira automatiquement

**Vous verrez Chrome :**
- Naviguer sur Instagram
- Se connecter (si nécessaire)
- Accéder aux profils des comptes ciblés
- Scroller la liste des followings
- Extraire les données en temps réel

### Via ligne de commande

```bash
# 1. Activer le mode visuel dans .env
cd /path/to/Datalake_Instagram_Following_Surveillance/docker
echo "VISUAL_MODE=true" >> .env

# 2. Redémarrer les conteneurs
docker-compose restart

# 3. Déclencher le scraping manuellement
docker exec instagram-airflow-scheduler python3 /opt/airflow/scripts/instagram_scraping_ml_pipeline.py mariadlaura
```

## 🐛 Dépannage

### Problème : "cannot open display :0"

**Cause** : Le serveur X11 n'est pas accessible depuis Docker

**Solutions** :
1. Vérifier que VcXsrv/X410 est lancé sur Windows
2. Relancer le script de configuration :
   ```bash
   ./scripts/setup_x11_visual_mode.sh
   ```
3. Vérifier xhost :
   ```bash
   xhost +local:
   ```

### Problème : "X0 socket permission denied"

**Cause** : Problème de permissions sur le socket X11

**Solution** :
```bash
sudo chmod 777 /tmp/.X11-unix/X*
./scripts/setup_x11_visual_mode.sh
```

### Problème : "No protocol specified"

**Cause** : xhost n'autorise pas les connexions locales

**Solution** :
```bash
xhost +local:
xhost +SI:localuser:$(whoami)
```

### Problème : Chrome s'affiche mais ne répond pas

**Cause** : Problème de performance X11 avec WSL2

**Solution** :
1. Utiliser VcXsrv au lieu de X410
2. Lancer VcXsrv avec les paramètres :
   - **Native opengl : ❌ Désactivé**
   - **Additional parameters : `-ac -nowgl`**

### Problème : "DISPLAY not set"

**Cause** : Variable d'environnement DISPLAY non définie

**Solution** :
```bash
export DISPLAY=:0
echo "export DISPLAY=:0" >> ~/.bashrc
source ~/.bashrc
```

## 📋 Configuration docker-compose.yml

La configuration X11 est **déjà incluse** dans docker-compose.yml :

```yaml
environment:
  VISUAL_MODE: '${VISUAL_MODE:-false}'
  DISPLAY: '${DISPLAY:-:0}'
volumes:
  - /tmp/.X11-unix:/tmp/.X11-unix
```

Aucune modification manuelle n'est nécessaire.

## 🔒 Sécurité

**Note importante** : L'utilisation de `xhost +local:` autorise toutes les connexions locales au serveur X11.

Pour une sécurité renforcée, vous pouvez autoriser uniquement des utilisateurs spécifiques :

```bash
# Autoriser seulement l'utilisateur courant
xhost +SI:localuser:$(whoami)

# Autoriser seulement Docker
xhost +local:docker
```

Cependant, pour un environnement de développement local, `xhost +local:` est suffisant.

## 📈 Performances

Le mode visuel consomme plus de ressources :

| Ressource | Mode headless | Mode visuel |
|-----------|---------------|-------------|
| CPU | ~20% | ~40% |
| RAM | ~500 MB | ~1 GB |
| Réseau X11 | 0 | ~10 MB/min |

**Recommandation** : Utiliser le mode visuel uniquement pour :
- Débogage
- Démonstrations
- Développement de nouvelles fonctionnalités

Pour la production et les scrapings réguliers, désactiver le mode visuel (VISUAL_MODE=false).

## ✅ Checklist de vérification

Avant d'utiliser le mode visuel, vérifiez :

- [ ] Serveur X11 lancé (VcXsrv/X410/WSLg)
- [ ] DISPLAY=:0 défini (`echo $DISPLAY`)
- [ ] Socket /tmp/.X11-unix/X0 existe
- [ ] xhost configuré (`xhost +local:`)
- [ ] Test xeyes réussi
- [ ] Conteneurs redémarrés après modification .env
- [ ] Dashboard accessible (http://localhost:8000/)

## 📚 Références

- [VcXsrv Documentation](https://sourceforge.net/projects/vcxsrv/)
- [WSLg GitHub](https://github.com/microsoft/wslg)
- [Docker X11 Forwarding Guide](https://github.com/mviereck/x11docker)

---

**Auteur** : Claude Code
**Date** : 27 novembre 2025
**Version** : 1.0
