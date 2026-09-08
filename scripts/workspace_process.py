"""Bounded lifecycle processes, including descendants started by Git hooks."""
from __future__ import annotations

import os
import signal
import subprocess

GIT_TIMEOUT_SECONDS = 120
FACADE_TIMEOUT_SECONDS = 900
RETIRE_TIMEOUT_SECONDS = 180
CLEANUP_TIMEOUT_SECONDS = 10


def run(argv, *, timeout, **kwargs):
    """subprocess.run's captured-output shape with process-tree timeout cleanup."""
    check = kwargs.pop('check', False)
    if kwargs.pop('capture_output', False):
        kwargs['stdout'] = subprocess.PIPE
        kwargs['stderr'] = subprocess.PIPE
    if os.name == 'nt':
        kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs['start_new_session'] = True
    process = subprocess.Popen(argv, **kwargs)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as error:
        cleanup = None
        try:
            if os.name == 'nt':
                killed = subprocess.run(
                    ['taskkill', '/PID', str(process.pid), '/T', '/F'],
                    capture_output=True, timeout=CLEANUP_TIMEOUT_SECONDS,
                )
                if killed.returncode:
                    cleanup = f'taskkill exit {killed.returncode}'
            else:
                os.killpg(process.pid, signal.SIGKILL)
        except (OSError, subprocess.TimeoutExpired) as failure:
            cleanup = str(failure)
        if process.poll() is None:
            process.kill()
        try:
            stdout, stderr = process.communicate(timeout=CLEANUP_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            # A surviving descendant may still own a pipe. Never wait without
            # a ceiling; leave the failed cleanup explicit to the caller.
            cleanup = cleanup or 'descendant output handles remain open'
            stdout, stderr = error.output, error.stderr
            if process.stdout:
                process.stdout.close()
            if process.stderr:
                process.stderr.close()
        error.output, error.stderr = stdout, stderr
        error.cleanup_error = cleanup
        raise
    completed = subprocess.CompletedProcess(argv, process.returncode, stdout, stderr)
    if check:
        completed.check_returncode()
    return completed
