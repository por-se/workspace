import os
from pathlib import PurePosixPath
import tempfile

from . import Shell


class Zsh(Shell):
    def add_cd_build(self, builds):
        cd_build = "# cd-build <build name>\n"
        cd_build += "function cd-build { if [ \"$#\" -gt 0 ]; then\n case $@ in\n"
        for build in builds:
            cd_build += f"{build.name}) cd \"{build.paths.build_dir}\";;\n"
        cd_build += "*) echo No build directory for \\\"$@\\\" found.;;\nesac\n"
        cd_build += "else\necho 'Usage: cd-build <build name>'\nfi\n}\n"

        self.add_additional_commands(cd_build)

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
