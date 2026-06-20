import json
import os
from logging import error
from dotenv import load_dotenv
from typing import Any, TypeVar, cast

type DescriptorOrPath = int | str | bytes | os.PathLike[str] | os.PathLike[bytes]

T = TypeVar("T", default=str)

class ScopedConfigLoader():
    def __init__(self, scope: str, loader: "ConfigLoader"):
        self._scope = scope
        self._loader = loader
    
    def get_attribute(self, key: str, default: T | None = None) -> T | None:
        new_key = f"{self._scope}.{key}"
        return self._loader.get_attribute(new_key, default)
    
    def set_attribute(self, key: str, val: Any) -> None:
        new_key = f"{self._scope}.{key}"
        self._loader.set_attribute(new_key, val)

    def set(self, key: str, value: Any) -> None:
        new_key = f"{self._scope}.{key}"
        self._loader.set(new_key, value)

    def get(self, key: str, default: T | None = None) -> T | None:
        new_key = f"{self._scope}.{key}"
        return self._loader.get(new_key, default)
    
    def get_value(self, key: str) -> Any:
        result = self.get(key, None)
        if result is None:
            raise RuntimeError("Unexpected null value in config")
        return result
    
    def scope(self, key: str):
        new_scope = f"{self._scope}.{key}"
        return self._loader.scope(new_scope)

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
        keys = key.split('.')
        if len(keys) == 1:
            if key in self._config:
                return cast(T, self._config[key])
            else:
                return default
        current_val = self._config
        for k in keys:
            current_val = current_val.get(k, None)
            if current_val is None:
                return None
        return cast(T, current_val)
    
    def get_value(self, key: str) -> Any:
        """
        Retrieves a value from config, raises a RuntimeError if the value doesn't exist
        """
        result = self.get(key, None)
        if result is None:
            raise RuntimeError("Unexpected null value in config")
        return result
    
    def scope(self, key: str) -> ScopedConfigLoader:
        return ScopedConfigLoader(key, self)
    
    def keys_missing(self, keys: list[str]) -> list[str]:
        if keys is None:
            return []
        return [k for k in keys if self.get(k) is None]

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
    
