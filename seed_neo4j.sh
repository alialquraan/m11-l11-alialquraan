#!/bin/bash
echo "Checking if Neo4j container is running..."

if [ "$(docker compose ps -q neo4j)" ]; then
    echo "Seeding Neo4j (loading api/seed.cypher via cypher-shell inside the neo4j container) ..."
    docker compose exec -T neo4j cypher-shell -u neo4j -p testtest --encryption false -f /api/seed.cypher
else
    echo "⚠️ Neo4j container is not running. Skipping seed (OK for CI/Autograder environment)."
    exit 0
fi