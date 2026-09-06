"""Native FramesHandler projection and raw ReturnAsStream seam checks."""
import json
import subprocess
import tempfile
import unittest


ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]
NODE = "node"
TRACE = "example-workflows/3d-browser-game/scripts/trace_frames.mjs"
TRACE_URI = (__import__("pathlib").Path(__file__).resolve().parents[1] / TRACE).as_uri()


def node(expression):
    if len(expression) < 20000:
        return subprocess.run(
            [NODE, "--input-type=module", "-e", expression],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30,
        )
    with tempfile.TemporaryDirectory() as directory:
        path = __import__("pathlib").Path(directory) / "case.mjs"
        path.write_text(expression, encoding="utf-8")
        return subprocess.run(
            [NODE, str(path)],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30,
        )


def native_trace(stalled=False):
    coverage = {
        "explicit": True,
        "coordinate_space": "drawing-buffer",
        "requested_region": {"x": 32, "y": 32, "width": 8, "height": 8},
        "resolved_region": {"x": 32, "y": 32, "width": 8, "height": 8},
        "drawing_buffer": {"width": 640, "height": 360},
        "viewport": {"width": 640, "height": 360},
        "dpr": 1,
        "sample_pixels": 64,
        "bytes_per_sample": 256,
        "origin": "webgl-bottom-left",
    }
    events = []
    for index in range(60):
        time = index * (1000 / 60)
        events.append({
            "name": "BeginFrame", "ts": time * 1000, "pid": 7, "tid": 8,
            "args": {"frameSeqId": index + 1, "layerTreeId": 2},
        })
        events.append({
            "name": "DrawFrame", "ts": (time + 1) * 1000, "pid": 7, "tid": 8,
            "args": {"frameSeqId": index + 1, "layerTreeId": 2},
        })
    events.insert(0, {
        "name": "LayerTreeHostImpl:snapshot", "ts": 0, "pid": 7, "tid": 8,
        "args": {"snapshot": {"active_tree": {"layers": [{
            "layer_id": 6, "layer_name": "LayoutHTMLCanvas CANVAS id='game'",
            "base_type": "cc::TextureLayerImpl", "draws_content": 1,
            "compositing_reasons": ["Canvas"],
        }]}}},
    })
    return {
        "format": "cdp-return-as-stream",
        "categories": ["devtools.timeline", "disabled-by-default-devtools.timeline.frame",
                        "disabled-by-default-devtools.timeline.layers", "disabled-by-default-cc.debug", "cc"],
        "transfer_mode": "ReturnAsStream",
        "raw_bytes": 1,
        "raw_stream_hash": "sha256:" + "a" * 64,
        "completion": {"stream": "1", "transferMode": "ReturnAsStream", "dataLossOccurred": False},
        "metadata": {"clock_reconciled": True, "window_start_ms": -100, "window_end_ms": 1100},
        "canvas_instrumentation": {
            "method": "webgl2.pixel-pack-buffer+fence-sync", "presentation": "render-callback-post-callback",
            "read_only": True, "preserve_drawing_buffer": False,
            "sampling": coverage,
            "readback": {"method": "webgl2.pixel-pack-buffer+fence-sync", "asynchronous": True,
                          "api": ["PIXEL_PACK_BUFFER", "readPixels-offset", "fenceSync", "clientWaitSync-timeout-0", "getBufferSubData"],
                          "max_pending": 4, "allocated_buffers": 4, "queued": 60, "completed": 60,
                          "lost": 0, "errors": 0, "context_losses": 0, "poll_count": 60,
                          "pending_at_cleanup": 0, "cleanup_observed": True,
                          "queue_duration_ms": 1, "wait_duration_ms": 1, "copy_duration_ms": 1, "poll_duration_ms": 1},
            "measurement_perturbation": {"status": "observed", "basis": "control-vs-instrumented", "control_callbacks": 60, "instrumented_callbacks": 60, "control_callback_rate_hz": 60, "instrumented_callback_rate_hz": 60, "callback_rate_delta_hz": 0, "samples": 60, "readback_errors": 0},
        },
        "measurement": {
            "scenario_id": "native-test", "observer": "render-callback-post-callback",
            "presentation": "render-callback-post-callback", "preserve_drawing_buffer": False,
            "sampling": coverage,
            "lifecycle": {"status": "observed", "scenario_id": "native-test", "seed": 7, "configured_url": "http://127.0.0.1/game", "reset": {"method": "page.reload", "observed": True}, "phase_transitions": [{"phase": "control", "start_observed": True}, {"phase": "instrumented", "start_observed": True}]},
            "warmup": {"status": "observed", "requested_ms": 1000, "observed_ms": 1000, "callbacks": 60, "callback_rate_hz": 60},
            "control": {"status": "observed", "requested_ms": 1000, "observed_ms": 1000, "callbacks": 60, "callback_rate_hz": 60},
            "instrumented": {"status": "observed", "requested_ms": 1000, "observed_ms": 1000, "callbacks": 60, "callback_rate_hz": 60, "samples": 60, "readback_errors": 0, "sample_duration_ms": {"count": 60, "total_ms": 1.2, "max_ms": 0.1, "p99_ms": 0.1}},
            "perturbation": {"status": "observed", "basis": "control-vs-instrumented", "control_callbacks": 60, "instrumented_callbacks": 60, "control_callback_rate_hz": 60, "instrumented_callback_rate_hz": 60, "callback_rate_delta_hz": 0, "samples": 60, "readback_errors": 0},
        },
        "traceEvents": events,
        "canvas_samples": ([{"timestamp_ms": index * (1000 / 60), "origin_timestamp_ms": index * (1000 / 60), "callback_index": index, "hash": f"frame-{index}", "source": "render-callback-post-callback", "completion_status": "complete", "duration_ms": 0.1}
                             for index in range(61)]
                            if not stalled else [{"timestamp_ms": 0, "origin_timestamp_ms": 0, "callback_index": 0, "hash": "a", "source": "render-callback-post-callback", "completion_status": "complete", "duration_ms": 0.1}, {"timestamp_ms": 200, "origin_timestamp_ms": 200, "callback_index": 1, "hash": "b", "source": "render-callback-post-callback", "completion_status": "complete", "duration_ms": 0.1}, {"timestamp_ms": 300, "origin_timestamp_ms": 300, "callback_index": 2, "hash": "b", "source": "render-callback-post-callback", "completion_status": "complete", "duration_ms": 0.1}]),
    }


class NativeTraceTests(unittest.TestCase):
    def qualify(self, trace):
        expression = (
            "import {qualifyPerformance} from " + json.dumps(TRACE_URI) + "; "
            "const t=" + json.dumps(trace) + "; "
            "const c={id:'native',artifact_commit:'git:x',mode:'animation',window:{start_ms:0,end_ms:1000},game_canvas:{canvas_selector:'#game'}}; "
            "console.log(JSON.stringify(qualifyPerformance({cell:c,trace:t,callbacks:Array.from({length:60},(_,i)=>i*1000/60)})));"
        )
        result = node(expression)
        self.assertEqual(0, result.returncode, result.stderr)
        return json.loads(result.stdout)

    def test_native_layer_presence_requires_pixel_change_for_fps(self):
        qualified = self.qualify(native_trace())
        self.assertEqual("qualified", qualified["status"])
        self.assertEqual(60, qualified["metrics"]["N"])
        stalled = self.qualify(native_trace(stalled=True))
        self.assertEqual("unverified", stalled["status"])
        self.assertIn("canvas-frame-floor", [item["code"] for item in stalled["failures"]])

    def test_sparse_canvas_changes_do_not_upgrade_intervening_frames(self):
        trace = native_trace()
        trace["canvas_samples"] = [
            {"timestamp_ms": time, "hash": f"sample-{index}"}
            for index, time in enumerate((0, 250, 500, 750, 1000))
        ]
        result = self.qualify(trace)
        self.assertEqual("unverified", result["status"])
        self.assertLess(result["metrics"]["C"], 59)
        self.assertIn("canvas-frame-floor", [item["code"] for item in result["failures"]])

    def test_native_default_buffer_path_requires_observed_presentation_seam(self):
        trace = native_trace()
        trace["canvas_instrumentation"]["preserve_drawing_buffer"] = True
        result = self.qualify(trace)
        self.assertEqual("unverified", result["status"])
        self.assertIn("missing-native-presentation-observation", [item["code"] for item in result["failures"]])
        trace = native_trace()
        trace["canvas_instrumentation"].pop("measurement_perturbation")
        trace["measurement"].pop("perturbation")
        result = self.qualify(trace)
        self.assertIn("missing-measurement-perturbation", [item["code"] for item in result["failures"]])
        trace = native_trace()
        trace["canvas_instrumentation"]["readback"]["asynchronous"] = False
        result = self.qualify(trace)
        self.assertIn("missing-asynchronous-readback", [item["code"] for item in result["failures"]])
        trace = native_trace()
        trace["canvas_samples"][1].pop("origin_timestamp_ms")
        result = self.qualify(trace)
        self.assertIn("invalid-readback-association", [item["code"] for item in result["failures"]])

    def test_native_canvas_flag_and_label_cannot_self_attribute(self):
        trace = native_trace()
        trace["traceEvents"] = [{"name": "frame", "timestamp_ms": 0, "canvas": True, "attribution": "game-canvas", "draw": True}]
        result = self.qualify(trace)
        self.assertEqual("unverified", result["status"])
        self.assertIn("missing-canvas-attribution", [item["code"] for item in result["failures"]])

    def test_begin_frame_queue_omits_undrawn_and_keeps_dropped_once(self):
        expression = (
            "import {buildFrameModel} from './" + TRACE + "'; "
            "const t={format:'trace-event-json',traceEvents:["
            "{name:'BeginFrame',ts:0,args:{frameSeqId:1,layerTreeId:2},pid:7},"
            "{name:'BeginFrame',ts:1000,args:{frameSeqId:2,layerTreeId:2},pid:7},"
            "{name:'DroppedFrame',ts:1100,args:{frameSeqId:2,layerTreeId:2,hasPartialUpdate:true},pid:7},"
            "{name:'BeginFrame',ts:2000,args:{frameSeqId:3,layerTreeId:2},pid:7},"
            "{name:'DrawFrame',ts:2100,args:{frameSeqId:3,layerTreeId:2},pid:7}]};"
            "console.log(JSON.stringify(buildFrameModel(t,{startMs:0,endMs:10}).frames));"
        )
        result = node(expression)
        self.assertEqual(0, result.returncode, result.stderr)
        rows = json.loads(result.stdout)
        self.assertEqual(["2", "3"], [row["id"] for row in rows])
        self.assertEqual(1, sum(row["dropped"] or row["isPartial"] for row in rows))

    def test_native_activity_index_preserves_pid_window_and_equal_snapshot_semantics(self):
        def model(update, snapshots=None):
            snapshots = snapshots or [{"name": "LayerTreeHostImpl:snapshot", "ts": 0, "pid": 7,
                "args": {"snapshot": {"active_tree": {"layers": [{
                    "layer_id": 6, "layer_name": "LayoutHTMLCanvas CANVAS id='game'",
                    "base_type": "cc::TextureLayerImpl", "compositing_reasons": ["Canvas"],
                }]}}}}]
            events = snapshots + [
                {"name": "BeginFrame", "ts": 100000, "pid": 7, "args": {"frameSeqId": 1}},
                {"name": "DrawFrame", "ts": 101000, "pid": 7, "args": {"frameSeqId": 1}},
            ]
            if update is not None:
                events.append(update)
            expression = (
                "import {buildFrameModel} from './" + TRACE + "'; "
                "const t=" + json.dumps({"format": "trace-event-json", "traceEvents": events}) + "; "
                "console.log(JSON.stringify(buildFrameModel(t,{target:{canvas_selector:'#game'},startMs:0,endMs:1000}).frames));"
            )
            result = node(expression)
            self.assertEqual(0, result.returncode, result.stderr)
            rows = json.loads(result.stdout)
            self.assertEqual(1, len(rows))
            return rows[0]

        self.assertTrue(model({"name": "CanvasUpdate", "ts": 120000, "pid": 7})["presentation_evidence"])
        self.assertTrue(model({"name": "CanvasUpdate", "ts": 120000})["presentation_evidence"])
        self.assertFalse(model({"name": "CanvasUpdate", "ts": 120000, "pid": 8})["presentation_evidence"])
        self.assertFalse(model({"name": "CanvasUpdate", "ts": 121000, "pid": 7})["presentation_evidence"])
        equal_time = [
            {"name": "LayerTreeHostImpl:snapshot", "ts": 0, "pid": 7,
             "args": {"snapshot": {"active_tree": {"layers": [{
                 "layer_id": 6, "layer_name": "LayoutHTMLCanvas CANVAS id='game'",
                 "base_type": "cc::TextureLayerImpl", "compositing_reasons": ["Canvas"],
             }]}}}},
            {"name": "LayerTreeHostImpl:snapshot", "ts": 0, "pid": 7,
             "args": {"snapshot": {"active_tree": {"layers": [{
                 "layer_id": 9, "layer_name": "LayoutHTMLCanvas CANVAS id='game'",
                 "base_type": "cc::TextureLayerImpl", "compositing_reasons": ["Canvas"],
             }]}}}},
        ]
        self.assertTrue(model({"name": "CanvasUpdate", "ts": 101000, "pid": 7}, equal_time)["ambiguous"])

    def test_return_as_stream_keeps_exact_nonserialized_bytes_and_completion(self):
        expression = (
            "import {collectCDPTrace} from './" + TRACE + "'; "
            "class C{constructor(){this.h=[]} once(n,f){this.h.push(f)} off(n,f){this.h=this.h.filter(x=>x!==f)} async send(n,a){"
            "if(n==='Tracing.end') setTimeout(()=>this.h[0]?.({stream:'s',dataLossOccurred:false,transferMode:'ReturnAsStream'}),0); "
            "if(n==='IO.read') return {data:'{\\\"traceEvents\\\":[]}',eof:true}; return {}}} "
            "const c=await collectCDPTrace(new C(),{durationMs:1,timeoutMs:1000}); "
            "console.log(JSON.stringify({bytes:c.raw_bytes,hash:c.raw_stream_hash,completion:c.completion,hidden:Buffer.isBuffer(c.rawStream),enumerated:Object.keys(c).includes('rawStream')}));"
        )
        result = node(expression)
        self.assertEqual(0, result.returncode, result.stderr)
        value = json.loads(result.stdout)
        self.assertTrue(value["bytes"] > 0)
        self.assertTrue(value["hidden"])
        self.assertFalse(value["enumerated"])
        self.assertFalse(value["completion"]["dataLossOccurred"])


if __name__ == "__main__":
    unittest.main()
