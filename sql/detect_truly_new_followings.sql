-- Vue pour détecter les VRAIS nouveaux followings (robuste aux scrapings incomplets)
CREATE OR REPLACE VIEW truly_new_followings AS
WITH scraping_quality AS (
    -- Évaluer la qualité de chaque scraping
    SELECT
        target_account,
        scraping_date,
        total_followings,
        is_complete,
        completeness_score,
        ROW_NUMBER() OVER (PARTITION BY target_account ORDER BY scraping_date DESC) as recency_rank
    FROM scraping_metadata
),
reference_scrapings AS (
    -- Pour chaque date, trouver le dernier scraping "complet" avant cette date
    SELECT
        s1.target_account,
        s1.scraping_date as current_date,
        MAX(s2.scraping_date) as last_complete_date
    FROM scraping_quality s1
    LEFT JOIN scraping_quality s2
        ON s1.target_account = s2.target_account
        AND s2.scraping_date < s1.scraping_date
        AND s2.is_complete = TRUE
    GROUP BY s1.target_account, s1.scraping_date
),
current_followings AS (
    -- Followings du scraping actuel
    SELECT DISTINCT
        f.target_account,
        f.aggregation_date::date as scraping_date,
        f.username,
        f.full_name,
        f.predicted_gender
    FROM final_aggregated_scraping f
    WHERE f.aggregation_date IS NOT NULL
),
reference_followings AS (
    -- Followings du dernier scraping complet
    SELECT DISTINCT
        f.target_account,
        r.current_date,
        f.username
    FROM reference_scrapings r
    INNER JOIN final_aggregated_scraping f
        ON f.target_account = r.target_account
        AND f.aggregation_date::date = r.last_complete_date
    WHERE r.last_complete_date IS NOT NULL
)
SELECT
    c.target_account,
    c.scraping_date,
    c.username,
    c.full_name,
    c.predicted_gender,
    'truly_new' as status,
    r.current_date as reference_date
FROM current_followings c
LEFT JOIN reference_followings r
    ON c.target_account = r.target_account
    AND c.scraping_date = r.current_date
    AND c.username = r.username
WHERE r.username IS NULL  -- N'existait pas dans le dernier scraping complet
AND c.scraping_date IN (
    -- Seulement pour les scrapings marqués comme "complets"
    SELECT scraping_date
    FROM scraping_quality
    WHERE target_account = c.target_account
    AND is_complete = TRUE
);

-- Vue pour l'historique des nouveaux avec contexte de qualité
CREATE OR REPLACE VIEW new_followings_history AS
SELECT
    tnf.target_account,
    tnf.scraping_date,
    tnf.username,
    tnf.full_name,
    tnf.predicted_gender,
    tnf.status,
    sm.completeness_score,
    sm.total_followings as scraping_total,
    tnf.reference_date
FROM truly_new_followings tnf
LEFT JOIN scraping_metadata sm
    ON tnf.target_account = sm.target_account
    AND tnf.scraping_date = sm.scraping_date
ORDER BY tnf.scraping_date DESC, tnf.target_account, tnf.username;

-- Fonction pour obtenir les nouveaux followings d'une date spécifique
CREATE OR REPLACE FUNCTION get_new_followings_for_date(
    p_target_account VARCHAR,
    p_date DATE
) RETURNS TABLE (
    username TEXT,
    full_name TEXT,
    predicted_gender TEXT,
    is_truly_new BOOLEAN,
    confidence_score DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    WITH last_complete AS (
        SELECT scraping_date, total_followings
        FROM scraping_metadata
        WHERE target_account = p_target_account
        AND scraping_date < p_date
        AND is_complete = TRUE
        ORDER BY scraping_date DESC
        LIMIT 1
    ),
    current_scraping AS (
        SELECT DISTINCT
            f.username,
            f.full_name,
            f.predicted_gender
        FROM final_aggregated_scraping f
        WHERE f.target_account = p_target_account
        AND f.aggregation_date::date = p_date
    ),
    reference_scraping AS (
        SELECT DISTINCT f.username
        FROM final_aggregated_scraping f, last_complete lc
        WHERE f.target_account = p_target_account
        AND f.aggregation_date::date = lc.scraping_date
    ),
    scraping_quality AS (
        SELECT completeness_score
        FROM scraping_metadata
        WHERE target_account = p_target_account
        AND scraping_date = p_date
    )
    SELECT
        cs.username::TEXT,
        cs.full_name::TEXT,
        cs.predicted_gender::TEXT,
        (rs.username IS NULL) as is_truly_new,
        COALESCE(sq.completeness_score, 0) as confidence_score
    FROM current_scraping cs
    LEFT JOIN reference_scraping rs ON cs.username = rs.username
    CROSS JOIN scraping_quality sq
    WHERE rs.username IS NULL;
END;
$$ LANGUAGE plpgsql;

-- Fonction pour comparer deux dates en tenant compte de la qualité
CREATE OR REPLACE FUNCTION compare_scrapings_smart(
    p_target_account VARCHAR,
    p_date1 DATE,
    p_date2 DATE
) RETURNS TABLE (
    username TEXT,
    full_name TEXT,
    predicted_gender TEXT,
    change_type TEXT, -- 'added', 'removed', 'stable'
    confidence TEXT   -- 'high', 'medium', 'low' selon qualité scrapings
) AS $$
DECLARE
    v_quality1 DECIMAL;
    v_quality2 DECIMAL;
    v_confidence VARCHAR;
BEGIN
    -- Récupérer les scores de qualité
    SELECT completeness_score INTO v_quality1
    FROM scraping_metadata
    WHERE target_account = p_target_account AND scraping_date = p_date1;

    SELECT completeness_score INTO v_quality2
    FROM scraping_metadata
    WHERE target_account = p_target_account AND scraping_date = p_date2;

    -- Déterminer la confiance globale
    IF v_quality1 >= 95 AND v_quality2 >= 95 THEN
        v_confidence := 'high';
    ELSIF v_quality1 >= 80 AND v_quality2 >= 80 THEN
        v_confidence := 'medium';
    ELSE
        v_confidence := 'low';
    END IF;

    RETURN QUERY
    WITH date1_data AS (
        SELECT DISTINCT
            f.username,
            f.full_name,
            f.predicted_gender
        FROM final_aggregated_scraping f
        WHERE f.target_account = p_target_account
        AND f.aggregation_date::date = p_date1
    ),
    date2_data AS (
        SELECT DISTINCT
            f.username,
            f.full_name,
            f.predicted_gender
        FROM final_aggregated_scraping f
        WHERE f.target_account = p_target_account
        AND f.aggregation_date::date = p_date2
    )
    -- Ajouts (dans date2, pas dans date1)
    SELECT
        d2.username::TEXT,
        d2.full_name::TEXT,
        d2.predicted_gender::TEXT,
        'added'::TEXT as change_type,
        v_confidence::TEXT
    FROM date2_data d2
    LEFT JOIN date1_data d1 ON d2.username = d1.username
    WHERE d1.username IS NULL

    UNION ALL

    -- Suppressions (dans date1, pas dans date2)
    SELECT
        d1.username::TEXT,
        d1.full_name::TEXT,
        d1.predicted_gender::TEXT,
        'removed'::TEXT as change_type,
        v_confidence::TEXT
    FROM date1_data d1
    LEFT JOIN date2_data d2 ON d1.username = d2.username
    WHERE d2.username IS NULL;
END;
$$ LANGUAGE plpgsql;
