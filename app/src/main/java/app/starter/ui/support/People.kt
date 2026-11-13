package app.starter.ui.support

import androidx.annotation.StringRes

/** Who made every MaksForge app; the first name on each app's Credits. */
const val CREATOR = "Maksymilian Średniawa"

/** Someone who helped with one app, listed under the creator. [role] is translated like any other string. */
data class Contributor(
    val name: String,
    @param:StringRes val role: Int,
)
