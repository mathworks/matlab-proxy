# Building matlab-proxy for use in a Docker Container

Builds a docker image based on `mathworks/matlab` with the **matlab-proxy** integrated.

## Build image
```bash
docker build -t <image_name> .
```
## Run image
```bash
docker run -it -p 8888:8888 -t <image_name>
```
