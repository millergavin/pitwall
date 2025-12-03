-- Create the non-superuser role
CREATE ROLE pitwall WITH LOGIN PASSWORD 'pitwall';

-- Transfer database ownership to pitwall role
ALTER DATABASE pitwall OWNER TO pitwall;

-- Create the schemas
CREATE SCHEMA bronze;
CREATE SCHEMA silver;
CREATE SCHEMA gold;

-- Revoke CREATE on public schema from public
REVOKE CREATE ON SCHEMA public FROM public;

-- Set default search_path for pitwall role
ALTER ROLE pitwall SET search_path TO "$user", bronze, silver, gold, public;

-- Grant full usage and creation rights on bronze, silver, gold schemas to pitwall role
GRANT USAGE, CREATE ON SCHEMA bronze TO pitwall;
GRANT USAGE, CREATE ON SCHEMA silver TO pitwall;
GRANT USAGE, CREATE ON SCHEMA gold TO pitwall;

-- Grant usage on public schema (but not CREATE, which was revoked above)
GRANT USAGE ON SCHEMA public TO pitwall;

