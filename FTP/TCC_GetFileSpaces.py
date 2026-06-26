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
        description="Connect to TCC via FTP and run site TCCAPISTREAM FastDir",
        epilog="""
   V1.1 (c) JCMBsoft 2026
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
        help="FastDir Path parameter (default: /)",
    )
    argp.add_argument(
        "--filespace",
        metavar="NAME",
        default="TrimbleSynchronizerData",
        help="FastDir FileSpaceShortName parameter (default: TrimbleSynchronizerData)",
    )
    argp.add_argument(
        "--recursive",
        metavar="BOOL",
        default="true",
        help="FastDir Recursive parameter (default: true)",
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
        "-P",
        "--progress",
        action="store_true",
        help="Show a progress bar while downloading and parsing FastDir data",
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
        sys.stderr.write("Timeout: {}s\n".format(args.timeout))
        sys.stderr.write("Verbose: {}\n".format(args.verbose))
        sys.stderr.write("Progress bar: {}\n".format(args.progress))
        sys.stderr.write("FTP wire debug: {}\n\n".format(args.verbose >= 3 or args.debug))

    return args


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
                entry["created"].strftime("%Y-%m-%d %H:%M:%S"),
                entry["modified"].strftime("%Y-%m-%d %H:%M:%S"),
            ]
        )
    print_table(headers, rows)
    print()
    print(
        "Folders: {}  Files: {}  Total file size: {}".format(
            parsed["number_dirs"],
            parsed["number_files"],
            human_bytes(parsed["files_size"]),
        )
    )


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

    try:
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
                parsed = parse_fastdir_response(data, show_progress=show_progress)
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
    except ftplib.error_perm as exc:
        logger.exception("SITE command failed: %s", exc)
        sys.exit("ERROR - SITE command failed: {}".format(exc))
    except OSError:
        logger.exception("SITE command failed")
        sys.exit("ERROR - SITE command failed")
    finally:
        try:
            logger.debug("Closing FTP session")
            ftp.quit()
            logger.debug("FTP session closed")
        except OSError:
            logger.debug("FTP quit raised OSError (connection may already be closed)")


if __name__ == "__main__":
    main()
