"""Tests for PackageService."""
import io
import os
import zipfile

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.skills.package_service import PackageService


def _make_zip(files: dict[str, str | bytes]) -> SimpleUploadedFile:
    """Build a ZIP in memory with given files."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            data = content.encode() if isinstance(content, str) else content
            zf.writestr(name, data)
    buf.seek(0)
    return SimpleUploadedFile("test.zip", buf.read(), content_type="application/zip")


VALID_SKILL_MD = """---
name: My Skill
description: A test skill
version: "1.0.0"
category: CODE_DEV
---

# My Skill

This is a **test** skill README.
"""


class TestProcessUpload:
    def test_valid_zip(self):
        f = _make_zip({"SKILL.md": VALID_SKILL_MD})
        result = PackageService.process_upload(f)
        assert result["version"] == "1.0.0"
        assert "<strong>test</strong>" in result["readme_html"] or "<b>test</b>" in result["readme_html"]
        assert result["package_sha256"]
        assert len(result["package_sha256"]) == 64
        assert result["package_size"] > 0
        assert result.get("name") == "My Skill"
        assert result.get("category") == "CODE_DEV"

    def test_missing_skill_md(self):
        f = _make_zip({"README.md": "hello"})
        with pytest.raises(ValueError, match="SKILL.md"):
            PackageService.process_upload(f)

    def test_skill_md_in_subdirectory(self):
        f = _make_zip({"my-skill/SKILL.md": VALID_SKILL_MD})
        result = PackageService.process_upload(f)
        assert result["version"] == "1.0.0"

    def test_invalid_zip(self):
        f = SimpleUploadedFile("bad.zip", b"not a zip", content_type="application/zip")
        with pytest.raises(ValueError, match="ZIP"):
            PackageService.process_upload(f)

    def test_missing_frontmatter(self):
        skill_md = "# No frontmatter\n\nJust markdown."
        f = _make_zip({"SKILL.md": skill_md})
        with pytest.raises(ValueError, match="frontmatter"):
            PackageService.process_upload(f)

    def test_missing_required_frontmatter_field(self):
        skill_md = "---\nname: test\n---\nBody"
        f = _make_zip({"SKILL.md": skill_md})
        with pytest.raises(ValueError, match="缺少必填字段"):
            PackageService.process_upload(f)


class TestValidateZipSafety:
    def test_path_traversal_rejected(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("../etc/passwd", "bad")
        buf.seek(0)
        f = SimpleUploadedFile("evil.zip", buf.read(), content_type="application/zip")
        with pytest.raises(ValueError, match="非法路径"):
            PackageService.process_upload(f)

    def test_forbidden_extension_rejected(self):
        f = _make_zip({
            "SKILL.md": VALID_SKILL_MD,
            "payload.exe": "bad binary",
        })
        with pytest.raises(ValueError, match="被禁止的文件类型"):
            PackageService.process_upload(f)

    def test_too_many_files_rejected(self):
        files = {"SKILL.md": VALID_SKILL_MD}
        for i in range(60):
            files[f"file_{i}.txt"] = f"content {i}"
        f = _make_zip(files)
        with pytest.raises(ValueError, match="文件数量"):
            PackageService.process_upload(f)


class TestExtractFileContents:
    def test_extracts_text_files(self):
        f = _make_zip({
            "SKILL.md": VALID_SKILL_MD,
            "script.py": "print('hello')",
            "data.json": '{"key": "value"}',
            "image.png": b"\x89PNG\r\n",
        })
        contents = PackageService.extract_file_contents(f)
        assert "SKILL.md" in contents
        assert "script.py" in contents
        assert "data.json" in contents
        assert "image.png" not in contents
