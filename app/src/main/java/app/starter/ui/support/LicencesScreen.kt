package app.starter.ui.support

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.HorizontalDivider
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
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import app.starter.R
import app.starter.theme.Spacing
import app.starter.ui.appViewModelExtras
import app.starter.ui.common.DetailScaffold
import app.starter.ui.common.LinkRow
import app.starter.ui.common.LinkTarget
import app.starter.ui.common.SectionHeader

/**
 * Credits: who made the app, who helped, then attribution for every dependency in *this* binary.
 *
 * The list is generated at build time by `app.cash.licensee` over the resolved runtime classpath —
 * not typed from `libs.versions.toml`, which would name a dozen artifacts where the build actually
 * ships two hundred. Apache-2.0 §4 travels with each of them, and a hand-written list cannot stay
 * true across a dependency bump.
 */
@Composable
fun LicencesScreen(
    onBack: () -> Unit,
    onOpenLicenceText: (spdxId: String, title: String) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: LicencesViewModel =
        viewModel(factory = LicencesViewModel.Factory, extras = appViewModelExtras()),
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()
    val context = LocalContext.current

    // Not saveable, and one slot for the screen: only the tap just made is worth reporting.
    var noBrowserFor by remember { mutableStateOf<String?>(null) }

    DetailScaffold(
        title = stringResource(R.string.support_credits),
        onBack = onBack,
        modifier = modifier,
    ) { contentModifier ->
        LazyColumn(modifier = contentModifier.fillMaxSize()) {
            item(key = "people") {
                Column {
                    SectionHeader(stringResource(R.string.credits_made_by))
                    PersonRow(CREATOR, stringResource(R.string.credits_creator))
                    if (SupportConfig.CONTRIBUTORS.isNotEmpty()) {
                        SectionHeader(stringResource(R.string.credits_helped_by))
                        SupportConfig.CONTRIBUTORS.forEach { PersonRow(it.name, stringResource(it.role)) }
                    }
                    HorizontalDivider(modifier = Modifier.padding(top = Spacing.section))
                    Text(
                        text = stringResource(R.string.settings_licences),
                        style = MaterialTheme.typography.titleMedium,
                        modifier = Modifier.padding(start = Spacing.base, end = Spacing.base, top = Spacing.section),
                    )
                    Text(
                        text = stringResource(R.string.licences_intro),
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(start = Spacing.base, end = Spacing.base, top = Spacing.snug),
                    )
                    if (state.unavailable) {
                        Text(
                            text = stringResource(R.string.licences_unavailable),
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.error,
                            modifier = Modifier.padding(start = Spacing.base, end = Spacing.base, top = Spacing.base),
                        )
                    }
                }
            }
            for (group in state.groups) {
                item(key = group.title) {
                    Column(modifier = Modifier.fillMaxWidth()) {
                        SectionHeader(group.title)
                        when (val link = group.link(state.bundledTexts)) {
                            is LicenceLink.Text ->
                                LinkRow(
                                    title = stringResource(R.string.licences_read),
                                    target = LinkTarget.Inside,
                                    onClick = { onOpenLicenceText(link.spdxId, link.title) },
                                )
                            is LicenceLink.Terms ->
                                LinkRow(
                                    title = stringResource(R.string.licences_open_terms),
                                    subtitle = link.url,
                                    target = LinkTarget.Outside,
                                    onClick = {
                                        noBrowserFor = if (context.openInBrowser(link.url)) null else group.title
                                    },
                                )
                            null -> Unit
                        }
                        if (noBrowserFor == group.title) {
                            Text(
                                text = stringResource(R.string.support_no_browser),
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.error,
                                modifier = Modifier.padding(horizontal = Spacing.base, vertical = Spacing.snug),
                            )
                        }
                        Text(
                            text = group.artifacts.joinToString("\n") { it.listing },
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.padding(horizontal = Spacing.base),
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun PersonRow(
    name: String,
    role: String,
) {
    Column(
        modifier = Modifier.fillMaxWidth().padding(horizontal = Spacing.base, vertical = Spacing.snug),
        verticalArrangement = Arrangement.spacedBy(Spacing.hair),
    ) {
        Text(name, style = MaterialTheme.typography.bodyLarge)
        Text(role, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}
