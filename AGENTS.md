# qrcode agent guide

Small Ziran QR Code encoder: one byte-mode segment, versions 1-40, four error
correction levels, automatic mask choice, smallest version that fits (raising
ECC while it still fits). Allocates nothing: a `QrCode` holds its modules and
the encoder working space. Port of Project Nayuki's generator (MIT); tests
match that library module for module.

## Layout

- `src/qrcode.zi` — the module, exported as `qrcode`; import `qrcode/qrcode`.
- `tests/qrcode_test.zi` — the shared test entry for C and portable runs.
- `Makefile` — default goal `check`; also `test`, `clean`, `zx-library`,
  `check-binary`, `check-binary-production`, `publish-zx`. `build/` holds
  outputs; an ignored `ziran.local.toml` drops `--locked`.

## Commands

- `make check` (runs `test`): `ziran check --project`, then the C build
  compiled with `cc -std=c99 -pedantic-errors` against the toolchain include
  directory, run; then the same entry bundled as `.zx` and run on the engine,
  requiring exit status 0.
- `make zx-library` / `make check-binary` / `make publish-zx` — pack, verify
  and publish the profiled ZX library (publish needs `ZIRAN_PACKAGE_NETRC`).

## Pins

- Toolchain: `ziran.lock` pins ziran.git
  `5462fe2ebf2c3c42663249e47ef99d61f45ff39f`.
- Consumers: `ziran add https://git.waozi.xyz/ziranlang/qrcode.git`.

## Question -> file

- API and allocation rules? -> README, `src/qrcode.zi`.
- Reference test vectors? -> `tests/qrcode_test.zi` (Nayuki port).
- ZX library workflow? -> `Makefile` targets.
- Which toolchain? -> `ziran.toml`, `ziran.lock`.
