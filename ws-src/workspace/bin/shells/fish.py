import os

from . import Shell


class Fish(Shell):
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
