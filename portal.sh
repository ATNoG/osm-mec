#/bin/bash

# Build and push the images
docker build -t localhost:5000/cfs-portal:latest cfs-portal

docker push localhost:5000/cfs-portal:latest


# Install the new version of the OSM-MEC
helm -n osm-mec upgrade --reuse-values osm-mec deployment/helm-chart \
    --set cfsPortal.deployment.image=localhost:5000/cfs-portal:latest \
    --set cfsPortal.enabled=true \
    --set cfsPortal.deployment.env.FEDERATION=true

# Restart the meao pod
kubectl -n osm-mec delete pod -l app=cfs-portal
