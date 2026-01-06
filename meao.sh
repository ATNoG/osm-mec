#/bin/bash

# Build and push the images
docker build -t localhost:5000/meao:latest meao/meao
docker build -t localhost:5000/meao-monitoring:latest meao/monitoring
docker build -t localhost:5000/meao-migration:latest meao/migration

docker push localhost:5000/meao:latest
docker push localhost:5000/meao-monitoring:latest
docker push localhost:5000/meao-migration:latest


# Install the new version of the OSM-MEC
helm -n osm-mec upgrade --reuse-values osm-mec deployment/helm-chart \
    --set meao.deployment.image=localhost:5000/meao:latest \
    --set meao.monitoring.deployment.image=localhost:5000/meao-monitoring:latest \
    --set meao.migration.deployment.image=localhost:5000/meao-migration:latest

# Restart the meao pod
kubectl -n osm-mec delete pod -l app=meao
