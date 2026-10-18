DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'npra') THEN
    CREATE ROLE npra LOGIN PASSWORD 'npra';
  END IF;
END
$$;

SELECT 'CREATE DATABASE npra_monitor OWNER npra'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'npra_monitor')\gexec
