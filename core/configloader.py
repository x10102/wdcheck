import json
import os
from logging import info, error
from dotenv import load_dotenv
from typing import Any, TypeVar, cast

type DescriptorOrPath = int | str | bytes | os.PathLike[str] | os.PathLike[bytes]

T = TypeVar("T", default=str)

class ConfigLoader():
    def __init__(self) -> None:
        self._attribs: dict[str, Any] = {}
        self._config: dict[str, Any] = {}

    def set_attribute(self, key: str, val: Any) -> None:
        self._attribs[key] = val

    def get_attribute(self, key: str, default: T | None = None) -> T | None:
        if key in self._attribs:
            return cast(T, self._attribs[key])
        else:
            return default
        
    def set(self, key: str, value: Any) -> None:
        self._config[key] = value

    def get(self, key: str, default: T | None = None) -> T | None:
        if key in self._config:
            return cast(T, self._config[key])
        else:
            return default
        
    def load_from_env(self) -> bool:
        load_result = load_dotenv(override=True, verbose=True, encoding='utf-8')
        self._config.update(os.environ)
        return load_result

    def load_from_json(self, path: DescriptorOrPath = 'config.json') -> bool:
        try:
            with open(path, 'r', encoding='utf-8') as configfile:
                self._config.update(json.load(configfile))
        except (OSError, IOError) as e:
            error(f"Failed to load config: I/O error ({str(e)})")
            return False
        except json.JSONDecodeError as e:
            error(f"Failed to load config: JSON decode error ({str(e)})")
            return False
        return True