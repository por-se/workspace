# Quickstart

```bash
$ ./ws build                # build all active configurations
$ ./ws build debug release  # build only debug and release
$ ./ws clean                # clean each project
$ ./ws clean --dist-clean   # completely remove all projects
$ ./ws shell debug          # start a shell with the environment (paths, etc.) set up for use of the debug configuration
$ ./ws run debug gdb klee   # run a single command (`gdb klee`) with the environment (paths, etc.) set up for use of the debug configuration
```
