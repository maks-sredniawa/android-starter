package app.starter.ui.support

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import androidx.annotation.StringRes
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import app.starter.R
import app.starter.theme.Spacing
import app.starter.ui.common.DetailScaffold
import app.starter.ui.common.LinkRow
import app.starter.ui.common.LinkTarget
import app.starter.ui.common.SectionHeader

/**
 * The route out of the app, for a user — or a tester — who has found something.
 *
 * **It belongs before the door, not in the polish phase.** Play's listing requires a contact address
 * whatever you do, and a closed test is the other half of the argument: a tester with no way to
 * report is a tester whose fourteen days produce nothing. The first app built from this template
 * shipped the two mail rows at its door and the rate-on-Play row later, when there was a listing to
 * rate.
 *
 * A detail screen pushed from Settings' *About* section, beside the licences row — not a third tab.
 * The bottom bar switches between roots, and support is not a root; it is somewhere you go once,
 * from the place you already go to look things up.
 *
 * No `ViewModel`: every row builds an intent from [SupportConfig] and hands it to the system. The
 * [tip] slot is the exception — the app passes `{ TipSection() }`, which holds its own `ViewModel`
 * (ADR-0007), and an app without the tip passes nothing.
 */
@Composable
fun SupportScreen(
    onBack: () -> Unit,
    onOpenCredits: () -> Unit,
    modifier: Modifier = Modifier,
    tip: @Composable () -> Unit = {},
) {
    val context = LocalContext.current

    // Not `rememberSaveable`: "the tap you just made went nowhere" is only true of the tap you just
    // made. One slot for the whole screen, because only the most recent tap is worth reporting, and
    // it renders under the group that holds the row.
    var missingApp by remember { mutableStateOf<MissingApp?>(null) }
    var versionCopied by remember { mutableStateOf(false) }

    fun reportHandOff(
        opened: Boolean,
        group: SupportGroup,
        @StringRes missing: Int,
    ) {
        missingApp = if (opened) null else MissingApp(group, missing)
    }

    @Composable
    fun MissingAppMessage(group: SupportGroup) {
        missingApp?.takeIf { it.group == group }?.let {
            Text(
                text = stringResource(it.message),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.error,
                modifier = Modifier.padding(horizontal = Spacing.base, vertical = Spacing.snug),
            )
        }
    }

    DetailScaffold(
        title = stringResource(R.string.support_title),
        onBack = onBack,
        modifier = modifier,
    ) { contentModifier ->
        Column(
            modifier =
                contentModifier
                    .fillMaxSize()
                    .verticalScroll(rememberScrollState()),
        ) {
            for (request in listOf(SupportRequest.Bug, SupportRequest.Feature)) {
                LinkRow(
                    title = stringResource(request.titleRes()),
                    subtitle = stringResource(request.hintRes()),
                    target = LinkTarget.Outside,
                    onClick = {
                        reportHandOff(
                            context.sendSupportMail(request),
                            SupportGroup.Feedback,
                            R.string.support_no_mail_app,
                        )
                    },
                )
            }
            LinkRow(
                title = stringResource(R.string.support_rate),
                subtitle = stringResource(R.string.support_rate_hint),
                target = LinkTarget.Outside,
                onClick = { reportHandOff(context.rateOnPlay(), SupportGroup.Feedback, R.string.support_no_play) },
            )
            MissingAppMessage(SupportGroup.Feedback)

            tip()

            SectionHeader(stringResource(R.string.settings_about))
            LinkRow(
                title = stringResource(R.string.support_site),
                subtitle = SupportConfig.SITE_URL.removePrefix("https://").trimEnd('/'),
                target = LinkTarget.Outside,
                onClick = { reportHandOff(context.openSite(), SupportGroup.About, R.string.support_no_browser) },
            )
            LinkRow(
                title = stringResource(R.string.support_privacy),
                subtitle = stringResource(R.string.support_privacy_hint),
                target = LinkTarget.Outside,
                onClick = {
                    reportHandOff(context.openPrivacyPolicy(), SupportGroup.About, R.string.support_no_browser)
                },
            )
            LinkRow(
                title = stringResource(R.string.support_credits),
                subtitle = stringResource(R.string.support_credits_hint),
                target = LinkTarget.Inside,
                onClick = onOpenCredits,
            )
            LinkRow(
                title = stringResource(R.string.support_more_apps),
                subtitle = stringResource(R.string.support_more_apps_hint),
                target = LinkTarget.Outside,
                onClick = { reportHandOff(context.openMoreApps(), SupportGroup.About, R.string.support_no_browser) },
            )
            MissingAppMessage(SupportGroup.About)
            LinkRow(
                title = stringResource(R.string.support_version, versionNumber),
                subtitle =
                    stringResource(
                        if (versionCopied) R.string.support_version_copied else R.string.support_version_hint,
                    ),
                target = LinkTarget.Here,
                onClick = {
                    context.copyToClipboard(context.versionLine())
                    versionCopied = true
                },
            )
        }
    }
}

private enum class SupportGroup { Feedback, About }

private data class MissingApp(
    val group: SupportGroup,
    @param:StringRes val message: Int,
)

private fun Context.copyToClipboard(text: String) {
    getSystemService(ClipboardManager::class.java)?.setPrimaryClip(ClipData.newPlainText(text, text))
}

internal fun SupportRequest.titleRes(): Int =
    when (this) {
        SupportRequest.Bug -> R.string.support_report
        SupportRequest.Feature -> R.string.support_feature
        SupportRequest.Language -> R.string.settings_language_report
    }

internal fun SupportRequest.hintRes(): Int =
    when (this) {
        SupportRequest.Bug -> R.string.support_report_hint
        SupportRequest.Feature -> R.string.support_feature_hint
        SupportRequest.Language -> R.string.settings_language_report_hint
    }
