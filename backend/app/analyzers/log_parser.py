import re
from typing import List, Optional, Tuple

from app.models.schemas import ParsedError, StackFrame


class LogParser:
    """Pure Python log parser for extracting error signatures and stack traces from CI logs."""

    # ANSI escape code stripper
    ANSI_REGEX = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")

    # Leading ISO-8601 timestamp stripper from GitHub Actions log lines
    TIMESTAMP_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z\s*")

    # Dynamic Exception Type match (supports any StandardError, CustomException, etc.)
    # Matches lines like:
    # E   ModuleNotFoundError: No module named 'terraform_validator'
    # E   AssertionError: Calculation regression: expected 5, got 4
    # ValueError: Required environment variable 'APP_CONFIG_PATH' is missing
    # SyntaxError: '(' was never closed
    EXCEPTION_LINE_REGEX = re.compile(
        r"^(?:E\s+)?([A-Z][a-zA-Z0-9_]*(?:Error|Exception|Failure|Fault|Warning)):?\s*(.*)$"
    )

    # Standard python traceback frame: File "/path/to/file.py", line 26, in func
    STACK_FRAME_REGEX = re.compile(
        r'File\s+"(?P<file>[^"]+)",\s+line\s+(?P<line>\d+)(?:,\s+in\s+(?P<func>\w+))?'
    )

    # Pytest short traceback file/line reference: src/calculator.py:26: ModuleNotFoundError
    PYTEST_LOC_REGEX = re.compile(
        r"^(?P<file>[a-zA-Z0-9_\-\./\\]+\.py):(?P<line>\d+):(?:\s*(?P<extra>.*))?$"
    )

    # Pytest failed test summary with parameterization support:
    # FAILED tests/test_calculator.py::test_add[2-3] - AssertionError: ...
    # FAILED tests/scenarios/test_assertion_failure.py::test_assertion_scenario
    FAILED_TEST_REGEX = re.compile(
        r"FAILED\s+(?P<test_path>[a-zA-Z0-9_\-\./\\]+)::(?P<test_name>[a-zA-Z0-9_]+)(?:\[(?P<params>[^\]]*)\])?"
    )

    # GitHub Actions workflow step group headers
    STEP_HEADER_REGEX = re.compile(r"^##\[group\]Run\s+(.*)$")

    # Sensitive credential redaction patterns
    CREDENTIAL_PATTERNS = [
        re.compile(r"(ghp_[a-zA-Z0-9_]{30,})"),
        re.compile(r"(github_pat_[a-zA-Z0-9_]{50,})"),
        re.compile(r"(Bearer\s+)[a-zA-Z0-9_\-\.]{15,}"),
        re.compile(r"((?:token|secret|password|api_key|access_key)\s*[:=]\s*)[^\s,;]+", re.IGNORECASE),
        re.compile(r"(AKIA[0-9A-Z]{16})"),
    ]

    def redact_sensitive(self, text: str) -> str:
        """Sanitize tokens, API keys, and sensitive auth strings from log text."""
        sanitized = text
        for pattern in self.CREDENTIAL_PATTERNS:
            sanitized = pattern.sub(r"\1[REDACTED]" if r"\1" in pattern.pattern else "[REDACTED]", sanitized)
        return sanitized

    def clean_line(self, line: str) -> str:
        """Strip ANSI escape sequences, timestamps, and trailing whitespace."""
        stripped_ansi = self.ANSI_REGEX.sub("", line)
        stripped_time = self.TIMESTAMP_REGEX.sub("", stripped_ansi)
        return self.redact_sensitive(stripped_time.rstrip())

    def normalize_signature(self, error_type: str, message: str) -> str:
        """Generate a canonical, normalized error signature for correlation and clustering."""
        clean_msg = message.strip()

        if error_type == "ModuleNotFoundError":
            pkg_match = re.search(r"No module named '([^']+)'", clean_msg)
            pkg = pkg_match.group(1) if pkg_match else "<package>"
            return f"ModuleNotFoundError: No module named '{pkg}'"

        if error_type == "ImportError":
            return f"ImportError: {clean_msg}"

        if error_type == "AssertionError":
            # Strip variable noise to produce canonical assert signature
            if "assert " in clean_msg:
                assert_part = clean_msg.split("assert ")[-1].strip()
                return f"AssertionError: assert {assert_part}"
            return f"AssertionError: {clean_msg[:80]}" if clean_msg else "AssertionError"

        if error_type == "SyntaxError":
            return f"SyntaxError: {clean_msg}"

        if error_type == "ValueError":
            return f"ValueError: {clean_msg[:80]}"

        return f"{error_type}: {clean_msg[:80]}" if clean_msg else error_type

    def parse(
        self,
        raw_logs: str,
        failed_step_hint: Optional[str] = None,
        is_truncated: bool = False,
    ) -> ParsedError:
        """Parse raw log text and extract structured error metadata."""
        if not raw_logs or not raw_logs.strip():
            return ParsedError(
                has_error=False,
                error_type=None,
                error_message="Empty log stream provided.",
                normalized_signature=None,
                is_truncated=is_truncated,
            )

        raw_lines = raw_logs.splitlines()
        cleaned_lines = [self.clean_line(l) for l in raw_lines]

        error_type: Optional[str] = None
        error_message: Optional[str] = None
        error_line_idx: Optional[int] = None
        failed_test: Optional[str] = None
        file_reference: Optional[str] = None
        line_number: Optional[int] = None
        detected_step: Optional[str] = failed_step_hint
        stack_frames: List[StackFrame] = []

        # Pass 1: Backward search for the primary failure locus and failed test
        for i in range(len(cleaned_lines) - 1, -1, -1):
            line = cleaned_lines[i]

            # Detect pytest FAILED test line
            if not failed_test:
                test_match = self.FAILED_TEST_REGEX.search(line)
                if test_match:
                    tpath = test_match.group("test_path")
                    tname = test_match.group("test_name")
                    tparam = test_match.group("params")
                    failed_test = f"{tpath}::{tname}[{tparam}]" if tparam else f"{tpath}::{tname}"

            # Detect primary Exception line (prefer innermost or summary exception)
            if not error_type:
                exc_match = self.EXCEPTION_LINE_REGEX.match(line)
                if exc_match:
                    candidate_type = exc_match.group(1)
                    candidate_msg = exc_match.group(2).strip()
                    # Exclude non-terminal warning notices
                    if candidate_type not in ("DeprecationWarning", "UserWarning", "PendingDeprecationWarning"):
                        error_type = candidate_type
                        error_message = candidate_msg
                        error_line_idx = i

            # Detect step header if no hint was provided
            if not detected_step and "##[error]" in line:
                for k in range(i, -1, -1):
                    header_match = self.STEP_HEADER_REGEX.match(cleaned_lines[k])
                    if header_match:
                        detected_step = header_match.group(1).strip()
                        break

        # Pass 2: Forward extraction of stack frames and file references
        # In tracebacks, the innermost application frame is the last frame before the exception
        for i, line in enumerate(cleaned_lines):
            # Match standard Python traceback frames: File "...", line X, in Y
            frame_match = self.STACK_FRAME_REGEX.search(line)
            if frame_match:
                fname = frame_match.group("file")
                fline = int(frame_match.group("line"))
                ffunc = frame_match.group("func")
                code_context = cleaned_lines[i + 1].strip() if i + 1 < len(cleaned_lines) else None
                stack_frames.append(
                    StackFrame(file=fname, line=fline, function=ffunc, code_context=code_context)
                )
                if "site-packages" not in fname and "_pytest" not in fname:
                    file_reference = fname
                    line_number = fline

            # Match pytest location format: tests/test.py:8: AssertionError or src/calculator.py:26: in load_external_yaml
            loc_match = self.PYTEST_LOC_REGEX.match(line)
            if loc_match:
                fname = loc_match.group("file")
                fline = int(loc_match.group("line"))
                if "site-packages" not in fname and "_pytest" not in fname:
                    file_reference = fname
                    line_number = fline

        if not error_type:
            # Fallback search for general error indicator if no Python exception matched
            for i in range(len(cleaned_lines) - 1, -1, -1):
                line = cleaned_lines[i]
                if "##[error]" in line or "FAILED " in line or "Error: " in line:
                    error_type = "BuildFailure"
                    error_message = line.replace("##[error]", "").strip()
                    error_line_idx = i
                    break

        if not error_type:
            return ParsedError(
                has_error=False,
                error_type=None,
                error_message=None,
                normalized_signature=None,
                failed_step=detected_step,
                is_truncated=is_truncated,
            )

        # Context lines extraction: up to 10 lines before and 10 lines after the error
        context_lines: List[str] = []
        if error_line_idx is not None:
            start_idx = max(0, error_line_idx - 10)
            end_idx = min(len(cleaned_lines), error_line_idx + 11)
            context_lines = [cleaned_lines[idx] for idx in range(start_idx, end_idx) if cleaned_lines[idx]]

        normalized_sig = self.normalize_signature(error_type, error_message or "")

        return ParsedError(
            has_error=True,
            error_type=error_type,
            error_message=error_message or "",
            normalized_signature=normalized_sig,
            failed_step=detected_step,
            failed_test=failed_test,
            file_reference=file_reference,
            line_number=line_number,
            stack_trace=stack_frames,
            context_lines=context_lines,
            is_truncated=is_truncated,
        )
