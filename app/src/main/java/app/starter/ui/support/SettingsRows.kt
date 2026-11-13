package app.starter.ui.support

import androidx.compose.runtime.Composable
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import app.starter.R
import app.starter.ui.common.LinkRow
import app.starter.ui.common.LinkTarget
import app.starter.ui.common.SectionHeader

/** Settings' *About* section, the same in every app. */
@Composable
fun AboutSection(
    onOpenSupport: () -> Unit,
    onOpenLicences: () -> Unit,
) {
    SectionHeader(stringResource(R.string.settings_about))
    LinkRow(stringResource(R.string.settings_support), LinkTarget.Inside, onClick = onOpenSupport)
    LinkRow(stringResource(R.string.settings_licences), LinkTarget.Inside, onClick = onOpenLicences)
}

/** The row under Settings' language picker that mails a translation report ([SupportRequest.Language]). */
@Composable
fun LanguageReportRow() {
    val context = LocalContext.current
    LinkRow(
        title = stringResource(SupportRequest.Language.titleRes()),
        subtitle = stringResource(SupportRequest.Language.hintRes()),
        target = LinkTarget.Outside,
        onClick = { context.sendSupportMail(SupportRequest.Language) },
    )
}
