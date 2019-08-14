# Continous Integration
This file documents the basic structure for continuous integration of workspaces and projects that rely on a workspace for being built (tested, etc.).

## High-level overview of the features
* For CI, create a docker container and build the workspace inside of it
* Finally, if desired, these containers can be uploaded to our docker registry ({eyrie/kleenet}.comsys.rwth-aachen.de)
	* In the current configuration, CI for the master branch will create & upload a container (if successful) containing an un-built workspace
	* For other branches, the final container after building etc. will be uploaded, but with a manual expiration date of 1 day
* Most of the CI process is implemented in the script `.gitlab-ci-src/run-ci.py`, so that it can also be used for the CI of other projects, e.g., KleeNet
* This does not yet actually run any tests as part of the build process, but lays the foundation for doing so.

## More detailed description
The following is a more detailed description of how CI is built, the reasoning, and next steps.

### Goals
The goal of our CI is to implement functionality to automatically build docker-containers that contain a workspace. Reasons for this are:
* Automated testing for workspaces (so no workspace functionality breaks)
* Automated testing of workspace-dependent projects (e.g., KleeNet, ...)
* Automated generation of docker-containers that can be given to students (or used for other purposes, e.g., evaluations)
* Automated generation of docker-containers that can be used for releases (although manual adjustments might be desired)

The current structure aims to enable (at least) all of these use-cases.

## How It Works
CI in gitlab runs the stages in the `.gitlab-ci.yml`. Currently, these execute slightly different code for `master` and other branches, but mostly perform the same steps; more on this later. As basis for our CI we chose the `docker:dind` container, which allows us to run docker commands in our CI scripts. This is required in order to build containers (and upload them).

### The `run-ci.py` Script
Most of the work is then performed by the `run-ci.py` script, which resides in the new directory `.gitlab-ci-src`, which is meant to contain files and script used for the CI. This script builds the docker container, including copying its workspace into the container, and then builds the workspace inside of the built container. Uploading of the generated containers is left to the caller of the script, i.e., is currently done from `.gitlab-ci.yml`. There are multiple goals achieved by factoring this functionality out of the `.gitlab-ci.yml`-script itself:

* Other projects (e.g., KleeNet, ...) can simply clone their corresponding workspace, adjust it (e.g., for using the current project-branch/-commit), and then call the `run-ci.py`-script.
* The script can be used locally to create containers for "personal" use.
* It is a python-script, allowing nicer (and more rich) functionality than writing bash/sh (which is what the `.gitlab-ci.yml` contains)

This script allows the caller to create **release** and **final** docker-images of the build process. For the **release** image, the caller can specify which stage of the build process should be tagged (e.g., pre-build, post-build, post-tests, final, etc.). However, if a step of the build process fails, the **release** image will also not exist. This image can be used for releases, used by students, etc.

Additionally, the script also creates (if desired) a **final** image of the container that was built, which will always be created from the final state of the docker container at the end of the CI process. This is useful for inspecting the output of a CI run, e.g., to inspect a log-file. This image will have an *expiration date* of **1 day** (for now) added to it, after which the image *is not guaranteed to be available anymore*. More on this later.

Since this script performs the `./ws setup` step inside the docker container, cloning private/laboratory-local repositories requires access rights to do so. When running as part of gitlab's CI, the script allows forwarding the gitlab CI token into the container for the duration of the build, which will allow this step to succeed. When running without CI, one can, e.g., simply perform `./ws setup` before calling the `run-ci.py` script, which will cause the `./ws setup` inside the container to become (basically) a no-op.

### Docker-Setup
The docker containers are generated from the `Dockerfile` inside the `.gitlab-ci-src` directory. This image is based on the `archlinux/base` image, and injected with all dependencies necessary to build the workspace. It also copies the workspace currently being CI'd into this image, and copies the workspace configuration residing at `.gitlab-ci-src/ws-settings.toml` into the workspace inside the image. This is done to configure the workspace to clone using `https` instead of `ssh`. Especially for repositories cloned from github, this is required, but for repositories residing on this gitlab it might also be useful when running the CI-script locally/on a system without an ssh-key.

An alternative to symlinking the file (and thereby overriding existing configuration in the workspace) would be to instead store and apply a *patch*.

The `.gitlab-ci.yml` also forwards a cache-directory and a ccache-directory to the `run-ci.py` script. This allows for faster clones & builds.

It might be better, in order to be able to use docker's *layer caching*, to instead always clone repositories and build from scratch. Layer caching would very probably drastically reduce the size of the generated images, and also be comparably fast to using reference-repos + ccache. This should be integratable into the existing CI structure without (bigger) breaking changes (which is an explicit goal of the current structure).

### Uploaded Containers
As also mentioned in the beginning, the `.gitlab-src.yml` script performs slightly different steps for the `master` branch and for other branches. For the `master` branch it instructs the `run-ci.py`-script to create a release image at the `pre-build` stage, meaning the container will contain an un-built workspace. However, since it's a release-image, the script will additionally build the workspace inside the container, and if any errors occur, not create the image.

For other branches, it will always upload the final image at the end of the build to the docker registry. The purpose here is to allow manual inspection of the results of compilation & tests.

### Our Docker-registry, and Expiring Containers
Currently, the size of a container containing a fully-built workspace is ~4.3GB (`release`-configuration only). This size is further compressed on our docker-registry, but is still non-negligible; Therefore, non-`release` images are tagged with a manual expiration time of *one day* (for now). This is done by adding a label to the container. Expiring/expired images can then be found (and deleted) by querying the registry, e.g., using https://laboratory.comsys.rwth-aachen.de/rath/docker-expire.
