#!/usr/bin/env python
"""
Run the Prediction Market Arbitrage web server
"""

import os
import sys
import argparse
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from pm_arb.web_server import run_server


def main():
    parser = argparse.ArgumentParser(
        description="Start the Prediction Market Arbitrage web server"
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", type=int, default=5000, help="Port to bind to (default: 5000)"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument(
        "--db",
        default="pm_arb_demo.db",
        help="Path to database file (default: pm_arb_demo.db)",
    )

    args = parser.parse_args()

    # Set environment variable for database path
    os.environ["PM_ARB_DB"] = args.db

    # Run the server
    run_server(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
