package app.starter.ui.support

import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.produceState
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.lifecycle.viewmodel.compose.viewModel
import app.starter.R
import app.starter.theme.Spacing
import app.starter.ui.appViewModelExtras
import app.starter.ui.common.DetailScaffold

/**
 * One licence's full text, read out of `assets/licences/<spdx-id>.txt`, under its full name.
 *
 * **The text ships with the binary rather than being linked.** Apache-2.0 §4(a) requires a copy of
 * the licence to travel with the distribution; a URL is not a copy, and it stops working the day the
 * host reorganises. The build fails if a dependency's licence is not on the allowlist, which is what
 * stops a new dependency arriving with no text behind it.
 *
 * [title] arrives on the navigation key because it is fixed by the licence itself, and looking it up
 * would mean re-parsing the whole report for one heading.
 */
@Composable
fun LicenceTextScreen(
    spdxId: String,
    title: String,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
    viewModel: LicencesViewModel =
        viewModel(factory = LicencesViewModel.Factory, extras = appViewModelExtras()),
) {
    val missing = stringResource(R.string.licence_text_missing)
    // `produceState` runs a suspending read and exposes the result as state — roughly a `useEffect`
    // that sets state when it resolves. Keyed on the id, so navigating to a different licence
    // re-reads rather than showing the previous one.
    val text by produceState(initialValue = "", spdxId, missing) {
        value = viewModel.licenceText(spdxId) ?: missing
    }

    DetailScaffold(title = title, onBack = onBack, modifier = modifier) { contentModifier ->
        // Selectable, because the one thing anybody does with a licence is quote from it.
        SelectionContainer(
            modifier =
                contentModifier
                    .verticalScroll(rememberScrollState())
                    .padding(Spacing.base),
        ) {
            Text(text = text, style = MaterialTheme.typography.bodySmall)
        }
    }
}
