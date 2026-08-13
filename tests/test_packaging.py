from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_static_ui_is_included_once_via_the_app_package() -> None:
    pyproject = (REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert 'packages = ["app"]' in pyproject
    assert "[tool.hatch.build.targets.wheel.force-include]" not in pyproject
    assert (REPOSITORY_ROOT / "app/static/index.html").is_file()
