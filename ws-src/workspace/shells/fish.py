import os

from . import Shell


class Fish(Shell):
    def add_cd_build(self, builds):
        cd_build = "# cd-build <build name>\n"
        cd_build += "function cd-build; if test (count $argv) -gt 0; switch $argv;\n"
        for build in builds:
            cd_build += f"case \"{build.name}\"; cd \"{build.paths.build_dir}\"\n"
        cd_build += "case '*'; echo No build directory for \\\"$argv\\\" found.; end;\n"
        cd_build += "else; echo 'Usage: cd-build <build name>'; end;\nend\n"

        self.add_additional_commands(cd_build)

    def spawn(self, env):
        os.execvpe("fish", [
            "fish", "-i", "-C", f"""
# set prompt
functions -c fish_prompt _ws_nested_prompt
function fish_prompt
    printf "%s" "{self.prompt_prefix}"
    _ws_nested_prompt
end

{self.additional_commands}
            """
        ], env)
