from vyper import v

from .ws_path import ws_path

DEFAULT_SETTINGS_FILE = (f'''config = "release"
default-linker = "gold"
preserve-settings = false

[uri-schemes]
"github://" = "ssh://git@github.com/"
"laboratory://" = "ssh://git@laboratory.comsys.rwth-aachen.de/"''')


def write_default_settings_file():
    with open(ws_path / "ws-settings.toml", "w") as file:
        print(DEFAULT_SETTINGS_FILE, file=file)


v.add_config_path(ws_path)
v.set_config_name("ws-settings")
v.set_config_type('toml')
try:
    v.read_in_config()
except FileNotFoundError:
    write_default_settings_file()
    v.read_in_config()

v.set_env_prefix('ws')
v.automatic_env()
v.set_env_key_replacer("-", "_")


def get(key: str):
    # in command line arguments and environment variables, dashes are replaced with underscores
    value = v.get(key.replace("-", "_"))
    if value is None:
        # in the config file, however, they are preserved
        value = v.get(key)
    return value
