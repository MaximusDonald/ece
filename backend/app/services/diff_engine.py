"""Diff engine for comparing report versions."""
import difflib
from typing import List, Dict, Any


class DiffLine:
    def __init__(self, type: str, content: str, line_number_old: int = None, line_number_new: int = None):
        self.type = type  # "added", "removed", "unchanged", "modified"
        self.content = content
        self.line_number_old = line_number_old
        self.line_number_new = line_number_new
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "content": self.content,
            "line_number_old": self.line_number_old,
            "line_number_new": self.line_number_new,
        }


def compute_diff(old_text: str, new_text: str) -> List[DiffLine]:
    """Compute line-level diff between two texts."""
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)
    
    diff = difflib.SequenceMatcher(None, old_lines, new_lines)
    result = []
    
    old_line_num = 1
    new_line_num = 1
    
    for tag, i1, i2, j1, j2 in diff.get_opcodes():
        if tag == "equal":
            for k in range(i1, i2):
                result.append(DiffLine("unchanged", old_lines[k], old_line_num, new_line_num))
                old_line_num += 1
                new_line_num += 1
        elif tag == "delete":
            for k in range(i1, i2):
                result.append(DiffLine("removed", old_lines[k], old_line_num, None))
                old_line_num += 1
        elif tag == "insert":
            for k in range(j1, j2):
                result.append(DiffLine("added", new_lines[k], None, new_line_num))
                new_line_num += 1
        elif tag == "replace":
            # Show as remove + add
            for k in range(i1, i2):
                result.append(DiffLine("removed", old_lines[k], old_line_num, None))
                old_line_num += 1
            for k in range(j1, j2):
                result.append(DiffLine("added", new_lines[k], None, new_line_num))
                new_line_num += 1
    
    return result


def compute_diff_summary(diff_lines: List[DiffLine]) -> Dict[str, int]:
    """Compute summary statistics from diff."""
    summary = {"added": 0, "removed": 0, "modified": 0, "unchanged": 0}
    for line in diff_lines:
        summary[line.type] = summary.get(line.type, 0) + 1
    return summary


def format_diff_for_display(diff_lines: List[DiffLine], context_lines: int = 3) -> List[DiffLine]:
    """Filter diff to show only changes with context."""
    if not diff_lines:
        return []
    
    # Find indices of changed lines
    changed_indices = [i for i, line in enumerate(diff_lines) if line.type != "unchanged"]
    if not changed_indices:
        return diff_lines[:context_lines * 2]  # Show only context if no changes
    
    # Determine range to show
    start = max(0, min(changed_indices) - context_lines)
    end = min(len(diff_lines), max(changed_indices) + context_lines + 1)
    
    return diff_lines[start:end]