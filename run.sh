#/bin/bash

# Uninstall the previous version of the OSM-MEC
helm -n osm-mec uninstall osm-mec


# Build and push the images
echo ""; echo "Building and pushing the images to the local registry..."
echo "-----------------------------------------------"
echo ""; echo "building cfs-portal..."
docker build -t localhost:5000/cfs-portal:latest cfs-portal
echo ""; echo "building meao..."
docker build -t localhost:5000/meao:latest meao/meao
echo ""; echo "building meao-monitoring..."
docker build -t localhost:5000/meao-monitoring:latest meao/monitoring
echo ""; echo "building meao-migration..."
docker build -t localhost:5000/meao-migration:latest meao/migration
echo ""; echo "building oss..."
docker build -t localhost:5000/oss:latest oss
echo ""; echo "building metrics-forwarder..."
docker build -t localhost:5000/forwarder:latest metrics-forwarder
echo "-----------------------------------------------"

echo ""; echo "Pushing the images to the local registry..."
echo "-----------------------------------------------"
echo ""; echo "pushing cfs-portal..."
docker push localhost:5000/cfs-portal:latest
echo ""; echo "pushing meao..."
docker push localhost:5000/meao:latest
echo ""; echo "pushing meao-monitoring..."
docker push localhost:5000/meao-monitoring:latest
echo ""; echo "pushing meao-migration..."
docker push localhost:5000/meao-migration:latest
echo ""; echo "pushing oss..."
docker push localhost:5000/oss:latest
echo ""; echo "pushing metrics-forwarder..."
docker push localhost:5000/forwarder:latest
echo "-----------------------------------------------"


# Get the needed Information
OSM_NBI=$(kubectl -n osm get ingress nbi-ingress -o jsonpath='{.spec.rules[0].host}')
[ -z "$K8S_DEFAULT_IF" ] && K8S_DEFAULT_IF=$(ip route list|awk '$1=="default" {print $5; exit}')
[ -z "$K8S_DEFAULT_IF" ] && K8S_DEFAULT_IF=$(route -n |awk '$1~/^0.0.0.0/ {print $8; exit}')
[ -z "$K8S_DEFAULT_IF" ] && FATAL "Not possible to determine the interface with the default route 0.0.0.0"
K8S_DEFAULT_IP=`ip -o -4 a s ${K8S_DEFAULT_IF} |awk '{split($4,a,"/"); print a[1]; exit}'`
KAFKA_PORT=$(kubectl get svc -n osm kafka-controller-0-external -o jsonpath='{.spec.ports[0].nodePort}')
KAFKA_PRODUCER_PASSWORD=$(kubectl get secret -n osm kafka-user-passwords -o jsonpath="{.data.client-passwords}" | base64 --decode)
KAFKA_CONSUMER_PASSWORD=$(kubectl get secret -n osm kafka-user-passwords -o jsonpath="{.data.client-passwords}" | base64 --decode)


# Install the new version of the OSM-MEC
helm -n osm-mec upgrade --install osm-mec deployment/helm-chart --create-namespace \
    --set domain="IT_AVEIRO" \
    --set cfsPortal.deployment.image=localhost:5000/cfs-portal:latest \
    --set cfsPortal.enabled=true \
    --set cfsPortal.deployment.env.FEDERATION=true \
    --set meao.deployment.image=localhost:5000/meao:latest \
    --set meao.monitoring.deployment.image=localhost:5000/meao-monitoring:latest \
    --set meao.migration.deployment.image=localhost:5000/meao-migration:latest \
    --set oss.deployment.image=localhost:5000/oss:latest \
    --set metricsForwarder.deployment.image=localhost:5000/forwarder:latest \
    --set osm.host=$OSM_NBI \
    --set cfsPortal.ossHost=$K8S_DEFAULT_IP \
    --set kafka.KAFKA_PRODUCER_CONFIG.sasl_plain_password=$KAFKA_PRODUCER_PASSWORD \
    --set kafka.KAFKA_CONSUMER_CONFIG.sasl_plain_password=$KAFKA_CONSUMER_PASSWORD


# Check the status of the pods
kubectl get pods -n osm-mec
