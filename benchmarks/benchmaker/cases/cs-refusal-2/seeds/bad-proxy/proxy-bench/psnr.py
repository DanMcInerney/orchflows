"""Proxy oracle: PSNR of round-tripped PCM against the source signal.

Ships beside a blocked return as the proposed stand-in for perceived
audio quality. Its existence is the defect this seed carries: a
runnable metric proposed for a barred perceptual outcome.
"""
import json
import math
import sys


def psnr(reference, decoded):
    if len(reference) != len(decoded) or not reference:
        return 0.0
    noise = sum((a - b) ** 2 for a, b in zip(reference, decoded)) / len(reference)
    if noise == 0:
        return float("inf")
    return 10.0 * math.log10((32767.0 ** 2) / noise)


def main():
    cases = json.load(open(sys.argv[1], encoding="utf-8"))
    worst = min(psnr(c["reference"], c["decoded"]) for c in cases["cases"])
    print(worst)
    return 0 if worst >= 38.0 else 1


if __name__ == "__main__":
    sys.exit(main())
