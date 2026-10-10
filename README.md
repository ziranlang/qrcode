# QR Code

QR Code is a small [Ziran](https://github.com/ziranlang/ziran) package that
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
ziran add https://github.com/ziranlang/qrcode.git
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
