#!/bin/bash

# build docker file and push to azure

# docker login vaultsearch.azurecr.io
# username vaultsearch
# pasword  (get it from azure access keys to azurecr)

# docker build -t vaultsearch .
# docker run -d -p 8000:8000 --name esla vaultsearch

#  https://blog.container-solutions.com/a-guide-to-solving-those-mystifying-cors-issues

#  https://docs.microsoft.com/en-us/azure/container-registry/container-registry-get-started-docker-cli
#  to put into azurecr.io 
#  az login
#  az acr login --name vaultsearch


docker build -t vaultsearch -f Dockerfile  .
# docker run -d -p 8000:8000 --name essearch vaultsearch
echo "build done"
docker tag vaultsearch vaultsearch.azurecr.io/vaultsearch 
echo "tag done"
docker push vaultsearch.azurecr.io/vaultsearch 
echo "push done"
