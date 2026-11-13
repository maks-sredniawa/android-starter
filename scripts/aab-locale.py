#!/usr/bin/env python3
"""Assert a locale's translated strings actually reached the bundle.

    python3 scripts/aab-locale.py [locale ...] [path/to/app-release.aab]

With no locale named it checks every language `locales_config.xml` ships. The base strings
(`values/strings.xml`) are checked on every run.

Why this exists: in the app this template was extracted from, a patch release
had to fix *Polish not reaching a shipped artifact at all*. `values-pl/strings.xml`
was complete, the translation test was green, and the build still went up without
the translations. Every check in that chain read the source; nothing read the
artifact. So this one reads the artifact, and it asserts rather than prints — the
same lesson as `scripts/aab-version.py`, applied to a different field.

An AAB keeps every locale's strings in `base/resources.pb`; Play splits them into
per-language APKs at install time. So the bytes are there to look for, and their
absence is exactly the failure that patch release had to fix.

Exits non-zero if any base or translated string is missing from the resource table.
"""

import re
import sys
import zipfile
import xml.etree.ElementTree as ET

RES = "app/src/main/res"
LOCALES_CONFIG = f"{RES}/xml/locales_config.xml"
ANDROID_NAME = "{http://schemas.android.com/apk/res/android}name"

# Android's own backslash escapes, which aapt resolves on the way in — the XML
# holds \' but the resource table holds '. Entities like &amp; are already
# handled by the XML parser before we get here.
UNESCAPE = {r"\'": "'", r"\"": '"', r"\\": "\\", r"\n": "\n", r"\t": "\t"}


def resolve(node):
    """The plain value aapt would store for one <string> element.

    itertext() rather than .text because a styled string (<b>, <i>) keeps its
    markup as spans and its *text* as the value, so joining the pieces is what
    the resource table will hold.
    """
    text = "".join(node.itertext())

    # A value wrapped in double quotes keeps its whitespace and loses the quotes;
    # everything else has the whitespace the author used for line-wrapping
    # collapsed away.
    if len(text) >= 2 and text.startswith('"') and text.endswith('"'):
        text = text[1:-1]
    else:
        # ASCII whitespace only, as aapt2 collapses it: a no-break space (French "fasse ?") is text.
        text = re.sub(r"[ \t\r\n]+", " ", text).strip(" \t\r\n")

    # Only *then* are Android's own escapes turned into characters. The order is
    # load-bearing: \n means a real newline in the resource table, so unescaping
    # it before the collapse above would flatten it right back into a space and
    # the string would look absent from a bundle that in fact carries it.
    for escaped, plain in UNESCAPE.items():
        text = text.replace(escaped, plain)
    return text


def strings_from(path):
    """{name: value} for every <string> and <plurals><item> in one strings.xml."""
    try:
        root = ET.parse(path).getroot()
    except FileNotFoundError:
        sys.exit(f"no such resource file: {path}")

    values = {}
    for node in root:
        name = node.get("name")
        if node.tag == "string" and name:
            values[name] = resolve(node)
        elif node.tag == "plurals" and name:
            for item in node.findall("item"):
                values[f"{name}[{item.get('quantity')}]"] = resolve(item)
    return values


def field(value):
    """A string as the resource table stores it: protobuf field 1, length-delimited.

    `String.value` and `StyledString.value` are both field 1, so each value sits in the table as
    0x0a, its byte length as a varint, then its UTF-8 bytes. Matching that whole field rather than
    the bare bytes keeps a value from being found inside a longer one: Polish "Pomoc" is a prefix
    of "Pomoc i opinie", and a bare-substring match passed with the short one stripped.
    """
    data = value.encode()
    length, varint = len(data), bytearray()
    while True:
        byte = length & 0x7F
        length >>= 7
        if length:
            varint.append(byte | 0x80)
        else:
            varint.append(byte)
            return b"\x0a" + bytes(varint) + data


def missing_from(table, values):
    """[(name, value)] for every non-empty value that is not a whole string field of the table."""
    return [(name, value) for name, value in values.items() if value and field(value) not in table]


def report_missing(missing, source, detail=""):
    print(
        f"\nMISSING: {len(missing)} string(s) from {source} are not in base/resources.pb{detail}.\n"
        "Do not upload this artifact.",
        file=sys.stderr,
    )
    for name, value in missing[:15]:
        print(f"  {name} = {value!r}", file=sys.stderr)
    if len(missing) > 15:
        print(f"  … and {len(missing) - 15} more", file=sys.stderr)


def qualifier(tag):
    """The `values-` qualifier for a BCP-47 tag: `pl` -> `pl`, `pt-BR` -> `pt-rBR`.

    Two spellings of one locale. `locales_config.xml` carries the tag and the resource directory
    carries the qualifier, so anything that reads the first to find the second needs this —
    `TranslationTest.qualifier` is the same function on the Kotlin side.
    """
    parts = tag.split("-")
    return f"{parts[0]}-r{parts[1]}" if len(parts) == 2 else tag


def shipped_locales():
    """Every translated locale, read from the file the language picker itself reads.

    A hardcoded `pl` was the whole list when this script was first written. At nine it is how
    eight languages reach the tracks unchecked — and "a locale did not reach the artifact" is the
    one failure this script exists to catch. Read rather than repeated, so a tenth language is one
    line of XML here as everywhere else.
    """
    root = ET.parse(LOCALES_CONFIG).getroot()
    tags = [node.get(ANDROID_NAME) for node in root]
    return [tag for tag in tags if tag and tag != "en"]


def check_base(table, default):
    """The English base strings against the resource table. 0 if every one is in the bundle.

    A string the release shrinker strips is gone from every language at once, so the base is where
    that loss shows first, and it has no translation to cover for it.
    """
    print()
    missing = missing_from(table, default)
    checked = len([v for v in default.values() if v])
    print("locale       base")
    print(f"checked      {checked} strings from values/strings.xml")
    if missing:
        report_missing(missing, "values/strings.xml")
        return 1
    print(f"all {checked} base strings are present in base/resources.pb")
    return 0


def check(locale, table, default):
    """One locale against the resource table. 0 if every string of it is in the bundle."""
    print()
    source = f"values-{qualifier(locale)}/strings.xml"
    translated = strings_from(f"{RES}/{source}")

    # A string identical to its English counterpart ("OK", a proper name) proves
    # nothing about the translation having shipped — it would be present either
    # way. The ones that *differ* are the load-bearing subset, so they are counted
    # separately and the run fails if there are implausibly few.
    present = {name: value for name, value in translated.items() if value}
    missing = missing_from(table, present)
    distinct = sum(default.get(name) != value for name, value in present.items())
    distinct_missing = sum(default.get(name) != value for name, value in missing)

    checked = len(present)
    print(f"locale       {locale}")
    print(f"checked      {checked} strings from {source}")
    print(f"distinct     {distinct} differ from values/strings.xml")

    if missing:
        report_missing(missing, source, f" ({distinct_missing} of them translated)")
        return 1

    if distinct < checked // 2:
        print(
            f"\nSUSPICIOUS: only {distinct} of {checked} strings differ from English.\n"
            "That is what a locale falling back to the default looks like.",
            file=sys.stderr,
        )
        return 1

    print(f"all {checked} {locale} strings are present in base/resources.pb")
    return 0


def main():
    args = sys.argv[1:]
    path = "app/build/outputs/bundle/release/app-release.aab"
    locales = []
    for arg in args:
        # The bundle is recognised by its extension rather than by position, so the locales stay
        # optional and variable in number without the two arguments having to be ordered.
        if arg.endswith(".aab"):
            path = arg
        else:
            locales.append(arg)
    locales = locales or shipped_locales()

    try:
        with zipfile.ZipFile(path) as bundle:
            table = bundle.read("base/resources.pb")
    except FileNotFoundError:
        sys.exit(f"no such bundle: {path}\nRun ./gradlew bundleRelease first.")
    except KeyError:
        sys.exit(f"{path} has no base/resources.pb — is it an AAB?")

    default = strings_from(f"{RES}/values/strings.xml")

    # Every locale is checked before anything exits, because "which languages made it" is the
    # question, and stopping at the first failure answers it for one.
    failed = ["base"] if check_base(table, default) else []
    failed += [locale for locale in locales if check(locale, table, default)]
    print()
    if failed:
        print(f"FAILED: {', '.join(failed)} — do not upload this artifact.", file=sys.stderr)
        return 1
    print(f"the base strings and all {len(locales)} shipped locales are present in {path}: {', '.join(locales)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
