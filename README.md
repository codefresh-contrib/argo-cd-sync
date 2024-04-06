# Argo CD Sync for Codefresh's GitOps Runtimes

Step to perform a Sync operation on an Argo CD App when using the Codefresh's GitOps Runtimes

## Development

-   To activate venv

```sh
cd /to/root/dir
python3 -m venv venv --clear
source venv/bin/activate
```

-   Download all dependencies

```sh
pip install --upgrade pip
pip install -r requirements.txt
```

-   Update list of requirements:

```sh
pip freeze > requirements.txt
```

## Running it

Create a variables.env file with the following content:

```sh
ENDPOINT=https://g.codefresh.io/2.0/api/graphql
CF_API_KEY=XYZ
RUNTIME=<the_runtime_name>
NAMESPACE=<the_namespace>
APPLICATION=<the_app_name>
```

-   Running in shell:

```sh
export $( cat variables.env | xargs ) && python argocd_sync.py
```

-   Running as a container:

```sh
export image_name="`yq .name service.yaml`"
export image_tag="`yq .version service.yaml`"
export registry="franciscocodefresh" ## e.g., the Docker Hub account
docker build -t ${image_name} .
docker run --rm --env-file variables.env ${image_name}
docker tag ${image_name} ${registry}/${image_name}:${image_tag}
docker push ${registry}/${image_name}:${image_tag}
```

When using ARM:
```sh
docker build \
    --tag ${registry}/${image_name}:${image_tag} \
    --platform linux/arm64/v8,linux/amd64 \
    --builder container \
    --push \
    .
```

If you don't have a builder using the `docker-container` driver:
```sh
docker buildx create --name container --driver=docker-container
```
