-- =====================================================================
-- SYSTÈME DE FUSION INTELLIGENTE DES SCRAPINGS MULTIPLES
-- =====================================================================
-- Objectif : Fusionner tous les scrapings du jour pour obtenir la liste
--            la plus complète possible et détecter précisément les
--            ajouts/suppressions avec niveau de confiance
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. TABLE : daily_unified_followings
-- Stocke la vue fusionnée quotidienne de tous les scrapings valides
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS daily_unified_followings (
    id SERIAL PRIMARY KEY,
    target_account VARCHAR(255) NOT NULL,
    date DATE NOT NULL,
    username VARCHAR(255) NOT NULL,
    full_name TEXT,
    predicted_gender VARCHAR(10),
    gender_confidence FLOAT,

    -- Métadonnées de fusion
    appearances_count INT NOT NULL DEFAULT 1,  -- Nombre de scrapings où ce following apparaît
    total_scrapings INT NOT NULL,              -- Nombre total de scrapings valides du jour
    confidence_score FLOAT NOT NULL,            -- = appearances_count / total_scrapings
    first_seen_at TIMESTAMP,                    -- Premier scraping où il est apparu ce jour
    last_seen_at TIMESTAMP,                     -- Dernier scraping où il est apparu

    -- Détection des changements
    is_new BOOLEAN DEFAULT FALSE,               -- Nouveau following (absent jour J-1)
    is_removed BOOLEAN DEFAULT FALSE,           -- Supprimé (présent J-1, absent J)
    change_confidence VARCHAR(10),              -- HIGH/MEDIUM/LOW

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT unique_daily_following UNIQUE (target_account, date, username)
);

CREATE INDEX idx_daily_unified_account_date ON daily_unified_followings(target_account, date);
CREATE INDEX idx_daily_unified_username ON daily_unified_followings(username);
CREATE INDEX idx_daily_unified_new ON daily_unified_followings(target_account, date, is_new) WHERE is_new = true;
CREATE INDEX idx_daily_unified_removed ON daily_unified_followings(target_account, date, is_removed) WHERE is_removed = true;

-- ---------------------------------------------------------------------
-- 2. FONCTION : get_valid_scrapings_for_day
-- Retourne tous les scrapings valides (>50% complétude) pour un jour donné
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_valid_scrapings_for_day(
    p_account VARCHAR(255),
    p_date DATE,
    p_min_completeness FLOAT DEFAULT 50.0
)
RETURNS TABLE (
    scraping_timestamp TIMESTAMP,
    total_followings INT,
    completeness_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        sm.scraping_timestamp,
        sm.total_followings,
        sm.completeness_score
    FROM scraping_metadata sm
    WHERE sm.target_account = p_account
      AND sm.scraping_date = p_date
      AND sm.completeness_score >= p_min_completeness
    ORDER BY sm.scraping_timestamp;
END;
$$ LANGUAGE plpgsql;

-- ---------------------------------------------------------------------
-- 3. FONCTION : rebuild_unified_followings_for_day
-- Reconstruit la vue fusionnée en combinant tous les scrapings valides
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION rebuild_unified_followings_for_day(
    p_account VARCHAR(255),
    p_date DATE
)
RETURNS TABLE (
    total_unique_followings INT,
    scrapings_used INT,
    coverage_improvement FLOAT
) AS $$
DECLARE
    v_scrapings_count INT;
    v_unique_count INT;
    v_instagram_total INT;
    v_best_single_scraping INT;
    v_improvement FLOAT;
BEGIN
    -- Supprimer les données existantes pour ce jour
    DELETE FROM daily_unified_followings
    WHERE target_account = p_account AND date = p_date;

    -- Compter le nombre de scrapings valides
    SELECT COUNT(*) INTO v_scrapings_count
    FROM scraping_metadata sm
    WHERE sm.target_account = p_account
      AND sm.scraping_date = p_date
      AND sm.completeness_score >= 50.0;

    IF v_scrapings_count = 0 THEN
        RAISE NOTICE 'Aucun scraping valide trouvé pour % le %', p_account, p_date;
        RETURN;
    END IF;

    -- Obtenir le nombre Instagram reporté
    SELECT instagram_reported_total INTO v_instagram_total
    FROM scraping_metadata
    WHERE target_account = p_account
      AND scraping_date = p_date
      AND instagram_reported_total IS NOT NULL
    ORDER BY scraping_timestamp DESC
    LIMIT 1;

    -- Fusionner tous les followings de tous les scrapings valides
    INSERT INTO daily_unified_followings (
        target_account,
        date,
        username,
        full_name,
        predicted_gender,
        gender_confidence,
        appearances_count,
        total_scrapings,
        confidence_score,
        first_seen_at,
        last_seen_at
    )
    SELECT
        p_account,
        p_date,
        f.username,
        MAX(f.full_name) as full_name,  -- Prendre le full_name le plus récent
        MAX(f.predicted_gender) as predicted_gender,
        MAX(f.confidence) as gender_confidence,
        COUNT(DISTINCT sm.scraping_timestamp) as appearances_count,
        v_scrapings_count as total_scrapings,
        ROUND((COUNT(DISTINCT sm.scraping_timestamp)::NUMERIC / v_scrapings_count::NUMERIC) * 100, 2) as confidence_score,
        MIN(sm.scraping_timestamp) as first_seen_at,
        MAX(sm.scraping_timestamp) as last_seen_at
    FROM instagram_followings f
    INNER JOIN scraping_metadata sm ON (
        f.target_account = sm.target_account
        AND f.scraping_date::date = sm.scraping_date
        AND f.scraping_date = sm.scraping_timestamp
    )
    WHERE f.target_account = p_account
      AND f.scraping_date::date = p_date
      AND sm.completeness_score >= 50.0
    GROUP BY f.username;

    -- Compter les followings uniques obtenus
    SELECT COUNT(*) INTO v_unique_count
    FROM daily_unified_followings
    WHERE target_account = p_account AND date = p_date;

    -- Calculer l'amélioration par rapport au meilleur scraping unique
    SELECT MAX(total_followings) INTO v_best_single_scraping
    FROM scraping_metadata
    WHERE target_account = p_account
      AND scraping_date = p_date
      AND completeness_score >= 50.0;

    v_improvement := ROUND(((v_unique_count::NUMERIC - v_best_single_scraping::NUMERIC) / v_best_single_scraping::NUMERIC) * 100, 2);

    RAISE NOTICE 'Fusion completed for account: % date: %', p_account, p_date;
    RAISE NOTICE 'Scrapings used: %', v_scrapings_count;
    RAISE NOTICE 'Unique followings: %', v_unique_count;
    RAISE NOTICE 'Best single scraping: %', v_best_single_scraping;
    RAISE NOTICE 'Improvement: +% followings', (v_unique_count - v_best_single_scraping);
    IF v_instagram_total IS NOT NULL THEN
        RAISE NOTICE 'Instagram reported: %', v_instagram_total;
        RAISE NOTICE 'Coverage percent: %', ROUND((v_unique_count::NUMERIC / v_instagram_total::NUMERIC) * 100, 2);
    END IF;

    RETURN QUERY
    SELECT v_unique_count, v_scrapings_count, v_improvement;
END;
$$ LANGUAGE plpgsql;

-- ---------------------------------------------------------------------
-- 4. FONCTION : detect_changes_with_confidence
-- Détecte les ajouts et suppressions en comparant avec le jour précédent
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION detect_changes_with_confidence(
    p_account VARCHAR(255),
    p_date DATE
)
RETURNS TABLE (
    new_followings_count INT,
    removed_followings_count INT,
    high_confidence_changes INT
) AS $$
DECLARE
    v_prev_date DATE;
    v_new_count INT := 0;
    v_removed_count INT := 0;
    v_high_conf_count INT := 0;
BEGIN
    -- Date du jour précédent
    v_prev_date := p_date - INTERVAL '1 day';

    -- Marquer les nouveaux followings (présents en J, absents en J-1)
    UPDATE daily_unified_followings duf
    SET
        is_new = TRUE,
        change_confidence = CASE
            WHEN duf.confidence_score >= 80 THEN 'HIGH'
            WHEN duf.confidence_score >= 50 THEN 'MEDIUM'
            ELSE 'LOW'
        END,
        updated_at = NOW()
    WHERE duf.target_account = p_account
      AND duf.date = p_date
      AND NOT EXISTS (
          SELECT 1 FROM daily_unified_followings prev
          WHERE prev.target_account = p_account
            AND prev.date = v_prev_date
            AND prev.username = duf.username
            AND prev.confidence_score >= 50  -- Seulement si c'était fiable
      );

    GET DIAGNOSTICS v_new_count = ROW_COUNT;

    -- Marquer les followings supprimés (présents en J-1, absents en J)
    INSERT INTO daily_unified_followings (
        target_account,
        date,
        username,
        full_name,
        predicted_gender,
        gender_confidence,
        appearances_count,
        total_scrapings,
        confidence_score,
        is_removed,
        change_confidence
    )
    SELECT
        p_account,
        p_date,
        prev.username,
        prev.full_name,
        prev.predicted_gender,
        prev.gender_confidence,
        0 as appearances_count,
        (SELECT COUNT(*) FROM scraping_metadata WHERE target_account = p_account AND scraping_date = p_date AND completeness_score >= 50) as total_scrapings,
        0 as confidence_score,
        TRUE as is_removed,
        CASE
            WHEN prev.confidence_score >= 80 THEN 'HIGH'
            WHEN prev.confidence_score >= 50 THEN 'MEDIUM'
            ELSE 'LOW'
        END as change_confidence
    FROM daily_unified_followings prev
    WHERE prev.target_account = p_account
      AND prev.date = v_prev_date
      AND prev.confidence_score >= 50  -- Seulement si c'était fiable
      AND NOT EXISTS (
          SELECT 1 FROM daily_unified_followings cur
          WHERE cur.target_account = p_account
            AND cur.date = p_date
            AND cur.username = prev.username
      )
    ON CONFLICT (target_account, date, username) DO NOTHING;

    GET DIAGNOSTICS v_removed_count = ROW_COUNT;

    -- Compter les changements à haute confiance
    SELECT COUNT(*) INTO v_high_conf_count
    FROM daily_unified_followings
    WHERE target_account = p_account
      AND date = p_date
      AND (is_new = TRUE OR is_removed = TRUE)
      AND change_confidence = 'HIGH';

    RAISE NOTICE 'Change detection for account: % date: %', p_account, p_date;
    RAISE NOTICE 'New followings: %', v_new_count;
    RAISE NOTICE 'Removed followings: %', v_removed_count;
    RAISE NOTICE 'High confidence changes: %', v_high_conf_count;

    RETURN QUERY
    SELECT v_new_count, v_removed_count, v_high_conf_count;
END;
$$ LANGUAGE plpgsql;

-- ---------------------------------------------------------------------
-- 5. FONCTION : get_unified_view_for_day
-- Retourne la vue unifiée pour affichage dans le dashboard
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_unified_view_for_day(
    p_account VARCHAR(255),
    p_date DATE DEFAULT CURRENT_DATE
)
RETURNS TABLE (
    username VARCHAR(255),
    full_name TEXT,
    predicted_gender VARCHAR(10),
    gender_confidence FLOAT,
    confidence_score FLOAT,
    appearances_count INT,
    total_scrapings INT,
    is_new BOOLEAN,
    is_removed BOOLEAN,
    change_confidence VARCHAR(10)
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        duf.username,
        duf.full_name,
        duf.predicted_gender,
        duf.gender_confidence,
        duf.confidence_score,
        duf.appearances_count,
        duf.total_scrapings,
        duf.is_new,
        duf.is_removed,
        duf.change_confidence
    FROM daily_unified_followings duf
    WHERE duf.target_account = p_account
      AND duf.date = p_date
      AND duf.is_removed = FALSE  -- Exclure les supprimés de la vue principale
    ORDER BY duf.username;
END;
$$ LANGUAGE plpgsql;

-- ---------------------------------------------------------------------
-- 6. FONCTION : get_daily_stats
-- Retourne les statistiques de la vue unifiée
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_daily_stats(
    p_account VARCHAR(255),
    p_date DATE DEFAULT CURRENT_DATE
)
RETURNS TABLE (
    total_unique INT,
    total_male INT,
    total_female INT,
    total_unknown INT,
    new_today INT,
    removed_today INT,
    scrapings_used INT,
    avg_confidence FLOAT,
    instagram_reported INT,
    coverage_percent FLOAT
) AS $$
DECLARE
    v_instagram_total INT;
BEGIN
    -- Obtenir le nombre Instagram reporté
    SELECT instagram_reported_total INTO v_instagram_total
    FROM scraping_metadata
    WHERE target_account = p_account
      AND scraping_date = p_date
      AND instagram_reported_total IS NOT NULL
    ORDER BY scraping_timestamp DESC
    LIMIT 1;

    RETURN QUERY
    SELECT
        COUNT(*)::INT as total_unique,
        COUNT(*) FILTER (WHERE predicted_gender = 'male')::INT as total_male,
        COUNT(*) FILTER (WHERE predicted_gender = 'female')::INT as total_female,
        COUNT(*) FILTER (WHERE predicted_gender IS NULL OR predicted_gender = 'unknown')::INT as total_unknown,
        COUNT(*) FILTER (WHERE is_new = TRUE)::INT as new_today,
        COUNT(*) FILTER (WHERE is_removed = TRUE)::INT as removed_today,
        MAX(total_scrapings)::INT as scrapings_used,
        ROUND(AVG(confidence_score), 2)::NUMERIC as avg_confidence,
        v_instagram_total as instagram_reported,
        CASE
            WHEN v_instagram_total > 0 THEN ROUND((COUNT(*)::NUMERIC / v_instagram_total::NUMERIC) * 100, 2)
            ELSE NULL
        END as coverage_percent
    FROM daily_unified_followings
    WHERE target_account = p_account
      AND date = p_date
      AND is_removed = FALSE;
END;
$$ LANGUAGE plpgsql;

-- =====================================================================
-- COMMENTAIRES ET DOCUMENTATION
-- =====================================================================
COMMENT ON TABLE daily_unified_followings IS 'Vue fusionnée quotidienne de tous les scrapings valides - combine les données pour obtenir la liste la plus complète possible';
COMMENT ON COLUMN daily_unified_followings.appearances_count IS 'Nombre de scrapings où ce following apparaît (sur le total des scrapings valides du jour)';
COMMENT ON COLUMN daily_unified_followings.confidence_score IS 'Pourcentage d''apparition = (appearances_count / total_scrapings) * 100';
COMMENT ON COLUMN daily_unified_followings.is_new IS 'TRUE si ce following est nouveau (absent du jour J-1)';
COMMENT ON COLUMN daily_unified_followings.is_removed IS 'TRUE si ce following a été supprimé (présent en J-1, absent en J)';
COMMENT ON COLUMN daily_unified_followings.change_confidence IS 'Niveau de confiance du changement détecté: HIGH (>80%), MEDIUM (50-80%), LOW (<50%)';

COMMENT ON FUNCTION rebuild_unified_followings_for_day IS 'Reconstruit la vue fusionnée en combinant TOUS les scrapings valides du jour pour obtenir la liste la plus complète';
COMMENT ON FUNCTION detect_changes_with_confidence IS 'Détecte les vrais ajouts et suppressions en comparant avec le jour précédent, avec niveau de confiance';
COMMENT ON FUNCTION get_unified_view_for_day IS 'Retourne la vue unifiée pour affichage dans le dashboard';
COMMENT ON FUNCTION get_daily_stats IS 'Retourne les statistiques globales de la vue unifiée (total, genre, nouveaux, supprimés, couverture)';
