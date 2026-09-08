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
    job = _WindowsJob() if os.name == 'nt' else None
    if job is not None:
        kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP | 4  # CREATE_SUSPENDED
    else:
        kwargs['start_new_session'] = True
    try:
        process = subprocess.Popen(argv, **kwargs)
        if job is not None:
            job.start(process)
    except BaseException:
        if job is not None:
            job.close()
        raise
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as error:
        cleanup = None
        try:
            if job is not None:
                job.close()
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
    finally:
        if job is not None:
            job.close()
    completed = subprocess.CompletedProcess(argv, process.returncode, stdout, stderr)
    if check:
        completed.check_returncode()
    return completed


class _WindowsJob:
    """Own a suspended command and all descendants before any code can run."""

    def __init__(self):
        import ctypes
        from ctypes import wintypes
        self.ctypes = ctypes
        class Basic(ctypes.Structure):
            _fields_ = [('process_time', ctypes.c_longlong), ('job_time', ctypes.c_longlong),
                        ('flags', wintypes.DWORD), ('minimum', ctypes.c_size_t),
                        ('maximum', ctypes.c_size_t), ('processes', wintypes.DWORD),
                        ('affinity', ctypes.c_size_t), ('priority', wintypes.DWORD),
                        ('scheduling', wintypes.DWORD)]
        class Counters(ctypes.Structure):
            _fields_ = [(name, ctypes.c_ulonglong) for name in
                        ('read_ops', 'write_ops', 'other_ops', 'read_bytes', 'write_bytes', 'other_bytes')]
        class Limits(ctypes.Structure):
            _fields_ = [('basic', Basic), ('io', Counters), ('process_memory', ctypes.c_size_t),
                        ('job_memory', ctypes.c_size_t), ('peak_process', ctypes.c_size_t),
                        ('peak_job', ctypes.c_size_t)]
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.kernel = kernel
        kernel.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
        kernel.CreateJobObjectW.restype = wintypes.HANDLE
        kernel.SetInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD)
        kernel.SetInformationJobObject.restype = wintypes.BOOL
        kernel.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
        kernel.AssignProcessToJobObject.restype = wintypes.BOOL
        kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel.CloseHandle.restype = wintypes.BOOL
        self.handle = kernel.CreateJobObjectW(None, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        limits = Limits()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not kernel.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            error = ctypes.WinError(ctypes.get_last_error())
            self.close()
            raise error

    def start(self, process):
        ctypes = self.ctypes
        try:
            if not self.kernel.AssignProcessToJobObject(self.handle, int(process._handle)):
                raise ctypes.WinError(ctypes.get_last_error())
            resume = ctypes.WinDLL('ntdll').NtResumeProcess
            resume.argtypes = (ctypes.c_void_p,)
            resume.restype = ctypes.c_long
            result = resume(int(process._handle))
            if result:
                raise OSError(f'NtResumeProcess failed: {result}')
        except BaseException:
            process.kill()
            process.wait(timeout=CLEANUP_TIMEOUT_SECONDS)
            raise

    def close(self):
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None
