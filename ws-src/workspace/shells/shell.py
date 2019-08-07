import abc


class Shell(abc.ABC):
    def __init__(self):
        self.prompt_prefix = ""
        self.additional_commands = ""

    def set_prompt_prefix(self, prompt_prefix):
        self.prompt_prefix = prompt_prefix

    def add_additional_commands(self, commands):
        self.additional_commands += commands

    @abc.abstractmethod
    def add_cd_build(self, builds):
        raise NotImplementedError

    @abc.abstractmethod
    def spawn(self, env):
        raise NotImplementedError
