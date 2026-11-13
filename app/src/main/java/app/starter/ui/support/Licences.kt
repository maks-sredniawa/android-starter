package app.starter.ui.support

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

// The attribution list, as the build wrote it and as the screen reads it .
//
// `licences.json` is **generated**, not committed: `app.cash.licensee` resolves the variant's
// runtime classpath at build time and `BundleLicences` copies its report into the variant's assets.
// So the shapes here are Licensee's, not ours — which is why they are permissive about what is
// absent and why the parser ignores unknown keys. A plugin bump that adds a field must not blank
// this screen.
//
// Everything in this file is deliberately free of Android: the parsing and the grouping are the half
// worth testing, and a JVM table test can only reach them if no `AssetManager` is in the way.

/** The asset the build's `BundleLicences` task writes. Kept in step with `app/build.gradle.kts`. */
const val LICENCES_ASSET = "licences.json"

/** Where a licence's own text lives, when it is ours to ship — `licences/Apache-2.0.txt`. */
const val LICENCE_TEXT_DIRECTORY = "licences"

/**
 * One dependency in the shipped binary.
 *
 * Kotlin note: `@Serializable` plus a default value is how kotlinx.serialization spells "optional".
 * `name` is absent for artifacts whose POM never set one, and both licence lists are absent rather
 * than empty when a dependency has no licence of that kind — so every one of them has a default and
 * the parse cannot fail on a well-formed report.
 */
@Serializable
data class LicensedArtifact(
    val groupId: String,
    val artifactId: String,
    val version: String,
    val name: String? = null,
    /** Where a file the build fetched itself came from, and its SHA-256; Licensee never writes it. */
    val source: String? = null,
    val spdxLicenses: List<SpdxLicence> = emptyList(),
    val unknownLicenses: List<UnknownLicence> = emptyList(),
) {
    /** `androidx.room:room-runtime:2.8.4` — the identity a reader can actually look up. */
    val coordinates: String get() = "$groupId:$artifactId:$version"

    /** What the screen lists for this artifact: its coordinates, and its source under them when known. */
    val listing: String get() = source?.let { "$coordinates\n$it" } ?: coordinates

    /** The POM's own name where there is one; the artifact id is a better fallback than nothing. */
    val displayName: String get() = name?.takeIf(String::isNotBlank) ?: artifactId
}

/** A licence Licensee recognised, so it has an SPDX identifier and a canonical name. */
@Serializable
data class SpdxLicence(
    val identifier: String,
    val name: String,
    val url: String? = null,
)

/**
 * A licence Licensee could not map to SPDX — for example, a vendor's own terms of service.
 *
 * Both fields are nullable because a POM may declare a `<license>` with only one of them. A licence
 * with neither is unusable and is dropped by [groupLicences] rather than rendered as a blank heading.
 */
@Serializable
data class UnknownLicence(
    val name: String? = null,
    val url: String? = null,
)

/**
 * Every artifact that shares one licence, which is what the screen draws as a section.
 *
 * [spdxId] is null for the licences that are not open source. That distinction is the one this type
 * exists to carry: an SPDX licence's **text travels with the binary** as a bundled asset, where a
 * vendor's terms of service are not yours to redistribute and can only be linked ([url]).
 *
 * A dual-licensed dependency legitimately appears in two groups. Nothing here ships that way
 * today, but the obligation is per licence rather than per artifact, so listing it twice is correct
 * and de-duplicating would be the bug.
 */
data class LicenceGroup(
    val title: String,
    val spdxId: String?,
    val url: String?,
    val artifacts: List<LicensedArtifact>,
)

/**
 * Lenient on purpose — see the file header. `isLenient` is *not* set: the input is machine-written
 * JSON, and accepting malformed input would only hide a broken generator.
 */
private val json = Json { ignoreUnknownKeys = true }

/**
 * Licensee's report, grouped by licence and ordered for reading.
 *
 * **SPDX licences first, by identifier; then the unrecognised ones, by name.** That is not
 * alphabetical across the whole list and it is not by size — it puts the licences whose text this app
 * actually ships above the two it can only link to, which is the distinction a reader needs first.
 *
 * Kotlin note: `groupBy` would only work over one key per element, and an artifact can carry several
 * licences — so this folds into a `LinkedHashMap` by hand. `LinkedHashMap` keeps insertion order,
 * which the sort at the end then replaces; it is used for determinism while building, not for the
 * final order.
 */
fun groupLicences(
    report: String,
    bundled: List<LicensedArtifact> = emptyList(),
): List<LicenceGroup> {
    val artifacts = json.decodeFromString<List<LicensedArtifact>>(report) + bundled

    // Key → (title, spdxId, url). The key is the identity of the licence itself: an SPDX identifier
    // where there is one, and the terms' own URL otherwise, so two POMs spelling the same terms with
    // different `<name>`s still land in one group.
    val buckets = LinkedHashMap<String, MutableList<LicensedArtifact>>()
    val headers = LinkedHashMap<String, LicenceGroup>()

    fun place(
        key: String,
        title: String,
        spdxId: String?,
        url: String?,
        artifact: LicensedArtifact,
    ) {
        headers.getOrPut(key) { LicenceGroup(title, spdxId, url, emptyList()) }
        buckets.getOrPut(key) { mutableListOf() }.add(artifact)
    }

    artifacts.forEach { artifact ->
        artifact.spdxLicenses.forEach { licence ->
            place(licence.identifier, licence.name, licence.identifier, licence.url, artifact)
        }
        artifact.unknownLicenses.forEach { licence ->
            // A licence with neither a name nor a URL says nothing and gets no section. It cannot
            // occur in a report Licensee accepted — `allowUrl` needs a URL — and is handled here so
            // that a future `allowDependency` cannot draw an empty heading.
            val key = licence.url ?: licence.name ?: return@forEach
            place(key, licence.name ?: key, null, licence.url, artifact)
        }
    }

    return headers
        .map { (key, header) ->
            header.copy(
                // By the three fields rather than by the coordinate string, which is not the same
                // order: `-` sorts before `:`, so a plain string sort files `androidx.activity:
                // activity` *after* `activity-compose` and `activity-ktx` — the parent module
                // underneath its own children, which reads as a bug on the phone.
                artifacts =
                    buckets
                        .getValue(key)
                        .sortedWith(compareBy({ it.groupId }, { it.artifactId }, { it.version })),
            )
        }.sortedWith(compareBy({ it.spdxId == null }, { it.spdxId ?: it.title }))
}

/** Stays for an app that keeps its own Credits screen, whose `LicencesViewModel.kt` calls it. */
fun licencesOrBundled(
    bundled: List<LicensedArtifact>,
    report: () -> String,
): List<LicenceGroup> = readCredits(bundled, report).groups

data class Credits(
    val groups: List<LicenceGroup>,
    val reportUnreadable: Boolean,
)

/**
 * The screen's one policy for a report it cannot read: show the bundled credits alone rather than
 * nothing, because those are often the notices a licence obliges the app to show, and set
 * [Credits.reportUnreadable] so the screen can say the list is incomplete.
 */
fun readCredits(
    bundled: List<LicensedArtifact>,
    report: () -> String,
): Credits =
    runCatching { Credits(groupLicences(report(), bundled), reportUnreadable = false) }
        .getOrElse { Credits(groupLicences("[]", bundled), reportUnreadable = true) }

sealed interface LicenceLink {
    data class Text(
        val spdxId: String,
        val title: String,
    ) : LicenceLink

    data class Terms(
        val url: String,
    ) : LicenceLink
}

/**
 * [bundledTexts] is read from the assets rather than assumed from the SPDX id, so a licence whose
 * text was never added degrades to its link instead of a screen saying the text is missing.
 */
fun LicenceGroup.link(bundledTexts: Set<String>): LicenceLink? =
    when {
        spdxId != null && spdxId in bundledTexts -> LicenceLink.Text(spdxId, title)
        url != null -> LicenceLink.Terms(url)
        else -> null
    }
