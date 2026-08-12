from app.github.diff import parse_file_diff


def test_parse_file_diff_maps_added_lines_to_github_positions() -> None:
    diff = parse_file_diff(
        {
            "filename": "app/example.py",
            "status": "modified",
            "patch": (
                "@@ -1,3 +1,4 @@\n import os\n-old = 1\n+new = 1\n"
                "+danger = eval(user_input)\n keep = True"
            ),
        }
    )

    assert diff.contains_line(2)
    assert diff.contains_line(3)
    assert diff.position_for_line(2) == 3
    assert diff.position_for_line(3) == 4
    assert not diff.contains_line(4)


def test_parse_file_diff_ignores_binary_or_missing_patch() -> None:
    diff = parse_file_diff({"filename": "image.png", "status": "modified"})

    assert diff.additions == set()
    assert diff.positions == {}
