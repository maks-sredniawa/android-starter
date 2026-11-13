package app.starter.ui.support

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.ViewModelProvider.AndroidViewModelFactory.Companion.APPLICATION_KEY
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

data class LicencesUiState(
    val loading: Boolean = true,
    val groups: List<LicenceGroup> = emptyList(),
    val bundledTexts: Set<String> = emptySet(),
) {
    /** Only once loading is done: an empty list mid-read is not an unreadable report. */
    val unavailable: Boolean get() = !loading && groups.isEmpty()
}

class LicencesViewModel(
    application: Application,
) : AndroidViewModel(application) {
    private val state = MutableStateFlow(LicencesUiState())
    val uiState: StateFlow<LicencesUiState> = state.asStateFlow()

    init {
        viewModelScope.launch {
            // Off the main thread: reading an asset is a disk read, and this one is a few hundred
            // kilobytes of JSON.
            state.value =
                withContext(Dispatchers.IO) {
                    val assets = getApplication<Application>().assets
                    LicencesUiState(
                        loading = false,
                        groups =
                            licencesOrBundled(SupportConfig.BUNDLED_CREDITS) {
                                assets.open(LICENCES_ASSET).bufferedReader().use { it.readText() }
                            },
                        bundledTexts =
                            assets
                                .list(LICENCE_TEXT_DIRECTORY)
                                .orEmpty()
                                .map { it.removeSuffix(".txt") }
                                .toSet(),
                    )
                }
        }
    }

    /** A bundled licence's own text, or null when it is not one we ship. */
    suspend fun licenceText(spdxId: String): String? =
        withContext(Dispatchers.IO) {
            runCatching {
                getApplication<Application>()
                    .assets
                    .open("$LICENCE_TEXT_DIRECTORY/$spdxId.txt")
                    .bufferedReader()
                    .use { it.readText() }
            }.getOrNull()
        }

    companion object {
        val Factory: ViewModelProvider.Factory =
            viewModelFactory {
                initializer { LicencesViewModel(this[APPLICATION_KEY] as Application) }
            }
    }
}
