from __future__ import annotations

import argparse
from pathlib import Path

import run_proxy_eval


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True, help="Directory for fresh evaluation outputs")
    args = parser.parse_args()

    run_proxy_eval.OUTPUT_DIR = Path(args.output_dir)
    run_proxy_eval.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_proxy_eval.main()


if __name__ == "__main__":
    main()
