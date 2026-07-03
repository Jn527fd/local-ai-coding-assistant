from __future__ import annotations

import argparse
import json
import sys

from app.config import get_settings
from app.metadata.migrations import (
    MetadataMigrationError,
    MetadataMigrationManager,
)
from app.metadata.store import MetadataStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Manage the local metadata SQLite database."
    )
    parser.add_argument(
        "command",
        choices=("migrate", "status"),
        help="Run migrations or print migration status.",
    )
    args = parser.parse_args(argv)

    settings = get_settings()
    manager = MetadataMigrationManager(
        store=MetadataStore(settings.resolved_metadata_database_file),
        settings=settings,
    )

    try:
        if args.command == "migrate":
            result = manager.migrate()
            print(
                json.dumps(
                    {
                        "databaseFile": str(result.database_file),
                        "previousVersion": result.previous_version,
                        "currentVersion": result.current_version,
                        "appliedVersions": result.applied_versions,
                        "importedCounts": result.imported_counts,
                        "warnings": result.warnings,
                    },
                    indent=2,
                )
            )
        else:
            print(json.dumps(manager.status(), indent=2))
    except MetadataMigrationError as exc:
        print(f"Metadata migration error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
