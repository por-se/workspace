# Quickstart

```bash
$ ./ws build                # build all active configurations
$ ./ws build debug release  # build only debug and release
$ ./ws shell debug          # start a shell with the environment (paths, etc.) set up for use of the debug configuration
$ ./ws run debug gdb klee   # run a single command (`gdb klee`) with the environment (paths, etc.) set up for use of the debug configuration
$ ./ws clean                # clean each project
$ ./ws clean --dist-clean   # completely remove all projects
```

# Configurations
Available configurations are stored as toml files in [`/build_configs/available/*.toml`](/build_configs/available). Generally speaking, configurations are a list of individual builds that are processed in order.

To see all available recipes and their options, use `./ws list_options`.

Configurations can also be *active*, which is achieved by symlinking them to [`/build_configs/active`](/build_configs/active).

## Default Configurations
By default, 4 configurations are available:
- release
- profile
- debug
- sanitized

And one is active:
- release

# Updating (a.k.a. Something Weird Has Happened)
Generally speaking, updating the workspace can be done simply by checking out the newest revision. However, every one in a while there may be breaking changes to the workspace. *Breaking changes may happen at any time.*

Should something have gone wrong during an update, save all changes you may have performed and do a full cleanse.

## Full Cleanse (Safe)
Basically, delete everything and clone the workspace new. `ccache` has your back :).

```bash
$ git clean -xdff
$ rm -f .git/info/exclude
$ git pull --ff-only
$ git checkout .
```

## Keeping Repositories (Slightly Unsafe)
Basically, delete all object files. `ccache` has your back :).

Most of the time it should be OK to keep most of the repositories around.

```bash
$ rm -rf klee-uclibc # we do not support shadow builds for klee-uclibc
$ rm -rf .build
$ git pull --ff-only
```
