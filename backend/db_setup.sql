-- HRMS local database setup (PostgreSQL). Run with: psql -U postgres -f db_setup.sql
SELECT 'CREATE ROLE hrms LOGIN CREATEDB PASSWORD ''YTSiIZVdxDiSGjCs2vaYkDX9''' WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'hrms')\gexec
ALTER ROLE hrms WITH LOGIN CREATEDB PASSWORD 'YTSiIZVdxDiSGjCs2vaYkDX9';
SELECT 'CREATE DATABASE hrms OWNER hrms' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'hrms')\gexec
SELECT 'CREATE DATABASE hrms_test OWNER hrms' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'hrms_test')\gexec
\echo HRMS database setup complete
