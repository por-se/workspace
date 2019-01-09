import sys, os, shutil, subprocess, argparse, multiprocessing
from pathlib import Path
from pprint import pprint

import toml
import shellingham

import workspace_base.recipes
from workspace_base.workspace import Workspace
from .workspace import Workspace

def _get_all_recipes():
    # collect all true subclasses of 'recipes.Recipe' that are in 'recipes'
    # https://stackoverflow.com/questions/7584418/iterate-the-classes-defined-in-a-module-imported-dynamically
    all_recipes = dict(
        [(name, cls) for name, cls in recipes.__dict__.items()
         if isinstance(cls, type) and issubclass(cls, recipes.Recipe)
         and not cls == recipes.Recipe])
    return all_recipes

def ws_from_config(ws_path, config_path):
    ws = Workspace(ws_path)

    assert config_path, "no config given"
    assert config_path.exists(), f"given config doesn't exist ({config_path})"
    assert not ws.builds, "build order already defined"

    with open(config_path) as f:
        config = toml.load(f)

    all_recipes = _get_all_recipes()

    for (target, variations) in config.items():
        if not target in all_recipes:
            raise RuntimeError(
                f"no recipe for target '{target}' found (i.e., no class '{target}' in module 'workspace_base.recipes')"
            )

        seen_names = set()
        for options in variations:
            rep = all_recipes[target](**options)

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

    parser.add_argument(
        'configs',
        metavar='config',
        type=str,
        nargs='*',
        help="The configurations to build")

    parser.add_argument(
        '-j',
        '--num_threads',
        type=int,
        default=multiprocessing.cpu_count(),
        help="specify number of threads to use in parallel")

    args = parser.parse_args()

    ws_path = __ws_path_from_here()

    if args.configs:
        available_config_dir = ws_path / 'build_configs' / 'available'
        configs = [available_config_dir / f"{config}.toml" for config in args.configs]
    else:
        if "WS_ENV_CONFIGURATION" in os.environ:
            available_config_dir = ws_path / 'build_configs' / 'available'
            configs = [
                available_config_dir / f"{os.environ['WS_ENV_CONFIGURATION']}.toml"
            ]
        else:
            active_config_dir = ws_path / 'build_configs' / 'active'
            configs = active_config_dir.glob('*.toml')

    for config in configs:
        ws = ws_from_config(ws_path, config)
        ws.build(num_threads = args.num_threads)


def env_main():
    cmd_name = Path(sys.argv[0]).name
    if len(sys.argv) != 2:
        print(f"Usage: pipenv run {cmd_name} <config_name>", file=sys.stderr)
        print(
            f"Example (for 'default.toml' config): pipenv run {cmd_name} default",
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

    ws = workspace_base.ws_from_config(ws_path, config_path)
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

def list_options_main():
    parser = argparse.ArgumentParser(
        description=
        "List all available options. If given a configuration, only for the recipes appearing in that configuration, otherwise for all available recipes."
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

    if config:
        raise NotImplementedError
    else:
        all_recipes = _get_all_recipes()
        for (name, clas) in all_recipes.items():
            print(f"{name}:")
            clas.list_options()
            print()
