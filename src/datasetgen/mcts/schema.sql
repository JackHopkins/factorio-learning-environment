-- Programs table to store history
CREATE TABLE programs (
    id SERIAL PRIMARY KEY,
    code TEXT NOT NULL,
    value FLOAT DEFAULT 0.0,
    visits INTEGER DEFAULT 0,
    parent_id INTEGER REFERENCES programs(id),
    state_json JSONB,
    conversation_json JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    holdout_value: FLOAT DEFAULT 0.0,
    raw_reward: FLOAT DEFAULT 0.0,
    version: INTEGER DEFAULT 0, -- version of the program code
    version_description: TEXT DEFAULT NULL, -- description of the version change
);

-- Task queue table
CREATE TABLE evaluation_queue (
    id SERIAL PRIMARY KEY,
    program_id INTEGER REFERENCES programs(id),
    status TEXT DEFAULT 'pending',
    instance_id INTEGER,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    result_json JSONB
);

CREATE OR REPLACE FUNCTION sample_parent(target_version INTEGER)
RETURNS INTEGER AS $$
DECLARE
    selected_id INTEGER;
BEGIN
    WITH recent AS (
        SELECT id, value
        FROM programs
        WHERE version = target_version
        ORDER BY created_at DESC
        LIMIT 100
    ),
    softmax AS (
        SELECT
            id,
            EXP(value - (SELECT MAX(value) FROM recent)) as weight
        FROM recent
    )
    SELECT id INTO selected_id
    FROM softmax
    WHERE random() <= (
        weight / (SELECT SUM(weight) FROM softmax)
    )
    LIMIT 1;

    RETURN selected_id;
END;
$$ LANGUAGE plpgsql;