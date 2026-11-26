"""The course site is served with a strict security policy; see hooks/csp_headers.py."""
import base64
import hashlib
import importlib.util
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "hooks" / "csp_headers.py"
spec = importlib.util.spec_from_file_location("csp_headers", HOOK)
csp_headers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(csp_headers)


def sha(text: str) -> str:
    return "'sha256-" + base64.b64encode(hashlib.sha256(text.encode()).digest()).decode() + "'"


def test_only_inline_code_is_hashed(tmp_path):
    (tmp_path / "index.html").write_text(
        '<script>var a=1</script>'
        '<script src="assets/app.js"></script>'
        '<script id="__config" type="application/json">{"base": "."}</script>'
        '<script>  </script>'
    )
    assert csp_headers.inline_script_hashes(tmp_path) == [sha("var a=1")]


def test_headers_file_allows_the_inline_scripts_and_nothing_remote(tmp_path):
    (tmp_path / "index.html").write_text("<script>var a=1</script>")
    csp_headers.on_post_build({"site_dir": str(tmp_path)})
    headers = (tmp_path / "_headers").read_text()
    policy = next(line for line in headers.splitlines() if "Content-Security-Policy" in line)
    assert sha("var a=1") in policy
    assert "default-src 'none'" in policy
    assert "font-src 'self'" in policy
    assert "googleapis" not in policy and "github" not in policy
    assert len(policy) < 2000  # Cloudflare Pages drops longer header lines


def test_only_renamed_files_are_cached_for_a_year(tmp_path):
    (tmp_path / "index.html").write_text("<p>hi</p>")
    csp_headers.on_post_build({"site_dir": str(tmp_path)})
    blocks = (tmp_path / "_headers").read_text().split("\n\n")
    immutable = [b.splitlines()[0] for b in blocks if "immutable" in b]
    assert immutable == ["/assets/javascripts/*", "/assets/stylesheets/*", "/assets/external/*"]
