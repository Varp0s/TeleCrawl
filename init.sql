-- PostgreSQL initialization script
CREATE DATABASE telecrawl;
\c telecrawl;

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
