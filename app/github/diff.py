from dataclasses import dataclass, field


@dataclass(frozen=True)
class DiffLine:
    new_line: int
    position: int
    content: str


@dataclass
class FileDiff:
    filename: str
    status: str
    patch: str
    additions: set[int] = field(default_factory=set)
    positions: dict[int, int] = field(default_factory=dict)

    def contains_line(self, line: int) -> bool:
        return line in self.additions

    def position_for_line(self, line: int) -> int | None:
        return self.positions.get(line)


def parse_file_diff(file_payload: dict) -> FileDiff:
    filename = file_payload["filename"]
    patch = file_payload.get("patch") or ""
    status = file_payload.get("status", "modified")
    result = FileDiff(filename=filename, status=status, patch=patch)
    if not patch:
        return result

    old_line = 0
    new_line = 0
    position = 0
    for raw_line in patch.splitlines():
        if raw_line.startswith("@@"):
            old_line, new_line = _parse_hunk_header(raw_line)
            continue
        position += 1
        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            result.additions.add(new_line)
            result.positions[new_line] = position
            new_line += 1
        elif raw_line.startswith("-") and not raw_line.startswith("---"):
            old_line += 1
        else:
            old_line += 1
            new_line += 1
    return result


def parse_pull_request_files(files: list[dict]) -> dict[str, FileDiff]:
    return {
        item["filename"]: parse_file_diff(item)
        for item in files
        if item.get("status") != "removed"
    }


def _parse_hunk_header(header: str) -> tuple[int, int]:
    # Example: @@ -10,7 +10,8 @@ optional context
    parts = header.split()
    old_start = int(parts[1].split(",")[0][1:])
    new_start = int(parts[2].split(",")[0][1:])
    return old_start, new_start
