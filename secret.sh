#!/usr/bin/env bash
# secret.sh — password-protect a private note with AES-256.
#
#   ./secret.sh lock     encrypt .notes.md  -> .notes.md.enc  (then deletes plaintext)
#   ./secret.sh unlock   decrypt .notes.md.enc -> .notes.md
#   ./secret.sh view     decrypt to screen only (no plaintext file left on disk)
#
# You are prompted for the passphrase each time. It is never stored by this script.
# Tip: save the passphrase in macOS Keychain so you can't lose it again:
#   ./secret.sh keep            store the passphrase in your login Keychain
#   ./secret.sh show-key        print the saved passphrase (Keychain may prompt)
# Then unlock without retyping:
#   ./secret.sh unlock --keychain   /   ./secret.sh view --keychain

set -euo pipefail

PLAIN=".notes.md"
ENC=".notes.md.enc"
CIPHER="-aes-256-cbc -pbkdf2 -iter 600000 -salt"
KEYCHAIN_SERVICE="pm-agent-notes"
KEYCHAIN_ACCOUNT="$(whoami)"

_pass_from_keychain() {
  security find-generic-password -s "$KEYCHAIN_SERVICE" -a "$KEYCHAIN_ACCOUNT" -w 2>/dev/null
}

# Resolve passphrase: --keychain pulls it from Keychain, else openssl prompts.
_pass_args() {
  if [ "${2:-}" = "--keychain" ]; then
    local p; p="$(_pass_from_keychain)" || { echo "No passphrase saved. Run: ./secret.sh keep" >&2; exit 1; }
    printf -- "-pass pass:%s" "$p"
  fi
}

case "${1:-}" in
  lock)
    [ -f "$PLAIN" ] || { echo "No $PLAIN to lock."; exit 1; }
    # shellcheck disable=SC2046
    openssl enc $CIPHER $(_pass_args "$@") -in "$PLAIN" -out "$ENC"
    rm -f "$PLAIN"
    echo "Locked -> $ENC (plaintext removed). Unlock with: ./secret.sh unlock"
    ;;
  unlock)
    [ -f "$ENC" ] || { echo "No $ENC to unlock."; exit 1; }
    # shellcheck disable=SC2046
    openssl enc -d $CIPHER $(_pass_args "$@") -in "$ENC" -out "$PLAIN" \
      || { echo "Wrong passphrase or corrupt file."; rm -f "$PLAIN"; exit 1; }
    echo "Unlocked -> $PLAIN"
    ;;
  view)
    [ -f "$ENC" ] || { echo "No $ENC to view."; exit 1; }
    # shellcheck disable=SC2046
    openssl enc -d $CIPHER $(_pass_args "$@") -in "$ENC" 2>/dev/null \
      || { echo "Wrong passphrase or corrupt file."; exit 1; }
    ;;
  keep)
    # Store the passphrase in the macOS login Keychain (-U updates if it exists).
    printf "Passphrase to save in Keychain: "
    read -rs PW; echo
    security add-generic-password -U -s "$KEYCHAIN_SERVICE" -a "$KEYCHAIN_ACCOUNT" -w "$PW"
    echo "Saved to Keychain (service: $KEYCHAIN_SERVICE). Retrieve with: ./secret.sh show-key"
    ;;
  show-key)
    _pass_from_keychain || { echo "No passphrase saved in Keychain."; exit 1; }
    ;;
  *)
    echo "Usage: ./secret.sh {lock|unlock|view|keep|show-key} [--keychain]"
    exit 1
    ;;
esac
