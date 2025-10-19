#!/usr/bin/env python3
"""
Verification script for DetachedInstance error fixes
Tests that the error handler works correctly
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))


def test_imports():
    """Test that all required modules import correctly"""
    print("🧪 Testing imports...")

    try:
        from src.utils.error_handler import DatabaseErrorHandler

        print("  ✅ DatabaseErrorHandler imported successfully")
    except ImportError as e:
        print(f"  ❌ Failed to import DatabaseErrorHandler: {e}")
        return False

    try:
        import pages

        print("  ✅ Pages module accessible")
    except ImportError as e:
        print(f"  ⚠️  Pages import: {e} (expected in non-Streamlit context)")

    return True


def test_error_detection():
    """Test error detection patterns"""
    print("\n🧪 Testing error detection patterns...")

    from src.utils.error_handler import DatabaseErrorHandler

    test_cases = [
        ("DetachedInstance error", True),
        ("Object is detached from session", True),
        ("not bound to a Session", True),
        ("object is being detached from the Session", True),
        ("Unexpected state when detaching", True),
        ("Generic database error", False),
        ("Connection timeout", False),
        ("Query failed", False),
    ]

    for error_msg, should_detect in test_cases:

        class TestError(Exception):
            pass

        error = TestError(error_msg)
        detected = DatabaseErrorHandler.is_detached_instance_error(error)

        status = "✅" if detected == should_detect else "❌"
        print(
            f"  {status} '{error_msg}' → detected={detected} (expected={should_detect})"
        )

        if detected != should_detect:
            return False

    return True


def test_error_handler_methods():
    """Test that error handler has all required methods"""
    print("\n🧪 Testing error handler methods...")

    from src.utils.error_handler import DatabaseErrorHandler

    required_methods = [
        "is_detached_instance_error",
        "log_database_error",
        "display_database_error",
        "display_generic_error",
    ]

    for method in required_methods:
        if hasattr(DatabaseErrorHandler, method):
            print(f"  ✅ {method} exists")
        else:
            print(f"  ❌ {method} missing")
            return False

    return True


def test_admin_pages_syntax():
    """Test that admin pages have valid Python syntax"""
    print("\n🧪 Testing admin pages syntax...")

    import py_compile

    pages_to_check = [
        "pages/2_Admin_Users.py",
        "pages/3_Admin_Rooms.py",
        "pages/4_Admin_Allocations.py",
    ]

    all_valid = True
    for page in pages_to_check:
        page_path = project_root / page
        if page_path.exists():
            try:
                py_compile.compile(str(page_path), doraise=True)
                print(f"  ✅ {page} - Valid syntax")
            except py_compile.PyCompileError as e:
                print(f"  ❌ {page} - Syntax error: {e}")
                all_valid = False
        else:
            print(f"  ⚠️  {page} - File not found")

    return all_valid


def test_documentation_exists():
    """Test that all documentation files exist"""
    print("\n🧪 Testing documentation...")

    docs_to_check = [
        "docs/DEBUGGING_DETACHED_INSTANCE.md",
        "docs/DETACHED_INSTANCE_VISUAL_EXPLANATION.md",
        "docs/SERVICE_FIX_IMPLEMENTATION_GUIDE.md",
        "DETACHED_INSTANCE_FIX_SUMMARY.txt",
        "FIX_COMPLETE.md",
    ]

    all_exist = True
    for doc in docs_to_check:
        doc_path = project_root / doc
        if doc_path.exists():
            size = doc_path.stat().st_size
            print(f"  ✅ {doc} ({size} bytes)")
        else:
            print(f"  ❌ {doc} - File not found")
            all_exist = False

    return all_exist


def main():
    """Run all verification tests"""
    print("=" * 70)
    print("🔍 Verifying DetachedInstance Error Fixes")
    print("=" * 70)

    tests = [
        ("Imports", test_imports),
        ("Error Detection", test_error_detection),
        ("Handler Methods", test_error_handler_methods),
        ("Pages Syntax", test_admin_pages_syntax),
        ("Documentation", test_documentation_exists),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ {test_name} test failed with exception: {e}")
            import traceback

            traceback.print_exc()
            results.append((test_name, False))

    print("\n" + "=" * 70)
    print("📊 Verification Results")
    print("=" * 70)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:8} {test_name}")

    all_passed = all(result for _, result in results)

    print("=" * 70)
    if all_passed:
        print("✅ All verification tests passed!")
        print("\nThe fix is ready for testing. You can now:")
        print("1. Navigate to admin pages in Streamlit")
        print("2. Test normal operations (filter, sort, view)")
        print("3. Check /logs/ for any errors")
        print("4. Verify error messages display correctly")
    else:
        print("❌ Some verification tests failed.")
        print("Please review the issues above.")

    print("=" * 70)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
