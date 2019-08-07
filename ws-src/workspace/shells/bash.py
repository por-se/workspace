import os
import tempfile

from . import Shell


class Bash(Shell):
    def add_cd_build(self, builds):
        cd_build = "# cd-build <build name>\n"
        cd_build += "function cd-build { if [ \"$#\" -gt 0 ]; then\n case $@ in\n"
        for build in builds:
            cd_build += f"{build.name}) cd \"{build.paths.build_dir}\";;\n"
        cd_build += "*) echo No build directory for \\\"$@\\\" found.;;\nesac\n"
        cd_build += "else\necho 'Usage: cd-build <build name>'\nfi\n}\n"

        self.add_additional_commands(cd_build)

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
