from __future__ import annotations
import json, os, shutil, sys, tempfile
from pathlib import Path
from urllib.parse import urlparse
REQUIRED_FIELDS = ("name", "icon", "type", "path", "category")
VALID_TYPES = {"app", "folder", "website"}

def app_directory() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

def bundled_file(filename: str) -> Path:
    return Path(getattr(sys, "_MEIPASS", app_directory())) / filename

def config_path() -> Path:
    target = app_directory() / "apps.json"
    if target.is_file():
        return target
    bundled = bundled_file("apps.json")
    if bundled.is_file():
        try:
            shutil.copy2(bundled, target)
            return target
        except OSError as exc:
            raise ConfigError('Konfigurasi tidak dapat disimpan di folder ini. Pindahkan launcher ke folder yang bisa Anda tulis.') from exc
    return target

class ConfigError(ValueError):
    pass

def load_shortcuts() -> list[dict]:
    path = config_path()
    if not path.is_file():
        raise ConfigError(
            f"File apps.json tidak ditemukan.\n\nLokasi yang dicari:\n{path}"
        )

    try:
        with path.open("r", encoding="utf-8-sig") as file:
            data = json.load(file)
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"JSON tidak valid pada baris {exc.lineno}, kolom {exc.colno}.\n"
            f"{exc.msg}"
        ) from exc
    except OSError as exc:
        raise ConfigError(f"apps.json tidak dapat dibaca:\n{exc}") from exc

    if not isinstance(data, list):
        raise ConfigError("apps.json harus berisi array JSON [ ... ].")

    result, errors = [], []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            errors.append(f"Item {index} harus berupa objek.")
            continue
        missing = [f for f in REQUIRED_FIELDS if f not in item]
        if missing:
            errors.append(f"Item {index}: field hilang: {', '.join(missing)}")
            continue
        if not all(isinstance(item[f], str) for f in REQUIRED_FIELDS):
            errors.append(f"Item {index}: semua field wajib berupa teks.")
            continue

        entry = dict(item)
        entry.update({f: item[f].strip() for f in REQUIRED_FIELDS})
        if not isinstance(entry.get("icon_path", ""), str):
            errors.append(f"Item {index}: icon_path harus berupa teks.")
            continue
        if not all(entry[field] for field in REQUIRED_FIELDS):
            errors.append(f"Item {index}: field wajib tidak boleh kosong.")
            continue
        if entry["type"] not in VALID_TYPES:
            errors.append(f"Item {index}: type harus app, folder, atau website.")
            continue

        if "args" in item:
            if not isinstance(item["args"], list) or not all(
                isinstance(a, str) for a in item["args"]
            ):
                errors.append(f"Item {index}: args harus berupa daftar teks.")
                continue
            entry["args"] = item["args"]

        if entry["type"] == "website":
            parsed = urlparse(entry["path"])
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                errors.append(f"Item {index}: URL website tidak valid.")
                continue
        result.append(entry)

    if errors:
        raise ConfigError("Ada masalah pada apps.json:\n\n" + "\n".join(errors[:12]))
    from keybindings import validate_bindings
    try:
        return validate_bindings(result)
    except ValueError as exc:
        raise ConfigError(str(exc)) from exc

def expand_path(value: str) -> str:
    return os.path.expandvars(os.path.expanduser(value.strip().strip('"')))

def resolve_executable(value: str) -> str | None:
    expanded = expand_path(value)
    candidate = Path(expanded)
    if not candidate.is_absolute():
        candidate = app_directory() / candidate
    if candidate.is_file():
        return str(candidate.resolve())
    if not any(sep in expanded for sep in ("/", "\\")):
        return shutil.which(expanded)
    return None

def resolve_local_path(value: str) -> Path:
    path = Path(expand_path(value))
    return path if path.is_absolute() else app_directory() / path

def save_items(items):
    from keybindings import validate_bindings
    items=validate_bindings([dict(item) for item in items])
    target = config_path()
    temp = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=target.parent,
                                         suffix='.tmp', delete=False) as file:
            temp = Path(file.name)
            json.dump(items, file, ensure_ascii=False, indent=2)
            file.flush()
            os.fsync(file.fileno())
        if target.exists():
            shutil.copy2(target, target.with_suffix('.json.bak'))
        os.replace(temp, target)
    finally:
        if temp and temp.exists():
            temp.unlink()

def load_settings():
    target = app_directory() / 'settings.json'
    if not target.exists():
        return {'global_hotkey':'Alt+Z','autostart':False}
    from keybindings import normalize_key
    try:
        value=json.loads(target.read_text(encoding='utf-8-sig'))
        if not isinstance(value,dict):raise ValueError('Format pengaturan tidak valid.')
        return {'global_hotkey':normalize_key(value.get('global_hotkey','Alt+Z'),global_key=True),
                'autostart':value.get('autostart') is True}
    except (OSError,ValueError) as exc:
        raise ConfigError('Pengaturan launcher tidak valid: '+str(exc)) from exc

def save_settings(values):
    from keybindings import normalize_key
    value={'global_hotkey':normalize_key(values['global_hotkey'],global_key=True),
           'autostart':bool(values.get('autostart',False))}
    target = app_directory() / 'settings.json'
    temporary = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=target.parent,
                                         suffix='.tmp', delete=False) as file:
            temporary = Path(file.name)
            json.dump(value, file, indent=2)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, target)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()

