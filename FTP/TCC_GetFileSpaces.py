#!/usr/bin/env python3

import argparse
import ftplib
import json
import logging
import os
import sys
from datetime import datetime
from pprint import pprint
from urllib.parse import quote

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("TCC_FTP_GetFileSpaces")


def parse_args():
    argp = argparse.ArgumentParser(
        description="Connect to TCC via FTP using FastDir or a recursive FTP scan",
        epilog="""
   V1.2 (c) JCMBsoft 2026
   """,
    )
    argp.add_argument(
        "-u", "--user", metavar="USER", required=True, help="TCC user name"
    )
    argp.add_argument(
        "-o", "--org", metavar="ORG", required=True, help="TCC organisation"
    )
    argp.add_argument(
        "-p", "--password", metavar="PASSWD", required=True, help="TCC password"
    )
    argp.add_argument(
        "--path",
        metavar="PATH",
        default="/",
        help="FastDir Path parameter, or subpath for --ftp-scan (default: /)",
    )
    argp.add_argument(
        "--filespace",
        metavar="NAME",
        default="TrimbleSynchronizerData",
        help="File space name under /TCC/<org>/ (default: TrimbleSynchronizerData)",
    )
    argp.add_argument(
        "--recursive",
        metavar="BOOL",
        default="true",
        help="Recurse into subdirectories (default: true)",
    )
    argp.add_argument(
        "-t",
        "--timeout",
        type=int,
        default=60,
        help="Timeout in seconds for each FTP operation (default: 60)",
    )
    argp.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase output verbosity (1=info, 2=debug, 3+=FTP wire log)",
    )
    argp.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Enable FTP protocol wire-level debug (same as -vvv)",
    )
    argp.add_argument(
        "-T",
        "--Tell",
        action="store_true",
        help="Print settings before connecting",
    )
    argp.add_argument(
        "--ftp-scan",
        action="store_true",
        help="Use a normal recursive FTP directory scan instead of SITE FastDir",
    )
    argp.add_argument(
        "-P",
        "--progress",
        action="store_true",
        help="Show a progress bar while downloading, parsing, or scanning",
    )
    return argp.parse_args()


def process_args(args):
    if args.debug:
        args.verbose = max(args.verbose, 3)

    if args.verbose == 0:
        logger.setLevel(logging.WARNING)
    elif args.verbose == 1:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.DEBUG)

    if args.Tell:
        sys.stderr.write("User: {} Org: {}\n".format(args.user, args.org))
        sys.stderr.write("Path: {}\n".format(args.path))
        sys.stderr.write("FileSpaceShortName: {}\n".format(args.filespace))
        sys.stderr.write("Recursive: {}\n".format(args.recursive))
        sys.stderr.write("FTP scan mode: {}\n".format(args.ftp_scan))
        sys.stderr.write("Timeout: {}s\n".format(args.timeout))
        sys.stderr.write("Verbose: {}\n".format(args.verbose))
        sys.stderr.write("Progress bar: {}\n".format(args.progress))
        sys.stderr.write("FTP wire debug: {}\n\n".format(args.verbose >= 3 or args.debug))

    return args


def recursive_enabled(value):
    return str(value).lower() in ("true", "1", "yes", "on")


def format_timestamp(value):
    if value is None:
        return "-"
    return value.strftime("%Y-%m-%d %H:%M:%S")


def normalize_display_path(path):
    if not path or path == "/":
        return "/"
    return "/" + path.strip("/")


def build_remote_scan_root(org, filespace, path="/"):
    remote = "/TCC/{}/{}".format(org, filespace)
    subpath = path.strip("/")
    if subpath:
        remote = remote.rstrip("/") + "/" + subpath
    return remote


def build_display_path(base, name, is_dir):
    if base == "/":
        display = "/" + name
    else:
        display = base.rstrip("/") + "/" + name
    if is_dir:
        display += "/"
    return display


def parse_mlsd_timestamp(value):
    if not value:
        return None
    if len(value) >= 14:
        timestamp = datetime.strptime(value[:14], "%Y%m%d%H%M%S")
        if len(value) > 15 and value[14] == ".":
            fraction = value[15:].ljust(6, "0")[:6]
            timestamp = timestamp.replace(microsecond=int(fraction))
        return timestamp
    return None


def parse_mdtm_response(response):
    parts = response.split()
    if len(parts) < 2:
        return None
    return parse_mlsd_timestamp(parts[1])


def facts_timestamp(facts, key):
    if not facts:
        return None
    return parse_mlsd_timestamp(facts.get(key))


def list_directory_entries(ftp):
    try:
        return [(name, facts) for name, facts in ftp.mlsd()], True
    except ftplib.error_perm:
        logger.debug("MLSD not supported in %s, falling back to NLST", ftp.pwd())
        return [(name, None) for name in ftp.nlst()], False


def entry_is_directory(ftp, name, facts):
    if facts:
        entry_type = facts.get("type")
        if entry_type == "dir":
            return True
        if entry_type == "file":
            return False
    current = ftp.pwd()
    try:
        ftp.cwd(name)
        ftp.cwd(current)
        return True
    except ftplib.error_perm:
        ftp.cwd(current)
        return False


def get_file_metadata(ftp, name, facts):
    modified = facts_timestamp(facts, "modify")
    created = facts_timestamp(facts, "create")
    size = 0
    if facts and facts.get("size") is not None:
        try:
            size = int(facts["size"])
        except (TypeError, ValueError):
            size = 0
    if modified is None:
        try:
            modified = parse_mdtm_response(ftp.sendcmd("MDTM " + name))
        except ftplib.error_perm:
            modified = None
    if size == 0:
        try:
            file_size = ftp.size(name)
            if file_size is not None:
                size = int(file_size)
        except (ftplib.error_perm, TypeError, ValueError):
            size = 0
    if created is None:
        created = modified
    return created, modified, size


def make_scan_entry(entry_type, display_path, created, modified, size):
    is_folder = entry_type == "folder"
    return {
        "type": entry_type,
        "is_folder": is_folder,
        "path": display_path,
        "created": created,
        "modified": modified,
        "size": size,
    }


def report_entry_counts_stderr(parsed):
    sys.stderr.write(
        "Directories: {}  Files: {}\n".format(
            parsed["number_dirs"],
            parsed["number_files"],
        )
    )
    sys.stderr.flush()


class ScanStatus:
    """Live stderr status for recursive FTP scans."""

    def __init__(self, show_status=True, show_progress=False, width=40):
        self.show_status = show_status
        self.show_progress = show_progress
        self.width = width
        self.number_dirs = 0
        self.number_files = 0
        self.total_entries = 0
        self._last_width = 0

    def note_entry(self, entry):
        if entry["is_folder"]:
            self.number_dirs += 1
        else:
            self.number_files += 1
        self.total_entries += 1
        if self.show_status or self.show_progress:
            self._render()

    def close(self):
        if not (self.show_status or self.show_progress):
            return
        self._render(done=True)
        sys.stderr.write("\n")
        sys.stderr.flush()

    def _render(self, done=False):
        parts = ["Scanning FTP"]
        if self.show_progress:
            marker_pos = self.total_entries % self.width
            segment = min(3, self.width - marker_pos)
            bar = (
                " " * marker_pos
                + "=" * segment
                + " " * (self.width - marker_pos - segment)
            )
            parts.append("[{}]".format(bar))
        if self.show_status:
            parts.append(
                "{} directories, {} files".format(
                    self.number_dirs, self.number_files
                )
            )
        message = " ".join(parts)
        if done:
            message += " complete"
        sys.stderr.write(
            "\r{:<{width}}".format(
                message, width=max(self._last_width, len(message))
            )
        )
        sys.stderr.flush()
        self._last_width = max(self._last_width, len(message))


def ftp_recursive_scan(
    ftp,
    remote_root,
    display_root="/",
    recursive=True,
    show_status=True,
    show_progress=False,
):
    entries = []
    number_dirs = 0
    number_files = 0
    files_size = 0
    status = ScanStatus(
        show_status=show_status,
        show_progress=show_progress,
    )

    def add_entry(entry):
        nonlocal number_dirs, number_files, files_size
        entries.append(entry)
        if entry["is_folder"]:
            number_dirs += 1
        else:
            number_files += 1
            files_size += entry["size"]
        status.note_entry(entry)

    def scan(remote_dir, display_dir, first=False):
        starting_cwd = ftp.pwd()
        logger.debug("Scanning remote directory %s", remote_dir)
        try:
            ftp.cwd(remote_dir)
            if first:
                root_display = normalize_display_path(display_dir)
                if not root_display.endswith("/"):
                    root_display += "/"
                add_entry(
                    make_scan_entry("folder", root_display, None, None, 0)
                )

            items, used_mlsd = list_directory_entries(ftp)
            if not used_mlsd:
                logger.info("Using NLST/MDTM/SIZE fallback for %s", remote_dir)

            for name, facts in items:
                if name in (".", ".."):
                    continue

                is_dir = entry_is_directory(ftp, name, facts)
                display_path = build_display_path(display_dir, name, is_dir)

                if is_dir:
                    created = facts_timestamp(facts, "create")
                    modified = facts_timestamp(facts, "modify")
                    if modified is None:
                        modified = created
                    if created is None:
                        created = modified
                    add_entry(
                        make_scan_entry(
                            "folder", display_path, created, modified, 0
                        )
                    )
                    if recursive:
                        scan(
                            remote_dir.rstrip("/") + "/" + name,
                            display_path.rstrip("/"),
                        )
                        ftp.cwd(remote_dir)
                else:
                    created, modified, size = get_file_metadata(ftp, name, facts)
                    add_entry(
                        make_scan_entry(
                            "file", display_path, created, modified, size
                        )
                    )
        finally:
            ftp.cwd(starting_cwd)

    try:
        scan(
            remote_root,
            normalize_display_path(display_root),
            first=True,
        )
    finally:
        status.close()

    return {
        "entries": entries,
        "number_dirs": number_dirs,
        "number_files": number_files,
        "files_size": files_size,
    }


def human_bytes(size):
    if size < 1024:
        return "{} B".format(size)
    value = float(size)
    for unit in ("KB", "MB", "GB", "TB", "PB"):
        value /= 1024.0
        if value < 1024.0:
            return "{:.1f} {}".format(value, unit)
    return "{:.1f} EB".format(value / 1024.0)


class ProgressBar:
    """Simple stderr progress bar (no external dependencies)."""

    def __init__(self, label, total=None, enabled=True, width=40):
        self.label = label
        self.total = total
        self.current = 0
        self.enabled = enabled
        self.width = width
        self._last_width = 0

    def update(self, amount=1):
        if not self.enabled:
            return
        self.current += amount
        self._render()

    def close(self):
        if not self.enabled:
            return
        self._render(done=True)
        sys.stderr.write("\n")
        sys.stderr.flush()

    def _render(self, done=False):
        if self.total and self.total > 0:
            ratio = min(self.current / self.total, 1.0)
            filled = int(self.width * ratio)
            if filled >= self.width:
                bar = "=" * self.width
            else:
                bar = "=" * filled + ">" + " " * (self.width - filled - 1)
            message = "{} [{}] {} / {} ({:.0f}%)".format(
                self.label,
                bar,
                human_bytes(self.current),
                human_bytes(self.total),
                ratio * 100,
            )
        else:
            marker_pos = int((self.current / max(65536, 1)) % self.width)
            segment = min(3, self.width - marker_pos)
            bar = " " * marker_pos + "=" * segment + " " * (self.width - marker_pos - segment)
            suffix = human_bytes(self.current)
            if done:
                suffix += " complete"
            message = "{} [{}] {}".format(self.label, bar, suffix)

        sys.stderr.write("\r{:<{width}}".format(message, width=max(self._last_width, len(message))))
        sys.stderr.flush()
        self._last_width = max(self._last_width, len(message))


def parse_fastdir_line(line):
    """Parse one FastDir line (from TSD_Process.Parse_Fast_Dir)."""
    split_line = line.split("|")
    if len(split_line) < 6:
        logger.warning("Did not get a full FastDir line: %s", line)
        return None

    entry_type = split_line[0]
    if entry_type == "folder":
        is_folder = True
    elif entry_type == "file":
        is_folder = False
    else:
        logger.warning("Invalid type field in line: %s", line)
        return None

    def parse_timestamp(value):
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")

    directory, name = os.path.split(split_line[5])
    if directory.startswith("/"):
        directory = directory[1:]

    return {
        "type": entry_type,
        "is_folder": is_folder,
        "id": split_line[1],
        "created": parse_timestamp(split_line[2]),
        "modified": parse_timestamp(split_line[3]),
        "size": int(split_line[4]),
        "path": split_line[5],
        "directory": directory,
        "name": name,
    }


def parse_fastdir_response(text, show_progress=False):
    """Parse a FastDir BEGIN/END block (from TSD_Process.Load_TSD_FastDir)."""
    entries = []
    number_dirs = 0
    number_files = 0
    files_size = 0
    lines = text.splitlines()
    if not lines or lines[0].strip() != "BEGIN":
        raise ValueError("FastDir response did not start with BEGIN")

    content_lines = []
    for line in lines[1:]:
        line = line.strip()
        if line and line != "END":
            content_lines.append(line)

    progress = ProgressBar(
        "Parsing FastDir",
        total=len(content_lines),
        enabled=show_progress and len(content_lines) > 0,
    )
    try:
        for line in content_lines:
            entry = parse_fastdir_line(line)
            progress.update(1)
            if entry is None:
                continue
            entries.append(entry)
            if entry["is_folder"]:
                number_dirs += 1
            else:
                number_files += 1
                files_size += entry["size"]
    finally:
        progress.close()

    return {
        "entries": entries,
        "number_dirs": number_dirs,
        "number_files": number_files,
        "files_size": files_size,
    }


def print_table(headers, rows):
    str_rows = [[str(cell) for cell in row] for row in rows]
    widths = [len(header) for header in headers]
    for row in str_rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    def format_row(cells):
        return "  ".join(cell.ljust(widths[index]) for index, cell in enumerate(cells))

    print(format_row(headers))
    print(format_row(["-" * width for width in widths]))
    for row in str_rows:
        print(format_row(row))


def report_fastdir_table(parsed):
    headers = ["Type", "Path", "Size", "Created", "Modified"]
    rows = []
    for entry in parsed["entries"]:
        size = "-" if entry["is_folder"] else human_bytes(entry["size"])
        rows.append(
            [
                entry["type"],
                entry["path"],
                size,
                format_timestamp(entry["created"]),
                format_timestamp(entry["modified"]),
            ]
        )
    print_table(headers, rows)
    print()
    print("Total file size: {}".format(human_bytes(parsed["files_size"])))


def parse_site_response(response):
    """Extract JSON or text from an FTP SITE command response."""
    code = None
    body = response
    if response and response[:3].isdigit():
        code = int(response[:3])
        body = response[4:] if len(response) > 4 else ""
    logger.debug("Parsed response code=%s body_len=%d", code, len(body))
    if body:
        logger.debug("Response body preview: %r", body[:500])
    try:
        return code, json.loads(body)
    except (TypeError, json.JSONDecodeError):
        return code, body


def build_fastdir_argument(
    org, path="/", filespace="TrimbleSynchronizerData", recursive="true"
):
    """Build the SITE sub-command argument for TCCAPISTREAM FastDir."""
    params = (
        "Path={}&OrgShortName={}&FileSpaceShortName={}&Recursive={}".format(
            quote(path, safe=""),
            quote(org, safe=""),
            quote(filespace, safe=""),
            quote(recursive, safe=""),
        )
    )
    logger.debug(
        "FastDir params (decoded): Path=%r OrgShortName=%r FileSpaceShortName=%r Recursive=%r",
        path,
        org,
        filespace,
        recursive,
    )
    return "TCCAPISTREAM FastDir {}".format(params)


def read_stream_response(ftp, site_argument, show_progress=False):
    """Read a TCCAPISTREAM response from the FTP data connection."""
    site_cmd = "SITE {}".format(site_argument)
    logger.info("Sending: %s", site_cmd)
    conn, expected_size = ftp.ntransfercmd(site_cmd)
    logger.debug(
        "Data connection open (expected_size=%s)", expected_size
    )
    progress = ProgressBar(
        "Downloading FastDir",
        total=expected_size if expected_size and expected_size > 0 else None,
        enabled=show_progress,
    )
    chunks = []
    try:
        while True:
            block = conn.recv(65536)
            if not block:
                break
            chunks.append(block)
            progress.update(len(block))
            logger.debug(
                "Read %d bytes from stream (%d total)",
                len(block),
                sum(len(c) for c in chunks),
            )
    finally:
        progress.close()
        conn.close()
    ftp.voidresp()
    payload = b"".join(chunks)
    logger.info("Stream read complete (%d bytes)", len(payload))
    return payload.decode("utf-8", errors="replace")


def send_site_command(ftp, site_argument, show_progress=False):
    """Run SITE TCCAPISTREAM; read streamed body when the server opens a data conn."""
    site_cmd = "SITE {}".format(site_argument)
    try:
        return read_stream_response(ftp, site_argument, show_progress=show_progress)
    except ftplib.error_perm as exc:
        logger.debug(
            "Stream transfer failed (%s); falling back to control-channel sendcmd",
            exc,
        )
        response = ftp.sendcmd(site_cmd)
        logger.debug("sendcmd response: %r", response)
        return response


def main():
    args = process_args(parse_args())
    host = "{}.myconnectedsite.com".format(args.org)
    login_user = "{}.{}".format(args.user, args.org)
    site_argument = build_fastdir_argument(
        args.org,
        path=args.path,
        filespace=args.filespace,
        recursive=args.recursive,
    )

    logger.info("Target host: %s", host)
    logger.info("Login user: %s", login_user)
    logger.info("SITE argument: %s", site_argument)
    logger.debug("Timeout: %ss", args.timeout)

    try:
        logger.debug("Opening FTP connection to %s", host)
        ftp = ftplib.FTP(timeout=args.timeout)
        if args.verbose >= 3:
            ftp.set_debuglevel(2)
            logger.debug("FTP wire-level debug enabled")
        ftp.connect(host)
        logger.info("Connected to %s", host)
        logger.debug("Server welcome: %s", ftp.getwelcome())
    except OSError:
        logger.exception("Could not connect to %s", host)
        sys.exit("ERROR - Could not connect to {}".format(host))

    try:
        logger.debug("Logging in as %s", login_user)
        ftp.login(login_user, args.password)
        logger.info("FTP login successful")
        logger.debug("Current directory after login: %s", ftp.pwd())
    except ftplib.error_perm as exc:
        logger.exception("FTP login failed: %s", exc)
        sys.exit(
            "ERROR - Invalid FTP authentication for {} ({})".format(login_user, exc)
        )
    except OSError:
        logger.exception("FTP login failed")
        sys.exit("ERROR - FTP login failed")

    show_progress = args.progress and args.verbose < 3 and not args.debug
    recursive = recursive_enabled(args.recursive)
    parsed = None

    try:
        if args.ftp_scan:
            remote_root = build_remote_scan_root(
                args.org, args.filespace, args.path
            )
            logger.info("Running recursive FTP scan of %s", remote_root)
            ftp.sendcmd("TYPE I")
            parsed = ftp_recursive_scan(
                ftp,
                remote_root,
                display_root=args.path,
                recursive=recursive,
                show_status=True,
                show_progress=show_progress,
            )
            print("FTP scan of {}:".format(remote_root))
            report_fastdir_table(parsed)
        else:
            logger.info("Running SITE TCCAPISTREAM FastDir")
            response = send_site_command(
                ftp, site_argument, show_progress=show_progress
            )
            logger.info("SITE command completed")
            logger.debug("Raw response: %r", response)
            code, data = parse_site_response(response)
            if code is not None:
                logger.info("FTP response code: %s", code)
            print("FastDir response from {}:".format(host))
            logger.info("SITE %s", site_argument)
            if isinstance(data, str) and data.strip().startswith("BEGIN"):
                try:
                    parsed = parse_fastdir_response(
                        data, show_progress=show_progress
                    )
                    report_fastdir_table(parsed)
                    if args.verbose >= 2:
                        print()
                        print("Raw FastDir response:")
                        print(data)
                except ValueError as exc:
                    logger.error("%s", exc)
                    print(data)
            elif isinstance(data, (dict, list)):
                pprint(data)
            else:
                print(data)
        if parsed is not None:
            report_entry_counts_stderr(parsed)
    except ftplib.error_perm as exc:
        logger.exception("FTP operation failed: %s", exc)
        sys.exit("ERROR - FTP operation failed: {}".format(exc))
    except OSError:
        logger.exception("FTP operation failed")
        sys.exit("ERROR - FTP operation failed")
    finally:
        try:
            logger.debug("Closing FTP session")
            ftp.quit()
            logger.debug("FTP session closed")
        except OSError:
            logger.debug("FTP quit raised OSError (connection may already be closed)")


if __name__ == "__main__":
    main()
