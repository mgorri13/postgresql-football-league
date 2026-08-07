CREATE ROLE football_readonly NOLOGIN;

GRANT CONNECT ON DATABASE football_league TO football_readonly;
GRANT USAGE ON SCHEMA public TO football_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO football_readonly;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT ON TABLES TO football_readonly;