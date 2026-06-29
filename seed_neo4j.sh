#!/bin/bash
echo "Waiting for Neo4j to be fully ready..."
sleep 15

echo "Seeding Neo4j (loading api/seed.cypher via cypher-shell inside the neo4j container) ..."
docker compose exec -T neo4j cypher-shell -u neo4j -p testtest --encryption false -f /api/seed.cypher