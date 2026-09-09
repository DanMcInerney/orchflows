"""Decode a delivered portrait MP4 through its artifact's locked Remotion tools.

This technical boundary cannot judge visible captions, craft, or heard audio.
Production settings are explicit CLI values, never inferred from the video.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import json
import math
from pathlib import Path
import re
import subprocess
import sys


class ProbeError(ValueError):
    """An output or its declared toolchain fails the delivery contract."""


def run_cli(project, tool, args):
    cli = project / 'node_modules/@remotion/cli/remotion-cli.js'
    if not cli.is_file():
        raise ProbeError('missing locked local Remotion CLI; run npm ci in project')
    lock = json.loads((project / 'package-lock.json').read_text(encoding='utf-8'))
    expected = lock['packages']['node_modules/@remotion/cli']['version']
    installed = json.loads((cli.parent / 'package.json').read_text(encoding='utf-8'))
    if expected != '4.0.522' or installed['version'] != expected:
        raise ProbeError('Remotion CLI differs from qualified lock pin 4.0.522')
    proc = subprocess.run(['node', str(cli), tool, *args], cwd=project,
                          capture_output=True, text=True, timeout=300)
    if proc.returncode:
        raise ProbeError(f'{tool} exit {proc.returncode}: {proc.stderr[-3000:]}')
    return proc.stdout, proc.stderr


def number(value, label):
    try:
        result = float(Fraction(str(value)))
    except (ValueError, ZeroDivisionError):
        raise ProbeError(f'invalid {label}: {value}') from None
    if not math.isfinite(result):
        raise ProbeError(f'nonfinite {label}')
    return result


def inspect_metadata(data, seconds, fps, require_audio):
    if not isinstance(data, dict) or not isinstance(data.get('streams'), list):
        raise ProbeError('malformed stream metadata')
    streams = data.get('streams', [])
    if any(not isinstance(s, dict) for s in streams):
        raise ProbeError('malformed stream entry')
    videos = [s for s in streams if s.get('codec_type') == 'video']
    audios = [s for s in streams if s.get('codec_type') == 'audio']
    if len(videos) != 1:
        raise ProbeError('expected exactly one video stream')
    video = videos[0]
    for field, expected in {'codec_name': 'h264', 'width': 1080, 'height': 1920,
                            'pix_fmt': 'yuv420p', 'color_space': 'bt709',
                            'color_transfer': 'bt709', 'color_primaries': 'bt709',
                            'color_range': 'tv'}.items():
        if video.get(field) != expected:
            raise ProbeError(f'{field}: expected {expected}, got {video.get(field)}')
    for field in ('r_frame_rate', 'avg_frame_rate'):
        if abs(number(video.get(field), field) - fps) > 0.001:
            raise ProbeError(f'{field} differs from declared fps')
    duration = number(video.get('duration'), 'video duration')
    if abs(duration - seconds) > 1 / fps + 0.000001:
        raise ProbeError('video duration differs by more than one frame')
    frames = number(video.get('nb_read_frames'), 'decoded frame count')
    if frames <= 0 or abs(frames - seconds * fps) > 1.000001:
        raise ProbeError('decoded frame count differs by more than one frame')
    if require_audio and len(audios) != 1:
        raise ProbeError('expected exactly one audio stream')
    if len(audios) > 1:
        raise ProbeError('multiple audio streams are not a delivery mix')
    for audio in audios:
        if audio.get('codec_name') != 'aac':
            raise ProbeError('delivery audio must be AAC')
        rate = number(audio.get('sample_rate'), 'audio sample rate')
        if rate != 48000:
            raise ProbeError('delivery audio sample rate must be 48000')
        # AAC encoder priming/tail can extend container/audio duration. Compare
        # streams; allow two AAC packets plus one video frame, not arbitrary drift.
        tolerance = 2048 / rate + 1 / fps
        if abs(number(audio.get('duration'), 'audio duration') - duration) > tolerance:
            raise ProbeError('audio duration exceeds AAC padding/frame tolerance')
        if abs(number(audio.get('start_time', 0), 'audio start')) > tolerance:
            raise ProbeError('audio starts outside AAC padding/frame tolerance')
    if abs(number(video.get('start_time', 0), 'video start')) > 1 / fps:
        raise ProbeError('video does not begin at zero')
    return video, audios


def loudness(stderr, target, tolerance, peak):
    matches = re.findall(r'\{\s*"input_i"[\s\S]*?\}', stderr)
    if not matches:
        raise ProbeError('FFmpeg returned no loudness measurement')
    measured = json.loads(matches[-1])
    integrated = number(measured['input_i'], 'integrated loudness')
    true_peak = number(measured['input_tp'], 'true peak')
    if abs(integrated - target) > tolerance:
        raise ProbeError(f'loudness {integrated} LUFS outside {target} +/- {tolerance}')
    if true_peak > peak:
        raise ProbeError(f'true peak {true_peak} dBTP exceeds {peak}')
    return {'integrated_lufs': integrated, 'true_peak_dbtp': true_peak}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--video', type=Path, required=True)
    parser.add_argument('--seconds', type=float, required=True)
    parser.add_argument('--fps', type=float, default=30)
    parser.add_argument('--audio', choices=('required', 'optional'), default='required')
    parser.add_argument('--lufs', type=float, default=-16)
    parser.add_argument('--lufs-tolerance', type=float, default=2)
    parser.add_argument('--true-peak', type=float, default=-1)
    args = parser.parse_args(argv)
    try:
        if not 1 <= args.seconds <= 120 or not 1 <= args.fps <= 60:
            raise ProbeError('seconds must be 1..120 and fps 1..60')
        if not all(math.isfinite(x) for x in (args.lufs, args.lufs_tolerance, args.true_peak)):
            raise ProbeError('audio settings must be finite')
        if args.lufs_tolerance < 0 or not -70 <= args.lufs <= -5 or not -9 <= args.true_peak <= 0:
            raise ProbeError('invalid production audio settings')
        project = args.project.resolve()
        video_path = (project / args.video).resolve()
        if not video_path.is_file() or video_path.stat().st_size == 0:
            raise ProbeError('video absent or empty')
        out, _ = run_cli(project, 'ffprobe', ['-v', 'error', '-count_frames',
                         '-show_streams', '-show_format', '-of', 'json', str(video_path)])
        video, audios = inspect_metadata(json.loads(out), args.seconds, args.fps,
                                        args.audio == 'required')
        # ffprobe metadata alone can survive damaged packets. Decode every stream
        # to null with fatal decoder errors and retain FFmpeg's exact failure.
        run_cli(project, 'ffmpeg', ['-v', 'error', '-xerror', '-err_detect', 'explode',
                '-i', str(video_path), '-map', '0:v:0', '-map', '0:a?',
                '-c:v', 'rawvideo', '-c:a', 'pcm_s16le', '-f', 'null', '-'])
        signal = None
        if audios:
            _, err = run_cli(project, 'ffmpeg', ['-hide_banner', '-i', str(video_path),
                '-vn', '-af', f'loudnorm=I={args.lufs}:TP={args.true_peak}:print_format=json',
                '-f', 'null', '-'])
            signal = loudness(err, args.lufs, args.lufs_tolerance, args.true_peak)
        print(json.dumps({'video': str(video_path), 'decoded': True,
                          'frames': video['nb_read_frames'], 'audio': signal,
                          'gaps': ['visual craft', 'visible captions', 'heard audio']}))
        return 0
    except (ProbeError, OSError, KeyError, TypeError, json.JSONDecodeError,
            subprocess.TimeoutExpired) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
