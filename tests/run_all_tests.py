#!/usr/bin/env python3
"""
Comprehensive test runner for the Blake package.

Runs all tests including unit, integration, and performance tests.
"""

import sys
import subprocess
import time
from pathlib import Path
import argparse
import json
from datetime import datetime


class TestRunner:
    """Comprehensive test runner for Blake package."""
    
    def __init__(self, verbose=False, coverage=False):
        """Initialize the test runner."""
        self.verbose = verbose
        self.coverage = coverage
        self.results = {
            "start_time": datetime.now().isoformat(),
            "test_suites": {},
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "errors": []
        }
    
    def run_command(self, command, description):
        """Run a command and capture results."""
        print(f"\n🧪 {description}")
        print(f"Command: {' '.join(command)}")
        print("-" * 60)
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent
            )
            
            duration = time.time() - start_time
            
            # Parse pytest output
            output_lines = result.stdout.split('\n')
            test_summary = None
            
            for line in output_lines:
                if "failed" in line and "passed" in line:
                    test_summary = line
                    break
            
            return {
                "command": command,
                "description": description,
                "return_code": result.return_code,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration": duration,
                "test_summary": test_summary,
                "success": result.return_code == 0
            }
            
        except Exception as e:
            duration = time.time() - start_time
            return {
                "command": command,
                "description": description,
                "return_code": 1,
                "stdout": "",
                "stderr": str(e),
                "duration": duration,
                "test_summary": None,
                "success": False
            }
    
    def run_unit_tests(self):
        """Run unit tests."""
        command = ["python", "-m", "pytest", "tests/unit/", "-v"]
        if self.coverage:
            command.extend(["--cov=blake", "--cov-report=html", "--cov-report=term"])
        
        return self.run_command(command, "Running Unit Tests")
    
    def run_integration_tests(self):
        """Run integration tests."""
        command = ["python", "-m", "pytest", "tests/integration/", "-v"]
        if self.coverage:
            command.extend(["--cov=blake", "--cov-report=html", "--cov-report=term"])
        
        return self.run_command(command, "Running Integration Tests")
    
    def run_performance_tests(self):
        """Run performance tests."""
        command = ["python", "-m", "pytest", "tests/performance/", "-v"]
        
        return self.run_command(command, "Running Performance Tests")
    
    def run_download_tests(self):
        """Run download system tests."""
        command = ["python", "-m", "pytest", "tests/integration/test_*.py", "-v", "-k", "download"]
        
        return self.run_command(command, "Running Download Tests")
    
    def run_visualization_tests(self):
        """Run visualization tests."""
        command = ["python", "-m", "pytest", "tests/integration/test_visualization.py", "-v"]
        
        return self.run_command(command, "Running Visualization Tests")
    
    def run_all_tests(self):
        """Run all test suites."""
        print("🚀 Starting Comprehensive Test Suite")
        print("=" * 60)
        
        # Run unit tests
        unit_result = self.run_unit_tests()
        self.results["test_suites"]["unit"] = unit_result
        
        # Run integration tests
        integration_result = self.run_integration_tests()
        self.results["test_suites"]["integration"] = integration_result
        
        # Run performance tests
        performance_result = self.run_performance_tests()
        self.results["test_suites"]["performance"] = performance_result
        
        # Run specific test categories
        download_result = self.run_download_tests()
        self.results["test_suites"]["download"] = download_result
        
        visualization_result = self.run_visualization_tests()
        self.results["test_suites"]["visualization"] = visualization_result
        
        # Calculate totals
        self.calculate_totals()
        
        # Generate report
        self.generate_report()
        
        return self.results
    
    def calculate_totals(self):
        """Calculate total test statistics."""
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        
        for suite_name, suite_result in self.results["test_suites"].items():
            if suite_result["success"]:
                # Try to extract test counts from output
                output = suite_result["stdout"]
                if "passed" in output:
                    # Simple parsing - could be improved
                    lines = output.split('\n')
                    for line in lines:
                        if "passed" in line and "failed" in line:
                            try:
                                parts = line.split()
                                for i, part in enumerate(parts):
                                    if part == "passed":
                                        passed = int(parts[i-1])
                                        passed_tests += passed
                                        total_tests += passed
                                    elif part == "failed":
                                        failed = int(parts[i-1])
                                        failed_tests += failed
                                        total_tests += failed
                            except (ValueError, IndexError):
                                pass
        
        self.results["total_tests"] = total_tests
        self.results["passed_tests"] = passed_tests
        self.results["failed_tests"] = failed_tests
    
    def generate_report(self):
        """Generate comprehensive test report."""
        self.results["end_time"] = datetime.now().isoformat()
        self.results["total_duration"] = (
            datetime.fromisoformat(self.results["end_time"]) - 
            datetime.fromisoformat(self.results["start_time"])
        ).total_seconds()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        for suite_name, suite_result in self.results["test_suites"].items():
            status = "✅ PASSED" if suite_result["success"] else "❌ FAILED"
            duration = f"{suite_result['duration']:.2f}s"
            print(f"{suite_name.upper():<15} {status:<10} {duration:>8}")
            
            if suite_result["test_summary"]:
                print(f"  {suite_result['test_summary']}")
        
        print(f"\n📈 OVERALL STATISTICS:")
        print(f"  Total Tests: {self.results['total_tests']}")
        print(f"  Passed: {self.results['passed_tests']}")
        print(f"  Failed: {self.results['failed_tests']}")
        print(f"  Success Rate: {(self.results['passed_tests'] / max(self.results['total_tests'], 1) * 100):.1f}%")
        print(f"  Total Duration: {self.results['total_duration']:.2f}s")
        
        # Save detailed report
        report_path = Path(__file__).parent / "test_report.json"
        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\n📄 Detailed report saved to: {report_path}")
        
        # Overall success
        overall_success = all(suite["success"] for suite in self.results["test_suites"].values())
        if overall_success:
            print("\n🎉 ALL TESTS PASSED!")
        else:
            print("\n❌ SOME TESTS FAILED!")
        
        return overall_success


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Comprehensive Test Runner for Blake Package")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--coverage", "-c", action="store_true", help="Run with coverage")
    parser.add_argument("--suite", choices=["unit", "integration", "performance", "download", "visualization"], 
                       help="Run specific test suite")
    
    args = parser.parse_args()
    
    runner = TestRunner(verbose=args.verbose, coverage=args.coverage)
    
    if args.suite:
        # Run specific test suite
        if args.suite == "unit":
            result = runner.run_unit_tests()
        elif args.suite == "integration":
            result = runner.run_integration_tests()
        elif args.suite == "performance":
            result = runner.run_performance_tests()
        elif args.suite == "download":
            result = runner.run_download_tests()
        elif args.suite == "visualization":
            result = runner.run_visualization_tests()
        
        print(f"\n{'✅ PASSED' if result['success'] else '❌ FAILED'}: {result['description']}")
        sys.exit(0 if result['success'] else 1)
    else:
        # Run all tests
        success = runner.run_all_tests()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

