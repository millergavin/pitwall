-- Initialize Pitwall database with proper role separation
-- pitwall_admin: superuser (created by docker, can do destructive ops)
-- pitwall: day-to-day admin (owns everything, no superuser privileges)

-- Create the pitwall role (non-superuser)
CREATE ROLE pitwall WITH LOGIN PASSWORD 'pitwall' NOSUPERUSER NOCREATEDB NOCREATEROLE;

-- Create the schemas (as pitwall_admin initially)
CREATE SCHEMA bronze;
CREATE SCHEMA silver;
CREATE SCHEMA gold;

-- Transfer schema ownership to pitwall immediately
ALTER SCHEMA bronze OWNER TO pitwall;
ALTER SCHEMA silver OWNER TO pitwall;
ALTER SCHEMA gold OWNER TO pitwall;

-- Revoke CREATE on public schema from public (security best practice)
REVOKE CREATE ON SCHEMA public FROM public;

-- Set default search_path for pitwall role
ALTER ROLE pitwall SET search_path TO "$user", bronze, silver, gold, public;

-- Grant full privileges on schemas to pitwall
GRANT ALL PRIVILEGES ON SCHEMA bronze TO pitwall;
GRANT ALL PRIVILEGES ON SCHEMA silver TO pitwall;
GRANT ALL PRIVILEGES ON SCHEMA gold TO pitwall;
GRANT USAGE ON SCHEMA public TO pitwall;

-- Set default privileges: any objects created by pitwall_admin grant full access to pitwall
ALTER DEFAULT PRIVILEGES FOR ROLE pitwall_admin IN SCHEMA bronze GRANT ALL ON TABLES TO pitwall;
ALTER DEFAULT PRIVILEGES FOR ROLE pitwall_admin IN SCHEMA silver GRANT ALL ON TABLES TO pitwall;
ALTER DEFAULT PRIVILEGES FOR ROLE pitwall_admin IN SCHEMA gold GRANT ALL ON TABLES TO pitwall;

ALTER DEFAULT PRIVILEGES FOR ROLE pitwall_admin IN SCHEMA bronze GRANT ALL ON SEQUENCES TO pitwall;
ALTER DEFAULT PRIVILEGES FOR ROLE pitwall_admin IN SCHEMA silver GRANT ALL ON SEQUENCES TO pitwall;
ALTER DEFAULT PRIVILEGES FOR ROLE pitwall_admin IN SCHEMA gold GRANT ALL ON SEQUENCES TO pitwall;

-- Note: For existing databases, run 11-fix-role-permissions.sql to transfer ownership
-- of all existing objects to pitwall
