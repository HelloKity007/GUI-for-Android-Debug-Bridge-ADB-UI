# -*- coding: utf-8 -*-
"""
Quick Test Script - Tests basic functionality of all extensions
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test all module imports"""
    print("Testing module imports...")
    
    try:
        from adb_gui import ADBGUI
        print("✓ Main GUI imported")
    except Exception as e:
        print(f"✗ Main GUI import failed: {e}")
        return False
    
    try:
        from file_manager_advanced import FileManagerDialog
        print("✓ File Manager imported")
    except Exception as e:
        print(f"✗ File Manager import failed: {e}")
        return False
    
    try:
        from app_manager import AppManagerDialog
        print("✓ App Manager imported")
    except Exception as e:
        print(f"✗ App Manager import failed: {e}")
        return False
    
    try:
        from test_scripts_extension import TestScriptsDialog
        print("✓ Test Scripts imported")
    except Exception as e:
        print(f"✗ Test Scripts import failed: {e}")
        return False
    
    try:
        from cluster_control_extension import ClusterControlDialog
        print("✓ Cluster Control imported")
    except Exception as e:
        print(f"✗ Cluster Control import failed: {e}")
        return False
    
    return True

def test_config():
    """Test configuration file"""
    print("\nTesting configuration...")
    
    config_file = 'config.ini'
    if not os.path.exists(config_file):
        print(f"✗ {config_file} not found")
        return False
    
    print(f"✓ {config_file} exists")
    
    import configparser
    config = configparser.ConfigParser()
    try:
        config.read(config_file, encoding='utf-8')
        print(f"✓ Config loaded successfully")
        
        # Check sections
        required_sections = ['Paths', 'Extensions', 'Settings']
        for section in required_sections:
            if config.has_section(section):
                print(f"  ✓ [{section}] section found")
            else:
                print(f"  ✗ [{section}] section missing")
        
        # Check extensions
        extensions = ['scrcpy_enabled', 'awesome_adb_enabled', 'test_scripts_enabled', 'cluster_control_enabled']
        for ext in extensions:
            if config.has_option('Extensions', ext):
                print(f"  ✓ {ext} configured")
            else:
                print(f"  ✗ {ext} missing")
        
        return True
    except Exception as e:
        print(f"✗ Config loading failed: {e}")
        return False

def test_directories():
    """Test required directories"""
    print("\nTesting directory structure...")
    
    required_dirs = [
        'extension',
        'test_data',
        'cluster_scripts'
    ]
    
    all_exist = True
    for dir_name in required_dirs:
        if os.path.exists(dir_name):
            print(f"✓ {dir_name}/ exists")
        else:
            print(f"⚠ {dir_name}/ will be created on first use")
    
    return True

def test_device_connection():
    """Test ADB device connection"""
    print("\nTesting device connection...")
    
    import subprocess
    try:
        result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            devices = [line for line in lines[1:] if '\tdevice' in line]
            
            if devices:
                print(f"✓ {len(devices)} device(s) connected")
                for device in devices:
                    device_id = device.split('\t')[0]
                    print(f"  → {device_id}")
                
                # Check device type
                device_id = devices[0].split('\t')[0]
                prop_result = subprocess.run(
                    ['adb', '-s', device_id, 'shell', 'getprop', 'ro.build.characteristics'],
                    capture_output=True, text=True, timeout=5
                )
                if prop_result.returncode == 0:
                    characteristics = prop_result.stdout.strip().lower()
                    if 'tv' in characteristics:
                        print(f"  ⚠ Device type: TV (some features may be limited)")
                    else:
                        print(f"  ✓ Device type: Phone/Tablet")
                
                return True
            else:
                print("✗ No devices connected")
                print("  Please connect a device via USB with debugging enabled")
                return False
        else:
            print("✗ ADB command failed")
            return False
    except FileNotFoundError:
        print("✗ ADB not found in PATH")
        print("  Please configure ADB path in the application")
        return False
    except Exception as e:
        print(f"✗ Error checking devices: {e}")
        return False

def main():
    """Run quick tests"""
    print("=" * 60)
    print("ADB GUI - Quick Validation Test")
    print("=" * 60)
    print()
    
    results = []
    
    # Run tests
    results.append(("Module Imports", test_imports()))
    results.append(("Configuration", test_config()))
    results.append(("Directory Structure", test_directories()))
    results.append(("Device Connection", test_device_connection()))
    
    # Summary
    print("\n" + "=" * 60)
    print("QUICK TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print()
    print(f"Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All quick tests passed!")
        print("You can now run the full test suite with run_automated_tests.py")
    else:
        print("\n⚠ Some tests failed. Please check the errors above.")
    
    print("\n" + "=" * 60)
    print("To run full automated tests:")
    print("  1. Windows: Double-click run_tests.bat")
    print("  2. Command line: python run_automated_tests.py")
    print("=" * 60)

if __name__ == "__main__":
    main()
    print("\nPress Enter to exit...")
    input()
