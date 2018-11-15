import argparse, os

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
