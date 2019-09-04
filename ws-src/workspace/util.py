from __future__ import annotations

from pathlib import Path
from typing import Mapping, MutableMapping, Optional, Sequence, Union


def env_prepend_path(env: MutableMapping[str, str], key: str, path: Union[Path, str]) -> MutableMapping[str, str]:
    if key in env and env[key] != "":
        env[key] = f'{path}:{env[key]}'
    else:
        env[key] = f'{path}'
    return env


def _terminal_set_raw_input() -> Optional[int]:
    """
    Sets the terminal to raw input mode. Returns the old mode.
    """
    import tty

    stdin: int = 0
    try:
        old_mode = mode = tty.tcgetattr(stdin)  # type: ignore

        mode[tty.IFLAG] &= ~(tty.BRKINT | tty.ICRNL | tty.INPCK | tty.ISTRIP | tty.IXON)  # type: ignore
        mode[tty.CFLAG] &= ~(tty.CSIZE | tty.PARENB)  # type: ignore
        mode[tty.CFLAG] |= tty.CS8  # type: ignore
        mode[tty.LFLAG] &= ~(tty.ECHO | tty.ICANON | tty.IEXTEN | tty.ISIG)  # type: ignore
        mode[tty.CC][tty.VMIN] = 1  # type: ignore
        mode[tty.CC][tty.VTIME] = 0  # type: ignore

        tty.tcsetattr(stdin, tty.TCSAFLUSH, mode)  # type: ignore

        return old_mode
    except tty.error:  # type: ignore
        return None


def _terminal_restore_input(old_mode: Optional[int]) -> None:
    """
    Restores the terminal to the old input mode.
    """
    if old_mode is not None:
        import tty

        stdin: int = 0
        tty.tcsetattr(stdin, tty.TCSAFLUSH, old_mode)  # type: ignore


def run_with_prefix(  # pylint: disable=too-many-locals,too-many-statements
        command: Union[Sequence[Union[str, Path]], Union[str, Path]],
        prefix: str,
        cwd: Optional[Path] = None,
        env: Optional[Mapping[str, str]] = None,
        check: bool = False) -> None:
    """
    Runs a command (similar to `subprocess.run`) attached to a new pty, prefixing every line in the output with
    `prefix`.
    """

    if isinstance(command, Path):
        command = [str(command)]
    elif isinstance(command, str):
        command = [command]
    else:
        assert isinstance(command, list)
        command = [str(arg) for arg in command]
    assert isinstance(command, list)

    import os
    import pty
    import sys

    start_of_line: bool = True  # denotes whether we start at the beginning of a line
    owed_carriage_return: bool = False  # `True` iff the previously read block omitted printing a final b'\r'
    prefix_bytes: bytes = prefix.encode()

    def read(fd):  # pylint: disable=too-many-branches
        """
        This function is called repeatedly whenever the pty fd becomes ready to be read from.

        In addition to copying over the user content, we perform a very basic kind of terminal emulation:
        - Any occurence of the "terminal newline" `b"\r\n"` is reduced (back) to `b"\n"`.
        - At the beginning of a new line and after returning the cursor to the beginning of a line with `b"\r"`, the
          prefix is printed
        """
        nonlocal start_of_line, owed_carriage_return, prefix_bytes

        data = os.read(fd, 1024)

        output = bytes()
        if data:
            if owed_carriage_return:
                owed_carriage_return = False
                if data[0] != 0x0A:
                    output += b"\r"
                    output += prefix_bytes
                # else (b"\r\n") drop the carriage return
            elif start_of_line:
                start_of_line = False
                output += prefix_bytes
        else:  # EoF
            if owed_carriage_return:
                owed_carriage_return = False
                output += b"\r"

        j = 0
        for (i, byte) in enumerate(data):
            byte = data[i]
            if byte == 0x0A:  # \n
                output += data[j:i + 1]
                j = i + 1
                if i + 1 < len(data):
                    output += prefix_bytes
                else:
                    start_of_line = True
            elif byte == 0x0D:  # \r
                if i + 1 < len(data):
                    if data[i + 1] == 0x0A:  # \r\n
                        output += data[j:i]
                        j = i + 1
                    else:
                        output += data[j:i + 1]
                        output += prefix_bytes
                        j = i + 1
                else:
                    owed_carriage_return = True
                    output += data[j:i]
                    j = i + 1

        output += data[j:]

        return output

    # flush, as we will use raw IO during the call
    sys.stdout.flush()
    sys.stderr.flush()

    pid, fd = pty.fork()
    if pid == pty.CHILD:
        if cwd:
            os.chdir(cwd)
        os.execvpe(command[0], command, env if env is not None else os.environ.copy())

    mode = _terminal_set_raw_input()
    try:
        pty._copy(fd, read, lambda fd: os.read(fd, 1024))  # type: ignore  # pylint: disable=protected-access
    except OSError:
        pass

    _terminal_restore_input(mode)
    os.close(fd)

    status = os.waitpid(pid, 0)[1]
    if check and status:
        raise Exception(f'Command {command[0]} failed with non-zero exit status {status}')
