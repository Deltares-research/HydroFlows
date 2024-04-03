import re
from typing import List

from pydantic import BaseModel, Field, validator


class ParamsHydromt(BaseModel):
    data_libs: List[str] = Field(default_factory=list)

    @validator("data_libs", pre=True)
    def split(cls, v: object) -> object:
        """Split comma and space seperated string to list."""
        if isinstance(v, str):
            v = v.strip()
            # split by comma but not inside quotes
            regex = r"[^,\s\"']+|\"([^\"]*)\"|'([^']*)'"
            if not any(re.findall(regex, v)):  # no commas, split by space
                # split by space but not inside quotes
                regex = r"[^\s\"']+|\"([^\"]*)\"|'([^']*)'"
            vlist = [
                m.group(1) or m.group(2) or m.group(0)
                for m in re.finditer(regex, v)
            ]
            # strip whitespace and quotes from values
            return [v.strip("'\" ") for v in vlist]
        return v
