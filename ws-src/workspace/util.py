def env_prepend_path(env, key: str, path):
    if key in env and env[key] != "":
        env[key] = f'{path}:{env[key]}'
    else:
        env[key] = f'{path}'
    return env
