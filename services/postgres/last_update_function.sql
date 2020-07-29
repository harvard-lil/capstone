CREATE OR REPLACE FUNCTION track_last_update()
    RETURNS TRIGGER AS
$$
DECLARE
    row     RECORD;
    changed boolean;
BEGIN
    -- skip updates where no relevant columns are changed
    IF TG_OP = 'UPDATE' THEN
        EXECUTE 'SELECT ' || TG_ARGV[1] || ';' INTO changed USING OLD, NEW;
        if changed = false then
            return null;
        end if;
    end if;

    -- get row object to use for case_id
    IF TG_OP = 'DELETE' THEN
        row = OLD;
    ELSE
        row = NEW;
    END IF;

    -- write to CaseLastUpdate
    EXECUTE 'INSERT INTO capdb_caselastupdate (case_id, timestamp, indexed) VALUES($1.' || TG_ARGV[0] || ', NOW(), false)' ||
            'ON CONFLICT (case_id)' ||
            'DO UPDATE SET timestamp = NOW(), indexed = false;'
        USING row;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- CREATE OR REPLACE FUNCTION track_last_update() RETURNS TRIGGER AS
-- $$
--     var case_id_col = TG_ARGV[0], update_fields = TG_ARGV.slice(1);
--
--     // do nothing if no relevant fields changed
--     if (TG_OP === "UPDATE") {
--         for(var i=0; i<update_fields.length && OLD[update_fields[i]] === NEW[update_fields[i]]; i++);
--         if (i === update_fields.length)
--             return;
--     }
--
--     // update capdb_caselastupdate
--     var row = TG_OP === "DELETE" ? OLD : NEW;
--     plv8.execute(
--         'INSERT INTO capdb_caselastupdate (case_id, timestamp, indexed) VALUES($1, NOW(), false)\
--         ON CONFLICT (case_id)\
--         DO UPDATE SET timestamp = NOW(), indexed = false;', row[case_id_col]);
-- $$
-- LANGUAGE "plv8";

CREATE OR REPLACE FUNCTION fkey_last_update()
    RETURNS TRIGGER AS
$$
DECLARE
    changed boolean;
BEGIN
    -- TG_ARGV[0] is the field on capdb_casemetadata, e.g. 'volume_id'
    -- TG_ARGV[1] is the primary key on the foreign table, e.g. 'barcode'
    -- TG_ARGV[2] are fields on the foreign table that should trigger a change to capdb_caselastupdate

    -- skip updates where no relevant columns are changed
    EXECUTE 'SELECT ' || TG_ARGV[2] || ';' INTO changed USING OLD, NEW;
    if changed = false then
        return null;
    end if;

    -- write to CaseLastUpdate
    EXECUTE 'INSERT INTO capdb_caselastupdate (case_id, timestamp, indexed) ' ||
            'SELECT id, NOW(), false FROM capdb_casemetadata WHERE ' || TG_ARGV[0] || '=$1.' || TG_ARGV[1] || ' ' ||
            'ON CONFLICT (case_id)' ||
            'DO UPDATE SET timestamp = NOW(), indexed = false;'
        USING NEW;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- CREATE OR REPLACE FUNCTION fkey_last_update() RETURNS TRIGGER AS
-- $$
--     var fkey_col = TG_ARGV[0], id_col = TG_ARGV[1], update_fields = TG_ARGV.slice(2);
--
--     // do nothing if no relevant fields changed
--     for(var i=0; i<update_fields.length && OLD[update_fields[i]] === NEW[update_fields[i]]; i++);
--     if (i === update_fields.length)
--         return;
--
--     // update capdb_caselastupdate
--     plv8.execute(
--         'INSERT INTO capdb_caselastupdate (case_id, timestamp, indexed)\
--         SELECT id, NOW(), false FROM capdb_casemetadata WHERE '+fkey_col+'=$1\
--         ON CONFLICT (case_id)\
--         DO UPDATE SET timestamp = NOW(), indexed = false;', NEW[id_col]);
-- $$
-- LANGUAGE "plv8";



-- example usage
-- DROP TRIGGER IF EXISTS fkey_last_update_trigger ON capdb_reporter;
-- CREATE TRIGGER fkey_last_update_trigger
--     AFTER UPDATE OF full_name
--     ON capdb_reporter
--     FOR EACH ROW
-- EXECUTE PROCEDURE fkey_last_update('reporter_id', 'id', 'full_name');
--
-- DROP TRIGGER IF EXISTS last_update_trigger ON capdb_citation;
-- CREATE TRIGGER last_update_trigger
--     AFTER INSERT OR DELETE OR UPDATE OF type, cite
--     ON capdb_citation
--     FOR EACH ROW
-- EXECUTE PROCEDURE track_last_update('case_id', 'type', 'cite');


