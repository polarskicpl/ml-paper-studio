#!/usr/bin/env python3
"""Download an allowlisted HTTPS template without asserting official provenance."""
import argparse
import hashlib
import http.client
import ipaddress
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import socket
import ssl
import sys
import tarfile
import tempfile
import time
import unicodedata
from urllib.parse import unquote, urljoin, urlsplit
import zipfile

MAX_ENTRIES = 5000
MAX_FILE = 50 * 1024 * 1024
MAX_UNPACKED = 200 * 1024 * 1024
SINGLE_SUFFIXES = {'.tex', '.cls', '.sty', '.bst', '.bib', '.pdf'}


class TemplateError(ValueError):
    pass


def host_name(value):
    value = value.rstrip('.').lower()
    try:
        value = value.encode('idna').decode('ascii')
    except UnicodeError as exc:
        raise TemplateError('Invalid hostname') from exc
    if not value or not re.fullmatch(r'[a-z0-9.-]+', value):
        raise TemplateError('Allow hosts must be exact hostnames without ports or wildcards')
    return value


def parse_url(url):
    if any(ord(c) <= 32 or ord(c) == 127 for c in url):
        raise TemplateError('Whitespace or control character in URL')
    try:
        parts = urlsplit(url)
        port = parts.port if parts.port is not None else 443
    except ValueError as exc:
        raise TemplateError('Invalid URL') from exc
    if parts.scheme.lower() != 'https' or not parts.hostname:
        raise TemplateError('Only absolute HTTPS URLs are accepted')
    if parts.username is not None or parts.password is not None or parts.fragment:
        raise TemplateError('URL user information and fragments are not accepted')
    if port < 1:
        raise TemplateError('Invalid URL port')
    return parts, host_name(parts.hostname), port


def public_addresses(host, port):
    try:
        rows = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise TemplateError('Hostname resolution failed') from exc
    addresses = list(dict.fromkeys(row[4][0] for row in rows))
    def acceptable(value):
        address = ipaddress.ip_address(value)
        return address.is_global and not any((address.is_private, address.is_loopback,
            address.is_link_local, address.is_reserved, address.is_unspecified, address.is_multicast))
    if not addresses or not all(acceptable(a) for a in addresses):
        raise TemplateError('Every resolved address must be a public IP address')
    return addresses


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    """Connect to a validated public address while checking the hostname via TLS."""
    def __init__(self, host, port, address):
        super().__init__(host, port, timeout=30, context=ssl.create_default_context())
        self.address = address

    def connect(self):
        raw = socket.create_connection((self.address, self.port), self.timeout)
        try:
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except BaseException:
            raw.close()
            raise


def download(url, directory, allowed, max_bytes):
    current, redirects = url, []
    started = last_progress = time.monotonic()
    for hop in range(6):
        parts, host, port = parse_url(current)
        if host not in allowed:
            raise TemplateError('Download or redirect host is outside --allow-host')
        addresses = public_addresses(host, port)
        conn = PinnedHTTPSConnection(host, port, addresses[0])
        try:
            path = parts.path or '/'
            if parts.query:
                path += '?' + parts.query
            conn.request('GET', path, headers={'User-Agent': 'ml-paper-studio-template/1.0'})
            response = conn.getresponse()
            if response.status in (301, 302, 303, 307, 308):
                location = response.getheader('Location')
                if not location or hop == 5:
                    raise TemplateError('Missing redirect location or more than five redirects')
                target = urljoin(current, location)
                redirects.append({'from': current, 'to': target, 'status': response.status})
                current = target
                continue
            if response.status != 200:
                raise TemplateError('HTTP response was not 200: ' + str(response.status))
            length = response.getheader('Content-Length')
            if length and length.isdigit() and int(length) > max_bytes:
                raise TemplateError('Download exceeds the compressed-size limit')
            name = PurePosixPath(unquote(parts.path)).name or 'template-download.bin'
            if not re.fullmatch(r'[A-Za-z0-9._-]{1,150}', name) or name in ('.', '..'):
                name = 'template-download.bin'
            output = directory / name
            size, digest = 0, hashlib.sha256()
            print('[download] started', flush=True)
            with output.open('xb') as stream:
                while True:
                    if time.monotonic() - started > 300:
                        raise TemplateError('Download exceeded the 300-second time budget')
                    chunk = response.read(64 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > max_bytes:
                        raise TemplateError('Download exceeds the compressed-size limit')
                    stream.write(chunk)
                    digest.update(chunk)
                    if time.monotonic() - last_progress >= 15:
                        print(f'[download] {size} bytes; elapsed {time.monotonic()-started:.1f}s', flush=True)
                        last_progress = time.monotonic()
            print(f'[download] completed {size} bytes in {time.monotonic()-started:.1f}s', flush=True)
            return output, current, redirects, digest.hexdigest()
        finally:
            conn.close()
    raise TemplateError('Redirect limit exceeded')


def safe_name(raw):
    if not raw or '\\' in raw or any(ord(c) < 32 for c in raw):
        raise TemplateError('Invalid archive member name')
    path = PurePosixPath(raw)
    if path.is_absolute() or '..' in path.parts or re.match(r'^[A-Za-z]:', raw):
        raise TemplateError('Archive path escapes the template directory')
    if str(path) == '.' or len(path.parts) > 64:
        raise TemplateError('Invalid archive path or excessive path depth')
    return path


def check_members(members):
    seen, total = set(), 0
    if len(members) > MAX_ENTRIES:
        raise TemplateError('Archive contains too many entries')
    for raw, size, is_dir, _ in members:
        rel = safe_name(raw)
        key = unicodedata.normalize('NFC', str(rel)).casefold()
        if key in seen:
            raise TemplateError('Duplicate or case-colliding archive paths')
        seen.add(key)
        if size < 0 or size > MAX_FILE:
            raise TemplateError('Archive member exceeds the single-file limit')
        if not is_dir:
            total += size
    if total > MAX_UNPACKED:
        raise TemplateError('Archive exceeds the unpacked-size limit')


def copy_member(source, target, expected, used):
    target.parent.mkdir(parents=True, exist_ok=True)
    size = 0
    with target.open('xb') as output:
        while True:
            chunk = source.read(64 * 1024)
            if not chunk:
                break
            size += len(chunk)
            used[0] += len(chunk)
            if size > MAX_FILE or size > expected or used[0] > MAX_UNPACKED:
                raise TemplateError('Actual extracted bytes exceed declared or allowed limits')
            output.write(chunk)
    if size != expected:
        raise TemplateError('Archive member size mismatch')


def extract_template(archive, target):
    """Validate metadata before writes; extract only into a newly created directory."""
    if target.exists() or target.is_symlink():
        raise TemplateError('Extraction target already exists')
    members, used = [], [0]
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as package:
            for item in package.infolist():
                kind = (item.external_attr >> 16) & 0o170000
                if kind not in (0, 0o040000, 0o100000) or item.flag_bits & 1:
                    raise TemplateError('ZIP links, special files and encrypted entries are rejected')
                members.append((item.filename, item.file_size, item.is_dir(), item))
            check_members(members)
            target.mkdir()
            for raw, size, is_dir, item in members:
                dest = target.joinpath(*safe_name(raw).parts)
                if is_dir:
                    dest.mkdir(parents=True, exist_ok=True)
                else:
                    with package.open(item) as source:
                        copy_member(source, dest, size, used)
    elif tarfile.is_tarfile(archive):
        with tarfile.open(archive, 'r:*') as package:
            for item in package:
                if not (item.isdir() or item.isreg()):
                    raise TemplateError('TAR links and special files are rejected')
                members.append((item.name, item.size, item.isdir(), item))
                if len(members) > MAX_ENTRIES:
                    raise TemplateError('Archive contains too many entries')
            check_members(members)
            target.mkdir()
            for raw, size, is_dir, item in members:
                dest = target.joinpath(*safe_name(raw).parts)
                if is_dir:
                    dest.mkdir(parents=True, exist_ok=True)
                else:
                    with package.extractfile(item) as source:
                        copy_member(source, dest, size, used)
    else:
        if archive.suffix.lower() not in SINGLE_SUFFIXES or archive.stat().st_size > MAX_FILE:
            raise TemplateError('Not a supported archive or explicitly allowed single file')
        target.mkdir()
        with archive.open('rb') as source:
            copy_member(source, target / archive.name, archive.stat().st_size, used)
    files = []
    for file in sorted(target.rglob('*')):
        if file.is_file():
            digest = hashlib.sha256()
            with file.open('rb') as stream:
                for chunk in iter(lambda: stream.read(64 * 1024), b''):
                    digest.update(chunk)
            files.append({'path': file.relative_to(target).as_posix(), 'sha256': digest.hexdigest(), 'size': file.stat().st_size})
    if not files:
        raise TemplateError('Template contains no files')
    return files


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', required=True)
    parser.add_argument('--dest', required=True, type=Path)
    parser.add_argument('--source-page', required=True)
    parser.add_argument('--allow-host', required=True, action='append')
    parser.add_argument('--max-mb', type=float, default=50)
    args = parser.parse_args(argv)
    staging = None
    created_dest = False
    try:
        if not 0 < args.max_mb < float('inf'):
            raise TemplateError('--max-mb must be finite and positive')
        allowed = {host_name(host) for host in args.allow_host}
        parse_url(args.url)
        _, source_host, source_port = parse_url(args.source_page)
        public_addresses(source_host, source_port)
        dest = args.dest.absolute()
        if dest.exists() or dest.is_symlink():
            raise TemplateError('--dest must not already exist')
        dest.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix='.' + dest.name + '.fetch-', dir=dest.parent))
        (staging / 'download').mkdir()
        archive, final_url, redirects, digest = download(args.url, staging / 'download', allowed, int(args.max_mb * 1024 * 1024))
        print('[extract] started', flush=True)
        files = extract_template(archive, staging / 'template')
        print('[extract] completed ' + str(len(files)) + ' files', flush=True)
        manifest = {'status': 'downloaded_and_extracted', 'source_url': args.url, 'final_url': final_url,
                    'source_page': args.source_page, 'fetched_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                    'archive_path': archive.relative_to(staging).as_posix(), 'archive_sha256': digest,
                    'redirect_chain': redirects, 'files': files, 'validation_scope': 'provenance_not_established'}
        # Exclusive mkdir prevents overwriting even an empty destination created concurrently.
        dest.mkdir()
        created_dest = True
        for child in staging.iterdir():
            child.rename(dest / child.name)
        (dest / 'template-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print('[template] saved ' + str(dest / 'template-manifest.json'), flush=True)
        return 0
    except (Exception, KeyboardInterrupt) as exc:
        if created_dest:
            failed = {'status': 'failed', 'error': str(exc), 'validation_scope': 'provenance_not_established'}
            (dest / 'template-manifest.json').write_text(json.dumps(failed, indent=2) + '\n', encoding='utf-8')
        print('[template] failed: ' + str(exc), file=sys.stderr, flush=True)
        return 1
    finally:
        if staging is not None:
            shutil.rmtree(staging)
            print('[template] removed own temporary workspace', flush=True)


if __name__ == '__main__':
    raise SystemExit(main())
