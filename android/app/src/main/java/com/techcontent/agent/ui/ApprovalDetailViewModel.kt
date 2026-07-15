package com.techcontent.agent.ui

import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.techcontent.agent.data.api.ApprovalRepository
import com.techcontent.agent.data.model.ApprovalItem
import kotlinx.coroutines.launch

/**
 * ViewModel for [ApprovalDetailFragment].
 *
 * Exposes:
 *  - [approval]   — the loaded [ApprovalItem] (null while loading)
 *  - [uiState]    — loading / success / error / action-complete state
 */
class ApprovalDetailViewModel(
    private val repository: ApprovalRepository = ApprovalRepository(),
) : ViewModel() {

    sealed class UiState {
        data object Loading : UiState()
        data object Success : UiState()
        data class Error(val message: String) : UiState()
        data object ActionComplete : UiState()
    }

    private val _approval = MutableLiveData<ApprovalItem?>()
    val approval: LiveData<ApprovalItem?> = _approval

    private val _uiState = MutableLiveData<UiState>(UiState.Loading)
    val uiState: LiveData<UiState> = _uiState

    // ------------------------------------------------------------------
    // Public API
    // ------------------------------------------------------------------

    fun loadApproval(approvalId: String) {
        _uiState.value = UiState.Loading
        viewModelScope.launch {
            repository.getApproval(approvalId)
                .onSuccess { item ->
                    _approval.value = item
                    _uiState.value = UiState.Success
                }
                .onFailure { err ->
                    _uiState.value = UiState.Error(err.message ?: "Failed to load approval")
                }
        }
    }

    fun approve(approvalId: String, editedContent: String?) {
        _uiState.value = UiState.Loading
        viewModelScope.launch {
            repository.approve(approvalId, editedContent)
                .onSuccess { _uiState.value = UiState.ActionComplete }
                .onFailure { err ->
                    _uiState.value = UiState.Error(err.message ?: "Approve failed")
                }
        }
    }

    fun reject(approvalId: String) {
        _uiState.value = UiState.Loading
        viewModelScope.launch {
            repository.reject(approvalId)
                .onSuccess { _uiState.value = UiState.ActionComplete }
                .onFailure { err ->
                    _uiState.value = UiState.Error(err.message ?: "Reject failed")
                }
        }
    }
}
