# 🚀 Guide de démarrage rapide

Installation complète du projet en **10 minutes** avec un seul dépôt GitHub.

## ✅ Prérequis

### Obligatoires
- **Docker Desktop** installé et **démarré**
- **Git** installé
- **Connexion Internet**

### Optionnels (pour le mode visuel)
- **Serveur X11** (VcXsrv/X410 sous Windows, intégré sur Linux/Mac)

**C'est tout !** Python, Make, Airflow, PostgreSQL, Elasticsearch sont tous conteneurisés.

---

## 📦 Installation automatique

### Étape 1 : Cloner le projet

```bash
git clone https://github.com/YOUR_USERNAME/Datalake_Instagram_Following_Surveillance.git
cd Datalake_Instagram_Following_Surveillance
```

### Étape 2 : Installation complète en une commande

```bash
make install
```

**Ce que fait cette commande** :
1. ✅ Vérifie les prérequis (Docker, Docker Compose)
2. ✅ Configure l'environnement (`.env`, répertoires)
3. ✅ Configure X11 pour le mode visuel
4. ✅ Construit les images Docker
5. ✅ Démarre tous les services
6. ✅ Installe le système de fusion intelligente
7. ✅ Vérifie que tout fonctionne

**Durée** : ~10 minutes (dépend de votre connexion)

---

## 🎮 Utilisation rapide

### Accès au dashboard

```bash
# Ouvrir automatiquement
make open

# Ou manuellement
http://localhost:8000/
```

### Lancer un scraping manuel

#### Via le Dashboard (Recommandé)

1. Ouvrir http://localhost:8000/
2. Cliquer sur **"Lancer scraping"** (bouton vert en haut à droite)
3. **Optionnel** : Cocher "Mode visuel" pour voir Chrome en action
4. Cliquer sur **"Lancer"**

#### Via ligne de commande

```bash
make test-scraping
```

---

## 🔧 Commandes essentielles

```bash
make help           # Aide complète
make start          # Démarrer
make stop           # Arrêter
make status         # État des services
make logs           # Voir les logs
make verify         # Vérifier l'installation
make test-visual-mode  # Tester le mode visuel
```

---

## 📚 Documentation complète

Pour plus de détails, consultez :
- [README.md](README.md) - Vue d'ensemble
- [docs/](docs/) - Documentation technique complète

---

**Félicitations ! Votre pipeline est maintenant opérationnel ! 🎉**
