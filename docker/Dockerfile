# ==============================================================================
# Dockerfile pour Instagram Following Surveillance Pipeline
# ==============================================================================
# Ce Dockerfile construit une image Airflow complète avec:
# - Selenium + Chromium (scraping Instagram)
# - Apache Spark + PySpark (traitement de données)
# - PostgreSQL JDBC driver (stockage relationnel)
# - Elasticsearch connector (indexation recherche)
# - Gender detection ML (prédictions de genre)
# ==============================================================================

FROM apache/airflow:2.10.3-python3.12

# ==============================================================================
# PHASE 1: Installation des packages système (en tant que root)
# ==============================================================================

USER root

# Installer tous les packages système nécessaires + support X11 pour mode visuel
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        chromium \
        chromium-driver \
        openjdk-17-jre-headless \
        wget \
        curl \
        libglib2.0-0 \
        libnss3 \
        libgconf-2-4 \
        libfontconfig1 \
        x11-apps \
        x11-xserver-utils \
        xauth \
        libxext6 \
        libxrender1 \
        libxtst6 \
        libxi6 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ==============================================================================
# PHASE 2: Téléchargement des JARs Spark
# ==============================================================================

RUN mkdir -p /opt/airflow/jars && \
    wget -q https://jdbc.postgresql.org/download/postgresql-42.2.27.jar \
        -O /opt/airflow/jars/postgresql-42.2.27.jar && \
    wget -q https://repo1.maven.org/maven2/org/elasticsearch/elasticsearch-spark-30_2.12/8.5.3/elasticsearch-spark-30_2.12-8.5.3.jar \
        -O /opt/airflow/jars/elasticsearch-spark-30_2.12-8.5.3.jar && \
    ls -lh /opt/airflow/jars/

# ==============================================================================
# PHASE 3: Création des répertoires et liens symboliques
# ==============================================================================

# Créer la structure de répertoires
RUN mkdir -p /opt/airflow/scripts \
             /opt/airflow/dags \
             /opt/airflow/logs \
             /opt/airflow/data \
             /opt/airflow/cookies \
             /tmp/scraping_output

# Créer le lien symbolique /sources -> /opt/airflow (pour compatibilité avec les scripts)
RUN mkdir -p /sources && \
    ln -sf /opt/airflow /sources/instagram_surveillance

# Permissions
RUN chown -R airflow:root /opt/airflow/scripts \
                           /opt/airflow/dags \
                           /opt/airflow/logs \
                           /opt/airflow/data \
                           /opt/airflow/cookies \
                           /tmp/scraping_output \
                           /sources

# ==============================================================================
# PHASE 4: Installation des dépendances Python
# ==============================================================================

COPY requirements.txt /requirements.txt

USER airflow

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /requirements.txt

# Vérifier les installations critiques
RUN python -c "import selenium; print(f'✅ Selenium {selenium.__version__}')" && \
    python -c "import pyspark; print(f'✅ PySpark {pyspark.__version__}')" && \
    python -c "import pandas; print(f'✅ Pandas {pandas.__version__}')" && \
    python -c "import gender_guesser; print('✅ Gender-guesser installed')"

# ==============================================================================
# PHASE 5: Configuration des variables d'environnement
# ==============================================================================

# Java pour Spark
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="${JAVA_HOME}/bin:${PATH}"

# Spark
ENV SPARK_HOME=/home/airflow/.local/lib/python3.12/site-packages/pyspark
ENV PYSPARK_PYTHON=/usr/local/bin/python
ENV PYSPARK_DRIVER_PYTHON=/usr/local/bin/python

# Chrome/Chromium pour Selenium
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver
ENV SE_CACHE_PATH=/tmp/selenium_cache

# Airflow
ENV AIRFLOW_HOME=/opt/airflow
ENV PYTHONPATH="${PYTHONPATH}:/opt/airflow/scripts"

# ==============================================================================
# INFO
# ==============================================================================

USER root
RUN echo "==================== BUILD INFO ====================" && \
    echo "Airflow version: 2.10.3" && \
    echo "Python version: 3.12" && \
    java -version 2>&1 | head -1 && \
    chromium --version && \
    chromedriver --version && \
    echo "===================================================="

USER airflow
