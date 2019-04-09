# Quickstart

```bash
$ ./ws build                # build all active configurations
$ ./ws activate-cfg debug   # activate the debug configuration
$ ./ws deactivate-cfg debug # deactivate the debug configuration again
$ ./ws build debug release  # build only debug and release
$ ./ws shell debug          # start a shell with the environment (paths, etc.) set up for use of the debug configuration
$ ./ws run debug gdb klee   # run a single command (`gdb klee`) with the environment (paths, etc.) set up for use of the debug configuration
$ ./ws clean                # clean workspace
$ ./ws clean --dist-clean   # completely remove all projects - WILL NUKE YOUR CHANGES!
```

# Configurations
Available configurations are stored as toml files in [`/ws-config/*.toml`](/ws-config/). Generally speaking, configurations are a list of individual builds that are processed in order.

To see all available recipes and their options, use `./ws list_options -c $CONFIG`.

Configurations can also be *active*, which is achieved by running `./ws activate-cfg $CONFIG`. Similarly, to deactivate them, run `./ws deactivate-cfg $CONFIG`. For example, if you wish `debug` to be active, run `./ws activate-cfg debug`.

## Default Configurations
By default, 4 configurations are available:
- release
- profile
- debug
- sanitized

And one is active:
- release

# Updating
Generally speaking, updating the workspace can be done simply by cleaning the workspace and checking out the newest revision. Most of the time, it should be safe to keep the checked out sources, as they are:

```bash
$ ./ws clean         # always clean at least the build artifacts
$ git pull --ff-only # get updates
```

However, *breaking changes may happen at any time*. If you are in doubt, store all your changes in a safe place and nuke the workspace.

# Cleaning (a.k.a. "Help Me, Something Weird Has Happened")

A misconfigured workspace (e.g., due to a breaking change introduced during updating the workspace) may cause arbitrarily weird effects. Additionally, some subprojects (e.g., klee-uclibc) are built using build systems that can get confused, even during what may seem to be innocuous usage.

## Just Delete Build Artefacts (Often Good Enough)
Basically, delete all object files without touching the sources. `ccache` has your back :).

```bash
$ ./ws clean
```

## Delete Build Artefacts and Sources (Good Enough Unless You Broke the Workspace)
Basically, delete all object files and checked out sources. ***This will undo any changes you may have stored in the checked out repositories!***

```bash
$ ./ws clean --dist-clean
```

## Nuke Everything (Last Resort)
Basically, delete everything and clone the workspace new. ***This will undo any changes you may have stored in the workspace!***

```bash
$ git clean -xdff         # nuke everything
$ rm -f .git/info/exclude # including in the git folder
$ git checkout .          # including changes to the workspace scripts
```
