import os
import platform
import shutil
import re

DEFAULT_ARROW_INDEX_NAME = "__index_level_0__"


def mark_as_hidden(path):
    is_windows = platform.system() == "Windows"
    if is_windows:
        mark_as_hidden_command = f"attrib +h {path}"
        os.system(mark_as_hidden_command)


def delete_folder_tree(path):
    try:
        shutil.rmtree(path)
    except FileNotFoundError:
        pass
    except PermissionError as e:
        # Force delete stubborn open file on Windows
        os.system(f'cmd /k "del /f /q /a {e.filename}"')
        # Try to delete folder with stubborn file deleted
        delete_folder_tree(path)


def expand_home_dir_modifier(path):
    return os.path.expanduser(path)


def filter_items_like_pattern(items, *, like):
    pattern = _sql_str_pattern_to_regexp(like)
    results = _filter(items, like=pattern)
    return results


def _sql_str_pattern_to_regexp(pattern):
    if pattern[0] != "%":
        pattern = "^" + pattern
    if pattern[-1] != "%":
        pattern = pattern + "$"
    pattern = pattern.replace("?", ".")
    pattern = pattern.replace("%", ".*")

    pattern = pattern.lower()
    return re.compile(pattern)


def _filter(items, *, like):
    str_lower_list = [item.lower() for item in items]
    filtered_list = set(filter(like.search, str_lower_list))
    results = [item for item in items if item.lower() in filtered_list]
    return results


def check_if_arg_errors_is_valid(errors):
    if errors not in {"raise", "ignore"}:
        raise ValueError("'errors' must be either 'raise' or 'ignore'")


def check_if_arg_warnings_is_valid(warnings):
    if warnings not in {"warn", "ignore"}:
        raise ValueError("'warnings' must be either 'warn' or 'ignore'")
