#!/usr/bin/env python3
"""
Startup performance diagnostic script for SilAuto.
Run this to identify what's causing slow startup times.
"""

import asyncio
import time
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.constants import PARATEXT_PROJECTS_DIR, EXPERIMENTS_DIR, SCRIPTURE_DIR
from app.routers.projects import scan_projects
from app.routers.scriptures import scan_scriptures
from app.routers.translations import scan_translations


async def time_operation(name, operation):
    """Time an async operation and print results."""
    print(f"\n🔄 Starting {name}...")
    start_time = time.time()
    try:
        if asyncio.iscoroutinefunction(operation):
            result = await operation()
        else:
            result = await asyncio.to_thread(operation)
        end_time = time.time()
        duration = end_time - start_time
        print(f"✅ {name} completed in {duration:.2f} seconds")
        return duration, result
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"❌ {name} failed after {duration:.2f} seconds: {e}")
        return duration, None


def check_directories():
    """Check if data directories exist and report their sizes."""
    print("📁 Checking data directories:")

    dirs_to_check = [
        ("Projects", PARATEXT_PROJECTS_DIR),
        ("Experiments", EXPERIMENTS_DIR),
        ("Scripture", SCRIPTURE_DIR),
    ]

    for name, path in dirs_to_check:
        if path.exists():
            if path.is_dir():
                try:
                    # Count files
                    file_count = sum(1 for _ in path.rglob("*") if _.is_file())
                    print(f"  ✅ {name}: {path} ({file_count} files)")
                except Exception as e:
                    print(f"  ⚠️  {name}: {path} (error counting files: {e})")
            else:
                print(f"  ❌ {name}: {path} (not a directory)")
        else:
            print(f"  ❌ {name}: {path} (does not exist)")


async def main():
    """Run startup performance diagnostics."""
    print("🚀 SilAuto Startup Performance Diagnostics")
    print("=" * 50)

    # Check directories first
    check_directories()

    print("\n⏱️  Timing individual operations:")

    total_start = time.time()

    # Time each operation
    times = {}

    times["projects"], _ = await time_operation("Project scanning", scan_projects)
    times["translations"], _ = await time_operation(
        "Translation scanning", scan_translations
    )
    times["scriptures"], _ = await time_operation("Scripture scanning", scan_scriptures)

    total_time = time.time() - total_start

    print("\n📊 Summary:")
    print(f"  Total time: {total_time:.2f} seconds")
    print(
        f"  Project scanning: {times.get('projects', 0):.2f}s ({times.get('projects', 0) / total_time * 100:.1f}%)"
    )
    print(
        f"  Translation scanning: {times.get('translations', 0):.2f}s ({times.get('translations', 0) / total_time * 100:.1f}%)"
    )
    print(
        f"  Scripture scanning: {times.get('scriptures', 0):.2f}s ({times.get('scriptures', 0) / total_time * 100:.1f}%)"
    )

    print("\n💡 Recommendations:")
    if times.get("scriptures", 0) > 10:
        print("  - Scripture scanning is slow. Consider:")
        print(
            "    * Setting ENABLE_SCRIPTURE_CACHE=false if you don't need scripture stats"
        )
        print("    * Reducing MAX_CONCURRENT_FILE_PROCESSING")
        print("    * Setting SKIP_HEAVY_OPERATIONS_ON_STARTUP=true")

    if times.get("translations", 0) > 5:
        print("  - Translation scanning is slow. Consider:")
        print(
            "    * Setting ENABLE_TRANSLATION_CACHE=false if you don't need translations"
        )
        print("    * Checking if EXPERIMENTS_DIR has too many nested directories")

    if total_time > 30:
        print("  - Overall startup is very slow. Consider:")
        print("    * Setting SKIP_HEAVY_OPERATIONS_ON_STARTUP=true for development")
        print("    * Using lazy loading with LAZY_LOAD_CACHES=true")

    print("\n🔧 Configuration options (set in .env file):")
    print("   SKIP_HEAVY_OPERATIONS_ON_STARTUP=true  # Skip all scanning on startup")
    print("   MAX_CONCURRENT_FILE_PROCESSING=3       # Reduce concurrent processing")
    print("   ENABLE_SCRIPTURE_CACHE=false           # Disable scripture scanning")
    print("   ENABLE_TRANSLATION_CACHE=false         # Disable translation scanning")


if __name__ == "__main__":
    asyncio.run(main())
