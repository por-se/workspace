import os
import tempfile

from .shell import Shell


class Bash(Shell):
    def add_cd_build_dir(self):
        cd_build_dir = """
# cd-build-dir
function cd-build-dir {
    output=$(build-dir --cd-build-dir "$@")
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
