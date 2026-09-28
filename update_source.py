#!/usr/bin/env python3
"""Regenerate apps.json from the latest releases of the app repos.

Reads the current apps.json (keeps every old version entry), asks GitHub for
each app's latest release, and prepends a version entry only when the tag
moved. The .ipa downloads only on a version change, just to hash it.

Run locally:  python3 update_source.py
Needs nothing beyond the standard library.
"""

import hashlib
import json
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE_FILE = HERE / "apps.json"
RAW = "https://raw.githubusercontent.com/devinprater/apps/main"

APPS = [
    {
        "name": "iBestSpeech",
        "bundleIdentifier": "com.devin.ibestspeech",
        "developerName": "Devin Prater",
        "subtitle": "Keynote Gold voices as system voices.",
        "localizedDescription": (
            "Keynote Gold voices as system voices on iPhone and iPad, "
            "working with VoiceOver, Spoken Content and anything using the "
            "system voices, all on the device and offline. Bring your own "
            "Keynote Gold engine file: the app imports it at run time.\n\n"
            "This build includes voice data that is not part of the open "
            "code and belongs to its owners. It is included for personal "
            "accessibility use, is not covered by the code licence, and "
            "will be removed if a rights holder asks."
        ),
        "iconURL": f"{RAW}/icons/ibestspeech.png",
        "repo": "devinprater/iBestSpeech",
    },
    {
        "name": "iTruVoice",
        "bundleIdentifier": "com.devin.itruvoice",
        "developerName": "Devin Prater",
        "subtitle": "TruVoice voices as system voices.",
        "localizedDescription": (
            "TruVoice voices (Peter, Julia, Sidney and the rest) as system "
            "voices on iPhone and iPad, working with VoiceOver, Spoken "
            "Content and anything using the system voices, all on the "
            "device and offline.\n\n"
            "This build includes voice data that is not part of the open "
            "code and belongs to its owners: Centigram Communications, "
            "whose TruVoice later passed to Lernout & Hauspie, ScanSoft and "
            "Nuance. It is included for personal accessibility use, is not "
            "covered by the code licence, and will be removed if a rights "
            "holder asks."
        ),
        # No icon ships with the app yet; the field is omitted until one
        # lands in icons/itruvoice.png.
        "repo": "devinprater/iTruVoice",
    },
]


def api(url):
    req = urllib.request.Request(url, headers={"User-Agent": "apps-source-updater"})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def sha256_of(url):
    digest = hashlib.sha256()
    req = urllib.request.Request(url, headers={"User-Agent": "apps-source-updater"})
    with urllib.request.urlopen(req) as r:
        for chunk in iter(lambda: r.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    source = json.loads(SOURCE_FILE.read_text())
    by_id = {a["bundleIdentifier"]: a for a in source["apps"]}

    for cfg in APPS:
        rel = api(f"https://api.github.com/repos/{cfg['repo']}/releases/latest")
        tag = rel["tag_name"]
        version = tag[1:] if tag.startswith("v") else tag
        asset = next(
            (a for a in rel["assets"] if a["name"].endswith("-sideload.ipa")),
            None,
        )
        if asset is None:
            print(f"{cfg['name']}: no sideload .ipa on {tag}, skipped")
            continue

        app = by_id.get(cfg["bundleIdentifier"])
        if app is None:
            app = {
                "name": cfg["name"],
                "bundleIdentifier": cfg["bundleIdentifier"],
                "developerName": cfg["developerName"],
                "subtitle": cfg["subtitle"],
                "localizedDescription": cfg["localizedDescription"],
                "category": "utilities",
                "versions": [],
            }
            if "iconURL" in cfg:
                app["iconURL"] = cfg["iconURL"]
            source["apps"].append(app)
            by_id[cfg["bundleIdentifier"]] = app

        if any(v.get("version") == version for v in app["versions"]):
            print(f"{cfg['name']}: {version} already listed")
            continue

        print(f"{cfg['name']}: adding {version} (hashing the .ipa)")
        app["versions"].insert(0, {
            "version": version,
            "date": rel["published_at"],
            "localizedDescription": rel["body"] or "",
            "downloadURL": asset["browser_download_url"],
            "size": asset["size"],
            "sha256": sha256_of(asset["browser_download_url"]),
        })

    SOURCE_FILE.write_text(json.dumps(source, indent=2, ensure_ascii=False) + "\n")
    print("apps.json written")


if __name__ == "__main__":
    main()
