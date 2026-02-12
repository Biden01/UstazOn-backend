#!/bin/bash
set -e

# Ensure password is always set correctly
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    ALTER USER postgres WITH PASSWORD 'hcAPWlSXOVMXYUcH36SkDAio9tmwWT3';
EOSQL
