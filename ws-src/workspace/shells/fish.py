import os

from . import Shell


class Fish(Shell):
    def add_cd_build_dir(self):
        cd_build_dir = """
# cd-build-dir
function cd-build-dir
    set -l output (build-dir --cd-build-dir $argv 2>&1)
    set -l exitcode $status
    if test $exitcode -ne 0
        echo $output >&2
        return $exitcode
    end
    if string match -r '^cd .*' $output
        eval $output
    else
        printf '%s\n' $output
    end
end
        """
        self.add_additional_commands(cd_build_dir)

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
