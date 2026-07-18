from __future__ import annotations

from io import StringIO

import pytest

from executor import ExecutorError, stow_package
from packages import PackageMetadata
from ui import UI


def test_stow_package_creates_file_links_without_stow(tmp_path) -> None:
    dotfiles_root = tmp_path / "dotfiles"
    package_dir = dotfiles_root / "zsh"
    home_dir = tmp_path / "home"
    source_file = package_dir / ".zshrc"

    source_file.parent.mkdir(parents=True)
    source_file.write_text("export ZDOTDIR=$HOME/.config/zsh\n", encoding="utf-8")
    home_dir.mkdir()

    stow_package(
        _package_metadata("zsh", home_dir),
        _config(home_dir),
        _ui(),
        dotfiles_root=dotfiles_root,
    )

    target_file = home_dir / ".zshrc"
    assert target_file.is_symlink()
    assert target_file.resolve() == source_file.resolve()


def test_stow_package_removes_stale_owned_links_and_creates_directory_links(tmp_path) -> None:
    dotfiles_root = tmp_path / "dotfiles"
    package_dir = dotfiles_root / "nvim"
    home_dir = tmp_path / "home"
    source_dir = package_dir / ".config" / "nvim.link"
    old_source_file = package_dir / ".config" / "nvim" / "init.lua"

    (source_dir / "lua").mkdir(parents=True)
    (source_dir / "init.lua").write_text("vim.opt.number = true\n", encoding="utf-8")
    home_target = home_dir / ".config" / "nvim"
    home_target.mkdir(parents=True)
    (home_target / "init.lua").symlink_to(old_source_file)

    stow_package(
        _package_metadata("nvim", home_dir),
        _config(home_dir),
        _ui(),
        dotfiles_root=dotfiles_root,
    )

    assert home_target.is_symlink()
    assert home_target.resolve() == source_dir.resolve()
    assert not (home_dir / ".config" / "nvim" / "init.lua").is_symlink()


def test_stow_package_fails_on_existing_foreign_target(tmp_path) -> None:
    dotfiles_root = tmp_path / "dotfiles"
    package_dir = dotfiles_root / "zsh"
    home_dir = tmp_path / "home"
    source_file = package_dir / ".zshrc"

    source_file.parent.mkdir(parents=True)
    source_file.write_text("export ZDOTDIR=$HOME/.config/zsh\n", encoding="utf-8")
    home_dir.mkdir()
    target_file = home_dir / ".zshrc"
    target_file.write_text("existing\n", encoding="utf-8")

    with pytest.raises(ExecutorError, match="target already exists"):
        stow_package(
            _package_metadata("zsh", home_dir),
            _config(home_dir),
            _ui(),
            dotfiles_root=dotfiles_root,
        )

    assert target_file.read_text(encoding="utf-8") == "existing\n"


def test_stow_package_dry_run_does_not_modify_target(tmp_path) -> None:
    dotfiles_root = tmp_path / "dotfiles"
    package_dir = dotfiles_root / "bat"
    home_dir = tmp_path / "home"
    source_file = package_dir / ".config" / "bat" / "config"

    source_file.parent.mkdir(parents=True)
    source_file.write_text("--theme=ansi\n", encoding="utf-8")
    home_dir.mkdir()

    stdout = StringIO()
    stow_package(
        _package_metadata("bat", home_dir),
        _config(home_dir),
        _ui(stdout=stdout, verbose=True),
        dotfiles_root=dotfiles_root,
        dry_run=True,
    )

    assert not (home_dir / ".config" / "bat" / "config").exists()
    assert "Link reconciliation preview complete" in stdout.getvalue()


def _package_metadata(name: str, target_root) -> PackageMetadata:
    return PackageMetadata(
        directory_name=name,
        name=name,
        description=f"{name} package",
        required_tools=(),
        stow_enabled=True,
        stow_target=str(target_root),
    )


def _config(target_root) -> dict[str, dict[str, str]]:
    return {
        "stow": {
            "directory": ".",
            "target": str(target_root),
        }
    }


def _ui(*, stdout=None, verbose: bool = False) -> UI:
    return UI(verbose=verbose, color=False, stdout=stdout or StringIO(), stderr=StringIO())