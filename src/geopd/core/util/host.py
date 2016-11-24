import logging
import shlex
from subprocess import PIPE
from subprocess import Popen

log = logging.getLogger(__name__)


class ProcessError(RuntimeError):
    def __init__(self, message, commands, returncode, stderr):
        super(ProcessError, self).__init__(message)
        self.commands = commands
        self.returncode = returncode
        self.stderr = stderr


def run(*command_lines, **kwargs):
    input_string = kwargs.pop('input_string', None)
    stdin = PIPE if input_string else None

    procs = list()
    commands = [shlex.split(line) for line in command_lines]
    for args in commands:
        log.info("run: {0}".format(args))
        p = Popen(args, stdin=procs[-1].stdout if procs else stdin, stdout=PIPE, stderr=PIPE, shell=False)
        procs.append(p)

    if stdin:
        procs[0].stdin.write(input_string)
        if len(procs) > 1:
            procs[0].stdin.close()

    for p in procs[:-1]:
        p.stdout.close()

    stdout, stderr = procs[-1].communicate()

    for p in procs[:-1]:
        p.wait()

    if procs[-1].returncode:
        raise ProcessError(message='process failed: {0}'.format(' | '.join(command_lines)),
                           commands=commands,
                           returncode=procs[-1].returncode,
                           stderr=iter(stderr.splitlines()))

    return stdout
