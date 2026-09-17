"""Regenerate the README stack-icons row from real repo language data.

Reads all owned (non-fork) repos of rawalsinghpsnl via the GitHub API,
sums language bytes, maps the top languages to skillicons.dev ids and
rewrites the <!--STACK:start--> block in README.md. No mock data.
"""
import json
import os
import re
import urllib.request

USER = "rawalsinghpsnl"
TOKEN = os.environ["GITHUB_TOKEN"]

LANG_TO_ICON = {
    "TypeScript": "ts",
    "JavaScript": "js",
    "HTML": "html",
    "CSS": "css",
    "Python": "py",
    "Shell": "bash",
    "Dockerfile": "docker",
    "SCSS": "sass",
    "Vue": "vue",
    "JSON": "json",
    "Markdown": "md",
    "YAML": "yaml",
    "Java": "java",
    "Go": "go",
}


def api(url):
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "profile-stack-updater",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def main():
    repos = api(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner")
    totals: dict = {}
    for repo in repos:
        if repo.get("fork"):
            continue
        try:
            langs = api(repo["languages_url"])
        except Exception as exc:  # noqa: BLE001 - one repo must not break the run
            print(f"skip {repo.get('name')}: {exc}")
            continue
        for lang, byte_count in langs.items():
            totals[lang] = totals.get(lang, 0) + byte_count

    ranked = sorted(totals, key=totals.get, reverse=True)
    icons = [LANG_TO_ICON[lang] for lang in ranked if lang in LANG_TO_ICON][:10]
    print("real language bytes:", {k: totals[k] for k in ranked[:10]})
    print("icons:", icons)
    if not icons:
        print("no mappable languages found; leaving README untouched")
        return

    img = f'<img src="https://skillicons.dev/icons?i={",".join(icons)}&theme=dark" alt="Stack" />'
    path = "README.md"
    with open(path, encoding="utf-8") as fh:
        content = fh.read()
    updated = re.sub(
        r"<!--STACK:start-->.*?<!--STACK:end-->",
        f"<!--STACK:start-->\n{img}\n<!--STACK:end-->",
        content,
        flags=re.S,
    )
    if updated != content:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(updated)
        print("README stack updated")
    else:
        print("README already up to date")


if __name__ == "__main__":
    main()
