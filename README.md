# QR Code

QR Code is a small [Ziran](https://git.waozi.xyz/ziranlang/ziran) package that
encodes text as a QR Code: one byte-mode segment, versions 1 to 40, the four
error correction levels and an automatically chosen mask. It chooses the
smallest version that holds the text and raises the error correction level
while that version still fits. It allocates nothing: a `QrCode` holds its
modules and the encoder's working space.

It is a port of Project Nayuki's
[QR Code generator library](https://www.nayuki.io/page/qr-code-generator-library)
(MIT License), and its tests match that library module for module.

## Use it

```sh
ziran add https://git.waozi.xyz/ziranlang/qrcode.git
```

```zi
#import "qrcode/qrcode"

using QrEcc;

code: QrCode;

Draw :: (text: string) {
    if !QrEncodeText(text, cast(QrEcc)QrEccMedium, *code) { return }
    for y: 0..code.size - 1 {
        for x: 0..code.size - 1 {
            if QrModule(*code, x, y) {
                // Paint a dark module at (x, y), inside a light border of
                // at least four modules.
            }
        }
    }
}
```

A `QrCode` is about 70 KB, so keep it in a global or on the heap rather than
on a small thread stack.

## Check it

```sh
make
```

## ZX library

`make check-binary` packs a development library from the working tree and
runs the same matrix hashes and input validation cases in native C and the ZX
engine. The isolated consumer imports `qrcode/qrcode` with an empty source
cache. An ignored `ziran.local.toml` toolchain override can select a local
compiler for this test.

The `default` profile sets no feature defines. It supports the portable ZX
engine and uses no package-specific native libraries or host bindings. The
producer and consumer tests run on Linux.

The Gitea workflow runs `make check check-binary-production` before publishing
`default.zx` and its descriptor `default.zx.tsv` under the full Git revision
in the `qrcode-zx-library` Generic Package Registry. The production target packs
the clean committed revision with the exact toolchain pinned in `ziran.lock`
and verifies registry discovery before running the offline consumer.

Use the full published revision when adding the dependency. Ziran records the
library profile, digest and toolchain identity in the consumer lock. The import
and types in the example above are the same with either dependency source or a
ZX library. The compiler can use the library's checked modules during application
lowering.

```sh
ziran add https://git.waozi.xyz/ziranlang/qrcode.git --ref "$commit"
ziran bundle --project --locked --entry app:main -o app.zx app.zi
ziran bundle --project --locked --offline --entry app:main -o app.zx app.zi
```
