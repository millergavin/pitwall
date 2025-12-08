-- Fix role permissions: pitwall owns everything, pitwall_admin is superuser for emergencies
-- Run as pitwall_admin (superuser)

-- Ensure pitwall role exists with proper settings
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'pitwall') THEN
        CREATE ROLE pitwall WITH LOGIN PASSWORD 'pitwall';
    END IF;
END
$$;

-- Ensure pitwall owns the database
ALTER DATABASE pitwall OWNER TO pitwall;

-- Transfer schema ownership to pitwall
ALTER SCHEMA bronze OWNER TO pitwall;
ALTER SCHEMA silver OWNER TO pitwall;
ALTER SCHEMA gold OWNER TO pitwall;

-- Transfer ALL tables in each schema to pitwall
DO $$
DECLARE
    r RECORD;
BEGIN
    -- Bronze tables
    FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'bronze'
    LOOP
        EXECUTE format('ALTER TABLE bronze.%I OWNER TO pitwall', r.tablename);
    END LOOP;
    
    -- Silver tables
    FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'silver'
    LOOP
        EXECUTE format('ALTER TABLE silver.%I OWNER TO pitwall', r.tablename);
    END LOOP;
    
    -- Gold tables (if any)
    FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'gold'
    LOOP
        EXECUTE format('ALTER TABLE gold.%I OWNER TO pitwall', r.tablename);
    END LOOP;
END
$$;

-- Transfer ALL views in each schema to pitwall
DO $$
DECLARE
    r RECORD;
BEGIN
    -- Bronze views
    FOR r IN SELECT viewname FROM pg_views WHERE schemaname = 'bronze'
    LOOP
        EXECUTE format('ALTER VIEW bronze.%I OWNER TO pitwall', r.viewname);
    END LOOP;
    
    -- Silver views
    FOR r IN SELECT viewname FROM pg_views WHERE schemaname = 'silver'
    LOOP
        EXECUTE format('ALTER VIEW silver.%I OWNER TO pitwall', r.viewname);
    END LOOP;
    
    -- Gold views
    FOR r IN SELECT viewname FROM pg_views WHERE schemaname = 'gold'
    LOOP
        EXECUTE format('ALTER VIEW gold.%I OWNER TO pitwall', r.viewname);
    END LOOP;
END
$$;

-- Transfer ALL materialized views to pitwall
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN SELECT schemaname, matviewname FROM pg_matviews 
             WHERE schemaname IN ('bronze', 'silver', 'gold')
    LOOP
        EXECUTE format('ALTER MATERIALIZED VIEW %I.%I OWNER TO pitwall', r.schemaname, r.matviewname);
    END LOOP;
END
$$;

-- Transfer ALL sequences to pitwall
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN SELECT schemaname, sequencename FROM pg_sequences 
             WHERE schemaname IN ('bronze', 'silver', 'gold')
    LOOP
        EXECUTE format('ALTER SEQUENCE %I.%I OWNER TO pitwall', r.schemaname, r.sequencename);
    END LOOP;
END
$$;

-- Transfer ALL functions to pitwall
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN SELECT n.nspname as schema, p.proname as name, 
                    pg_get_function_identity_arguments(p.oid) as args
             FROM pg_proc p
             JOIN pg_namespace n ON p.pronamespace = n.oid
             WHERE n.nspname IN ('bronze', 'silver', 'gold')
    LOOP
        EXECUTE format('ALTER FUNCTION %I.%I(%s) OWNER TO pitwall', r.schema, r.name, r.args);
    END LOOP;
END
$$;

-- Transfer ALL types/enums to pitwall
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN SELECT n.nspname as schema, t.typname as name
             FROM pg_type t
             JOIN pg_namespace n ON t.typnamespace = n.oid
             WHERE n.nspname IN ('bronze', 'silver', 'gold')
               AND t.typtype = 'e'  -- enums only
    LOOP
        EXECUTE format('ALTER TYPE %I.%I OWNER TO pitwall', r.schema, r.name);
    END LOOP;
END
$$;

-- Grant pitwall full privileges on schemas
GRANT ALL PRIVILEGES ON SCHEMA bronze TO pitwall;
GRANT ALL PRIVILEGES ON SCHEMA silver TO pitwall;
GRANT ALL PRIVILEGES ON SCHEMA gold TO pitwall;
GRANT USAGE ON SCHEMA public TO pitwall;

-- Grant pitwall full privileges on all existing objects
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA bronze TO pitwall;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA silver TO pitwall;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA gold TO pitwall;

GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA bronze TO pitwall;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA silver TO pitwall;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA gold TO pitwall;

-- Set default privileges for future objects created by pitwall_admin
-- (in case pitwall_admin creates something, pitwall still gets access)
ALTER DEFAULT PRIVILEGES FOR ROLE pitwall_admin IN SCHEMA bronze GRANT ALL ON TABLES TO pitwall;
ALTER DEFAULT PRIVILEGES FOR ROLE pitwall_admin IN SCHEMA silver GRANT ALL ON TABLES TO pitwall;
ALTER DEFAULT PRIVILEGES FOR ROLE pitwall_admin IN SCHEMA gold GRANT ALL ON TABLES TO pitwall;

ALTER DEFAULT PRIVILEGES FOR ROLE pitwall_admin IN SCHEMA bronze GRANT ALL ON SEQUENCES TO pitwall;
ALTER DEFAULT PRIVILEGES FOR ROLE pitwall_admin IN SCHEMA silver GRANT ALL ON SEQUENCES TO pitwall;
ALTER DEFAULT PRIVILEGES FOR ROLE pitwall_admin IN SCHEMA gold GRANT ALL ON SEQUENCES TO pitwall;

-- Confirm pitwall does NOT have superuser privileges (safety)
ALTER ROLE pitwall WITH NOSUPERUSER NOCREATEDB NOCREATEROLE;

-- Set search path for pitwall
ALTER ROLE pitwall SET search_path TO "$user", bronze, silver, gold, public;

-- Summary output
DO $$
DECLARE
    mat_views_count INTEGER;
    tables_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO mat_views_count FROM pg_matviews WHERE schemaname IN ('bronze', 'silver', 'gold');
    SELECT COUNT(*) INTO tables_count FROM pg_tables WHERE schemaname IN ('bronze', 'silver', 'gold');
    
    RAISE NOTICE '✅ Ownership transfer complete:';
    RAISE NOTICE '   - % tables transferred to pitwall', tables_count;
    RAISE NOTICE '   - % materialized views transferred to pitwall', mat_views_count;
    RAISE NOTICE '   - pitwall_admin remains superuser for emergency/destructive operations';
    RAISE NOTICE '   - pitwall is now the day-to-day admin (no superuser privileges)';
END
$$;

