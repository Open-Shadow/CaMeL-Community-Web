"""Package upload, validation, and download helpers."""
import hashlib
import os
import tempfile
import zipfile
from pathlib import Path

import markdown
import nh3
import yaml
from django.core.files.uploadedfile import UploadedFile

from common.constants import (
    FORBIDDEN_EXTENSIONS,
    MAX_PACKAGE_FILE_COUNT,
    MAX_PACKAGE_FILE_SIZE,
    MAX_PACKAGE_SIZE,
    PACKAGE_PRESIGNED_URL_EXPIRY,
)


class PackageService:
    """Handle ZIP package upload, validation, parsing, and download."""

    @classmethod
    def process_upload(cls, uploaded: UploadedFile) -> dict:
        """Validate and process an uploaded ZIP file.

        Returns a dict with keys:
            package_file, package_sha256, package_size, readme_html, version,
            and any metadata from SKILL.md frontmatter.
        """
        if uploaded.size > MAX_PACKAGE_SIZE:
            raise ValueError(f"文件包不得超过 {MAX_PACKAGE_SIZE // (1024 * 1024)} MB")

        # Read file content and compute hash
        content = uploaded.read()
        sha256 = hashlib.sha256(content).hexdigest()
        uploaded.seek(0)

        # Validate ZIP structure
        if not zipfile.is_zipfile(uploaded):
            raise ValueError("上传文件不是有效的 ZIP 格式")
        uploaded.seek(0)

        with tempfile.TemporaryDirectory() as tmpdir:
            with zipfile.ZipFile(uploaded) as zf:
                cls._validate_zip_safety(zf)
                zf.extractall(tmpdir)

            # Find SKILL.md (could be at root or in a single subdirectory)
            skill_md_path = cls._find_skill_md(tmpdir)
            if not skill_md_path:
                raise ValueError("ZIP 包必须包含 SKILL.md 文件")

            frontmatter, body = cls._parse_skill_md(skill_md_path)
            readme_html = cls._render_markdown(body)

        uploaded.seek(0)
        result = {
            "package_file": uploaded,
            "package_sha256": sha256,
            "package_size": len(content),
            "readme_html": readme_html,
            "version": frontmatter.get("version", "1.0.0"),
        }

        # Pass through frontmatter metadata for auto-fill
        for key in ("name", "description", "category", "tags", "output_format", "example_input", "example_output"):
            if key in frontmatter:
                result.setdefault(key, frontmatter[key])

        return result

    @classmethod
    def _validate_zip_safety(cls, zf: zipfile.ZipFile):
        """Check for path traversal, forbidden extensions, file limits, zip bombs."""
        infos = zf.infolist()
        if len(infos) > MAX_PACKAGE_FILE_COUNT:
            raise ValueError(f"文件包内文件数量不得超过 {MAX_PACKAGE_FILE_COUNT}")

        total_size = 0
        for info in infos:
            # Reject directories that look like symlinks
            if info.external_attr >> 28 == 0xA:
                raise ValueError("ZIP 包不允许包含符号链接")

            # Path traversal check
            normalized = os.path.normpath(info.filename)
            if normalized.startswith("..") or normalized.startswith("/"):
                raise ValueError(f"ZIP 包含非法路径：{info.filename}")

            # Forbidden extensions
            _, ext = os.path.splitext(info.filename.lower())
            if ext in FORBIDDEN_EXTENSIONS:
                raise ValueError(f"ZIP 包含被禁止的文件类型：{ext}")

            # Single file size
            if info.file_size > MAX_PACKAGE_FILE_SIZE:
                raise ValueError(
                    f"文件 {info.filename} 超过 {MAX_PACKAGE_FILE_SIZE // (1024 * 1024)} MB 限制"
                )

            total_size += info.file_size

        # Zip bomb check (compressed vs uncompressed ratio)
        compressed_size = sum(i.compress_size for i in infos)
        if compressed_size > 0 and total_size / compressed_size > 100:
            raise ValueError("ZIP 文件疑似压缩炸弹")

    @staticmethod
    def _find_skill_md(extracted_dir: str) -> str | None:
        """Find SKILL.md at root or inside a single top-level directory."""
        root = Path(extracted_dir)
        direct = root / "SKILL.md"
        if direct.exists():
            return str(direct)

        # Check single subdirectory
        subdirs = [p for p in root.iterdir() if p.is_dir()]
        if len(subdirs) == 1:
            nested = subdirs[0] / "SKILL.md"
            if nested.exists():
                return str(nested)
        return None

    @staticmethod
    def _parse_skill_md(path: str) -> tuple[dict, str]:
        """Parse YAML frontmatter and body from SKILL.md."""
        with open(path, encoding="utf-8") as f:
            content = f.read()

        if not content.startswith("---"):
            raise ValueError("SKILL.md 必须以 YAML frontmatter 开头 (---)")

        parts = content.split("---", 2)
        if len(parts) < 3:
            raise ValueError("SKILL.md frontmatter 格式不正确")

        try:
            frontmatter = yaml.safe_load(parts[1]) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"SKILL.md frontmatter YAML 解析失败：{e}")

        for required in ("name", "description", "version"):
            if required not in frontmatter:
                raise ValueError(f"SKILL.md frontmatter 缺少必填字段：{required}")

        body = parts[2].strip()
        return frontmatter, body

    @staticmethod
    def _render_markdown(text: str) -> str:
        """Render markdown body to sanitized HTML."""
        raw_html = markdown.markdown(
            text,
            extensions=["fenced_code", "tables", "toc"],
        )
        return nh3.clean(raw_html)

    @staticmethod
    def generate_download_url(file_name: str) -> str:
        """Generate a pre-signed download URL for a package file."""
        from django.conf import settings
        import boto3
        from botocore.config import Config

        if not getattr(settings, "AWS_STORAGE_BUCKET_NAME", ""):
            # Local development fallback
            return f"/media/{file_name}"

        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            endpoint_url=settings.AWS_S3_ENDPOINT_URL or None,
            config=Config(signature_version="s3v4"),
        )
        return s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                "Key": file_name,
            },
            ExpiresIn=PACKAGE_PRESIGNED_URL_EXPIRY,
        )

    @classmethod
    def extract_file_contents(cls, uploaded: UploadedFile) -> dict[str, str]:
        """Extract text file contents from a ZIP for scanning."""
        contents: dict[str, str] = {}
        uploaded.seek(0)
        with zipfile.ZipFile(uploaded) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                _, ext = os.path.splitext(info.filename.lower())
                if ext in (".txt", ".md", ".py", ".sh", ".bash", ".js", ".ts", ".yaml", ".yml", ".json"):
                    try:
                        contents[info.filename] = zf.read(info.filename).decode("utf-8", errors="replace")
                    except Exception:
                        pass
        uploaded.seek(0)
        return contents
