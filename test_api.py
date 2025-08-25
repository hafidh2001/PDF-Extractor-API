#!/usr/bin/env python3
"""
Test script untuk PDF Metadata Extractor API
Pastikan API sudah berjalan di http://localhost:8000 sebelum menjalankan test ini
"""

import requests
import json
import sys
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

class Colors:
    """ANSI color codes untuk output terminal"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_test_header(test_name: str):
    """Print header untuk setiap test"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'='*50}{Colors.RESET}")
    print(f"{Colors.BLUE}{Colors.BOLD}Testing: {test_name}{Colors.RESET}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'='*50}{Colors.RESET}")

def print_success(message: str):
    """Print pesan sukses"""
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")

def print_error(message: str):
    """Print pesan error"""
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")

def print_info(message: str):
    """Print informasi"""
    print(f"{Colors.YELLOW}ℹ {message}{Colors.RESET}")

def test_root_endpoint():
    """Test root endpoint"""
    print_test_header("Root Endpoint (/)")
    
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            data = response.json()
            print_success(f"Root endpoint accessible")
            print_info(f"Message: {data.get('message', 'N/A')}")
            
            if 'endpoints' in data:
                print_info("Available endpoints:")
                for endpoint, desc in data['endpoints'].items():
                    print(f"  • {endpoint}: {desc}")
            return True
        else:
            print_error(f"Status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to API. Make sure it's running on http://localhost:8000")
        return False
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False

def test_list_files():
    """Test list files endpoint"""
    print_test_header("List Files (/list)")
    
    try:
        response = requests.get(f"{BASE_URL}/list")
        if response.status_code == 200:
            data = response.json()
            print_success(f"List endpoint working")
            print_info(f"Total files: {data.get('total_files', 0)}")
            
            files = data.get('files', [])
            if files:
                print_info("Files found:")
                for file in files[:3]:
                    print(f"  • {file['filename']} ({file['size_mb']} MB)")
                if len(files) > 3:
                    print(f"  ... and {len(files) - 3} more")
            else:
                print_info("No PDF files in BERKAS folder")
            return True
        else:
            print_error(f"Status code: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False

def test_extract_all():
    """Test extract all metadata endpoint"""
    print_test_header("Extract All Metadata (/extract)")
    
    try:
        response = requests.get(f"{BASE_URL}/extract")
        if response.status_code == 200:
            data = response.json()
            print_success(f"Extract endpoint working")
            print_info(f"Total files: {data.get('total_files', 0)}")
            print_info(f"Successful: {data.get('successful', 0)}")
            print_info(f"Failed: {data.get('failed', 0)}")
            
            results = data.get('results', [])
            if results:
                print_info("Sample extraction:")
                sample = results[0]
                print(f"  • File: {sample.get('file', 'N/A')}")
                print(f"  • Judul: {sample.get('judul', 'N/A')}")
                print(f"  • Penulis: {sample.get('penulis', 'N/A')}")
                print(f"  • Tahun: {sample.get('tahun', 'N/A')}")
            return True
        else:
            print_error(f"Status code: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False

def test_search():
    """Test search endpoint"""
    print_test_header("Search PDFs (/search)")
    
    test_keyword = "pdf"
    
    try:
        response = requests.get(f"{BASE_URL}/search", params={"keyword": test_keyword})
        if response.status_code == 200:
            data = response.json()
            print_success(f"Search endpoint working")
            print_info(f"Keyword: '{test_keyword}'")
            print_info(f"Files checked: {data.get('total_files_checked', 0)}")
            print_info(f"Matches found: {data.get('matches_found', 0)}")
            
            results = data.get('results', [])
            if results:
                print_info("Sample result:")
                sample = results[0]
                print(f"  • File: {sample.get('file', 'N/A')}")
                print(f"  • Relevance score: {sample.get('relevance_score', 0)}")
            return True
        else:
            print_error(f"Status code: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False

def test_extract_single():
    """Test extract single file endpoint"""
    print_test_header("Extract Single File (/extract/{filename})")
    
    # First get list of files
    try:
        list_response = requests.get(f"{BASE_URL}/list")
        if list_response.status_code == 200:
            files = list_response.json().get('files', [])
            
            if not files:
                print_info("No PDF files to test extraction")
                return True
            
            test_file = files[0]['filename']
            print_info(f"Testing with file: {test_file}")
            
            response = requests.get(f"{BASE_URL}/extract/{test_file}")
            if response.status_code == 200:
                data = response.json()
                print_success(f"Single file extraction working")
                print_info(f"Extracted metadata:")
                print(f"  • Judul: {data.get('judul', 'N/A')}")
                print(f"  • Penulis: {data.get('penulis', 'N/A')}")
                print(f"  • Tahun: {data.get('tahun', 'N/A')}")
                print(f"  • File size: {data.get('file_size', 0)} bytes")
                return True
            else:
                print_error(f"Status code: {response.status_code}")
                return False
        else:
            print_error("Cannot get file list")
            return False
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False

def test_invalid_file():
    """Test dengan file yang tidak ada"""
    print_test_header("Invalid File Test")
    
    try:
        response = requests.get(f"{BASE_URL}/extract/tidak_ada.pdf")
        if response.status_code == 404:
            print_success("Properly handles non-existent file (404)")
            return True
        else:
            print_error(f"Unexpected status code: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False

def run_all_tests():
    """Run all tests"""
    print(f"\n{Colors.BOLD}PDF Metadata Extractor API - Test Suite{Colors.RESET}")
    print(f"Target: {BASE_URL}")
    
    tests = [
        test_root_endpoint,
        test_list_files,
        test_extract_all,
        test_search,
        test_extract_single,
        test_invalid_file
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print_error(f"Test crashed: {str(e)}")
            failed += 1
    
    # Summary
    print(f"\n{Colors.BOLD}{'='*50}{Colors.RESET}")
    print(f"{Colors.BOLD}Test Summary{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*50}{Colors.RESET}")
    
    total = passed + failed
    print(f"{Colors.GREEN}Passed: {passed}/{total}{Colors.RESET}")
    
    if failed > 0:
        print(f"{Colors.RED}Failed: {failed}/{total}{Colors.RESET}")
    
    if passed == total:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ All tests passed!{Colors.RESET}")
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}✗ Some tests failed{Colors.RESET}")
    
    return failed == 0

if __name__ == "__main__":
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Test interrupted by user{Colors.RESET}")
        sys.exit(1)