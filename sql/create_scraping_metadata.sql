-- Table pour tracker la qualité/complétude de chaque scraping
CREATE TABLE IF NOT EXISTS scraping_metadata (
    id SERIAL PRIMARY KEY,
    target_account VARCHAR(255) NOT NULL,
    scraping_date DATE NOT NULL,
    scraping_timestamp TIMESTAMP NOT NULL,
    total_followings INTEGER NOT NULL,
    completeness_score DECIMAL(5,2), -- % estimé de complétude (100 = complet)
    is_complete BOOLEAN DEFAULT FALSE, -- Marqué comme "complet" si > 90% du max observé
    scraping_duration_seconds INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(target_account, scraping_date, scraping_timestamp)
);

-- Index pour requêtes rapides
CREATE INDEX IF NOT EXISTS idx_scraping_metadata_account_date
ON scraping_metadata(target_account, scraping_date DESC);

CREATE INDEX IF NOT EXISTS idx_scraping_metadata_complete
ON scraping_metadata(target_account, is_complete, scraping_date DESC);

-- Vue pour obtenir le dernier scraping "complet" par compte
CREATE OR REPLACE VIEW last_complete_scraping AS
SELECT DISTINCT ON (target_account)
    target_account,
    scraping_date,
    total_followings,
    completeness_score
FROM scraping_metadata
WHERE is_complete = TRUE
ORDER BY target_account, scraping_date DESC;

-- Fonction pour calculer le score de complétude
CREATE OR REPLACE FUNCTION calculate_completeness_score(
    p_target_account VARCHAR,
    p_current_count INTEGER
) RETURNS DECIMAL AS $$
DECLARE
    v_max_count INTEGER;
    v_avg_recent_count DECIMAL;
    v_score DECIMAL;
BEGIN
    -- Récupérer le max et la moyenne des 5 derniers scrapings
    SELECT
        MAX(total_followings),
        AVG(total_followings)
    INTO v_max_count, v_avg_recent_count
    FROM scraping_metadata
    WHERE target_account = p_target_account
    AND scraping_date >= CURRENT_DATE - INTERVAL '7 days';

    -- Si pas d'historique, considérer comme complet
    IF v_max_count IS NULL THEN
        RETURN 100.0;
    END IF;

    -- Calculer le score basé sur le max
    v_score := (p_current_count::DECIMAL / v_max_count::DECIMAL) * 100;

    -- Plafonner à 100
    IF v_score > 100 THEN
        v_score := 100;
    END IF;

    RETURN ROUND(v_score, 2);
END;
$$ LANGUAGE plpgsql;

-- Fonction pour marquer automatiquement les scrapings complets
CREATE OR REPLACE FUNCTION mark_complete_scrapings() RETURNS void AS $$
BEGIN
    UPDATE scraping_metadata
    SET is_complete = TRUE
    WHERE completeness_score >= 90.0
    AND is_complete = FALSE;
END;
$$ LANGUAGE plpgsql;
