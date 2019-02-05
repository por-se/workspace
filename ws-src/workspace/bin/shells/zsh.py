import os
from pathlib import PurePosixPath
import tempfile

from . import Shell


class Zsh(Shell):
    def spawn(self, env):
        # method inspired by https://www.zsh.org/mla/users/2017/msg00318.html
        # and https://superuser.com/a/591440

        # obtain $ZDOTDIR in zsh interactive shell
        zdotdir = PurePosixPath(
            os.popen('zsh -i -c "if [[ -v ZDOTDIR ]]; then echo -n $ZDOTDIR; else echo -n $HOME; fi"').read())

        with tempfile.TemporaryDirectory() as _tempdir:
            tempdir = PurePosixPath(_tempdir)

            with open(tempdir / '.zshrc', 'w+') as file:
                file.write(f"""
# reset $ZDOTDIR and source user's default configuration
ZDOTDIR="{zdotdir}"
[ -r $ZDOTDIR/.zshrc ] && . $ZDOTDIR/.zshrc

# remove this directory
rm -rf {tempdir}

# set prompt
PROMPT="{self.prompt_prefix}$PROMPT"

{self.additional_commands}
                """)

            # symlink tempdir/.zshenv to $ZDOTDIR/.zshenv
            os.symlink(zdotdir / '.zshenv', tempdir / '.zshenv')

            # set ZDOTDIR for zsh to initialize with tempdir/.zshrc
            env["ZDOTDIR"] = tempdir

            os.execvpe("zsh", ["zsh", "-i"], env)
