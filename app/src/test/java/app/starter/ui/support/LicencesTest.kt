package app.starter.ui.support

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Parsing Licensee's report, which is the half worth testing — the screen that draws the result is
 * a list. Everything here runs on the JVM because `Licences.kt` deliberately names no Android type.
 */
class LicencesTest {
    @Test
    fun `artifacts are grouped by licence, not by artifact`() {
        val report =
            """
            [
              {"groupId":"a","artifactId":"one","version":"1.0",
               "spdxLicenses":[{"identifier":"Apache-2.0","name":"Apache License 2.0"}]},
              {"groupId":"b","artifactId":"two","version":"2.0",
               "spdxLicenses":[{"identifier":"Apache-2.0","name":"Apache License 2.0"}]}
            ]
            """.trimIndent()
        val groups = groupLicences(report)
        assertEquals(1, groups.size)
        assertEquals(2, groups.single().artifacts.size)
    }

    @Test
    fun `a dual-licensed artifact appears under both, because the obligation is per licence`() {
        val report =
            """
            [
              {"groupId":"a","artifactId":"one","version":"1.0",
               "spdxLicenses":[
                 {"identifier":"Apache-2.0","name":"Apache License 2.0"},
                 {"identifier":"MIT","name":"MIT License"}]}
            ]
            """.trimIndent()
        assertEquals(2, groupLicences(report).size)
    }

    @Test
    fun `a bundled artifact joins the group of its licence and lists its source under the coordinates`() {
        val report =
            """[{"groupId":"a","artifactId":"one","version":"1.0",
                 "spdxLicenses":[{"identifier":"Apache-2.0","name":"Apache License 2.0"}]}]"""
        val model =
            LicensedArtifact(
                groupId = "models",
                artifactId = "tiny",
                version = "3",
                source = "https://example.org/tiny.bin sha256:abc",
                spdxLicenses = listOf(SpdxLicence("MIT", "MIT License")),
            )
        val dataSet =
            LicensedArtifact(
                groupId = "data",
                artifactId = "set",
                version = "1",
                spdxLicenses = listOf(SpdxLicence("Apache-2.0", "Apache License 2.0")),
            )

        val groups = groupLicences(report, bundled = listOf(model, dataSet)).associateBy { it.spdxId }

        assertEquals(listOf("a:one:1.0", "data:set:1"), groups.getValue("Apache-2.0").artifacts.map { it.coordinates })
        assertEquals(listOf(model), groups.getValue("MIT").artifacts)
        assertEquals("models:tiny:3\nhttps://example.org/tiny.bin sha256:abc", model.listing)
        assertEquals(dataSet.coordinates, dataSet.listing)
    }

    @Test
    fun `a plugin bump that adds an unknown field must not blank the screen`() {
        val report =
            """[{"groupId":"a","artifactId":"one","version":"1.0","somethingNew":true,
                 "spdxLicenses":[{"identifier":"Apache-2.0","name":"Apache License 2.0"}]}]"""
        assertTrue(groupLicences(report).isNotEmpty())
    }

    @Test
    fun `malformed input throws, and licencesOrBundled is where that is caught`() {
        // Deliberately *not* swallowed here. This function's job is to parse; a report it cannot
        // parse means the build's generator is broken, and returning an empty list would hide that
        // behind an empty screen. `licencesOrBundled` catches it and falls back to the bundled
        // credits, so a user never sees a crash — one caller, one policy.
        assertThrows(Exception::class.java) { groupLicences("not json") }
    }

    @Test
    fun `an unreadable report still shows the bundled credits`() {
        val bundled =
            listOf(
                LicensedArtifact(
                    groupId = "org.openstreetmap",
                    artifactId = "data",
                    version = "1",
                    spdxLicenses = listOf(SpdxLicence("ODbL-1.0", "Open Database License")),
                ),
            )

        val groups = licencesOrBundled(bundled) { error("asset missing") }

        assertEquals(listOf("ODbL-1.0"), groups.map { it.spdxId })
        assertEquals(bundled, groups.single().artifacts)
    }
}
