#!/usr/bin/env python3
"""Repeatable, account-free OCR benchmark using generated Chinese text.

Runs in a fresh data directory; measurements are synthetic, not game acceptance.
"""
import argparse
import contextlib
import json
import os
import platform
import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def benchmark(engine, iterations):
    import psutil
    from PIL import Image, ImageDraw, ImageFont
    from module.ocr import ocr

    process = psutil.Process()
    full = Image.new('RGB', (1920, 1080), 'white')
    font = ImageFont.truetype('/System/Library/Fonts/STHeiti Medium.ttc', 48)
    ImageDraw.Draw(full).text((100, 70), '每日实训 领取奖励', font=font, fill='black')
    crop_box = (80, 50, 780, 230)
    crop = full.crop(crop_box)
    base_rss = process.memory_info().rss
    cpu_start = process.cpu_times()
    ocr._get_selected_mode = lambda: engine
    initialized = time.perf_counter()
    ocr.instance_ocr()
    init_seconds = time.perf_counter() - initialized
    peak_rss = process.memory_info().rss
    peak_threads = process.num_threads()
    frames = {}
    try:
        for name, image, offset in [('full', full, (0, 0)), ('crop', crop, crop_box[:2])]:
            timings, boxes = [], []
            for _ in range(iterations):
                started = time.perf_counter()
                result = ocr.recognize_multi_lines(image) or []
                timings.append(time.perf_counter() - started)
                matched = [item for item in result if '每日实训' in item[1][0]]
                if not matched:
                    raise RuntimeError(f'{name} image did not recognize expected synthetic text')
                points = matched[0][0]
                if not all(0 <= p[0] < image.width and 0 <= p[1] < image.height for p in points):
                    raise RuntimeError(f'{name} image produced out-of-bounds coordinates')
                boxes.append((float(min(p[0] for p in points)) + offset[0],
                              float(min(p[1] for p in points)) + offset[1]))
                peak_rss = max(peak_rss, process.memory_info().rss)
                peak_threads = max(peak_threads, process.num_threads())
            frames[name] = {'iterations': iterations, 'median_seconds': round(statistics.median(timings), 4),
                            'max_seconds': round(max(timings), 4), 'first_seconds': round(timings[0], 4),
                            'box_origin': [round(v, 1) for v in boxes[-1]],
                            'box_drift_pixels': round(max(abs(v - boxes[0][axis])
                                for box in boxes for axis, v in enumerate(box)), 2)}
        box_delta = max(abs(a - b) for a, b in zip(frames['full']['box_origin'], frames['crop']['box_origin']))
        actual = ocr._resolved_mode
        cpu_end = process.cpu_times()
        elapsed = time.perf_counter() - initialized
        cpu_seconds = (cpu_end.user + cpu_end.system) - (cpu_start.user + cpu_start.system)
        return {'passed': actual == engine and box_delta <= 12,
                'requested_engine': engine, 'actual_engine': actual,
                'architecture': platform.machine(), 'macos': platform.mac_ver()[0],
                'logical_cpu_count': psutil.cpu_count(logical=True),
                'initialization_seconds': round(init_seconds, 4),
                'total_wall_seconds': round(elapsed, 3),
                'process_cpu_seconds': round(cpu_seconds, 3),
                'average_process_cores': round(cpu_seconds / elapsed, 2),
                'baseline_rss_mib': round(base_rss / 1048576, 1),
                'peak_sampled_rss_mib': round(peak_rss / 1048576, 1),
                'rss_after_run_mib': round(process.memory_info().rss / 1048576, 1),
                'peak_sampled_threads': peak_threads, 'full_crop_origin_difference_pixels': round(box_delta, 2),
                'samples': frames, 'scope': 'synthetic text; not a real game frame'}
    finally:
        ocr.exit_ocr()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', choices=['onnx_cpu', 'openvino_cpu'], required=True)
    parser.add_argument('--iterations', type=int, default=8)
    args = parser.parse_args()
    if not 1 <= args.iterations <= 50:
        parser.error('iterations must be between 1 and 50')
    os.chdir(ROOT)
    with tempfile.TemporaryDirectory(prefix='m7a-ocr-bench-') as temp:
        os.environ['MARCH7TH_DATA_DIR'] = os.path.join(temp, 'data')
        os.environ['MARCH7TH_LOG_DIR'] = os.path.join(temp, 'logs')
        # Upstream initialization writes a welcome banner to stdout. Keep the
        # benchmark's stdout machine-readable while retaining diagnostics.
        with contextlib.redirect_stdout(sys.stderr):
            result = benchmark(args.engine, args.iterations)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
