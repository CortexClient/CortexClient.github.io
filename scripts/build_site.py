#!/usr/bin/env python3
"""Build a self-contained GitHub Pages artifact using only Python's standard library."""
from __future__ import annotations

import argparse
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET


class HeadMetadata(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_title = False
        self.title = ""
        self.description = ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self.in_title = True
        if tag == "meta" and attrs.get("name", "").lower() == "description":
            self.description = attrs.get("content", "")

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data


class TagAttributes(HTMLParser):
    def __init__(self, tag: str) -> None:
        super().__init__(convert_charrefs=True)
        self.attrs = {}
        self.feed(tag)

    def handle_starttag(self, tag, attrs):
        self.attrs = dict(attrs)


def replace_attribute(tag: str, name: str, value: str | None) -> str:
    pattern = rf"\s+{re.escape(name)}(?=\s|=|/?>)(?:\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>]+))?"
    tag = re.sub(pattern, "", tag, flags=re.I)
    if value is None:
        return tag
    return tag[:-1] + f' {name}="{html.escape(value, quote=True)}">'


def https_url(value: str, name: str, *, directory: bool = False) -> str:
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as error:
        raise ValueError(f"{name}: invalid URL") from error
    if (not value or re.search(r"[\s<>\\]", value) or parsed.scheme != "https"
            or not parsed.hostname or parsed.username or parsed.password
            or parsed.hostname in {"localhost", "example.com", "example.org", "example.net"}
            or parsed.hostname.endswith((".invalid", ".example"))):
        raise ValueError(f"{name}: use a real, absolute HTTPS URL without credentials")
    if directory and (parsed.query or parsed.fragment or any(part in {".", ".."} for part in parsed.path.split("/"))):
        raise ValueError(f"{name}: site address must not contain query, fragment or dot segments")
    return value.rstrip("/") + "/" if directory else value


def read_config(root: Path) -> dict:
    text = (root / "config.js").read_text(encoding="utf-8-sig")
    match = re.fullmatch(r"\s*window\.SITE_CONFIG\s*=\s*(\{.*\})\s*;?\s*", text, re.S)
    if not match:
        raise ValueError("config.js must contain window.SITE_CONFIG = { ... }; with valid JSON")
    config = json.loads(match.group(1))
    if not isinstance(config, dict) or not config.get("product"):
        raise ValueError("config.js: product is required")
    if any(not isinstance(value, str) for value in config.values()):
        raise ValueError("config.js: all configuration values must be strings")
    for field in ("downloadUrl", "releaseUrl"):
        if config.get(field):
            https_url(config[field], field)
    if config.get("sha256") and not re.fullmatch(r"[a-fA-F0-9]{64}", config["sha256"]):
        raise ValueError("config.js: sha256 must be empty or contain exactly 64 hexadecimal characters")
    return config


def prepare_html(source: str, config: dict, site_url: str, social_image: bool) -> str:
    head_match = re.search(r"<head\b[^>]*>(.*?)</head>", source, flags=re.I | re.S)
    if not head_match:
        raise ValueError("index.html: head element is missing")
    metadata = HeadMetadata()
    metadata.feed(head_match.group(1))
    title, description = metadata.title.strip(), metadata.description.strip()
    if not title or not description:
        raise ValueError("index.html must have a nonempty title and meta description")
    escaped = lambda value: html.escape(value, quote=True)
    schema = {
        "@context": "https://schema.org", "@type": "SoftwareApplication",
        "name": config["product"], "applicationCategory": "DeveloperApplication",
        "description": description, "url": site_url,
    }
    for key, target in (("downloadUrl", "downloadUrl"), ("version", "softwareVersion"), ("platform", "operatingSystem")):
        if config.get(key):
            schema[target] = config[key]

    # Replace all owned head metadata; this remains idempotent after repeated builds.
    head = re.sub(r"<!-- SEO_ORIGIN_START -->.*?<!-- SEO_ORIGIN_END -->", "", head_match.group(1), flags=re.S)
    head = re.sub(r"<script\b[^>]*>.*?</script>", lambda m: "" if TagAttributes(m.group(0).split(">", 1)[0] + ">").attrs.get("id") == "software-schema" else m.group(0), head, flags=re.I | re.S)
    def remove_owned_meta(match):
        attrs = TagAttributes(match.group(0)).attrs
        owned_meta = attrs.get("property", "").startswith("og:") or attrs.get("name", "").startswith("twitter:")
        canonical = "canonical" in attrs.get("rel", "").lower().split()
        return "" if owned_meta or canonical else match.group(0)
    head = re.sub(r"<(?:meta|link)\b[^>]*>", remove_owned_meta, head, flags=re.I)
    lines = ["<!-- SEO_ORIGIN_START -->", f'<link rel="canonical" href="{escaped(site_url)}">']
    metas = {
        "og:type": "website", "og:site_name": config["product"], "og:title": title,
        "og:description": description, "og:locale": "ru_RU", "og:url": site_url,
        "twitter:card": "summary_large_image" if social_image else "summary",
        "twitter:title": title, "twitter:description": description,
    }
    if social_image:
        image_url = site_url + "assets/social-card.png"
        metas.update({"og:image": image_url, "og:image:width": "1200", "og:image:height": "630", "og:image:type": "image/png", "og:image:alt": config["product"], "twitter:image": image_url, "twitter:image:alt": config["product"]})
        schema["image"] = image_url
    for name, value in metas.items():
        attribute = "property" if name.startswith("og:") else "name"
        lines.append(f'<meta {attribute}="{name}" content="{escaped(value)}">')
    lines.append("<!-- SEO_ORIGIN_END -->")
    schema_json = json.dumps(schema, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    lines.append(f'<script type="application/ld+json" id="software-schema">{schema_json}</script>')
    head = head.rstrip() + "\n" + "\n".join(lines) + "\n"
    result = source[:head_match.start(1)] + head + source[head_match.end(1):]

    def release_link(match):
        tag = match.group(0)
        attrs = TagAttributes(tag).attrs
        if "data-download" in attrs:
            url = config.get("downloadUrl", "")
            tag = replace_attribute(tag, "href", url or "#download")
            tag = replace_attribute(tag, "aria-disabled", None)
            tag = replace_attribute(tag, "download", config.get("fileName") if url else None)
        if "data-release" in attrs:
            url = config.get("releaseUrl", "")
            tag = replace_attribute(tag, "href", url or "#download")
            tag = replace_attribute(tag, "hidden", None if url else "")
        return tag
    result = re.sub(r"<a\b[^>]*>", release_link, result, flags=re.I)
    fields = {
        "version": config.get("version") or "В описании релиза",
        "platform": config.get("platform") or "В описании релиза",
        "fileName": config.get("fileName") or "Ожидает публикации",
        "fileSize": config.get("fileSize") or "Пока не указан",
        "sha256": config.get("sha256") or "Будет опубликован со сборкой",
        "downloadStatus": "Сборка доступна для загрузки" if config.get("downloadUrl") else "Готовим ссылку на сборку",
        "releaseHost": urlsplit(config["releaseUrl"]).hostname if config.get("releaseUrl") else "Будет указан с релизом",
    }
    for field, value in fields.items():
        pattern = rf'(<([a-z][\w:-]*)\b[^>]*\bdata-field=[\"\']{field}[\"\'][^>]*>).*?(</\2\s*>)'
        result = re.sub(pattern, lambda m: m.group(1) + escaped(value) + m.group(3), result, flags=re.I | re.S)
    unavailable = "Ссылка на сборку появится здесь вместе со сведениями о выпуске."
    available = "Кнопка ведёт на файл напрямую. JavaScript не требуется для скачивания."
    result = re.sub(r"<noscript>.*?</noscript>", "<noscript>" + (available if config.get("downloadUrl") else unavailable) + "</noscript>", result, flags=re.I | re.S)
    return result


def build(root: Path, origin: str | None) -> Path:
    root = root.resolve()
    config = read_config(root)
    site_url = https_url(origin or config.get("siteUrl", ""), "siteUrl / --site-url", directory=True)
    config["siteUrl"] = site_url
    source = (root / "index.html").read_text(encoding="utf-8-sig")
    social = root / "assets" / "social-card.png"
    if social.exists():
        import struct
        image = social.read_bytes()
        if image[:8] != b"\x89PNG\r\n\x1a\n" or len(image) < 24 or struct.unpack(">II", image[16:24]) != (1200, 630):
            raise ValueError("assets/social-card.png must be a 1200 x 630 PNG")
    prepared = prepare_html(source, config, site_url, social.is_file())
    error_page = (root / "404.html").read_text(encoding="utf-8-sig")
    error_page = re.sub(r"<a\b[^>]*>", lambda m: replace_attribute(m.group(0), "href", site_url) if "data-home" in TagAttributes(m.group(0)).attrs else m.group(0), error_page, flags=re.I)
    # _site is reserved for generated files. Validate its exact resolved location before cleanup.
    output = root / "_site"
    if output.is_symlink() or output.resolve() != root / "_site":
        raise ValueError("Refusing to replace a redirected _site directory")
    if output.exists():
        shutil.rmtree(output)
    output.mkdir()
    for name in ("style.css", "effects.css", "script.js", "CNAME"):
        path = root / name
        if path.is_file():
            shutil.copyfile(path, output / name)
    extensions = {".svg", ".png", ".jpg", ".jpeg", ".webp", ".avif", ".gif", ".ico", ".woff", ".woff2", ".ttf", ".otf", ".css", ".js", ".mp4", ".webm"}
    if (root / "assets").is_dir():
        for path in (root / "assets").rglob("*"):
            if path.is_file() and path.suffix.lower() in extensions:
                if not path.resolve().is_relative_to(root):
                    raise ValueError(f"Asset points outside site: {path}")
                destination = output / path.relative_to(root)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, destination)
    (output / "index.html").write_text(prepared, encoding="utf-8")
    (output / "404.html").write_text(error_page, encoding="utf-8")
    (output / "config.js").write_text("window.SITE_CONFIG = " + json.dumps(config, ensure_ascii=False, indent=2).replace("<", "\\u003c") + ";\n", encoding="utf-8")
    (output / ".nojekyll").touch()
    namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", namespace)
    sitemap = ET.Element(f"{{{namespace}}}urlset")
    url = ET.SubElement(sitemap, f"{{{namespace}}}url")
    ET.SubElement(url, f"{{{namespace}}}loc").text = site_url
    ET.ElementTree(sitemap).write(output / "sitemap.xml", encoding="utf-8", xml_declaration=True)
    (output / "robots.txt").write_text("User-agent: *\nAllow: /\n\nSitemap: " + site_url + "sitemap.xml\n", encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-url", help="Real Pages base URL, including repository path; overrides config.js")
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    try:
        output = build(args.source, args.site_url)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"Build failed: {error}\n")
    print(f"Static site prepared: {output}")


if __name__ == "__main__":
    main()
