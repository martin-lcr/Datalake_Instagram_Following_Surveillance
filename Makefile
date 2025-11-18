# =============================================================================
# Makefile - Instagram Following Surveillance Pipeline
# =============================================================================
# Automatisation du déploiement et de la gestion du projet
#
# Usage:
#   make help          - Afficher l'aide
#   make install       - Installation complète (setup + build + up)
#   make start         - Démarrer les services
#   make stop          - Arrêter les services
# =============================================================================

.PHONY: help check-prereqs setup build up down logs status validate-cookies clean install restart

# Couleurs pour l'output
GREEN  := \033[0;32m
YELLOW := \033[0;33m
RED    := \033[0;31m
BLUE   := \033[0;34m
NC     := \033[0m # No Color

# Variables
DOCKER_COMPOSE := cd docker && docker compose
PROJECT_NAME := Instagram Following Surveillance Pipeline

# =============================================================================
# Aide
# =============================================================================

help: ## Afficher l'aide
	@echo "$(BLUE)╔════════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║  $(GREEN)Instagram Following Surveillance Pipeline - Makefile$(BLUE)       ║$(NC)"
	@echo "$(BLUE)╚════════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(YELLOW)Commandes de déploiement:$(NC)"
	@echo "  $(GREEN)make install$(NC)          Installation complète (première fois)"
	@echo "  $(GREEN)make start$(NC)            Démarrer les services"
	@echo "  $(GREEN)make stop$(NC)             Arrêter les services"
	@echo "  $(GREEN)make restart$(NC)          Redémarrer les services"
	@echo ""
	@echo "$(YELLOW)Commandes de gestion:$(NC)"
	@echo "  $(GREEN)make status$(NC)           Afficher le statut des services"
	@echo "  $(GREEN)make logs$(NC)             Voir les logs en temps réel"
	@echo "  $(GREEN)make validate-cookies$(NC) Valider les cookies Instagram"
	@echo "  $(GREEN)make shell$(NC)            Ouvrir un shell dans le container Airflow"
	@echo ""
	@echo "$(YELLOW)Commandes de développement:$(NC)"
	@echo "  $(GREEN)make build$(NC)            Rebuild les images Docker"
	@echo "  $(GREEN)make rebuild$(NC)          Rebuild sans cache"
	@echo "  $(GREEN)make clean$(NC)            Nettoyer (arrêter + supprimer volumes)"
	@echo "  $(GREEN)make clean-all$(NC)        Nettoyer complètement (données + images)"
	@echo ""
	@echo "$(YELLOW)Commandes utilitaires:$(NC)"
	@echo "  $(GREEN)make check-prereqs$(NC)    Vérifier les prérequis"
	@echo "  $(GREEN)make setup$(NC)            Configuration initiale uniquement"
	@echo "  $(GREEN)make urls$(NC)             Afficher les URLs d'accès"
	@echo "  $(GREEN)make open$(NC)             Ouvrir les dashboards dans le navigateur"
	@echo "  $(GREEN)make setup-auto-open$(NC)  Configurer auto-open à 09h00 (cron)"
	@echo ""

# =============================================================================
# Vérification des prérequis
# =============================================================================

check-prereqs: ## Vérifier que Docker et Docker Compose sont installés
	@echo "$(BLUE)🔍 Vérification des prérequis...$(NC)"
	@command -v docker >/dev/null 2>&1 || { echo "$(RED)❌ Docker n'est pas installé$(NC)"; exit 1; }
	@command -v docker compose >/dev/null 2>&1 || command -v docker-compose >/dev/null 2>&1 || { echo "$(RED)❌ Docker Compose n'est pas installé$(NC)"; exit 1; }
	@echo "$(GREEN)✅ Docker: $$(docker --version)$(NC)"
	@echo "$(GREEN)✅ Docker Compose: $$(docker compose version 2>/dev/null || docker-compose --version)$(NC)"
	@if [ ! -S /var/run/docker.sock ]; then \
		echo "$(RED)❌ Docker daemon n'est pas démarré$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)✅ Docker daemon est actif$(NC)"

# =============================================================================
# Configuration initiale
# =============================================================================

setup: check-prereqs ## Configuration initiale du projet
	@echo "$(BLUE)⚙️  Configuration initiale automatique...$(NC)"

	# Créer le répertoire cookies
	@if [ ! -d docker/cookies ]; then \
		echo "$(YELLOW)📁 Création du répertoire docker/cookies/...$(NC)"; \
		mkdir -p docker/cookies; \
		echo "$(GREEN)✅ Répertoire cookies créé$(NC)"; \
	else \
		echo "$(GREEN)✅ Répertoire cookies existe déjà$(NC)"; \
	fi

	# Créer le fichier .env depuis .env.example avec génération automatique
	@if [ ! -f docker/.env ]; then \
		echo "$(YELLOW)📝 Création et configuration automatique de docker/.env...$(NC)"; \
		cp docker/.env.example docker/.env; \
		DETECTED_UID=$$(id -u 2>/dev/null || echo "50000"); \
		GENERATED_SECRET=$$(openssl rand -hex 32 2>/dev/null || echo "please-change-this-secret-key-in-production"); \
		if [ "$(shell uname)" = "Darwin" ]; then \
			sed -i '' "s/AIRFLOW_UID=50000/AIRFLOW_UID=$$DETECTED_UID/" docker/.env; \
			sed -i '' "s/AIRFLOW_SECRET_KEY=your-secret-key-here/AIRFLOW_SECRET_KEY=$$GENERATED_SECRET/" docker/.env; \
		else \
			sed -i "s/AIRFLOW_UID=50000/AIRFLOW_UID=$$DETECTED_UID/" docker/.env; \
			sed -i "s/AIRFLOW_SECRET_KEY=your-secret-key-here/AIRFLOW_SECRET_KEY=$$GENERATED_SECRET/" docker/.env; \
		fi; \
		echo "$(GREEN)✅ Fichier .env créé et configuré automatiquement$(NC)"; \
		echo "   → AIRFLOW_UID: $$DETECTED_UID"; \
		echo "   → AIRFLOW_SECRET_KEY: $$GENERATED_SECRET"; \
	else \
		echo "$(GREEN)✅ Fichier .env existe déjà$(NC)"; \
	fi

	# Créer les autres répertoires nécessaires
	@mkdir -p data/raw data/formatted data/usage airflow/logs 2>/dev/null || true
	@echo "$(GREEN)✅ Répertoires de données créés$(NC)"

	# Vérifier le fichier des comptes Instagram
	@if [ ! -f instagram_accounts_to_scrape.txt ]; then \
		echo "$(YELLOW)📝 Création du fichier instagram_accounts_to_scrape.txt...$(NC)"; \
		echo "# Ajoutez vos comptes Instagram à surveiller (un par ligne)" > instagram_accounts_to_scrape.txt; \
		echo "# Exemple: username_instagram" >> instagram_accounts_to_scrape.txt; \
		echo "$(GREEN)✅ Fichier créé$(NC)"; \
	else \
		echo "$(GREEN)✅ Fichier instagram_accounts_to_scrape.txt existe$(NC)"; \
	fi

	@echo ""
	@echo "$(GREEN)✅ Configuration initiale terminée automatiquement !$(NC)"
	@echo ""
	@echo "$(YELLOW)Il ne vous reste plus qu'à:$(NC)"
	@echo "  1. Placer vos cookies Instagram dans $(BLUE)docker/cookies/www.instagram.com_cookies.txt$(NC)"
	@echo "  2. Éditer $(BLUE)instagram_accounts_to_scrape.txt$(NC) pour ajouter les comptes à surveiller"
	@echo "  3. Exécutez $(GREEN)make build$(NC) pour construire les images Docker"
	@echo "  4. Exécutez $(GREEN)make start$(NC) pour démarrer les services"
	@echo ""
	@echo "$(BLUE)💡 Ou utilisez $(GREEN)make install$(NC) pour tout faire en une commande !$(NC)"
	@echo ""

build: check-prereqs ## Construire les images Docker
	@echo "$(BLUE)🔨 Construction des images Docker...$(NC)"
	@$(DOCKER_COMPOSE) build
	@echo "$(GREEN)✅ Images Docker construites avec succès$(NC)"

rebuild: check-prereqs ## Reconstruire les images Docker sans cache
	@echo "$(BLUE)🔨 Reconstruction des images Docker (sans cache)...$(NC)"
	@$(DOCKER_COMPOSE) build --no-cache
	@echo "$(GREEN)✅ Images Docker reconstruites avec succès$(NC)"

up: check-prereqs ## Démarrer les services
	@echo "$(BLUE)🚀 Démarrage des services...$(NC)"
	@$(DOCKER_COMPOSE) up -d
	@echo ""
	@echo "$(GREEN)✅ Services démarrés !$(NC)"
	@echo ""
	@make --no-print-directory urls
	@echo ""
	@echo "$(YELLOW)💡 Utilisez 'make logs' pour voir les logs$(NC)"
	@echo "$(YELLOW)💡 Utilisez 'make status' pour voir l'état des services$(NC)"

start: up ## Alias pour 'up'

down: ## Arrêter les services
	@echo "$(BLUE)🛑 Arrêt des services...$(NC)"
	@$(DOCKER_COMPOSE) down
	@echo "$(GREEN)✅ Services arrêtés$(NC)"

stop: down ## Alias pour 'down'

restart: ## Redémarrer les services
	@echo "$(BLUE)🔄 Redémarrage des services...$(NC)"
	@make --no-print-directory down
	@sleep 2
	@make --no-print-directory up

# =============================================================================
# Monitoring et logs
# =============================================================================

status: ## Afficher le statut des services
	@echo "$(BLUE)📊 Statut des services:$(NC)"
	@$(DOCKER_COMPOSE) ps

logs: ## Voir les logs en temps réel (Ctrl+C pour quitter)
	@echo "$(BLUE)📜 Logs des services (Ctrl+C pour quitter):$(NC)"
	@$(DOCKER_COMPOSE) logs -f

logs-airflow: ## Voir les logs Airflow uniquement
	@$(DOCKER_COMPOSE) logs -f airflow-scheduler airflow-webserver

logs-elastic: ## Voir les logs Elasticsearch uniquement
	@$(DOCKER_COMPOSE) logs -f elasticsearch

# =============================================================================
# Validation et utilitaires
# =============================================================================

validate-cookies: ## Valider les cookies Instagram
	@echo "$(BLUE)🍪 Validation des cookies Instagram...$(NC)"
	@if [ ! -f docker/cookies/www.instagram.com_cookies.txt ]; then \
		echo "$(RED)❌ Fichier de cookies non trouvé: docker/cookies/www.instagram.com_cookies.txt$(NC)"; \
		exit 1; \
	fi
	@python3 scripts/validate_instagram_cookies.py || true

shell: ## Ouvrir un shell dans le container Airflow
	@echo "$(BLUE)🐚 Ouverture d'un shell dans Airflow...$(NC)"
	@$(DOCKER_COMPOSE) exec airflow-scheduler bash

urls: ## Afficher les URLs d'accès
	@echo "$(BLUE)🌐 URLs d'accès:$(NC)"
	@echo "  $(GREEN)Dashboard ⭐:$(NC)      http://localhost:8000"
	@echo "                        Vue globale et détaillée"
	@echo ""
	@echo "  $(GREEN)Airflow UI:$(NC)        http://localhost:8082"
	@echo "                        Username: airflow"
	@echo "                        Password: airflow"
	@echo ""
	@echo "  $(GREEN)Kibana:$(NC)            http://localhost:5601"
	@echo "  $(GREEN)Elasticsearch:$(NC)     http://localhost:9200"
	@echo "  $(GREEN)PostgreSQL:$(NC)        localhost:5433"
	@echo "                        Database: airflow"
	@echo "                        User: airflow"
	@echo "                        Password: airflow"

open: ## Ouvrir les dashboards dans le navigateur
	@echo "$(BLUE)🌐 Ouverture des dashboards...$(NC)"
	@if command -v xdg-open >/dev/null 2>&1; then \
		echo "$(GREEN)📊 Ouverture du Dashboard...$(NC)"; \
		xdg-open http://localhost:8000 2>/dev/null & \
		sleep 1; \
		echo "$(GREEN)🚀 Ouverture d'Airflow...$(NC)"; \
		xdg-open http://localhost:8082 2>/dev/null & \
		sleep 1; \
		echo "$(GREEN)📈 Ouverture de Kibana...$(NC)"; \
		xdg-open http://localhost:5601 2>/dev/null & \
	elif command -v open >/dev/null 2>&1; then \
		echo "$(GREEN)📊 Ouverture du Dashboard...$(NC)"; \
		open http://localhost:8000 & \
		sleep 1; \
		echo "$(GREEN)🚀 Ouverture d'Airflow...$(NC)"; \
		open http://localhost:8082 & \
		sleep 1; \
		echo "$(GREEN)📈 Ouverture de Kibana...$(NC)"; \
		open http://localhost:5601 & \
	else \
		echo "$(YELLOW)⚠️  Impossible de détecter le navigateur. Ouvrez manuellement:$(NC)"; \
		echo "  - Dashboard: http://localhost:8000"; \
		echo "  - Airflow:   http://localhost:8082"; \
		echo "  - Kibana:    http://localhost:5601"; \
	fi
	@echo "$(GREEN)✅ Dashboards lancés$(NC)"

# =============================================================================
# Nettoyage
# =============================================================================

clean: ## Arrêter et supprimer les volumes (données perdues)
	@echo "$(YELLOW)⚠️  Cette commande va supprimer toutes les données !$(NC)"
	@echo "$(YELLOW)Appuyez sur Ctrl+C pour annuler, ou Entrée pour continuer...$(NC)"
	@read confirm
	@echo "$(BLUE)🧹 Nettoyage complet...$(NC)"
	@$(DOCKER_COMPOSE) down -v
	@echo "$(GREEN)✅ Services arrêtés et volumes supprimés$(NC)"

clean-all: clean ## Nettoyage complet (données + images Docker)
	@echo "$(BLUE)🧹 Suppression des images Docker...$(NC)"
	@$(DOCKER_COMPOSE) down -v --rmi all
	@echo "$(GREEN)✅ Nettoyage complet terminé$(NC)"

clean-data: ## Supprimer uniquement les données du data lake
	@echo "$(YELLOW)⚠️  Suppression des données du data lake...$(NC)"
	@rm -rf data/raw/* data/formatted/* data/usage/*
	@echo "$(GREEN)✅ Données supprimées$(NC)"

# =============================================================================
# Installation complète
# =============================================================================

install: ## Installation complète (setup + build + start)
	@echo "$(BLUE)╔════════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║  $(GREEN)Installation complète du projet$(BLUE)                             ║$(NC)"
	@echo "$(BLUE)╚════════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@make --no-print-directory check-prereqs
	@echo ""
	@make --no-print-directory setup
	@echo ""
	@echo "$(YELLOW)⚠️  Avant de continuer, assurez-vous d'avoir:$(NC)"
	@echo "  1. Édité $(BLUE)docker/.env$(NC) (AIRFLOW_UID, AIRFLOW_SECRET_KEY)"
	@echo "  2. Ajouté les cookies dans $(BLUE)docker/cookies/www.instagram.com_cookies.txt$(NC)"
	@echo "  3. Édité $(BLUE)instagram_accounts_to_scrape.txt$(NC)"
	@echo ""
	@echo "$(YELLOW)Appuyez sur Entrée pour continuer le build et le démarrage...$(NC)"
	@read confirm
	@echo ""
	@make --no-print-directory build
	@echo ""
	@make --no-print-directory validate-cookies
	@echo ""
	@make --no-print-directory up
	@echo ""
	@echo "$(GREEN)╔════════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(GREEN)║  ✅ Installation terminée avec succès !                        ║$(NC)"
	@echo "$(GREEN)╚════════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""

# =============================================================================
# Développement
# =============================================================================

trigger-dag: ## Déclencher manuellement le DAG
	@echo "$(BLUE)🎯 Déclenchement manuel du DAG...$(NC)"
	@$(DOCKER_COMPOSE) exec airflow-scheduler airflow dags trigger instagram_scraping_surveillance_pipeline
	@echo "$(GREEN)✅ DAG déclenché$(NC)"

list-dags: ## Lister tous les DAGs
	@$(DOCKER_COMPOSE) exec airflow-scheduler airflow dags list

dag-state: ## Afficher l'état du DAG
	@$(DOCKER_COMPOSE) exec airflow-scheduler airflow dags state instagram_scraping_surveillance_pipeline

setup-auto-open: ## Configurer l'ouverture automatique des dashboards à 09h00
	@echo "$(BLUE)⏰ Configuration de l'ouverture automatique à 09h00...$(NC)"
	@bash scripts/setup_auto_open.sh

# =============================================================================
# Aide par défaut
# =============================================================================

.DEFAULT_GOAL := help
