.DEFAULT_GOAL := check

ZIRAN ?= ziran
CC ?= cc
BUILD := build

.PHONY: check test clean

# Checks the package, then runs the tests as C and as a portable bundle.
check: test

test:
	$(ZIRAN) check --project
	$(ZIRAN) build --project --target=c --entry qrcode_test:main \
		-o $(BUILD)/test-c tests/qrcode_test.zi
	$(CC) -std=c99 -pedantic-errors -I$$($(ZIRAN) pkg path ziran)/include \
		-I$(BUILD)/test-c $$(find $(BUILD)/test-c -name '*.c') -o $(BUILD)/qrcode-test
	$(BUILD)/qrcode-test
	$(ZIRAN) bundle --project --entry qrcode_test:main \
		-o $(BUILD)/qrcode-test.zib tests/qrcode_test.zi
	test "$$($(ZIRAN) run --project $(BUILD)/qrcode-test.zib)" = 0

clean:
	rm -rf $(BUILD)
