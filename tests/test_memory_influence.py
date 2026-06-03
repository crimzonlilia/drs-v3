from pathlib import Path

p = Path("memory_store/corrections/demo.yaml")
if p.exists():
    p.unlink()