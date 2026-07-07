from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class _Token:
    indent: int
    content: str
    line_number: int


def load_yaml_mapping(path: Path, *, error_type: type[Exception]) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise error_type(f"unable to read {path}: {exc}") from exc

    data = _load_yaml(text, path, error_type=error_type)
    if data is None:
        return {}

    if not isinstance(data, dict):
        raise error_type(f"{path} must contain a top-level mapping")

    return data


def _load_yaml(
    text: str,
    config_path: Path,
    *,
    error_type: type[Exception],
) -> Any:
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:
        return _load_minimal_yaml(text, config_path, error_type=error_type)

    try:
        return yaml.safe_load(text)
    except Exception as exc:
        raise error_type(f"invalid YAML in {config_path}: {exc}") from exc


def _load_minimal_yaml(
    text: str,
    config_path: Path,
    *,
    error_type: type[Exception],
) -> Any:
    tokens = _tokenize(text, config_path, error_type=error_type)
    if not tokens:
        return {}

    parsed, next_index = _parse_block(
        tokens,
        start_index=0,
        indent=tokens[0].indent,
        config_path=config_path,
        error_type=error_type,
    )
    if next_index != len(tokens):
        token = tokens[next_index]
        _raise_parse_error(
            error_type,
            config_path,
            token.line_number,
            "unexpected trailing content",
        )

    return parsed


def _tokenize(
    text: str,
    config_path: Path,
    *,
    error_type: type[Exception],
) -> list[_Token]:
    tokens: list[_Token] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        stripped_right = raw_line.rstrip()
        if not stripped_right:
            continue

        stripped_left = stripped_right.lstrip(" ")
        if not stripped_left or stripped_left.startswith("#"):
            continue

        indent_text = stripped_right[: len(stripped_right) - len(stripped_left)]
        if "\t" in indent_text:
            _raise_parse_error(
                error_type,
                config_path,
                line_number,
                "tabs are not supported in YAML indentation",
            )

        tokens.append(
            _Token(
                indent=len(indent_text),
                content=stripped_left,
                line_number=line_number,
            )
        )

    return tokens


def _parse_block(
    tokens: list[_Token],
    *,
    start_index: int,
    indent: int,
    config_path: Path,
    error_type: type[Exception],
) -> tuple[Any, int]:
    token = tokens[start_index]
    if token.indent != indent:
        _raise_parse_error(
            error_type,
            config_path,
            token.line_number,
            f"unexpected indentation; expected {indent} spaces",
        )

    if token.content.startswith("- "):
        return _parse_sequence(
            tokens,
            start_index=start_index,
            indent=indent,
            config_path=config_path,
            error_type=error_type,
        )

    return _parse_mapping(
        tokens,
        start_index=start_index,
        indent=indent,
        config_path=config_path,
        error_type=error_type,
    )


def _parse_mapping(
    tokens: list[_Token],
    *,
    start_index: int,
    indent: int,
    config_path: Path,
    error_type: type[Exception],
) -> tuple[dict[str, Any], int]:
    result: dict[str, Any] = {}
    index = start_index

    while index < len(tokens):
        token = tokens[index]
        if token.indent < indent:
            break

        if token.indent > indent:
            _raise_parse_error(
                error_type,
                config_path,
                token.line_number,
                "unexpected indentation inside mapping",
            )

        if token.content.startswith("- "):
            break

        if ":" not in token.content:
            _raise_parse_error(
                error_type,
                config_path,
                token.line_number,
                "expected a key/value mapping entry",
            )

        key, raw_value = token.content.split(":", 1)
        key = key.strip()
        value = raw_value.strip()
        if not key:
            _raise_parse_error(
                error_type,
                config_path,
                token.line_number,
                "mapping keys cannot be empty",
            )

        index += 1
        if value:
            result[key] = _parse_scalar(value)
            continue

        if index < len(tokens) and tokens[index].indent > indent:
            nested_indent = tokens[index].indent
            nested_value, index = _parse_block(
                tokens,
                start_index=index,
                indent=nested_indent,
                config_path=config_path,
                error_type=error_type,
            )
            result[key] = nested_value
            continue

        result[key] = {}

    return result, index


def _parse_sequence(
    tokens: list[_Token],
    *,
    start_index: int,
    indent: int,
    config_path: Path,
    error_type: type[Exception],
) -> tuple[list[Any], int]:
    result: list[Any] = []
    index = start_index

    while index < len(tokens):
        token = tokens[index]
        if token.indent < indent:
            break

        if token.indent > indent:
            _raise_parse_error(
                error_type,
                config_path,
                token.line_number,
                "unexpected indentation inside sequence",
            )

        if not token.content.startswith("- "):
            break

        item_content = token.content[2:].strip()
        if not item_content:
            index += 1
            if index >= len(tokens) or tokens[index].indent <= indent:
                _raise_parse_error(
                    error_type,
                    config_path,
                    token.line_number,
                    "sequence item is missing a value",
                )

            nested_value, index = _parse_block(
                tokens,
                start_index=index,
                indent=tokens[index].indent,
                config_path=config_path,
                error_type=error_type,
            )
            result.append(nested_value)
            continue

        if ":" in item_content:
            item_value, index = _parse_mapping_sequence_item(
                tokens,
                start_index=index,
                indent=indent,
                item_content=item_content,
                config_path=config_path,
                error_type=error_type,
            )
            result.append(item_value)
            continue

        result.append(_parse_scalar(item_content))
        index += 1

    return result, index


def _parse_mapping_sequence_item(
    tokens: list[_Token],
    *,
    start_index: int,
    indent: int,
    item_content: str,
    config_path: Path,
    error_type: type[Exception],
) -> tuple[dict[str, Any], int]:
    token = tokens[start_index]
    key, raw_value = item_content.split(":", 1)
    key = key.strip()
    value = raw_value.strip()
    if not key:
        _raise_parse_error(
            error_type,
            config_path,
            token.line_number,
            "mapping keys cannot be empty",
        )

    item: dict[str, Any] = {}
    index = start_index + 1

    if value:
        item[key] = _parse_scalar(value)
    elif index < len(tokens) and tokens[index].indent > indent:
        nested_value, index = _parse_block(
            tokens,
            start_index=index,
            indent=tokens[index].indent,
            config_path=config_path,
            error_type=error_type,
        )
        item[key] = nested_value
    else:
        item[key] = {}

    if index < len(tokens) and tokens[index].indent > indent:
        continuation, index = _parse_mapping(
            tokens,
            start_index=index,
            indent=tokens[index].indent,
            config_path=config_path,
            error_type=error_type,
        )
        item.update(continuation)

    return item, index


def _parse_scalar(raw_value: str) -> Any:
    if raw_value in {"true", "false"}:
        return raw_value == "true"

    if raw_value.isdigit():
        return int(raw_value)

    if len(raw_value) >= 2 and raw_value[0] == raw_value[-1] and raw_value[0] in {'"', "'"}:
        return raw_value[1:-1]

    return raw_value


def _raise_parse_error(
    error_type: type[Exception],
    config_path: Path,
    line_number: int,
    message: str,
) -> None:
    raise error_type(f"invalid YAML in {config_path}:{line_number}: {message}")