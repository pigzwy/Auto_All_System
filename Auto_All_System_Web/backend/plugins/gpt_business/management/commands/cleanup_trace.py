from __future__ import annotations

from django.core.management.base import BaseCommand

from ...storage import get_settings
from ...trace_cleanup import cleanup_trace_files, get_trace_cleanup_settings


class Command(BaseCommand):
    help = "Cleanup gpt_business trace files (logs/trace)."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="actually delete files")
        parser.add_argument("--max-age-days", type=int, default=None)
        parser.add_argument("--max-total-size-mb", type=int, default=None)
        parser.add_argument("--max-files", type=int, default=None)
        parser.add_argument("--min-keep-files", type=int, default=None)
        parser.add_argument("--pattern", type=str, default=None)

    def handle(self, *args, **options):
        settings = get_settings()
        overrides = {}
        if options.get("max_age_days") is not None:
            overrides["max_age_days"] = options["max_age_days"]
        if options.get("max_total_size_mb") is not None:
            overrides["max_total_size_mb"] = options["max_total_size_mb"]
        if options.get("max_files") is not None:
            overrides["max_files"] = options["max_files"]
        if options.get("min_keep_files") is not None:
            overrides["min_keep_files"] = options["min_keep_files"]
        if options.get("pattern"):
            overrides["pattern"] = options["pattern"]

        effective_settings = {**get_trace_cleanup_settings(settings), **overrides}
        result = cleanup_trace_files(
            settings,
            dry_run=not options.get("apply"),
            overrides=overrides,
        )

        self.stdout.write("trace cleanup settings:")
        for key in ["max_age_days", "max_total_size_mb", "max_files", "min_keep_files", "pattern"]:
            self.stdout.write(f"  - {key}: {effective_settings.get(key)}")

        self.stdout.write("trace cleanup result:")
        self.stdout.write(f"  - trace_dir: {result['trace_dir']}")
        self.stdout.write(f"  - dry_run: {result['dry_run']}")
        self.stdout.write(f"  - total_files: {result['total_files']}")
        self.stdout.write(f"  - kept_files: {result['kept_files']}")
        self.stdout.write(f"  - deleted_files: {result['deleted_files']}")
        self.stdout.write(f"  - freed_bytes: {result['freed_bytes']}")
