from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "validation" / "start_detection_fixture.sh"
README = REPO_ROOT / "scripts" / "validation" / "README.md"


def test_detection_fixture_uses_ultralytics_sample_and_redacts_publish_url() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "ultralytics/assets/bus.jpg" in text
    assert "VEZOR_SMOKE_FIXTURE_PUBLISH_URL" in text
    assert "rtsp://***" in text
    assert "$VEZOR_SMOKE_FIXTURE_PUBLISH_URL" in text
    assert "ffmpeg" in text
    assert "VEZOR_SMOKE_PYTHON:-python3" in text
    assert "2> >(" in text
    assert "sed -E" in text or "perl -pe" in text
    assert "[Rr][Tt][Ss][Pp]://" in text
    assert "rtsp://" in text
    assert text.count('"$VEZOR_SMOKE_FIXTURE_PUBLISH_URL"') == 1
    assert text.rstrip().endswith('"$VEZOR_SMOKE_FIXTURE_PUBLISH_URL"')

    for line in text.splitlines():
        if "printf" in line or "echo" in line:
            assert "$VEZOR_SMOKE_FIXTURE_PUBLISH_URL" not in line

    assert "-g 10" in text
    assert "-keyint_min 10" in text
    assert "-sc_threshold 0" in text


def test_validation_readme_marks_fixture_publish_url_sensitive() -> None:
    text = README.read_text(encoding="utf-8")

    assert "`VEZOR_SMOKE_FIXTURE_PUBLISH_URL` is also local-only" in text
    assert "Never commit" in text


def test_detection_fixture_redacts_uppercase_rtsp_stderr_and_preserves_ffmpeg_status(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "bus.jpg"
    image_path.write_bytes(b"fake image")

    fake_python = tmp_path / "fake-python"
    fake_python.write_text(f"#!/usr/bin/env bash\nprintf '%s\\n' {str(image_path)!r}\n", encoding="utf-8")
    fake_python.chmod(0o755)

    ffmpeg_last_arg = tmp_path / "ffmpeg-last-arg.txt"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_ffmpeg = bin_dir / "ffmpeg"
    fake_ffmpeg.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "last=''",
                'for arg in "$@"; do',
                '  last="$arg"',
                "done",
                'printf "%s\\n" "$last" > "$FAKE_FFMPEG_LAST_ARG"',
                "printf 'ffmpeg output url: RTSP://alice:s3cr3t@example.local/path\\n' >&2",
                "exit 73",
                "",
            ]
        ),
        encoding="utf-8",
    )
    fake_ffmpeg.chmod(0o755)

    raw_publish_url = "RTSP://alice:s3cr3t@example.local/path"
    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}{os.pathsep}{env['PATH']}",
            "FAKE_FFMPEG_LAST_ARG": str(ffmpeg_last_arg),
            "VEZOR_SMOKE_FIXTURE_PUBLISH_URL": raw_publish_url,
            "VEZOR_SMOKE_PYTHON": str(fake_python),
        }
    )

    result = subprocess.run(
        [str(SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 73
    assert "rtsp://***" in result.stderr
    assert "alice" not in result.stderr
    assert "s3cr3t" not in result.stderr
    assert raw_publish_url not in result.stderr
    assert ffmpeg_last_arg.read_text(encoding="utf-8").strip() == raw_publish_url


def test_detection_fixture_tolerates_ultralytics_startup_stdout_noise(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "bus.jpg"
    image_path.write_bytes(b"fake image")

    fake_python = tmp_path / "fake-python"
    fake_python.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "printf '%s\\n' 'Ultralytics settings notice'",
                f"printf '%s\\n' {str(image_path)!r}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    fake_python.chmod(0o755)

    ffmpeg_input_arg = tmp_path / "ffmpeg-input-arg.txt"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_ffmpeg = bin_dir / "ffmpeg"
    fake_ffmpeg.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "previous=''",
                'for arg in "$@"; do',
                '  if [[ "$previous" == "-i" ]]; then',
                '    printf "%s\\n" "$arg" > "$FAKE_FFMPEG_INPUT_ARG"',
                "  fi",
                '  previous="$arg"',
                "done",
                "exit 73",
                "",
            ]
        ),
        encoding="utf-8",
    )
    fake_ffmpeg.chmod(0o755)

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}{os.pathsep}{env['PATH']}",
            "FAKE_FFMPEG_INPUT_ARG": str(ffmpeg_input_arg),
            "VEZOR_SMOKE_FIXTURE_PUBLISH_URL": "rtsp://example.local/path",
            "VEZOR_SMOKE_PYTHON": str(fake_python),
        }
    )

    result = subprocess.run(
        [str(SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 73
    assert ffmpeg_input_arg.read_text(encoding="utf-8").strip() == str(image_path)
