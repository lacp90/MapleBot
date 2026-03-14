"""
MapleBot - Config Loader
Loads settings from config.yaml with sensible defaults.
"""

import os
import yaml


_config = None


def load_config(path="config.yaml"):
    """Load configuration from YAML file."""
    global _config
    if _config is not None:
        return _config

    # Try project root first, then relative to this file
    if not os.path.exists(path):
        alt = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
        if os.path.exists(alt):
            path = alt

    with open(path, "r") as f:
        _config = yaml.safe_load(f)

    return _config


def get(section, key=None, default=None):
    """Get a config value. Usage: get('keys', 'attack') or get('thresholds')."""
    cfg = load_config()
    if cfg is None:
        return default
    val = cfg.get(section, default)
    if key is not None and isinstance(val, dict):
        return val.get(key, default)
    return val


def reload():
    """Force reload config from disk."""
    global _config
    _config = None
    return load_config()
