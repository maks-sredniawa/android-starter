package app.starter.ui.support

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import app.starter.R
import app.starter.theme.Spacing
import app.starter.ui.appViewModelExtras
import app.starter.ui.common.DetailScaffold
import app.starter.ui.common.SectionHeader

/**
 * Attribution for every dependency in *this* binary.
 *
 * The list is generated at build time by `app.cash.licensee` over the resolved runtime classpath —
 * not typed from `libs.versions.toml`, which would name a dozen artifacts where the build actually
 * ships two hundred. Apache-2.0 §4 travels with each of them, and a hand-written list cannot stay
 * true across a dependency bump.
 */
@Composable
fun LicencesScreen(
    onBack: () -> Unit,
    onOpenLicence: (String) -> Unit,
    modifier: Modifier = Modifier,
    viewModel: LicencesViewModel =
        viewModel(factory = LicencesViewModel.Factory, extras = appViewModelExtras()),
) {
    val groups by viewModel.groups.collectAsStateWithLifecycle()

    DetailScaffold(
        title = stringResource(R.string.settings_licences),
        onBack = onBack,
        modifier = modifier,
    ) { contentModifier ->
        LazyColumn(modifier = contentModifier.fillMaxSize()) {
            for (group in groups) {
                item(key = group.title) {
                    Column(
                        modifier =
                            Modifier
                                .fillMaxWidth()
                                // Only an SPDX licence has text bundled with the binary; a vendor's
                                // own terms can only be linked, so that row is not tappable here.
                                .then(
                                    if (group.spdxId != null) {
                                        Modifier.clickable { onOpenLicence(group.spdxId!!) }
                                    } else {
                                        Modifier
                                    },
                                ),
                    ) {
                        SectionHeader(group.title)
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
