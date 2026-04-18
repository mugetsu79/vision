from __future__ import annotations

import pathlib
import subprocess
import sys
import textwrap


def test_main_import_does_not_require_numpy() -> None:
    script = textwrap.dedent(
        """
        import builtins
        import pathlib
        import sys

        sys.path.insert(0, str(pathlib.Path.cwd() / "src"))
        real_import = builtins.__import__

        def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "numpy" or name.startswith("numpy."):
                raise ModuleNotFoundError("No module named 'numpy'")
            return real_import(name, globals, locals, fromlist, level)

        builtins.__import__ = guarded_import
        import argus.main
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=pathlib.Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_main_import_is_available_under_argus_package() -> None:
    script = textwrap.dedent(
        """
        import pathlib
        import sys

        sys.path.insert(0, str(pathlib.Path.cwd() / "src"))
        import argus.main
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=pathlib.Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
