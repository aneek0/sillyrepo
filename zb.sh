#!/bin/bash
# Zerobrew installer + root-friendly wrapper
# Usage: sudo bash install_zerobrew_root.sh

set -euo pipefail

# === Configuration ===
# Where zb/zbx binaries go (system-wide)
ZEROBREW_BIN="/usr/local/bin"

# Where zerobrew stores data, packages, cache (system-wide)
ZEROBREW_ROOT="/opt/zerobrew"
ZEROBREW_PREFIX="${ZEROBREW_ROOT}/prefix"

# Download URL for latest release
GITHUB_API="https://api.github.com/repos/lucasgelfond/zerobrew/releases/latest"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[*]${NC} $1"; }
ok()    { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
fail()  { echo -e "${RED}[✗]${NC} $1"; exit 1; }

# === Preflight ===
if [[ $EUID -ne 0 ]]; then
    warn "Not running as root. Re-invoking with sudo..."
    exec sudo "$0" "$@"
fi

info "Installing Zerobrew for root/system-wide use"
info "  Binaries:  ${ZEROBREW_BIN}"
info "  Data:      ${ZEROBREW_ROOT}"
info "  Prefix:    ${ZEROBREW_PREFIX}"

# === Detect platform ===
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)
case "$ARCH" in
    x86_64|amd64)  ARCH="x86_64" ;;
    aarch64|arm64) ARCH="arm64" ;;
    *)             fail "Unsupported architecture: $ARCH" ;;
esac

PLATFORM="${OS}/${ARCH}"
info "Platform: ${PLATFORM}"

# === Fetch latest release ===
info "Fetching latest release info..."
RELEASE_JSON=$(curl -fsSL "$GITHUB_API") || fail "Failed to fetch release info from GitHub"

TAG=$(echo "$RELEASE_JSON" | grep -oP '"tag_name":\s*"\K[^"]+') || fail "Could not parse release tag"
info "Latest release: ${TAG}"

# Find the right asset
ASSET_PATTERN=""
case "${OS}" in
    linux)   ASSET_PATTERN="linux.*${ARCH}" ;;
    darwin)  ASSET_PATTERN="darwin.*${ARCH}" ;;
    *)       fail "Unsupported OS: ${OS}" ;;
esac

DOWNLOAD_URL=$(echo "$RELEASE_JSON" | grep -oP '"browser_download_url":\s*"\K[^"]+' | grep -iE "$ASSET_PATTERN" | head -1)

if [[ -z "$DOWNLOAD_URL" ]]; then
    fail "No prebuilt binary found for ${PLATFORM}. Build from source manually."
fi

info "Downloading: ${DOWNLOAD_URL}"

# === Download and extract ===
TMPDIR=$(mktemp -d)
trap "rm -rf ${TMPDIR}" EXIT

ARCHIVE="${TMPDIR}/zerobrew.tar.gz"
curl -fsSL -o "$ARCHIVE" "$DOWNLOAD_URL" || fail "Download failed"

info "Extracting..."
tar -xzf "$ARCHIVE" -C "$TMPDIR"

# Find binaries in extracted archive
ZB_BIN=$(find "$TMPDIR" -name "zb" -type f | head -1)
ZBX_BIN=$(find "$TMPDIR" -name "zbx" -type f | head -1)

if [[ -z "$ZB_BIN" ]]; then
    fail "Could not find 'zb' binary in archive"
fi

# === Install ===
info "Creating directories..."
mkdir -p "$ZEROBREW_BIN"
mkdir -p "$ZEROBREW_ROOT"
mkdir -p "$ZEROBREW_PREFIX"

info "Installing binaries to ${ZEROBREW_BIN}..."
cp -f "$ZB_BIN" "${ZEROBREW_BIN}/zb"
chmod 755 "${ZEROBREW_BIN}/zb"

if [[ -n "$ZBX_BIN" ]]; then
    cp -f "$ZBX_BIN" "${ZEROBREW_BIN}/zbx"
    chmod 755 "${ZEROBREW_BIN}/zbx"
fi

# === Environment setup ===
info "Writing environment config..."
cat > /etc/profile.d/zerobrew.sh <<EOF
# Zerobrew - system-wide installation
export ZEROBREW_ROOT="${ZEROBREW_ROOT}"
export ZEROBREW_PREFIX="${ZEROBREW_PREFIX}"
export PATH="${ZEROBREW_PREFIX}/bin:\${PATH}"
EOF
chmod 644 /etc/profile.d/zerobrew.sh

# === Wrapper for zb that sets env vars ===
# The zb binary looks for ZEROBREW_ROOT/ZEROBREW_PREFIX env vars
# We create a wrapper that always sets them, so it works from any context
cat > "${ZEROBREW_BIN}/zb-root" <<'WRAPPER'
#!/bin/bash
# Zerobrew root wrapper - ensures proper env for system-wide use
export ZEROBREW_ROOT="${ZEROBREW_ROOT:-/opt/zerobrew}"
export ZEROBREW_PREFIX="${ZEROBREW_PREFIX:-/opt/zerobrew/prefix}"
exec /usr/local/bin/zb "$@"
WRAPPER
chmod 755 "${ZEROBREW_BIN}/zb-root"

# === Initialize ===
info "Initializing Zerobrew..."
export ZEROBREW_ROOT="$ZEROBREW_ROOT"
export ZEROBREW_PREFIX="$ZEROBREW_PREFIX"

"${ZEROBREW_BIN}/zb" init 2>/dev/null || true

# === Verify ===
echo ""
ok "Zerobrew installed successfully!"
echo ""
echo -e "  ${GREEN}zb --version${NC}"
zb_version=$("${ZEROBREW_BIN}/zb" --version 2>/dev/null || echo "unknown")
echo "  → ${zb_version}"
echo ""
echo "  Usage:"
echo "    zb install <package>       # install a package"
echo "    zb upgrade                 # upgrade all packages"
echo "    zb list                    # list installed packages"
echo "    zbx <package> <command>    # run without linking"
echo ""
echo "  Packages install to: ${ZEROBREW_PREFIX}"
echo "  Binaries available system-wide via ${ZEROBREW_PREFIX}/bin"
echo ""
echo "  For non-root users, source the env:"
echo "    source /etc/profile.d/zerobrew.sh"
echo ""
warn "Log out and back in (or source /etc/profile.d/zerobrew.sh) for PATH changes to take effect."
