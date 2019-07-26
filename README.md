# Quickstart

```bash
$ ./ws build                # build configurations from environment or settings file (default: release)
$ ./ws build debug release  # build debug and release
$ ./ws shell debug          # start a shell with the environment (paths, etc.) set up for use of the debug configuration
(debug) $ build             # build the configuration of the active shell (unless overwritten in settings file)
(debug) $ klee --help       # run debug klee
(debug) $ exit              # leave debug shell
$ ./ws run debug gdb klee   # run a single command (`gdb klee`) with the environment (paths, etc.) set up for use of the debug configuration
$ ./ws run gdb klee         # run a single command (`gdb klee`) with the environment (paths, etc.) set up for use of a configuration from environment or settings file (default: release)
$ ./ws clean                # clean workspace
$ ./ws clean --dist-clean   # completely remove all projects - WILL NUKE YOUR CHANGES!
```

# Settings
The workspace tools process three different kinds of settings, in the following order:
1. Command line arguments if they are present
2. Otherwise, environment variables beginning with `WS_`
3. If no environment variables are set either, the `ws-settings.toml` settings file is used
4. Some settings have additional defaults that are used as a last resort

For example, the `jobs` setting, which controls the available parallelism, will perform the following checks:
1. If a command line parameter (usually called `-j` or `--jobs`) is available, use that value
2. If no command line parameter is available, check the environment variable `WS_JOBS`
3. If no command line parameter is available and `WS_JOBS` is not set, check `ws-settings.toml` for the `jobs` key
4. If all this failed, use the default value `0`
(Note: If the `jobs` setting resolves to `0`, the number of CPUs is used.)

The settings file can be (re-)created using `./ws reset-settings` or by running any command, when it does not exist.

Note that the formats are obviously different depending on which method you choose. See [ws-doc/settings.md](ws-doc/settings.md) for a complete list of settings and how they can be passed.

# Configurations
Available configurations are stored as toml files in [`ws-config/*.toml`](/ws-config/). Configurations are lists of parameterized recipes that are processed in order.

To see all available recipes and their options, use `./ws list-options -c $CONFIG all`.

## Setting Default Configuration(s)
There are two settings that decide which configuration(s) are used in a command: `config` for operations on single configurations, such as `shell`, and `configs` for operations on (potentially) multiple configurations, such as `build`. The `configs` setting will default to the value of the `config` setting if it is not set.

Note that the formats are obviously different depending on which method you choose. See [ws-doc/settings.md](ws-doc/settings.md) for a complete list of settings and how they can be passed.

Examples:

```bash
$ ./ws build debug release                             # build debug and release configurations
$ WS_CONFIGS=release,profile ./ws build debug release  # build debug and release configurations
$ WS_CONFIGS=release,profile ./ws build                # build release and profile configurations
$ vim ws-settings.toml                                 # set `config` to "profile"
$ ./ws build                                           # build profile configuration
$ vim ws-settings.toml                                 # set `configs` to ["debug", "sanitized"]
$ ./ws build                                           # build debug and sanitized configurations
```

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

## Contributing
Install development dependencies with:

```bash
$ pipenv install --dev
```

Run the static type checker before submitting changes:

```bash
$ ws-src/run_mypy.sh
```

# Workspace Settings

The workspace saves its settings in the `ws-settings.toml` file, located in the base directory of the workspace. This file is created upon starting ws for the first time and deleted on `./ws clean --dist-clean`. It stores the currently active building configurations as well as the reference repository path (if already set) and the pull URLs for git.
## Pull via HTTPS or SSH
If you prefer pulling the git sources via HTTPS, rather than SSH as by default, you have to modify the pull URLs via the configuration file.
SSH clone (default):
```
[uri-schemes]
"github://" = "ssh://git@github.com/"
"laboratory://" = "ssh://git@laboratory.comsys.rwth-aachen.de/"
```
HTTPS clone:
```
[uri-schemes]
"github://" = "https://github.com/"
"laboratory://" = "https://laboratory.comsys.rwth-aachen.de/"
```
As after every `--dist-clean` the current config is deleted, the URLs will be reset and any changes have to be applied again.
Also, before the first execution the settings file is not written, so in order to check out via HTTPS, you have to create the file first. With `./ws reset-settings` the settings file will be reset to the default settings, if no file exists, a new one with the default settings will be created. To use HTTPS from the get go, all you need to do is initially run `reset-settings` at first, edit the newly created file as described above and then execute the workspace with `build` or `setup`.
