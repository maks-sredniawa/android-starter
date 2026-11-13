#!/usr/bin/env python3
"""Bring an app's Help and feedback, tip and Settings' About rows up to this template.

    python3 scripts/sync-support.py ~/repos/maks-sredniawa/darek            # write
    python3 scripts/sync-support.py ~/repos/maks-sredniawa/darek --check    # list drift, exit 1 if any

Run from android-starter, never from an app (bootstrap.py deletes it from a new one). The module is
`ui/support/` and, where the app keeps the tip, `tip/TipJar.kt` and `tip/TipBilling.kt`, their tests,
and the `shared:support` block of every `strings.xml` this template translates.

Never overwritten: `ui/support/SupportConfig.kt`, the app's own values. A member the template gained
since is added at its empty default when that default is app-neutral (an `emptyList()`); any other
missing member is reported for the person to set by hand. When an app has no config yet it is written
once from what the app already compiles in: the old `SUPPORT_ADDRESS`/`PLAY_PACKAGE`
constants, the `support_subject_bug` tag, and for the site and the fallback address the repo name of
the `origin` remote, or the directory name when the app has no `origin`.

An app keeps its own copy of any synced file by listing its path, relative to the package root or
to `app/src/main/res/`, in `scripts/support-sync.keep`.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import project  # noqa: E402

BEGIN = "<!-- shared:support begin"
END = "<!-- shared:support end -->"
BLOCK = re.compile(r"[ \t]*<!-- shared:support begin.*?<!-- shared:support end -->[ \t]*\n", re.S)
CONFIG = "ui/support/SupportConfig.kt"
TIP_ONLY = {"ui/support/TipSection.kt", "ui/support/SupportViewModel.kt"}
TIP_FILES = ["tip/TipJar.kt", "tip/TipBilling.kt"]
TIP_TESTS = ["tip/TipOutcomeTest.kt"]
TIP_STRINGS = re.compile(r'[ \t]*<!-- The tip \(ADR-0007\).*?-->[ \t]*\n|[ \t]*<string name="support_tip[^"]*".*?</string>[ \t]*\n', re.S)
RETIRED_STRINGS = ["support_subject_bug", "support_subject_feature", "support_subject_language"]
SITE = "https://maksforge.com"


def namespace_of(app: Path) -> str:
    text = (app / "app/build.gradle.kts").read_text(encoding="utf-8")
    return re.search(r'^\s*namespace\s*=\s*"([^"]+)"', text, re.M).group(1)


def application_id_of(app: Path) -> str:
    text = (app / "app/build.gradle.kts").read_text(encoding="utf-8")
    return re.search(r'^\s*applicationId\s*=\s*"([^"]+)"', text, re.M).group(1)


def repo_name(app: Path) -> str:
    """The GitHub repo's name, which a worktree's directory name is not."""
    remote = subprocess.run(["git", "-C", str(app), "remote", "get-url", "origin"], capture_output=True, text=True).stdout.strip()
    return re.sub(r"\.git$", "", remote.rstrip("/").rsplit("/", 1)[-1].rsplit(":", 1)[-1]) if remote else app.name


def package_dir(app: Path, source_set: str, namespace: str) -> Path:
    return app / "app/src" / source_set / "java" / namespace.replace(".", "/")


def module_files(has_tip: bool) -> list[tuple[str, str]]:
    """(source set, path under the package root) for every file the sync owns."""
    main = package_dir(project.ROOT, "main", project.NAMESPACE)
    test = package_dir(project.ROOT, "test", project.NAMESPACE)
    files = [
        ("main", p.relative_to(main).as_posix())
        for p in sorted((main / "ui/support").glob("*.kt"))
        if p.relative_to(main).as_posix() != CONFIG
    ]
    files += [("test", p.relative_to(test).as_posix()) for p in sorted((test / "ui/support").glob("*.kt"))]
    if has_tip:
        files += [("main", f) for f in TIP_FILES] + [("test", f) for f in TIP_TESTS]
    else:
        files = [(s, f) for s, f in files if f not in TIP_ONLY]
    return files


def retarget(text: str, namespace: str) -> str:
    return re.sub(rf"\b{re.escape(project.NAMESPACE)}\b", namespace, text)


def strip_strings(text: str, names: list[str]) -> str:
    for name in names:
        text = re.sub(rf'^[ \t]*<(string|plurals) name="{name}"[^>]*>.*?</\1>[ \t]*\n', "", text, flags=re.M | re.S)
    return text


RETIRED_COMMENTS = re.compile(
    r"[ \t]*<!-- (?:Help and feedback\. The three `support_subject_\*`|The tip \(ADR-0007\): a payment).*?-->[ \t]*\n"
    r"|[ \t]*<!-- Licences -->[ \t]*\n(?=\s*(?:<!--|</resources>))",
    re.S,
)


def block_names(block: str) -> list[str]:
    return re.findall(r'<(?:string|plurals) name="([^"]+)"', block)


def synced_strings(app_text: str, block: str) -> str:
    match = BLOCK.search(app_text)
    if match:
        # A string the template has just moved into the block must leave the app's own part of the file.
        names = block_names(block)
        return strip_strings(app_text[: match.start()], names) + block + strip_strings(app_text[match.end() :], names)
    text = strip_strings(app_text, block_names(block) + RETIRED_STRINGS)
    text = RETIRED_COMMENTS.sub("", text)
    text = re.sub(r"\n{3,}", "\n\n", text).rstrip()
    return text[: -len("</resources>")].rstrip() + "\n\n" + block + "</resources>\n"


def existing_constant(app: Path, namespace: str, names: list[str]) -> str | None:
    support = package_dir(app, "main", namespace) / "ui/support"
    for path in sorted(support.glob("*.kt")) if support.is_dir() else []:
        for name in names:
            match = re.search(rf'\b{name}\s*=\s*"([^"]+)"', path.read_text(encoding="utf-8"))
            if match:
                return match.group(1)
    return None


def first_config(app: Path, namespace: str) -> str:
    starter = (package_dir(project.ROOT, "main", project.NAMESPACE) / CONFIG).read_text(encoding="utf-8")
    base = (app / "app/src/main/res/values/strings.xml").read_text(encoding="utf-8")
    tag = re.search(r'name="support_subject_bug"[^>]*>(.*?) #bug<', base)
    name = re.search(r'name="app_name"[^>]*>([^<]+)<', base)
    repo = repo_name(app)
    values = {
        "SUPPORT_ADDRESS": existing_constant(app, namespace, ["SUPPORT_ADDRESS", "SUPPORT_EMAIL"])
        or f"{repo}.support@maksforge.com",
        "PLAY_PACKAGE": existing_constant(app, namespace, ["PLAY_PACKAGE"]) or application_id_of(app),
        "MAIL_TAG": tag.group(1) if tag else (name.group(1) if name else repo),
        "SITE_URL": f"{SITE}/{repo}/",
    }
    for key, value in values.items():
        starter = re.sub(rf'({key} = )"[^"]*"', rf'\1"{value}"', starter)
        print(f"  SupportConfig.{key} = {value}")
    return retarget(starter, namespace)


MEMBER = re.compile(r"(?:[ \t]*/\*\*.*?\*/\n)?[ \t]*(?:const )?val (\w+)\b[^\n]*\n", re.S)


def with_new_members(app_config: str) -> tuple[str, list[str], list[str]]:
    """The app's config with each missing app-neutral member added, what was added, and what is left to set."""
    template = (package_dir(project.ROOT, "main", project.NAMESPACE) / CONFIG).read_text(encoding="utf-8")
    body = template[template.index("object SupportConfig") :]
    missing = [m for m in MEMBER.finditer(body) if not re.search(rf"\bval {m.group(1)}\b", app_config)]
    neutral = [m for m in missing if m.group(0).rstrip().endswith("emptyList()")]
    by_hand = [m.group(1) for m in missing if m not in neutral]
    if not neutral:
        return app_config, [], by_hand
    end = app_config.rstrip().rindex("}")
    added = "".join("\n" + m.group(0) for m in neutral)
    return app_config[:end].rstrip("\n") + "\n" + added + "}\n", [m.group(1) for m in neutral], by_hand


LICENCE_TEXT_NOTE = (
    "Navigation: the licence text screen now takes the licence's full name — give NavigationKeys' "
    "LicenceText a `val title: String`, pass LicencesScreen `onOpenLicenceText = { spdxId, title -> "
    "backStack.add(LicenceText(spdxId, title)) }` and LicenceTextScreen `title = key.title`"
)


def navigation_notes(app: Path, namespace: str) -> list[str]:
    root = package_dir(app, "main", namespace)
    source = "\n".join(p.read_text(encoding="utf-8") for p in [root / "Navigation.kt", root / "NavigationKeys.kt"] if p.is_file())
    if "LicenceText" not in source:
        return []
    old_shape = "onOpenLicence =" in source or not re.search(r"class LicenceText\([^)]*\bval title\b", source)
    return [LICENCE_TEXT_NOTE] if old_shape else []


def plan(app: Path) -> tuple[dict[Path, str], list[str]]:
    """Every file the sync would write, with its new content, and what it wants a human to know."""
    namespace = namespace_of(app)
    keep_file = app / "scripts/support-sync.keep"
    keep = set(keep_file.read_text().split()) if keep_file.is_file() else set()
    has_tip = (package_dir(app, "main", namespace) / "tip").is_dir()
    writes: dict[Path, str] = {}
    notes: list[str] = []

    for source_set, rel in module_files(has_tip):
        if rel in keep:
            notes.append(f"kept the app's own {rel} (support-sync.keep)")
            kept = package_dir(app, source_set, namespace) / rel
            if rel == "ui/support/LicencesScreen.kt" and kept.is_file():
                text = kept.read_text(encoding="utf-8")
                if "CREATOR" not in text or "CONTRIBUTORS" not in text:
                    notes.append(f"the kept {rel} must show CREATOR and CONTRIBUTORS like the template's Credits screen")
            continue
        source = package_dir(project.ROOT, source_set, project.NAMESPACE) / rel
        writes[package_dir(app, source_set, namespace) / rel] = retarget(source.read_text(encoding="utf-8"), namespace)

    config = package_dir(app, "main", namespace) / CONFIG
    if not config.is_file():
        print(f"{app.name}: no {CONFIG} yet, writing it from what the app compiles in:")
        writes[config] = first_config(app, namespace)
    else:
        merged, added, by_hand = with_new_members(config.read_text(encoding="utf-8"))
        if added:
            writes[config] = merged
            notes.append(f"added {', '.join(added)} to {CONFIG} at the template's empty default")
        for name in by_hand:
            notes.append(f"{CONFIG} has no {name} — set it by hand to this app's own value")

    res = project.ROOT / "app/src/main/res"
    translated = set()
    for starter_strings in sorted(res.glob("values*/strings.xml")):
        match = BLOCK.search(starter_strings.read_text(encoding="utf-8"))
        if not match:
            continue
        values = starter_strings.parent.name
        translated.add(values)
        target = app / "app/src/main/res" / values / "strings.xml"
        if f"{values}/strings.xml" in keep or not target.is_file():
            continue
        # `UnusedResources` is an error in every app, so an app without the tip gets the block without its strings.
        block = match.group(0) if has_tip else TIP_STRINGS.sub("", match.group(0))
        writes[target] = synced_strings(target.read_text(encoding="utf-8"), block)
    for target in sorted((app / "app/src/main/res").glob("values-*/strings.xml")):
        if target.parent.name not in translated:
            notes.append(f"{target.parent.name}: the template has no translation of the shared:support block — translate it there")

    common = package_dir(app, "main", namespace) / "ui/common"
    source = "\n".join(p.read_text(encoding="utf-8") for p in common.glob("*.kt")) if common.is_dir() else ""
    for symbol in ["fun LinkRow(", "enum class LinkTarget", "fun SectionHeader(", "fun DetailScaffold(", "fun Context.startActivitySafely("]:
        if symbol not in source:
            notes.append(f"ui/common/ has no `{symbol}` — copy it from the template before building")
    if not {"ui/support/LicencesScreen.kt", "ui/support/LicenceTextScreen.kt"} & keep:
        notes += navigation_notes(app, namespace)
    if not has_tip:
        notes.append("no tip/ package: TipSection and SupportViewModel left out; pass no `tip` to SupportScreen")
    return writes, notes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("app", type=Path, help="the app's clone")
    parser.add_argument("--check", action="store_true", help="write nothing; exit 1 if anything would change")
    args = parser.parse_args()
    app = args.app.expanduser().resolve()
    if app == project.ROOT:
        print("sync-support: that is the template itself", file=sys.stderr)
        return 2
    if not (app / "app/build.gradle.kts").is_file():
        print(f"sync-support: {app} is not an Android app clone", file=sys.stderr)
        return 2

    writes, notes = plan(app)
    changed = [path for path, text in writes.items() if not path.is_file() or path.read_text(encoding="utf-8") != text]
    for path in changed:
        print(f"{'differs' if args.check else 'wrote'}  {path.relative_to(app)}")
        if not args.check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(writes[path], encoding="utf-8")
    for note in notes:
        print(f"note     {note}")
    if not changed:
        print(f"{app.name}: in step with the template")
    elif not args.check:
        print(
            f"\n{app.name}: now wire it up and build —\n"
            "  SettingsScreen: AboutSection(onOpenSupport, onOpenLicences) and LanguageReportRow()\n"
            "  Navigation: SupportScreen(onBack, onOpenCredits = { backStack.add(Licences) }, tip = { TipSection() })\n"
            "  Navigation: LicencesScreen(onBack, onOpenLicenceText = { spdxId, title -> backStack.add(LicenceText(spdxId, title)) })\n"
            "  ./gradlew spotlessApply test lint && python3 scripts/translation-gate.py origin/main"
        )
    return 1 if args.check and changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
