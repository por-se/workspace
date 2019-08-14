import os
from pathlib import Path
import tempfile

from .shell import Shell


class Zsh(Shell):
    def add_cd_build_dir(self):
        cd_build_dir = """
# cd-build-dir
function cd-build-dir {
    output=$(build-dir --cd-build-dir "$@" 2>&1)
    exitcode=$?
    if [[ $exitcode -ne 0 ]]; then
        >&2 echo "$output"
        return $exitcode
    fi
    regex="^cd .*"
    if [[ "$output" =~ $regex ]]; then
        eval "$output"
    else
        echo "$output"
    fi
}
        """

        self.add_additional_commands(cd_build_dir)

    def spawn(self, env):
        # method inspired by https://www.zsh.org/mla/users/2017/msg00318.html
        # and https://superuser.com/a/591440

        zdotdir = env["ZDOTDIR"] if "ZDOTDIR" in env else env["HOME"]

        with tempfile.TemporaryDirectory() as _tempdir:
            tempdir = Path(_tempdir)

            with open(tempdir / '.zshrc', 'w+') as file:
                file.write(f"""
# reset $ZDOTDIR and source user's default configuration
ZDOTDIR="{zdotdir}"
[[ -r "$ZDOTDIR/.zshrc" ]] && source "$ZDOTDIR/.zshrc"

# remove this directory
rm -rf {tempdir}

# set prompt
PROMPT="{self.prompt_prefix}$PROMPT"

{self.additional_commands}
                """)

            # symlink tempdir/.zshenv to $ZDOTDIR/.zshenv
            os.symlink(Path(zdotdir) / '.zshenv', tempdir / '.zshenv')

            # set ZDOTDIR for zsh to initialize with tempdir/.zshrc
            env["ZDOTDIR"] = str(tempdir)

            os.execvpe("zsh", ["zsh", "-i"], env)
