# Building matlab-proxy for use in a Docker Container

[Dockerfile](./Dockerfile) adds **matlab-proxy** package to an existing docker image with MATLAB

Supply the name of your custom image with the docker build arg `IMAGE_WITH_MATLAB`. The default value for this build argument is `mathworks/matlab:r2021b`

**NOTE:** Releases of MATLAB docker images starting from `r2022a` will have **matlab-proxy** integrated by default. 

This [Dockerfile](./Dockerfile) can be used as a reference for integrating **matlab-proxy** into your custom images or older MATLAB docker images.

## Build image
```bash
 docker build  --build-arg IMAGE_WITH_MATLAB=my_custom_image_with_matlab_installed \
               -f Dockerfile -t my_custom_image_with_matlab_proxy .
```
## Upgrading matlab-proxy package in a docker image

To keep your docker images updated with the latest release of **matlab-proxy** package, you can either:
* Update using a Dockerfile
* Update using `docker commit` command

**NOTE:** Updating the package using a Dockerfile is recommended as it helps in keeping track of the changes made to docker images.
### Approach 1: Using a Dockerfile
`Dockerfile.upgrade.matlab-proxy` showcases how to upgrade an existing installation of **matlab-proxy** package in a docker image.


```bash
 docker build  --build-arg IMAGE_WITH_MATLAB_PROXY=my_custom_image_with_matlab_proxy \
               -f Dockerfile.upgrade.matlab-proxy -t my_custom_image_with_matlab_proxy .
```

### Approach 2: Using `docker commit` command
Launch your container with `--entrypoint /bin/bash` flag 
```bash
$  docker run --rm -it --shm-size=512M --entrypoint /bin/bash my_custom_image_with_matlab_proxy:latest 
```

Once in the container, change to root user and upgrade the package
```bash
root@6624c4893071:/home/matlab/Documents/MATLAB: sudo su
root@6624c4893071:/home/matlab/Documents/MATLAB: python3 -m pip install --upgrade matlab-proxy
```

In a new terminal, grab the running container's ID and use the `docker ps` command
```bash
$ docker ps

CONTAINER ID        IMAGE                                        COMMAND                CREATED             STATUS              PORTS                          NAMES
6624c4893071        my_custom_image_with_matlab_proxy:latest     "/bin/run.sh -shell"   2 minutes ago       Up 2 minutes        5901/tcp, 6080/tcp, 8888/tcp   laughing_buck

```
In this case, the container ID is  `6624c4893071`. Now commit:
```bash
$ docker commit 6624c4893071 my_custom_image_with_matlab_proxy:latest
```

Stop the running container by exiting the shell
```bash
root@6624c4893071::/home/matlab/Documents/MATLAB: exit
matlab@6624c4893071::/home/matlab/Documents/MATLAB: exit
```

## Run the docker container
```bash
docker run -it -p 8888:8888 --shm-shared=512M my_custom_image_with_matlab_proxy:latest 
```

For modifying the behaviour of **matlab-proxy**, you can pass environment variables at run time
```bash
docker run -it -p 8888:8888 -e MLM_LICENSE_FILE="port@hostname" \
            --shm-shared=512M my_custom_image_with_matlab_proxy:latest 
```
For a complete list of environment variables that can be passed, see [Advanced-Usage.md](../Advanced-Usage.md)
