import sys, os, shutil, subprocess, argparse, multiprocessing
from pathlib import Path
from pprint import pprint

import toml
import shellingham

import workspace.recipes
from workspace.workspace import Workspace
from .workspace import Workspace

def _get_all_recipes():
    # collect all true subclasses of 'recipes.Recipe' that are in 'recipes'
    # https://stackoverflow.com/questions/7584418/iterate-the-classes-defined-in-a-module-imported-dynamically
    recipes_to_list = dict(
        [(name, cls) for name, cls in recipes.__dict__.items()
         if isinstance(cls, type) and issubclass(cls, recipes.Recipe)
         and not cls == recipes.Recipe])
    return recipes_to_list

def _resolve_or_default_configs(ws_path, given_configs):
    if given_configs:
        available_config_dir = ws_path / 'build_configs' / 'available'
        configs = [available_config_dir / f"{config}.toml" for config in given_configs]
    else:
        if "WS_ENV_CONFIGURATION" in os.environ:
            available_config_dir = ws_path / 'build_configs' / 'available'
            configs = [
                available_config_dir / f"{os.environ['WS_ENV_CONFIGURATION']}.toml"
            ]
        else:
            active_config_dir = ws_path / 'build_configs' / 'active'
            configs = active_config_dir.glob('*.toml')
    return configs


def _available_configs(ws_path):
    available_config_dir = ws_path / 'build_configs' / 'available'
    configs = available_config_dir.glob('*.toml')
    return configs

def ws_from_config(ws_path, config_path):
    ws = Workspace(ws_path)

    assert config_path, "no config given"
    assert config_path.exists(), f"given config doesn't exist ({config_path})"
    assert not ws.builds, "build order already defined"

    with open(config_path) as f:
        config = toml.load(f)

    recipes_to_list = _get_all_recipes()

    for (target, variations) in config.items():
        if not target in recipes_to_list:
            raise RuntimeError(
                f"no recipe for target '{target}' found (i.e., no class '{target}' in module 'workspace.recipes')"
            )

        seen_names = set()
        for options in variations:
            rep = recipes_to_list[target](**options)

            if rep.name in seen_names:
                raise RuntimeError(
                    f"two variations for target '{target}' with same name '{rep.name}' found"
                )
            seen_names.update({rep.name})

            ws.builds += [rep]

    return ws


def __ws_path_from_here():
    return Path(__file__).resolve().parent.parent.parent


def build_main():
    parser = util.EnvVarArgumentParser(
        description=
        "Build one or more configurations. By default, builds all configurations, or only the configuration of the current environment if one is active."
    )

    choice_group = parser.add_mutually_exclusive_group()
    choice_group.add_argument(
        'configs',
        metavar='CONFIG',
        type=str,
        nargs='*',
        default=False,
        help="The configurations to build")
    choice_group.add_argument(
        '-a',
        '--all',
        action='store_true',
        help="build all available configs")

    parser.add_argument(
        '-j',
        '--num_threads',
        type=int,
        default=multiprocessing.cpu_count(),
        help="specify number of threads to use in parallel")

    args = parser.parse_args()

    ws_path = __ws_path_from_here()

    configs = _available_configs(ws_path) if args.all else _resolve_or_default_configs(ws_path, args.configs)

    for config in configs:
        ws = ws_from_config(ws_path, config)
        ws.build(num_threads = args.num_threads)


def setup_main():
    parser = argparse.ArgumentParser(
        description=
        "Setup (usually download sources) one or more configurations. By default, setups all configurations, or only the configuration of the current environment if one is active."
    )

    choice_group = parser.add_mutually_exclusive_group()
    choice_group.add_argument(
        'configs',
        metavar='CONFIG',
        type=str,
        nargs='*',
        default=False,
        help="The configurations to build")
    choice_group.add_argument(
        '-a',
        '--all',
        action='store_true',
        help="build all available configs")

    args = parser.parse_args()

    ws_path = __ws_path_from_here()

    configs = _available_configs(ws_path) if args.all else _resolve_or_default_configs(ws_path, args.configs)

    for config in configs:
        ws = ws_from_config(ws_path, config)
        ws.setup()

def shell_main():
    cmd_name = Path(sys.argv[0]).name
    if len(sys.argv) != 2:
        print(f"Usage: {cmd_name} <config_name>", file=sys.stderr)
        print(
            f"Example (for 'release.toml' config): {cmd_name} release",
            file=sys.stderr)
        sys.exit(1)

    config_name = sys.argv[1]

    env = os.environ.copy()
    env["VIRTUAL_ENV_DISABLE_PROMPT"] = "1"

    ws_path = __ws_path_from_here()

    config_path = ws_path / 'build_configs' / 'available' / f"{config_name}.toml"
    if not config_path.exists():
        print(f"configuration '{config_name}' not found at '{config_path}'")
        sys.exit(1)

    ws = workspace.ws_from_config(ws_path, config_path)
    ws.add_to_env(env)

    # yes, the `str()` is actually necessary
    env["WS_ENV_CONFIGURATION"] = str(config_name)

    shell = shellingham.detect_shell()[0]
    if shell == "bash":
        prompt_cmd = f"PS1=\"({ws_path.name}) ({config_name}) $PS1\""
    elif shell == "zsh":
        prompt_cmd = f"PROMPT=\"({ws_path.name}) ({config_name}) $PROMPT\""
    elif shell == "fish":
        prompt_cmd = f"functions -c fish_prompt _fish_nested_prompt ; function fish_prompt ; printf \"\\n%s\" \"({ws_path.name}) ({config_name}) \" ; _fish_nested_prompt ; end"

    # need "--anyway" as we are already running in a pipenv context, so pipenv believes it should not spawn a shell..
    os.execvpe("pipenv", [
        shutil.which("pipenv"),
        "shell",
        "--anyway",
        prompt_cmd,
    ], env)

def run_main():
    cmd_name = Path(sys.argv[0]).name
    if len(sys.argv) < 3:
        print(f"Usage: {cmd_name} <config_name> <command> [args...]", file=sys.stderr)
        print(
            f"Example (for 'release.toml' config): {cmd_name} release which klee",
            file=sys.stderr)
        sys.exit(1)

    config_name = sys.argv[1]

    ws_path = __ws_path_from_here()

    config_path = ws_path / 'build_configs' / 'available' / f"{config_name}.toml"
    if not config_path.exists():
        print(f"configuration '{config_name}' not found at '{config_path}'")
        sys.exit(1)

    env = os.environ.copy()
    env["VIRTUAL_ENV_DISABLE_PROMPT"] = "1"
    ws = workspace.ws_from_config(ws_path, config_path)
    ws.add_to_env(env)

    # yes, the `str()` is actually necessary
    env["WS_ENV_CONFIGURATION"] = str(config_name)

    os.execvpe("pipenv", [
        shutil.which("pipenv"),
        "run",
        ] + sys.argv[2:], env)


def clean_main():
    parser = argparse.ArgumentParser(
        description=
        "Clean one or more configurations. By default, cleans all configurations, or only the configuration of the current environment if one is active."
    )

    choice_group = parser.add_mutually_exclusive_group()
    choice_group.add_argument(
        'configs',
        metavar='CONFIG',
        type=str,
        nargs='*',
        default=False,
        help="The configurations to build")
    choice_group.add_argument(
        '-a',
        '--all',
        action='store_true',
        help="build all available configs")

    parser.add_argument(
        "--dist-clean",
        action='store_true',
        default=False,
        help="Clean fully, e.g., also removing all cloned repositories etc."
    )

    args = parser.parse_args()

    ws_path = __ws_path_from_here()

    configs = _available_configs(ws_path) if args.all else _resolve_or_default_configs(ws_path, args.configs)

    for config in configs:
        ws = ws_from_config(ws_path, config)
        ws.clean(dist_clean=args.dist_clean)

def list_options_main():
    parser = argparse.ArgumentParser(
        description=
        "List all available options with their default values. If given a configuration, only for the recipes appearing in that configuration, otherwise for all available recipes."
    )

    parser.add_argument(
        'recipes',
        metavar='recipe',
        type=str,
        nargs='*',
        help="The recipes for which to print options")

    parser.add_argument(
        '-c',
        '--config',
        type=str,
        default=None,
        help="specify the configuration for which to print options")

    args = parser.parse_args()

    ws_path = __ws_path_from_here()

    if args.config:
        available_config_dir = ws_path / 'build_configs' / 'available'
        config = available_config_dir / f"{args.config}.toml"
    elif "WS_ENV_CONFIGURATION" in os.environ:
        available_config_dir = ws_path / 'build_configs' / 'available'
        config = available_config_dir / f"{os.environ['WS_ENV_CONFIGURATION']}.toml"
    else:
        config = None

    recipes_to_list = _get_all_recipes()
    if args.recipes:
        recipes_to_list = {k: recipes_to_list[k] for k in args.recipes}

    if config:
        ws = ws_from_config(ws_path, config)
        for rep in ws.builds:
            clas = rep.__class__
            name = clas.__name__
            if not name in recipes_to_list:
                continue
            print(f"{name}:")
            clas.list_options(instance=rep)
            print()
    else:
        for (name, clas) in recipes_to_list.items():
            print(f"{name}:")
            clas.list_options()
            print()
