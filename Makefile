.DEFAULT_GOAL := check

ZIRAN ?= ziran
LOCKED := $(if $(wildcard ziran.local.toml),,--locked)
CC ?= cc
BUILD := build
ZX_REPOSITORY := https://git.waozi.xyz/ziranlang/qrcode.git
ZX_REVISION ?= $(shell git rev-parse HEAD)
ZX_PROFILE := default
ZX_LIBRARY := $(BUILD)/zx-library/$(ZX_PROFILE).zx

.PHONY: check test clean zx-library check-binary check-binary-production publish-zx

# Checks the package, then runs the tests as C and as a portable bundle.
check: test

test:
	$(ZIRAN) check --project $(LOCKED)
	$(ZIRAN) build --project $(LOCKED) --target=c --entry qrcode_test:main \
		-o $(BUILD)/test-c tests/qrcode_test.zi
	$(CC) -std=c99 -pedantic-errors -I$$($(ZIRAN) pkg path ziran $(LOCKED))/include \
		-I$(BUILD)/test-c $$(find $(BUILD)/test-c -name '*.c') -o $(BUILD)/qrcode-test
	$(BUILD)/qrcode-test
	$(ZIRAN) bundle --project $(LOCKED) --entry qrcode_test:main \
		-o $(BUILD)/qrcode-test.zx tests/qrcode_test.zi
	test "$$($(ZIRAN) run --project $(LOCKED) $(BUILD)/qrcode-test.zx)" = 0

zx-library:
	mkdir -p $(dir $(ZX_LIBRARY))
	toolchain=$$($(ZIRAN) pkg path ziran --locked) && \
		"$$toolchain/build/bin/ziran" pkg zx pack-ir $(ZX_REPOSITORY) $(ZX_REVISION) $(ZX_PROFILE) $(ZX_LIBRARY) --locked

check-binary:
	mkdir -p $(dir $(ZX_LIBRARY))
	python3 tests/check_binary.py dev "$(ZIRAN)" $(ZX_REPOSITORY) $(ZX_REVISION) $(ZX_PROFILE) \
		$(ZX_LIBRARY) qrcode_test:main tests/qrcode_test.zi

check-binary-production: zx-library
	python3 tests/check_binary.py production "$(ZIRAN)" $(ZX_REPOSITORY) $(ZX_REVISION) $(ZX_PROFILE) \
		$(ZX_LIBRARY) qrcode_test:main tests/qrcode_test.zi

publish-zx:
	test -n "$$ZIRAN_PACKAGE_NETRC"
	toolchain=$$($(ZIRAN) pkg path ziran --locked --offline) && \
		"$$toolchain/build/bin/ziran" pkg zx publish-ir $(ZX_REPOSITORY) $(ZX_REVISION) $(ZX_PROFILE) $(ZX_LIBRARY) \
			--netrc "$$ZIRAN_PACKAGE_NETRC"

clean:
	rm -rf $(BUILD)
