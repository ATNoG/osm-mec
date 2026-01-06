#/bin/bash

# Build and push the images
docker build -t localhost:5000/oss:latest oss

docker push localhost:5000/oss:latest


# Install the new version of the OSM-MEC
helm -n osm-mec upgrade --reuse-values osm-mec deployment/helm-chart \
    --set oss.deployment.image=localhost:5000/oss:latest

# Restart the meao pod
kubectl -n osm-mec delete pod -l app=oss
