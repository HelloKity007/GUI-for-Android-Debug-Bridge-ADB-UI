# -*- coding: utf-8 -*-
"""
Automated Testing System for ADB GUI Extensions
Tests all newly added features and generates comprehensive test report
"""
import os
import sys
import time
import json
import traceback
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer


class TestResult:
    """Test result container"""
    def __init__(self, test_name, category):
        self.test_name = test_name
        self.category = category
        self.status = "NOT_RUN"  # PASS, FAIL, SKIP, ERROR, NOT_RUN
        self.message = ""
        self.error_details = ""
        self.duration = 0
        self.timestamp = None


class AutomatedTester:
    """Automated testing system"""
    
    def __init__(self):
        self.results = []
        self.app = None
        self.main_window = None
        self.device_id = None
        self.is_tv_device = False
        
    def init_app(self):
        """Initialize PyQt application"""
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication(sys.argv)
        
        # Import and create main window
        from adb_gui import ADBGUI
        self.main_window = ADBGUI()
        
        # Get device info
        self.detect_device()
        
    def detect_device(self):
        """Detect connected device and check if it's a TV"""
        try:
            result = self.main_window.adb.run_command("devices")
            if result['success']:
                for line in result['stdout'].strip().split('\n')[1:]:
                    if '\tdevice' in line:
                        self.device_id = line.split('\t')[0]
                        break
            
            if self.device_id:
                # Check device type
                prop_result = self.main_window.adb.run_command(
                    f"-s {self.device_id} shell getprop ro.build.characteristics"
                )
                if prop_result['success']:
                    characteristics = prop_result['stdout'].strip().lower()
                    self.is_tv_device = 'tv' in characteristics or 'television' in characteristics
                
                print(f"✓ Device detected: {self.device_id}")
                if self.is_tv_device:
                    print("  Device type: TV (some features may not be supported)")
                else:
                    print("  Device type: Phone/Tablet")
            else:
                print("✗ No device connected")
                
        except Exception as e:
            print(f"✗ Error detecting device: {e}")
    
    def add_result(self, test_name, category, status, message="", error_details="", duration=0):
        """Add test result"""
        result = TestResult(test_name, category)
        result.status = status
        result.message = message
        result.error_details = error_details
        result.duration = duration
        result.timestamp = datetime.now().isoformat()
        self.results.append(result)
        
        # Print result
        status_icon = {
            "PASS": "✓",
            "FAIL": "✗",
            "SKIP": "⊘",
            "ERROR": "⚠",
            "NOT_RUN": "○"
        }
        icon = status_icon.get(status, "?")
        print(f"{icon} {test_name}: {status} ({duration:.2f}s)")
        if message:
            print(f"  → {message}")
    
    def run_test(self, test_name, category, test_func, skip_on_tv=False):
        """Run a single test"""
        if skip_on_tv and self.is_tv_device:
            self.add_result(test_name, category, "SKIP", "TV device - feature not applicable")
            return
        
        start_time = time.time()
        try:
            test_func()
            duration = time.time() - start_time
            self.add_result(test_name, category, "PASS", "Test completed successfully", "", duration)
        except AssertionError as e:
            duration = time.time() - start_time
            self.add_result(test_name, category, "FAIL", str(e), traceback.format_exc(), duration)
        except Exception as e:
            duration = time.time() - start_time
            self.add_result(test_name, category, "ERROR", str(e), traceback.format_exc(), duration)
    
    # Test Categories
    
    def test_file_manager(self):
        """Test Advanced File Manager"""
        print("\n=== Testing Advanced File Manager ===")
        
        def test_open_dialog():
            from file_manager_advanced import FileManagerDialog
            dialog = FileManagerDialog(
                self.main_window, 
                self.main_window.adb, 
                self.device_id,
                self.main_window.colors,
                self.main_window.project_dir
            )
            assert dialog is not None, "Dialog creation failed"
            dialog.close()
        
        self.run_test("File Manager - Open Dialog", "File Manager", test_open_dialog)
        
        def test_storage_info():
            from file_manager_advanced import FileManagerDialog
            dialog = FileManagerDialog(
                self.main_window, 
                self.main_window.adb, 
                self.device_id,
                self.main_window.colors,
                self.main_window.project_dir
            )
            time.sleep(1)  # Wait for storage info
            assert hasattr(dialog, 'storage_label'), "Storage label not found"
            dialog.close()
        
        self.run_test("File Manager - Storage Info", "File Manager", test_storage_info)
        
        def test_favorites():
            from file_manager_advanced import FileManagerDialog
            dialog = FileManagerDialog(
                self.main_window, 
                self.main_window.adb, 
                self.device_id,
                self.main_window.colors,
                self.main_window.project_dir
            )
            assert len(dialog.favorites) > 0, "No default favorites"
            dialog.close()
        
        self.run_test("File Manager - Favorites Loading", "File Manager", test_favorites)
        
        def test_recycle_bin():
            from file_manager_advanced import FileManagerDialog
            dialog = FileManagerDialog(
                self.main_window, 
                self.main_window.adb, 
                self.device_id,
                self.main_window.colors,
                self.main_window.project_dir
            )
            assert hasattr(dialog, 'recycle_bin_enabled'), "Recycle bin feature not found"
            assert os.path.exists(dialog.recycle_bin_path), "Recycle bin directory not created"
            dialog.close()
        
        self.run_test("File Manager - Recycle Bin Feature", "File Manager", test_recycle_bin)
    
    def test_app_manager(self):
        """Test App Manager"""
        print("\n=== Testing App Manager ===")
        
        def test_open_dialog():
            from app_manager import AppManagerDialog
            dialog = AppManagerDialog(
                self.main_window,
                self.main_window.adb,
                self.device_id,
                self.main_window.colors
            )
            assert dialog is not None, "Dialog creation failed"
            dialog.close()
        
        self.run_test("App Manager - Open Dialog", "App Manager", test_open_dialog)
        
        def test_list_apps():
            from app_manager import AppManagerDialog
            dialog = AppManagerDialog(
                self.main_window,
                self.main_window.adb,
                self.device_id,
                self.main_window.colors
            )
            time.sleep(2)  # Wait for app list
            assert dialog.app_tree.topLevelItemCount() > 0, "No apps loaded"
            dialog.close()
        
        self.run_test("App Manager - List Apps", "App Manager", test_list_apps)
        
        def test_filter_apps():
            from app_manager import AppManagerDialog
            dialog = AppManagerDialog(
                self.main_window,
                self.main_window.adb,
                self.device_id,
                self.main_window.colors
            )
            time.sleep(2)
            initial_count = dialog.app_tree.topLevelItemCount()
            dialog.filter_edit.setText("com.android")
            dialog.apply_filter()
            filtered_count = sum(1 for i in range(dialog.app_tree.topLevelItemCount()) 
                               if not dialog.app_tree.topLevelItem(i).isHidden())
            assert filtered_count <= initial_count, "Filter not working"
            dialog.close()
        
        self.run_test("App Manager - Filter Apps", "App Manager", test_filter_apps)
    
    def test_test_scripts(self):
        """Test Automation Scripts Extension"""
        print("\n=== Testing Test Scripts Extension ===")
        
        def test_open_dialog():
            from test_scripts_extension import TestScriptsDialog
            dialog = TestScriptsDialog(
                self.main_window,
                self.main_window.adb,
                self.device_id,
                self.main_window.colors,
                self.main_window.project_dir
            )
            assert dialog is not None, "Dialog creation failed"
            assert os.path.exists(dialog.test_data_dir), "Test data directory not created"
            dialog.close()
        
        self.run_test("Test Scripts - Open Dialog", "Test Scripts", test_open_dialog)
        
        def test_batch_operations():
            from test_scripts_extension import TestScriptsDialog
            dialog = TestScriptsDialog(
                self.main_window,
                self.main_window.adb,
                self.device_id,
                self.main_window.colors,
                self.main_window.project_dir
            )
            assert hasattr(dialog, 'batch_install_btn'), "Batch install button not found"
            assert hasattr(dialog, 'uninstall_text'), "Uninstall text area not found"
            dialog.close()
        
        self.run_test("Test Scripts - Batch Operations UI", "Test Scripts", test_batch_operations)
        
        def test_performance_monitoring():
            from test_scripts_extension import TestScriptsDialog
            dialog = TestScriptsDialog(
                self.main_window,
                self.main_window.adb,
                self.device_id,
                self.main_window.colors,
                self.main_window.project_dir
            )
            assert hasattr(dialog, 'fps_package_edit'), "FPS test controls not found"
            assert hasattr(dialog, 'monitor_package_edit'), "Monitor controls not found"
            dialog.close()
        
        self.run_test("Test Scripts - Performance Monitoring UI", "Test Scripts", test_performance_monitoring)
        
        def test_app_info():
            from test_scripts_extension import TestScriptsDialog
            dialog = TestScriptsDialog(
                self.main_window,
                self.main_window.adb,
                self.device_id,
                self.main_window.colors,
                self.main_window.project_dir
            )
            assert hasattr(dialog, 'permission_package_edit'), "Permission controls not found"
            dialog.close()
        
        self.run_test("Test Scripts - App Info UI", "Test Scripts", test_app_info)
        
        def test_media_capture():
            from test_scripts_extension import TestScriptsDialog
            dialog = TestScriptsDialog(
                self.main_window,
                self.main_window.adb,
                self.device_id,
                self.main_window.colors,
                self.main_window.project_dir
            )
            assert hasattr(dialog, 'screenshot_count_spin'), "Screenshot controls not found"
            assert hasattr(dialog, 'record_duration_spin'), "Recording controls not found"
            dialog.close()
        
        self.run_test("Test Scripts - Media Capture UI", "Test Scripts", test_media_capture, skip_on_tv=True)
    
    def test_cluster_control(self):
        """Test Cluster Control Extension"""
        print("\n=== Testing Cluster Control ===")
        
        def test_open_dialog():
            from cluster_control_extension import ClusterControlDialog
            dialog = ClusterControlDialog(
                self.main_window,
                self.main_window.adb,
                self.device_id,
                self.main_window.colors,
                self.main_window.project_dir
            )
            assert dialog is not None, "Dialog creation failed"
            dialog.close()
        
        self.run_test("Cluster Control - Open Dialog", "Cluster Control", test_open_dialog)
        
        def test_device_list():
            from cluster_control_extension import ClusterControlDialog
            dialog = ClusterControlDialog(
                self.main_window,
                self.main_window.adb,
                self.device_id,
                self.main_window.colors,
                self.main_window.project_dir
            )
            time.sleep(1)  # Wait for device refresh
            assert dialog.device_list.count() > 0, "No devices in list"
            dialog.close()
        
        self.run_test("Cluster Control - Device List", "Cluster Control", test_device_list)
        
        def test_device_groups():
            from cluster_control_extension import ClusterControlDialog
            dialog = ClusterControlDialog(
                self.main_window,
                self.main_window.adb,
                self.device_id,
                self.main_window.colors,
                self.main_window.project_dir
            )
            assert hasattr(dialog, 'device_groups'), "Device groups not initialized"
            assert hasattr(dialog, 'groups_list'), "Groups list not found"
            dialog.close()
        
        self.run_test("Cluster Control - Device Groups", "Cluster Control", test_device_groups)
        
        def test_batch_commands():
            from cluster_control_extension import ClusterControlDialog
            dialog = ClusterControlDialog(
                self.main_window,
                self.main_window.adb,
                self.device_id,
                self.main_window.colors,
                self.main_window.project_dir
            )
            assert hasattr(dialog, 'batch_command_edit'), "Command edit not found"
            assert hasattr(dialog, 'template_combo'), "Template combo not found"
            dialog.close()
        
        self.run_test("Cluster Control - Batch Commands UI", "Cluster Control", test_batch_commands)
        
        def test_script_recording():
            from cluster_control_extension import ClusterControlDialog
            dialog = ClusterControlDialog(
                self.main_window,
                self.main_window.adb,
                self.device_id,
                self.main_window.colors,
                self.main_window.project_dir
            )
            assert hasattr(dialog, 'recording'), "Recording flag not found"
            assert hasattr(dialog, 'recorded_commands'), "Recorded commands list not found"
            assert os.path.exists(dialog.scripts_dir), "Scripts directory not created"
            dialog.close()
        
        self.run_test("Cluster Control - Script Recording", "Cluster Control", test_script_recording)
        
        def test_sync_actions():
            from cluster_control_extension import ClusterControlDialog
            dialog = ClusterControlDialog(
                self.main_window,
                self.main_window.adb,
                self.device_id,
                self.main_window.colors,
                self.main_window.project_dir
            )
            assert hasattr(dialog, 'sync_text_input'), "Text input not found"
            assert hasattr(dialog, 'tap_x'), "Tap coordinates not found"
            dialog.close()
        
        self.run_test("Cluster Control - Sync Actions UI", "Cluster Control", test_sync_actions, skip_on_tv=True)
    
    def test_enhanced_logging(self):
        """Test Enhanced Logging System"""
        print("\n=== Testing Enhanced Logging System ===")
        
        def test_log_filters():
            assert hasattr(self.main_window, 'log_level_combo'), "Log level combo not found"
            assert hasattr(self.main_window, 'log_filter_edit'), "Log filter not found"
            assert hasattr(self.main_window, 'auto_scroll_cb'), "Auto-scroll checkbox not found"
        
        self.run_test("Enhanced Logging - Filters", "Enhanced Logging", test_log_filters)
        
        def test_log_storage():
            assert hasattr(self.main_window, 'all_logs'), "Log storage not initialized"
            assert isinstance(self.main_window.all_logs, list), "Log storage is not a list"
        
        self.run_test("Enhanced Logging - Storage", "Enhanced Logging", test_log_storage)
        
        def test_export_function():
            assert hasattr(self.main_window, 'export_logs'), "Export function not found"
        
        self.run_test("Enhanced Logging - Export Function", "Enhanced Logging", test_export_function)
    
    def test_quick_actions(self):
        """Test Quick Actions Panel"""
        print("\n=== Testing Quick Actions ===")
        
        def test_quick_actions_tab():
            # Find Quick Actions tab
            tabs = self.main_window.findChildren(QApplication.instance().topLevelWidgets()[0].__class__)
            # Quick actions should be accessible
            assert hasattr(self.main_window, 'quick_battery_status'), "Battery status action not found"
        
        self.run_test("Quick Actions - Tab Exists", "Quick Actions", test_quick_actions_tab)
        
        def test_device_info_actions():
            assert hasattr(self.main_window, 'quick_device_info'), "Device info action not found"
            assert hasattr(self.main_window, 'quick_display_info'), "Display info action not found"
            assert hasattr(self.main_window, 'quick_storage_info'), "Storage info action not found"
        
        self.run_test("Quick Actions - Device Info", "Quick Actions", test_device_info_actions)
        
        def test_performance_actions():
            assert hasattr(self.main_window, 'quick_cpu_info'), "CPU info action not found"
            assert hasattr(self.main_window, 'quick_memory_info'), "Memory info action not found"
            assert hasattr(self.main_window, 'quick_top_processes'), "Top processes action not found"
        
        self.run_test("Quick Actions - Performance", "Quick Actions", test_performance_actions)
        
        def test_network_actions():
            assert hasattr(self.main_window, 'quick_ip_info'), "IP info action not found"
            assert hasattr(self.main_window, 'quick_wifi_info'), "WiFi info action not found"
        
        self.run_test("Quick Actions - Network", "Quick Actions", test_network_actions, skip_on_tv=True)
    
    def test_config_system(self):
        """Test Configuration System"""
        print("\n=== Testing Configuration System ===")
        
        def test_config_file():
            config_file = os.path.join(self.main_window.project_dir, 'config.ini')
            assert os.path.exists(config_file), "config.ini not found"
        
        self.run_test("Config System - File Exists", "Config System", test_config_file)
        
        def test_config_loading():
            assert hasattr(self.main_window, 'config'), "Config not loaded"
            assert self.main_window.config is not None, "Config is None"
        
        self.run_test("Config System - Loading", "Config System", test_config_loading)
        
        def test_extension_configs():
            assert self.main_window.config.has_section('Extensions'), "Extensions section not found"
            extensions = ['scrcpy_enabled', 'awesome_adb_enabled', 'test_scripts_enabled', 'cluster_control_enabled']
            for ext in extensions:
                assert self.main_window.config.has_option('Extensions', ext), f"{ext} not in config"
        
        self.run_test("Config System - Extension Configs", "Config System", test_extension_configs)
    
    def run_all_tests(self):
        """Run all tests"""
        print("=" * 60)
        print("ADB GUI - Automated Testing System")
        print("=" * 60)
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Device: {self.device_id or 'No device'}")
        print(f"Device Type: {'TV' if self.is_tv_device else 'Phone/Tablet'}")
        print("=" * 60)
        
        if not self.device_id:
            print("\n⚠ WARNING: No device connected. Some tests will fail.")
            print("Please connect a device and run tests again.\n")
        
        # Initialize application
        self.init_app()
        
        # Run test categories
        self.test_file_manager()
        self.test_app_manager()
        self.test_test_scripts()
        self.test_cluster_control()
        self.test_enhanced_logging()
        self.test_quick_actions()
        self.test_config_system()
        
        # Generate report
        self.generate_report()
    
    def generate_report(self):
        """Generate test report"""
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        # Count results
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == "PASS")
        failed = sum(1 for r in self.results if r.status == "FAIL")
        skipped = sum(1 for r in self.results if r.status == "SKIP")
        errors = sum(1 for r in self.results if r.status == "ERROR")
        
        print(f"Total Tests: {total}")
        print(f"✓ Passed: {passed}")
        print(f"✗ Failed: {failed}")
        print(f"⊘ Skipped: {skipped}")
        print(f"⚠ Errors: {errors}")
        
        if total > 0:
            pass_rate = (passed / (total - skipped)) * 100 if (total - skipped) > 0 else 0
            print(f"\nPass Rate: {pass_rate:.1f}% (excluding skipped)")
        
        # Category summary
        print("\n" + "-" * 60)
        print("CATEGORY BREAKDOWN")
        print("-" * 60)
        
        categories = {}
        for result in self.results:
            if result.category not in categories:
                categories[result.category] = {'PASS': 0, 'FAIL': 0, 'SKIP': 0, 'ERROR': 0}
            categories[result.category][result.status] += 1
        
        for category, counts in sorted(categories.items()):
            total_cat = sum(counts.values())
            print(f"\n{category}:")
            print(f"  ✓ {counts['PASS']} | ✗ {counts['FAIL']} | ⊘ {counts['SKIP']} | ⚠ {counts['ERROR']}")
        
        # Failed tests details
        if failed > 0 or errors > 0:
            print("\n" + "-" * 60)
            print("FAILED/ERROR TESTS DETAILS")
            print("-" * 60)
            
            for result in self.results:
                if result.status in ['FAIL', 'ERROR']:
                    print(f"\n{result.status}: {result.test_name}")
                    print(f"  Message: {result.message}")
                    if result.error_details:
                        print(f"  Details:\n{result.error_details[:500]}")
        
        # Skipped tests (TV-specific)
        if skipped > 0:
            print("\n" + "-" * 60)
            print("SKIPPED TESTS (TV Device Limitations)")
            print("-" * 60)
            
            for result in self.results:
                if result.status == 'SKIP':
                    print(f"  ⊘ {result.test_name}: {result.message}")
        
        # Save JSON report
        report_file = os.path.join(
            self.main_window.project_dir,
            f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'device': self.device_id,
            'device_type': 'TV' if self.is_tv_device else 'Phone/Tablet',
            'summary': {
                'total': total,
                'passed': passed,
                'failed': failed,
                'skipped': skipped,
                'errors': errors,
                'pass_rate': f"{pass_rate:.1f}%" if total > 0 else "N/A"
            },
            'categories': categories,
            'results': [
                {
                    'test_name': r.test_name,
                    'category': r.category,
                    'status': r.status,
                    'message': r.message,
                    'duration': r.duration,
                    'timestamp': r.timestamp
                }
                for r in self.results
            ]
        }
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            print(f"\n✓ Test report saved to: {report_file}")
        except Exception as e:
            print(f"\n✗ Failed to save report: {e}")
        
        print("\n" + "=" * 60)
        print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)


def main():
    """Main entry point"""
    tester = AutomatedTester()
    tester.run_all_tests()
    
    # Exit
    print("\nPress Enter to exit...")
    input()


if __name__ == "__main__":
    main()
