import argparse, os, sys, enum


class EmptyClass:
    pass

def j_from_num_threads(num_threads):
    if num_threads:
        return ["-j", str(num_threads)]
    else:
        return [""]


def env_prepend_path(env, key: str, path):
    if key in env and env[key] != "":
        env[key] = f'{path}:{env[key]}'
    else:
        env[key] = f'{path}'
    return env
