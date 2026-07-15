package com.techcontent.agent

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.navigation.NavController
import androidx.navigation.fragment.NavHostFragment
import androidx.navigation.ui.AppBarConfiguration
import androidx.navigation.ui.setupActionBarWithNavController
import com.techcontent.agent.databinding.ActivityMainBinding

/**
 * Single-activity host for the Tech Content Agent app.
 *
 * Navigation is managed by the Navigation Component ([NavHostFragment]).
 * FCM notification taps deliver an [android.content.Intent] with an
 * `approval_id` extra; [onNewIntent] forwards it to the NavController
 * so the app navigates to [ui.ApprovalDetailFragment] regardless of
 * whether the app was already running.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var navController: NavController

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setSupportActionBar(binding.toolbar)

        val navHostFragment =
            supportFragmentManager.findFragmentById(R.id.nav_host_fragment) as NavHostFragment
        navController = navHostFragment.navController

        val appBarConfig = AppBarConfiguration(navController.graph)
        setupActionBarWithNavController(navController, appBarConfig)

        // Handle notification tap that started the activity.
        handleIntent(intent)
    }

    override fun onNewIntent(intent: android.content.Intent) {
        super.onNewIntent(intent)
        handleIntent(intent)
    }

    override fun onSupportNavigateUp(): Boolean =
        navController.navigateUp() || super.onSupportNavigateUp()

    // ------------------------------------------------------------------
    // Private helpers
    // ------------------------------------------------------------------

    private fun handleIntent(intent: android.content.Intent) {
        val approvalId = intent.getStringExtra("approval_id") ?: return
        val args = android.os.Bundle().apply { putString("approval_id", approvalId) }
        navController.navigate(R.id.approvalDetailFragment, args)
    }
}
