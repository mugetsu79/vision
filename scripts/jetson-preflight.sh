#!/usr/bin/env bash

set -euo pipefail

failures=0

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

if [[ "$(uname -m)" == "aarch64" ]]; then
  pass "Jetson architecture is arm64"
else
  fail "Jetson architecture must be aarch64"
fi

check_command docker
check_command gst-inspect-1.0

if command -v dpkg-query >/dev/null 2>&1; then
  check_command_output "JetPack 6.2 is installed" '^6\.2' dpkg-query -W -f='${Version}' nvidia-jetpack
  if dpkg-query -W -f='${Version}' libnvinfer10 >/dev/null 2>&1; then
    check_command_output "TensorRT 10.x runtime is installed" '^10\.' dpkg-query -W -f='${Version}' libnvinfer10
  else
    fail "TensorRT 10.x runtime package libnvinfer10 is missing"
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

if [[ "$failures" -gt 0 ]]; then
  printf '\nJetson preflight failed with %d issue(s).\n' "$failures" >&2
  exit 1
fi

printf '\nJetson preflight passed.\n'
