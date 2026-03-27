#!/usr/bin/env python3
"""Profile the autonomous allocation routine with cProfile.

Examples:
    python profile_autonomous_allocation.py --semester 5
    python profile_autonomous_allocation.py --semester 5 --no-dry-run --dump stats.prof
    python profile_autonomous_allocation.py --semester 5 --sort tottime --limit 80
"""

from __future__ import annotations

import argparse
import cProfile
import json
import pstats
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.config.database import get_db_session
from src.services.optimized_autonomous_allocation_service import (
    OptimizedAutonomousAllocationService,  # noqa: E402
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Profile the partial autonomous allocation routine with cProfile."
    )
    parser.add_argument(
        "--semester",
        type=int,
        required=True,
        help="Semester ID to profile.",
    )
    parser.add_argument(
        "--no-dry-run",
        action="store_true",
        help="Execute real writes/commits instead of profiling in dry-run mode.",
    )
    parser.add_argument(
        "--sort",
        default="cumtime",
        choices=["cumtime", "tottime", "calls", "ncalls"],
        help="Primary pstats sort key.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=60,
        help="Number of rows to print from pstats output.",
    )
    parser.add_argument(
        "--dump",
        type=str,
        help="Optional output path for the raw .prof file (for snakeviz or other tools).",
    )
    parser.add_argument(
        "--callers",
        action="store_true",
        help="Print caller relationships for the top functions after the main stats.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    profiler = cProfile.Profile()
    with get_db_session() as session:
        service = OptimizedAutonomousAllocationService(session)
        profiler.enable()
        result = service.execute_autonomous_allocation_partial(
            args.semester,
            dry_run=not args.no_dry_run,
        )
        profiler.disable()

    if args.dump:
        profiler.dump_stats(args.dump)
        print(f"Saved raw profile to {args.dump}")

    print("Allocation result summary:")
    printable = {
        "success": result.get("success"),
        "semester_id": result.get("semester_id"),
        "mode": result.get("mode"),
        "total_demands_initial": result.get("total_demands_initial"),
        "allocations_completed": result.get("allocations_completed"),
        "block_groups_processed": result.get("block_groups_processed"),
        "block_groups_allocated": result.get("block_groups_allocated"),
        "demands_with_split_rooms": result.get("demands_with_split_rooms"),
        "conflicts_found": result.get("conflicts_found"),
        "execution_time": result.get("execution_time"),
        "performance": result.get("performance", {}),
    }
    print(json.dumps(printable, indent=2, ensure_ascii=False))
    print()
    print("cProfile results:")

    stats = pstats.Stats(profiler).strip_dirs().sort_stats(args.sort)
    stats.print_stats(args.limit)

    if args.callers:
        print("\nCallers:")
        stats.print_callers(args.limit)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())