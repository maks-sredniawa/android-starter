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
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

data class LicencesUiState(
    val loading: Boolean = true,
    val groups: List<LicenceGroup> = emptyList(),
    val bundledTexts: Set<String> = emptySet(),
    val unavailable: Boolean = false,
)

class LicencesViewModel(
    application: Application,
) : AndroidViewModel(application) {
    private val state = MutableStateFlow(LicencesUiState())
    val uiState: StateFlow<LicencesUiState> = state.asStateFlow()

    // An app that keeps its own LicencesScreen.kt (support-sync.keep) still reads this.
    val groups: StateFlow<List<LicenceGroup>> =
        state.map { it.groups }.stateIn(viewModelScope, SharingStarted.Eagerly, emptyList())

    init {
        viewModelScope.launch {
            // Off the main thread: reading an asset is a disk read, and this one is a few hundred
            // kilobytes of JSON.
            state.value =
                withContext(Dispatchers.IO) {
                    val assets = getApplication<Application>().assets
                    val credits =
                        readCredits(SupportConfig.BUNDLED_CREDITS) {
                            assets.open(LICENCES_ASSET).bufferedReader().use { it.readText() }
                        }
                    LicencesUiState(
                        loading = false,
                        groups = credits.groups,
                        bundledTexts =
                            runCatching { assets.list(LICENCE_TEXT_DIRECTORY).orEmpty() }
                                .getOrDefault(emptyArray())
                                .map { it.removeSuffix(".txt") }
                                .toSet(),
                        unavailable = credits.reportUnreadable,
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
