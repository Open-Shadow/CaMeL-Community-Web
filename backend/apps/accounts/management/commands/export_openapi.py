import json
from pathlib import Path

from django.core.management.base import BaseCommand

from config.api import api


class Command(BaseCommand):
    help = "Export Django Ninja OpenAPI schema to a JSON file."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default="openapi.json",
            help="Output file path for the exported OpenAPI schema.",
        )
        parser.add_argument(
            "--path-prefix",
            default="/api/",
            help="Path prefix passed to NinjaAPI.get_openapi_schema().",
        )

    def handle(self, *args, **options):
        output = Path(options["output"]).expanduser()
        if not output.is_absolute():
            output = Path.cwd() / output

        output.parent.mkdir(parents=True, exist_ok=True)

        schema = api.get_openapi_schema(path_prefix=options["path_prefix"])
        output.write_text(
            json.dumps(schema, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        self.stdout.write(self.style.SUCCESS(f"OpenAPI schema exported to {output}"))
