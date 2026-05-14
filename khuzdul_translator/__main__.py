"""Allow `python -m khuzdul_translator`."""
from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
