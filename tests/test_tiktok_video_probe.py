"""Technical delivery failures at the video probe seam, without render dependencies.

Actual renderer/decode observations live with the foundation evidence; these
cheap controls pin failure behavior rather than claiming audiovisual quality.
"""
from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tests._repo_root import ROOT

SCRIPT = ROOT / 'example-workflows/orchflows-videos/scripts/probe.py'
SPEC = importlib.util.spec_from_file_location('tiktok_probe', SCRIPT)
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


def metadata(seconds=1):
    return {'streams': [
        {'codec_type': 'video', 'codec_name': 'h264', 'width': 1080, 'height': 1920,
         'pix_fmt': 'yuv420p', 'color_space': 'bt709', 'color_transfer': 'bt709',
         'color_primaries': 'bt709', 'color_range': 'tv', 'r_frame_rate': '30/1',
         'avg_frame_rate': '30/1', 'duration': str(seconds),
         'nb_read_frames': str(seconds * 30), 'start_time': '0'},
        {'codec_type': 'audio', 'codec_name': 'aac', 'sample_rate': '48000',
         'duration': str(seconds + 0.045333), 'start_time': '0'}]}


class VideoProbeTests(unittest.TestCase):
    def invoke(self, root, **kwargs):
        args = ['--project', str(root), '--video', 'final.mp4', '--seconds', '1']
        for key, value in kwargs.items():
            args.extend(['--' + key.replace('_', '-'), str(value)])
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return probe.main(args)

    def test_missing_corrupt_and_actual_decode_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(1, self.invoke(root))
            (root / 'final.mp4').write_bytes(b'corrupt')
            with patch.object(probe, 'run_cli', side_effect=probe.ProbeError('ffprobe exit 1')):
                self.assertEqual(1, self.invoke(root))
            readings = [(json.dumps(metadata()), ''), ('', ''),
                        ('', '{"input_i":"-16.1","input_tp":"-2.2"}')]
            with patch.object(probe, 'run_cli', side_effect=readings) as run:
                self.assertEqual(0, self.invoke(root))
                decode = run.call_args_list[1].args
                self.assertEqual('ffmpeg', decode[1])
                self.assertIn('-xerror', decode[2])
            with patch.object(probe, 'run_cli', side_effect=[readings[0], probe.ProbeError('decode failed')]):
                self.assertEqual(1, self.invoke(root))

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'final.mp4').write_bytes(b'fixture')
            for rate, expected in ((44100, 1), (48000, 0)):
                data = metadata()
                data['streams'][1]['sample_rate'] = str(rate)
                readings = [(json.dumps(data), ''), ('', ''),
                            ('', '{"input_i":"-16.1","input_tp":"-2.2"}')]
                with self.subTest(rate=rate), patch.object(probe, 'run_cli', side_effect=readings):
                    self.assertEqual(expected, self.invoke(root))

    def test_endpoints_allow_aac_padding_but_reject_drift(self):
        for seconds in (1, 120):
            good = metadata(seconds)
            probe.inspect_metadata(good, seconds, 30, True)
            for stream, field, value in [(0, 'duration', str(seconds + .1)),
                                         (1, 'duration', str(seconds + .2)),
                                         (0, 'nb_read_frames', '0'),
                                         (1, 'start_time', '1')]:
                bad = copy.deepcopy(good)
                bad['streams'][stream][field] = value
                with self.subTest(seconds=seconds, field=field):
                    with self.assertRaises(probe.ProbeError):
                        probe.inspect_metadata(bad, seconds, 30, True)

    def test_stream_contract_rejects_wrong_size_fps_codec_and_color(self):
        for field, value in [('width', 1920), ('height', 1080), ('codec_name', 'hevc'),
                             ('color_space', 'bt470bg'), ('color_range', 'pc'),
                             ('pix_fmt', 'yuvj420p'), ('avg_frame_rate', '24/1'),
                             ('r_frame_rate', '0/0'), ('duration', 'N/A')]:
            bad = metadata()
            bad['streams'][0][field] = value
            with self.subTest(field=field), self.assertRaises(probe.ProbeError):
                probe.inspect_metadata(bad, 1, 30, True)
        with self.assertRaises(probe.ProbeError):
            probe.inspect_metadata({}, 1, 30, True)
        no_audio = metadata()
        no_audio['streams'].pop()
        with self.assertRaises(probe.ProbeError):
            probe.inspect_metadata(no_audio, 1, 30, True)
        probe.inspect_metadata(no_audio, 1, 30, False)

    def test_audio_settings_and_silent_clipped_or_off_target_signal_fail(self):
        for measured in ['{}', '{"input_i":"-inf","input_tp":"-inf"}',
                         '{"input_i":"-22","input_tp":"-2"}',
                         '{"input_i":"-16","input_tp":"0.1"}']:
            with self.subTest(measured=measured), self.assertRaises(probe.ProbeError):
                probe.loudness(measured, -16, 2, -1)
        with tempfile.TemporaryDirectory() as tmp:
            for kwargs in ({'seconds': 'nan'}, {'seconds': 121}, {'fps': 0},
                           {'lufs': 'nan'}, {'lufs_tolerance': -1}):
                self.assertEqual(1, self.invoke(Path(tmp), **kwargs))

    def test_malformed_tool_output_and_timeout_return_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'final.mp4').write_bytes(b'x')
            with patch.object(probe, 'run_cli', return_value=('{not json', '')):
                self.assertEqual(1, self.invoke(root))
            with patch.object(probe, 'run_cli', side_effect=subprocess.TimeoutExpired('ffmpeg', 300)):
                self.assertEqual(1, self.invoke(root))

    def test_toolchain_must_match_local_qualified_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(probe.ProbeError):
                probe.run_cli(root, 'ffprobe', [])
            package = root / 'node_modules/@remotion/cli'
            package.mkdir(parents=True)
            (package / 'remotion-cli.js').write_text('')
            (package / 'package.json').write_text('{"version":"4.0.521"}')
            (root / 'package-lock.json').write_text(json.dumps({'packages': {
                'node_modules/@remotion/cli': {'version': '4.0.522'}}}))
            with self.assertRaises(probe.ProbeError):
                probe.run_cli(root, 'ffprobe', [])


if __name__ == '__main__':
    unittest.main()
