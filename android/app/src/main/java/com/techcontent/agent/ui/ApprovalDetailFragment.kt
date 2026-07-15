package com.techcontent.agent.ui

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import com.google.android.material.snackbar.Snackbar
import com.techcontent.agent.databinding.FragmentApprovalDetailBinding

/**
 * Screen that shows a generated LinkedIn post and lets the user
 * review, optionally edit, and then confirm or reject it.
 *
 * Navigation argument:  `approval_id` (String) — provided by the
 * deep-link intent from [fcm.TechAgentMessagingService] or the nav graph.
 *
 * Flow:
 *  1. Fragment loads → ViewModel calls `GET /approvals/{id}`
 *  2. Post text displayed in a read-only [android.widget.TextView]
 *  3. **Edit** button toggles a [com.google.android.material.textfield.TextInputEditText]
 *  4. **Confirm** taps → `POST /approvals/{id}/approve` (with edited text if changed)
 *  5. **Reject** taps  → `POST /approvals/{id}/reject`
 *  6. Either action navigates back with a success snackbar
 */
class ApprovalDetailFragment : Fragment() {

    private var _binding: FragmentApprovalDetailBinding? = null
    private val binding get() = _binding!!

    private val viewModel: ApprovalDetailViewModel by viewModels()

    // ------------------------------------------------------------------
    // Lifecycle
    // ------------------------------------------------------------------

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?,
    ): View {
        _binding = FragmentApprovalDetailBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        val approvalId = arguments?.getString("approval_id")
            ?: error("ApprovalDetailFragment requires an approval_id argument")

        observeViewModel(approvalId)
        setupButtons(approvalId)

        viewModel.loadApproval(approvalId)
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }

    // ------------------------------------------------------------------
    // Private helpers
    // ------------------------------------------------------------------

    private fun observeViewModel(approvalId: String) {
        viewModel.approval.observe(viewLifecycleOwner) { item ->
            if (item == null) return@observe
            binding.textTopic.text = item.topic
            binding.textPostContent.setText(item.edited_content ?: item.original_content)
        }

        viewModel.uiState.observe(viewLifecycleOwner) { state ->
            when (state) {
                is ApprovalDetailViewModel.UiState.Loading -> {
                    binding.progressBar.visibility = View.VISIBLE
                    binding.buttonConfirm.isEnabled = false
                    binding.buttonReject.isEnabled = false
                }
                is ApprovalDetailViewModel.UiState.Success -> {
                    binding.progressBar.visibility = View.GONE
                    binding.buttonConfirm.isEnabled = true
                    binding.buttonReject.isEnabled = true
                }
                is ApprovalDetailViewModel.UiState.Error -> {
                    binding.progressBar.visibility = View.GONE
                    binding.buttonConfirm.isEnabled = true
                    binding.buttonReject.isEnabled = true
                    Snackbar.make(binding.root, state.message, Snackbar.LENGTH_LONG).show()
                }
                is ApprovalDetailViewModel.UiState.ActionComplete -> {
                    Snackbar.make(binding.root, "Done!", Snackbar.LENGTH_SHORT).show()
                    requireActivity().onBackPressedDispatcher.onBackPressed()
                }
            }
        }
    }

    private fun setupButtons(approvalId: String) {
        binding.buttonEdit.setOnClickListener {
            val isEditable = binding.textPostContent.isEnabled
            binding.textPostContent.isEnabled = !isEditable
            binding.buttonEdit.text = if (isEditable) "Edit" else "Done editing"
            if (isEditable) binding.textPostContent.clearFocus()
        }

        binding.buttonConfirm.setOnClickListener {
            val currentText = binding.textPostContent.text?.toString()
            val originalText = viewModel.approval.value?.original_content
            // Only send edited_content if the user actually changed the text.
            val editedContent = if (currentText != originalText) currentText else null
            viewModel.approve(approvalId, editedContent)
        }

        binding.buttonReject.setOnClickListener {
            viewModel.reject(approvalId)
        }
    }
}
