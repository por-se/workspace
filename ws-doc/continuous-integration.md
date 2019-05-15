Note: This documentation is taken from the original Merge Request that added CI: https://laboratory.comsys.rwth-aachen.de/symbiosys/projects/workspace_base/merge_requests/56.

---

This MR adds the basic structure for continuous integration of workspaces and projects that rely on a workspace for being built (tested, etc.).

## High-level overview of the features implemented in this MR
* For CI, create a docker container and build the workspace inside of it
* Finally, if desired, these containers can be uploaded to our docker registry ({eyrie/kleenet}.comsys.rwth-aachen.de)
  * In the current configuration, CI for the master branch will create & upload a container (if successful) containing an un-built workspace
  * For other branches, the final container after building etc. will be uploaded, but with a manual expiration date of 1 day
* Most of the CI process is implemented in the script `.gitlab-ci-src/run-ci.py`, so that it can also be used for the CI of other projects, e.g., KleeNet
* This does not yet actually run any tests as part of the build process, but "merely" lays the foundation for doing so.

## More detailed description
The following is a more detailed description of what this MR adds, the reasoning, and next steps.

### Goals
The goal of this MR is to implement functionality to automatically build docker-containers that contain a workspace. Reasons for this are:
* Automated testing for workspaces (so no workspace functionality breaks)
* Automated testing of workspace-dependent projects (e.g., KleeNet, ...)
* Automated generation of docker-containers that can be given to students (or used for other purposes, e.g., evaluations)
* Automated generation of docker-containers that can be used for releases (although manual adjustments might be desired)

This MR provides a basic structure that aims to enable (at least) all of these use-cases.

## How It Works
CI in gitlab runs the stages in the `.gitlab-ci.yml`. Currently, these execute slightly different code for `master` and other branches, but mostly perform the same steps; more on this later. As basis for our CI we chose the `docker:dind` container, which allows us to run docker commands in our CI scripts. This is required in order to build containers (and upload them).

### The `run-ci.py` Script
Most of the work is then performed by the `run-ci.py` script, which resides in the new directory `.gitlab-ci-src`, which is meant to contain files and script used for the CI. This script builds the docker container, including copying its workspace into the container, and then builds the workspace inside of the built container. Uploading of the generated containers is left to the caller of the script, i.e., is currently done inside the `.gitlab-ci.yml`. There are multiple goals achieved by factoring this functionality out of the `.gitlab-ci.yml`-script itself:

* Other projects (e.g., KleeNet, ...) can simply clone their corresponding workspace, adjust it (e.g., for using the current project-branch/-commit), and then call the `run-ci.py`-script.
* The script can be used locally to create containers for "personal" use.
* It is a python-script, allowing nicer (and more rich) functionality than writing bash (which is what the `.gitlab-ci.yml` contains)

This script allows the caller to create **release** and **final** docker-images of the build process. For the **release** image, the caller can specify which stage of the build process should be tagged (e.g., pre-build, post-build, post-tests, final, etc.). However, if a step of the build process fails, the **release** image will also not exist. This image can be used for releases, given to students, etc.

Additionally, the script also creates (if desired) a **final** image of the container that was built, which will always be created from the final state of the docker container at the end of the CI process (currently: after running `./ws build`). This is useful for inspecting the output of a CI run, e.g., to inspect a log-file. This image will have an *expiration date* of **1 day** (for now) added to it, after which the image *is not guaranteed to be available anymore*. More on this later.

### Docker-Setup
The docker containers are generated from the `Dockerfile` inside the `.gitlab-ci-src` directory. This image is based on the `archlinux/base` image, and injected with all dependencies necessary to build the workspace. It also copies the workspace currently being CI'd into this image, and symlinks the workspace configuration residing at `.gitlab-ci-src/.ws-config.toml` into the workspace inside the image. This is done to configure the location for the reference-repositories, and to configure the workspace to clone using `https://` instead of `ssh`. Especially for repositories cloned from github this is required, but for repositories residing on this gitlab it might also be useful when running the CI-script locally/on a system without an ssh-key.

An alternative to symlinking the file (and thereby overriding existing configuration in the workspace) would be to instead store and apply a *patch*. This is definitely something that could be done as a next step.

The `.gitlab-ci.yml` also forwards a cache-directory and a ccache-directory to the `run-ci.py` script. This allows for faster clones & builds.

It might be better, in order to be able to use docker's *layer caching*, to instead always clone repositories and build from scratch. Layer caching would very probably drastically reduce the size of the generated images, and also be comparably fast to using reference-repos + ccache. However, this will be left as a next step, and should be integratable into the structure introduced in this MR without (bigger) breaking changes (which is an explicit goal of this version).

### Changes to the Workspace
This MR also introduces the `--git-clone-args` argument to the `./ws setup` command. This argument, as the name implies, allows adding additional arguments to `git clone`-calls that happen during the `setup`-stage. In the `run-ci.py`-script this is used to clone the repositories with `--dissociate` (as the reference repos are mounted from external locations, and won't be available anymore in the created container), as well as `--depth=1`, in order to (hopefully) reduce the size of the containers.

The way this is implemented feels a little bit hacky/not completely clean (but it's not a complete hack), and throws up the question of how to handle configuration + overrides in general. But this discussion (while relevant) should probably happen in another MR.

### Uploaded Containers
As also mentioned in the beginning, the `.gitlab-src.yml` script performs slightly different steps for the `master` branch and for other branches. For the `master` branch it instructs the `run-ci.py`-script to create a release image at the `pre-build` stage, meaning the container will contain an un-built workspace. However, since it's a release-image, the script will additionally build the workspace inside the container, and if any errors occur, not create the image.

For other branches, it will always upload the final image at the end of the build (later on: also after running tests etc.) to the docker registry. The purpose here is to allow manual inspection of the results of compilation & tests.

### Our Docker-registry, and Expiring Containers
Currently, the size of a container containing a fully-built workspace is ~4.3GB (`release`-configuration only). This size is further compressed on our docker-registry, but is still non-negligible; Therefore, non-`release` images are tagged with a manual expiration time of *one day* (for now). This is done by adding a label to the container. Expiring/expired images can then be found (and deleted) by querying the registry, e.g., using https://laboratory.comsys.rwth-aachen.de/rath/docker-expire.

I have talked with Max Winck about this (who currently maintains the docker registry), and we will monitor how well this works, or whether additional size-saving (or more hardware) is necessary.

This sums up the structure as implemented in this MR.

## Next Steps
The following are some next steps that evolve this into actual CI for workspaces and workspace-dependent projects, as well as for increasing performance.

### Workspace-CI
One goal of this CI-undertaking is to add **self-tests** to the workspace, which would be how MRs to a workspace itself could be tested. This would involve, e.g., building the workspace, cleaning it, dist-cleaning, running `list_options` with different arguments, etc. Currently this needs to be done manually, which is error-prone.

### Workspace-dependent Project CI
Projects that currently 'require' a workspace in order to be built (e.g., KleeNet) should have CI added to them, using this CI. The idea would be that the CI of such a project clones the corresponding workspace that can be used to build the project, applies some patches to adjust this workspace to use the branch currently being CI'd, and then to run the `run-ci.py`-script. This should be done for our projects. Probably we will want to introduce a `./ws check`-subcommand, which runs some/all tests for cloned projects. Here we need to make sure that we don't *suddenly* spam images to the docker-registry, so roll-outs of CI to other projects should be well monitored.

### Performance Improvements
To increase the performance of builds, we will probably want to switch to docker's layer-caching, or at least offer it as an alternative. This was intentionally not yet implemented in this MR, because I wanted to get the structure right first. However, this CI-structure is designed in a way that should allow implementation of such features in a manner (almost) transparent to users of the CI.

Open for all feedback, comments, questions & discussions!