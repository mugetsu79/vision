#!/usr/bin/env bash

set -euo pipefail

failures=0
installer_mode=0
json_mode=0

for arg in "$@"; do
  case "$arg" in
    --installer)
      installer_mode=1
      ;;
    --json)
      json_mode=1
      ;;
    -h|--help)
      cat <<'USAGE'
Usage: scripts/jetson-preflight.sh [--installer] [--json]

Checks Jetson runtime prerequisites for Vezor edge operation.

Options:
  --installer   Include installer-specific port and device checks.
  --json        Emit a compact JSON summary after the normal check output.
USAGE
      exit 0
      ;;
    *)
      printf 'Unknown option: %s\n' "$arg" >&2
      exit 2
      ;;
  esac
done

pass() {
  printf 'PASS %s\n' "$1"
}

fail() {
  printf 'FAIL %s\n' "$1" >&2
  failures=$((failures + 1))
}

check_command() {
  if command -v "$1" >/dev/null 2>&1; then
    pass "command available: $1"
  else
    fail "missing command: $1"
  fi
}

check_file_contains() {
  local file="$1"
  local pattern="$2"
  local description="$3"

  if [[ -f "$file" ]] && grep -Eq "$pattern" "$file"; then
    pass "$description"
  else
    fail "$description"
  fi
}

check_command_output() {
  local description="$1"
  local pattern="$2"
  shift 2

  if "$@" 2>/dev/null | grep -Eq "$pattern"; then
    pass "$description"
  else
    fail "$description"
  fi
}

check_gst_element() {
  local element="$1"
  local description="$2"

  if gst-inspect-1.0 "$element" >/dev/null 2>&1; then
    pass "$description"
  else
    fail "$description"
  fi
}

check_port_available() {
  local port="$1"

  if command -v ss >/dev/null 2>&1 && ss -ltn "( sport = :$port )" | grep -q ":$port"; then
    fail "installer port $port is already in use"
  else
    pass "installer port $port is available"
  fi
}

check_udp_port_available() {
  local port="$1"

  if command -v ss >/dev/null 2>&1 && ss -lun "( sport = :$port )" | grep -q ":$port"; then
    fail "installer UDP port $port is already in use"
  else
    pass "installer UDP port $port is available"
  fi
}

if [[ "$(uname -m)" == "aarch64" ]]; then
  pass "Jetson architecture is arm64"
else
  fail "Jetson architecture must be aarch64"
fi

check_command docker
check_command gst-inspect-1.0
check_command ffmpeg
check_command ffprobe

if command -v gst-inspect-1.0 >/dev/null 2>&1; then
  check_gst_element rtspsrc "GStreamer RTSP source element is available"
  check_gst_element rtph264depay "GStreamer H264 RTP depay element is available"
  check_gst_element h264parse "GStreamer H264 parser element is available"
  check_gst_element avdec_h264 "GStreamer software H264 decoder is available"
  check_gst_element videoconvert "GStreamer video conversion element is available"
  check_gst_element appsink "GStreamer appsink element is available"
fi

if command -v dpkg-query >/dev/null 2>&1; then
  if dpkg-query -W -f='${Version}' nvidia-jetpack >/dev/null 2>&1; then
    check_command_output "JetPack 6.2.x metapackage is installed" '^6\.2' dpkg-query -W -f='${Version}' nvidia-jetpack
  else
    check_command_output "Jetson Linux 36.4/36.5 base is installed" '^36\.[45]' dpkg-query -W -f='${Version}' nvidia-l4t-core
  fi
  if dpkg-query -W -f='${Version}' libnvinfer10 >/dev/null 2>&1; then
    check_command_output "TensorRT 10.x runtime is installed" '^10\.' dpkg-query -W -f='${Version}' libnvinfer10
  elif dpkg-query -W -f='${Version}' tensorrt-libs >/dev/null 2>&1; then
    check_command_output "TensorRT 10.x runtime is installed" '^10\.' dpkg-query -W -f='${Version}' tensorrt-libs
  else
    fail "TensorRT 10.x runtime package libnvinfer10 or tensorrt-libs is missing"
  fi
  if dpkg-query -W -f='${Version}' nvidia-container-toolkit >/dev/null 2>&1; then
    pass "nvidia-container-toolkit package is installed"
  else
    fail "nvidia-container-toolkit package is missing"
  fi
else
  check_file_contains "/etc/nv_tegra_release" 'R36' "JetPack 6.x L4T release file is present"
fi

if command -v nvcc >/dev/null 2>&1; then
  check_command_output "CUDA 12.6 toolchain is installed" 'release 12\.6' nvcc --version
elif command -v dpkg-query >/dev/null 2>&1 && dpkg-query -W -f='${Version}' cuda-runtime-12-6 >/dev/null 2>&1; then
  pass "CUDA 12.6 runtime package is installed"
else
  check_file_contains "/usr/local/cuda/version.json" '"cuda": *"12\.6' "CUDA 12.6 runtime metadata is present"
fi

if [[ -e /dev/nvhost-nvdec ]] || gst-inspect-1.0 nvv4l2decoder >/dev/null 2>&1; then
  pass "NVDEC decode path is available"
else
  fail "NVDEC decode path is not available"
fi

if [[ -e /dev/nvhost-msenc ]] || gst-inspect-1.0 nvv4l2h264enc >/dev/null 2>&1; then
  fail "NVENC should not be available on Jetson Orin Nano Super 8 GB"
else
  pass "NVENC is absent as expected on Jetson Orin Nano Super 8 GB"
fi

if docker info >/dev/null 2>&1; then
  pass "Docker daemon is reachable"
else
  fail "Docker daemon is not reachable"
fi

if docker compose version >/dev/null 2>&1; then
  pass "Docker Compose v2 plugin is available"
else
  fail "Docker Compose v2 plugin is missing"
fi

if command -v nvidia-ctk >/dev/null 2>&1; then
  pass "nvidia-ctk is installed"
else
  fail "nvidia-ctk is missing"
fi

if [[ "$installer_mode" -eq 1 ]]; then
  for port in 8554 8888 8889 9108; do
    check_port_available "$port"
  done
  for port in 8189; do
    check_udp_port_available "$port"
  done

  if compgen -G "/dev/video*" >/dev/null; then
    pass "USB/UVC video device is present"
  else
    pass "no USB/UVC video device is attached"
  fi
fi

if [[ "$failures" -gt 0 ]]; then
  if [[ "$json_mode" -eq 1 ]]; then
    printf '{"status":"failed","installer_mode":%s,"failures":%d}\n' "$installer_mode" "$failures"
  fi
  printf '\nJetson preflight failed with %d issue(s).\n' "$failures" >&2
  exit 1
fi

if [[ "$json_mode" -eq 1 ]]; then
  printf '{"status":"passed","installer_mode":%s,"failures":0}\n' "$installer_mode"
fi
printf '\nJetson preflight passed.\n'
