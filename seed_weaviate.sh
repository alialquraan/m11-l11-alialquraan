#!/bin/bash
echo "Waiting for API and Weaviate to be fully ready..."
sleep 15

echo "Seeding Weaviate via the api container ..."
docker compose exec -T api python -m api.w9b_mapper.seed