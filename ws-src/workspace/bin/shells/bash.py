import os
import tempfile

from . import Shell


class Bash(Shell):
    def spawn(self, env):
        with tempfile.NamedTemporaryFile(mode='w+') as file:
            file.write(f"""
# source user's default configuration
[ -r $HOME/.bashrc ] && . $HOME/.bashrc

# remove this temporary file
rm {file.name}

# set prompt
PS1="{self.prompt_prefix}$PS1"

{self.additional_commands}
            """)
            file.flush()

            os.execvpe("bash", ["bash", "--init-file", file.name, "-i"], env)
