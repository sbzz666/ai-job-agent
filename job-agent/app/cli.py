"""Small command-line interface for validating local tools."""

from __future__ import annotations

import argparse
import json

from app.services.resume_parser import ResumeParseError, parse_resume


def main() -> int:
    parser = argparse.ArgumentParser(description="离线解析 TXT/DOCX/PDF 简历")
    subparsers = parser.add_subparsers(dest="command", required=True)
    parse_command = subparsers.add_parser("parse", help="解析一份简历")
    parse_command.add_argument("path")
    parse_command.add_argument("--show-text", action="store_true", help="显示敏感正文")
    args = parser.parse_args()

    try:
        result = parse_resume(args.path)
    except ResumeParseError as exc:
        parser.error(str(exc))

    output = result.model_dump(exclude={"text"})
    if args.show_text:
        output["text"] = result.text
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
