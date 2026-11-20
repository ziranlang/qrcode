"""Run the package's reference suite with only its ZX library available."""

import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import ssl
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Thread
from urllib.parse import urlsplit


def package_id(url, revision):
    return "p" + hashlib.sha256(f"{url}\n{revision}".encode()).hexdigest()[:16]


def discover_library(root, ziran, env, library, descriptor, repository, revision, profile):
    url = urlsplit(repository)
    owner, package = url.path.strip("/").removesuffix(".git").split("/")
    artifact = f"/api/packages/{owner}/generic/{package}-zx-library/{revision}/{profile}.zx"
    requests = []

    class Registry(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            requests.append(self.path)
            if self.path == artifact + ".tsv":
                data = descriptor.encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            elif self.path == artifact:
                with library.open("rb") as source:
                    self.send_response(200)
                    self.send_header("Content-Length", str(library.stat().st_size))
                    self.end_headers()
                    shutil.copyfileobj(source, self.wfile)
            else:
                self.send_error(404)

    cert, key = root / "cert.pem", root / "key.pem"
    result = subprocess.run(
        ["openssl", "req", "-new", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
         "-subj", f"/CN={url.hostname}", "-addext", f"subjectAltName=DNS:{url.hostname}",
         "-keyout", key, "-out", cert], capture_output=True, text=True,
    )
    if result.returncode:
        raise SystemExit(result.stderr)
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.load_cert_chain(cert, key)
    # Keep the canonical URL and certificate name for discovery and cache
    # identity. Only the test registry's transport is redirected to loopback.
    curl = shutil.which("curl")
    if curl is None:
        raise SystemExit("curl is required for the ZX library verification")
    tools = root / "tools"
    tools.mkdir()
    proxy = tools / "curl"
    proxy.write_text(
        '#!/bin/sh\nexec "$ZX_TEST_CURL" --disable --connect-to "$ZX_TEST_ROUTE" "$@"\n'
    )
    proxy.chmod(0o700)
    with HTTPServer(("127.0.0.1", 0), Registry) as server:
        server.socket = tls.wrap_socket(server.socket, server_side=True)
        env.update(
            ZIRAN_ZX_REGISTRY=f"{url.scheme}://{url.netloc}",
            ZIRAN_ZX_PROFILE=profile, CURL_CA_BUNDLE=str(cert),
            NO_PROXY=url.hostname, no_proxy=url.hostname,
            PATH=f"{tools}:{os.environ['PATH']}", ZX_TEST_CURL=curl,
            ZX_TEST_ROUTE=f"{url.hostname}:{url.port or 443}:127.0.0.1:{server.server_port}",
        )
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            subprocess.run([*ziran, "add", repository, "--ref", revision], cwd=root, env=env, check=True)
        finally:
            server.shutdown()
            thread.join()
    if requests != [artifact + ".tsv", artifact]:
        raise SystemExit(f"Unexpected library registry requests {requests!r}")


def prepare_development(ziran, root, env, repository, revision, profile, identity, tool_identity):
    dev = root / "libraries"
    dev.mkdir()
    artifact = dev / f"{identity}.zx"
    producer_env = dict(os.environ)
    producer_env.pop("ZIRAN_DEV_ZX_DIR", None)
    subprocess.run(
        [*ziran, "pkg", "zx", "pack-dev", repository, revision, profile, artifact, "--offline"],
        env=producer_env, check=True,
    )
    descriptor = inspect_library(ziran, artifact)
    if descriptor[:4] != ["dev", identity, tool_identity, profile] or not re.fullmatch(r"[0-9a-f]{64}", descriptor[4]):
        raise SystemExit("Development library has an unexpected package, toolchain, profile or source fingerprint")
    env["ZIRAN_DEV_ZX_DIR"] = str(dev)


def inspect_library(ziran, library):
    with library.open("rb") as artifact:
        digest = hashlib.file_digest(artifact, "sha256").hexdigest()
    descriptor = subprocess.check_output(
        [*ziran, "pkg", "zx", "inspect-ir", library], text=True
    ).rstrip("\n").split("\t")
    if len(descriptor) != (6 if descriptor[0] == "dev" else 5) or descriptor[-1] != digest:
        raise SystemExit("ZX library inspection did not match the artifact digest")
    return descriptor


def main():
    mode, tool, repository, revision, profile, filename, entry, *sources = sys.argv[1:]
    if mode not in ("dev", "production"):
        raise SystemExit(f"Unknown ZX library test mode {mode!r}")
    production = mode == "production"
    ziran = shlex.split(tool)
    ziran[0] = str(Path(shutil.which(ziran[0]) or ziran[0]).absolute())
    library = Path(filename).resolve()
    package = repository.rsplit("/", 1)[1].removesuffix(".git")
    app = f"{package}_binary_test"
    pin = json.loads(Path("ziran.lock").read_text())["toolchain"]
    toolchain = subprocess.check_output(
        [*ziran, "pkg", "path", "ziran", "--offline", *(["--locked"] if production else [])], text=True
    ).strip()
    ziran = [str(Path(toolchain) / "build/bin/ziran")]
    identity = package_id(repository, revision)
    tool_identity = package_id(pin["url"], pin["commit"])
    with TemporaryDirectory(prefix="consumer-", dir=library.parent) as directory:
        root = Path(directory).resolve()
        cache = root / "cache"
        hosts = root / "hosts"
        hosts.mkdir()
        env = {**os.environ, "XDG_CACHE_HOME": str(cache), "ZIRAN_HOST_PATH": str(hosts),
               "GIT_ALLOW_PROTOCOL": ""}
        for name in ("DISPLAY", "WAYLAND_DISPLAY", "CURL_SSL_BACKEND", "ZIRAN_DEV_ZX_DIR", "ZIRAN_LOCK_GIT_OBJECTS",
                     "ZIRAN_PACKAGE_MAP", "ZIRAN_PACKAGE_NETRC", "ZIRAN_PINNED_LAUNCHER", "ZIRAN_STD"):
            env.pop(name, None)

        for source in map(Path, sources):
            shutil.copyfile(source, root / source.name)
        manifest = (
            f'[package]\nname = "{app}"\nmodule_roots = ["."]\n'
            f'[toolchain]\ngit = "{pin["url"]}"\nref = "{pin["ref"]}"\n'
        )
        # Reuse the exact compiler and standard library without copying a
        # toolchain checkout into the isolated dependency cache.
        (root / "ziran.local.toml").write_text(f"[overrides]\nziran = {json.dumps(toolchain)}\n")
        lock_path = root / "ziran.lock"
        dependency = {"id": identity, "name": package, "url": repository,
                      "ref": revision, "commit": revision, "dependencies": {}}
        lock = {"format": 1, "root": {"name": app, "dependencies": {package: identity}},
                "toolchain": pin, "packages": [dependency]}
        if production:
            descriptor = inspect_library(ziran, library)
            if descriptor[:4] != ["2", identity, tool_identity, profile]:
                raise SystemExit("Production library has an unexpected package, toolchain or profile")
            (root / "ziran.toml").write_text(manifest)
            discover_library(root, ziran, env, library, "\t".join(descriptor) + "\n", repository, revision, profile)
            dependency["checked"] = {"profile": profile, "sha256": descriptor[-1], "toolchain": tool_identity}
            saved = lock_path.read_bytes()
            if json.loads(saved) != lock:
                raise SystemExit("Package discovery recorded an unexpected library pin")
            subprocess.run([*ziran, "lock", "--offline"], cwd=root, env=env, check=True)
            if lock_path.read_bytes() != saved:
                raise SystemExit("Offline lock changed the verified library pin")
        else:
            (root / "ziran.toml").write_text(
                manifest + f'[dependencies.{package}]\ngit = "{repository}"\nref = "{revision}"\n'
            )
            lock_path.write_text(json.dumps(lock))
            prepare_development(ziran, root, env, repository, revision, profile, identity, tool_identity)
        main_source = Path(sources[0]).name
        project = ["--project", "--offline", "--entry", entry]
        subprocess.run(
            [*ziran, "bundle", *project, "-o", "consumer.zx", main_source],
            cwd=root, env=env, check=True,
        )
        subprocess.run(
            [*ziran, "build", *project, "--target=c", "--exe", "-o", "native", main_source],
            cwd=root, env=env, check=True,
        )
        if (cache / "ziran" / "sources").exists():
            raise SystemExit("The dependency source was materialized during the offline build")

        output = subprocess.check_output(
            [*ziran, "run", "--backend", "engine", "consumer.zx"], cwd=root, env=env, text=True
        )
        native = subprocess.check_output(
            [root / "native" / Path(main_source).stem], cwd=root, env=env, text=True
        )
        print(output, end="")
        if output.splitlines() != [*native.splitlines(), "0"]:
            raise SystemExit("The native and ZX consumers did not agree")
        print(f"{package} {profile} {mode} library passed native and ZX offline without sources or host bindings")


if __name__ == "__main__":
    main()
