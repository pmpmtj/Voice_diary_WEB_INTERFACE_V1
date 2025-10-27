#!/usr/bin/env python
import os
import sys
from pathlib import Path


# Ensure repository root is on sys.path so `common` is importable
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT.parent))


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "diary_site.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()


