"""One bounded pool for harness-owned native sessions; monotonic deadlines."""
import asyncio
import json
import os
from pathlib import Path
import signal
import time

from common import write_json


async def stop_tree(process):
    if process.returncode is not None:
        return
    if os.name == 'nt':
        killer = await asyncio.create_subprocess_exec('taskkill', '/PID', str(process.pid), '/T', '/F',
                                                     stdout=asyncio.subprocess.DEVNULL,
                                                     stderr=asyncio.subprocess.DEVNULL)
        await asyncio.wait_for(killer.wait(), 10)
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    await asyncio.wait_for(process.wait(), 5)


class Scheduler:
    def __init__(self, jobs, deadline, log=None):
        if jobs < 1 or deadline <= 0:
            raise ValueError('Positive jobs and deadline required')
        self.slots = asyncio.Semaphore(jobs)
        self.local_slots = asyncio.Semaphore(2)
        self.end = time.monotonic() + deadline
        self.started = time.monotonic()
        self.log = Path(log) if log else None
        self.active = 0
        self.peak = 0

    def emit(self, **event):
        event['elapsed'] = round(time.monotonic() - self.started, 3)
        if self.log:
            with self.log.open('a', encoding='utf-8') as out:
                out.write(json.dumps(event) + '\n')

    async def process(self, command, *, cwd, directory, prompt='', timeout=150, until=None,
                      env=None, native=True, label='session'):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        queued = time.monotonic()
        end = min(self.end, until if until is not None else self.end)
        record = {'command': list(map(str, command)), 'status': 'not_started', 'label': label,
                  'queue_seconds': 0, 'seconds': 0, 'exit_code': None, 'gaps': []}
        pool = self.slots if native else self.local_slots
        acquired = False
        process = communication = None
        try:
            await asyncio.wait_for(pool.acquire(), max(0.001, end - time.monotonic()))
            acquired = True
            record['queue_seconds'] = round(time.monotonic() - queued, 3)
            remaining = min(timeout, end - time.monotonic())
            if remaining <= 0:
                return record
            started = time.monotonic()
            record['status'] = 'running'
            with (directory / 'events.jsonl').open('wb') as out, (directory / 'stderr.txt').open('wb') as err:
                spawning = asyncio.create_task(asyncio.create_subprocess_exec(*map(str, command), cwd=cwd, env=env,
                    stdin=asyncio.subprocess.PIPE, stdout=out, stderr=err, start_new_session=os.name != 'nt'))
                try:
                    process = await asyncio.shield(spawning)
                except asyncio.CancelledError:
                    # Cancellation during Windows process creation must still reap the new PID.
                    process = await spawning
                    await stop_tree(process)
                    record['exit_code'] = process.returncode
                    raise
                record['pid'] = process.pid
                if native:
                    self.active += 1
                    self.peak = max(self.peak, self.active)
                self.emit(kind='started', label=label, native=native, pid=process.pid, active=self.active)
                communication = asyncio.create_task(process.communicate(prompt.encode('utf-8')))
                try:
                    await asyncio.wait_for(asyncio.shield(communication), remaining)
                    record['status'] = 'completed' if process.returncode == 0 else 'error'
                except (asyncio.TimeoutError, asyncio.CancelledError) as error:
                    record['status'] = 'timeout' if isinstance(error, asyncio.TimeoutError) else 'canceled'
                    await stop_tree(process)
                    await communication
                    if native:
                        record['gaps'].append('Local process tree stopped; remote continuation is not independently verified.')
                finally:
                    record['seconds'] = round(time.monotonic() - started, 3)
                    record['exit_code'] = process.returncode
                    if native:
                        self.active -= 1
                    self.emit(kind='finished', label=label, native=native, status=record['status'], active=self.active)
        except asyncio.TimeoutError:
            record['gaps'].append('Deadline expired before a slot became available.')
        except asyncio.CancelledError:
            record['status'] = 'canceled'
        except Exception as error:
            record['status'] = 'error'
            record['gaps'].append(f'{type(error).__name__}: {error}')
            if process and process.returncode is None:
                await stop_tree(process)
        finally:
            if acquired:
                pool.release()
            write_json(directory / 'execution.json', record)
        return record
