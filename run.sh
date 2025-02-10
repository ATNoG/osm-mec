helm -n osm-mec uninstall osm-mec

docker build -t localhost:5000/cfs-portal:latest cfs-portal
docker push localhost:5000/cfs-portal:latest
docker build -t localhost:5000/meao:latest meao
docker push localhost:5000/meao:latest
docker build -t localhost:5000/oss:latest oss
docker push localhost:5000/oss:latest

OSM_NBI=$(kubectl -n osm get ingress nbi-ingress -o jsonpath='{.spec.rules[0].host}')
[ -z "$K8S_DEFAULT_IF" ] && K8S_DEFAULT_IF=$(ip route list|awk '$1=="default" {print $5; exit}')
[ -z "$K8S_DEFAULT_IF" ] && K8S_DEFAULT_IF=$(route -n |awk '$1~/^0.0.0.0/ {print $8; exit}')
[ -z "$K8S_DEFAULT_IF" ] && FATAL "Not possible to determine the interface with the default route 0.0.0.0"
K8S_DEFAULT_IP=`ip -o -4 a s ${K8S_DEFAULT_IF} |awk '{split($4,a,"/"); print a[1]; exit}'`
KAFKA_PORT=$(kubectl get svc -n osm kafka-controller-0-external -o jsonpath='{.spec.ports[0].nodePort}')
KAFKA_PRODUCER_PASSWORD=$(kubectl get secret -n osm kafka-user-passwords -o jsonpath="{.data.client-passwords}" | base64 --decode)
KAFKA_CONSUMER_PASSWORD=$(kubectl get secret -n osm kafka-user-passwords -o jsonpath="{.data.client-passwords}" | base64 --decode)

helm -n osm-mec upgrade --install osm-mec osm-mec-helm-chart \
    --set cfsPortal.deployment.image=localhost:5000/cfs-portal:latest \
    --set meao.deployment.image=localhost:5000/meao:latest \
    --set oss.deployment.image=localhost:5000/oss:latest \
    --set osm.host=$OSM_NBI \
    --set cfsPortal.ossHost=$K8S_DEFAULT_IP \
    --set kafka.KAFKA_PRODUCER_CONFIG.sasl_plain_password=$KAFKA_PRODUCER_PASSWORD \
    --set kafka.KAFKA_CONSUMER_CONFIG.sasl_plain_password=$KAFKA_CONSUMER_PASSWORD

kubectl get pods -n osm-mec
