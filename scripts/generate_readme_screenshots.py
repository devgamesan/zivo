#!/usr/bin/env python3
"""Generate README screenshots."""

from __future__ import annotations

import asyncio

from peneo.readme_screenshots import generate_readme_screenshots


def main() -> None:
    asyncio.run(generate_readme_screenshots())


if __name__ == "__main__":
    main()
