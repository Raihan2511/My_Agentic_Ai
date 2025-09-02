import os, pathlib
from lxml import etree

class DTDRegistry:
    def __init__(self, base_dir: str | None = None):
        self.base = pathlib.Path(base_dir or os.getenv("DTD_DIR", "Backend/Resources/dtds")).resolve()
        self._cache: dict[str, etree.DTD] = {}

    def get(self, label: str) -> etree.DTD:
        if label in self._cache:
            return self._cache[label]
        path = self.base / f"{label}.dtd"
        if not path.exists():
            alt = next(self.base.glob(f"{label}*.dtd"), None)
            path = alt or path
        with open(path, "rb") as f:
            dtd = etree.DTD(f)
        self._cache[label] = dtd
        return dtd
