package app.starter.ui.support

/**
 * Everything about Help and feedback that differs from one app to the next — **the one file in
 * `ui/support/` that `scripts/sync-support.py` never overwrites.** Every other file in this package,
 * and the `shared:support` block of each `strings.xml`, comes from android-starter.
 *
 * `bootstrap.py` writes the four constants. Each is compiled into every build and frozen there for as
 * long as a sideloaded copy survives, so the address and the site sit on a domain we own, whose
 * routing can move without a release. The Play listing's contact field carries the same address —
 * `docs/DOD.md`, *Before the first upload*.
 */
object SupportConfig {
    const val SUPPORT_ADDRESS = "support@example.com"

    /**
     * The id Play knows this app by, as a literal rather than `BuildConfig.APPLICATION_ID`: debug
     * builds carry `applicationIdSuffix = ".debug"`, and Play has never heard of the suffixed id.
     */
    const val PLAY_PACKAGE = "com.example.starter"

    /** The mail subject's prefix — "Starter #bug" — which a mail filter sorts on. Never translated. */
    const val MAIL_TAG = "Starter"

    /** The app's page on maksforge.com; the privacy policy is `privacy-policy` beneath it. */
    const val SITE_URL = "https://maksforge.com/android-starter/"

    /**
     * What the build ships that Licensee never sees — a model or a data set fetched as a file — shown
     * on the Credits screen beside the dependencies.
     */
    val BUNDLED_CREDITS: List<LicensedArtifact> = emptyList()
}
