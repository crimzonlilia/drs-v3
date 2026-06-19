import os
from pathlib import Path

def main():
    root = Path(".")
    print("Searching for pnpm-lock.yaml...")
    found = False
    for path in root.glob("**/pnpm-lock.yaml"):
        if ".venv" not in path.parts and "node_modules" not in path.parts:
            print("Found:", path)
            found = True
    if not found:
         print("No pnpm-lock.yaml found (excluding .venv and node_modules).")

if __name__ == "__main__":
    main()
