"""Configure Google-only local Auth from private .env, then start the local stack."""

import argparse
import os
import re
import subprocess
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--restart", action="store_true")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    enabled = bool(
        os.getenv("GOOGLE_CLIENT_ID", "").strip() and os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
    )
    path = ROOT / "supabase/config.toml"
    config = path.read_text()
    config = re.sub(
        r"(\[auth\.email\]\n(?:#[^\n]*\n)*)enable_signup = (?:true|false)",
        r"\1enable_signup = false",
        config,
    )
    config = re.sub(
        r"(\[auth\.external\.google\]\n)enabled = (?:true|false)",
        lambda m: m[1] + "enabled = " + str(enabled).lower(),
        config,
    )
    path.write_text(config)
    print(
        "Google OAuth: " + ("configured" if enabled else "credentials required; provider disabled"),
        flush=True,
    )
    cli = ["npx", "--yes", "supabase@2.122.0"]
    if args.restart:
        subprocess.run(cli + ["stop"], cwd=ROOT, check=True)
    subprocess.run(cli + ["start"], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
