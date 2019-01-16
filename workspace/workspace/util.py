import argparse, os, sys, enum


# https://stackoverflow.com/questions/10551117/setting-options-from-environment-variables-when-using-argparse/24662215#24662215
class EnvVarArgumentParser(argparse.ArgumentParser):
    class _CustomHelpFormatter(argparse.ArgumentDefaultsHelpFormatter):
        def _get_help_string(self, action):
            help = super()._get_help_string(action)
            if action.dest != 'help':
                help += ' [env: {}]'.format(action.dest.upper())
            return help

    def __init__(self, *, formatter_class=_CustomHelpFormatter, **kwargs):
        super().__init__(formatter_class=formatter_class, **kwargs)

    def _add_action(self, action):
        action.default = os.environ.get(action.dest.upper(), action.default)
        return super()._add_action(action)


def j_from_num_threads(num_threads):
    if num_threads:
        return ["-j", str(num_threads)]
    else:
        return [""]


def adjusted_cmake_args(original_args, adjustments):
    """
    Adjust a list of cmake arguments 'original_args', e.g., ['-DFOO=bar', '-DBAR=foo'] with a list of adjustments 'adjustments', e.g., ['-DFOO=BLUB', '-UBAR', '-DNEW=VAL'].
    These adjustment can only contain '-DXXX=yyy' and '-UXXX' entries. Changed entries will be changed, new entries will be appended,
    and '-U'-entries will be removed from the result, which otherwise is a copy of 'original_args'.
    """

    class Mode(enum.Enum):
        DEFINE = 1
        UNDEFINE = 2

    new_args = list(original_args)

    for adj in adjustments:
        if adj.startswith("-D"):
            mode = Mode.DEFINE
            needle = adj[:adj.index("=") + 1]
        elif adj.startswith("-U"):
            mode = Mode.UNDEFINE
            needle = "-D" + adj[2:] + "="
        else:
            raise ValueError(
                f"adjust_cmake_args: currently only adjustments starting with '-D' or '-U' are possible, but got '{adj}' instead. Please open an issue if required."
            )

        found = False
        for i in range(0, len(new_args)):
            if new_args[i].startswith(needle):
                found = True
                if mode == Mode.DEFINE:
                    new_args[i] = adj
                elif mode == Mode.UNDEFINE:
                    del new_args[i]
                else:
                    assert False, f"unexpected mode: '{mode}'"
                break

        if not found and mode == Mode.DEFINE:
            new_args = new_args + [adj]

    return new_args
