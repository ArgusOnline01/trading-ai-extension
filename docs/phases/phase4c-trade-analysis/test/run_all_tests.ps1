# Phase 4C: Run All Tests
# Runs all Phase 4C test suites

$ErrorActionPreference = "Continue"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Phase 4C: Complete Test Suite" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if server is running
Write-Host "Checking if server is running..." -ForegroundColor Yellow
try {
    # Try health endpoint first, then fallback to trades endpoint
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8765/health" -Method Get -TimeoutSec 2 -ErrorAction Stop
        Write-Host "OK Server is running (health endpoint)" -ForegroundColor Green
    } catch {
        # Fallback: try trades endpoint
        $response = Invoke-WebRequest -Uri "http://localhost:8765/trades?limit=1" -Method Get -TimeoutSec 2 -ErrorAction Stop
        Write-Host "OK Server is running (trades endpoint)" -ForegroundColor Green
    }
    Write-Host ""
} catch {
    Write-Host "ERROR Server is not running. Please start the server first." -ForegroundColor Red
    Write-Host "  Run: docker-compose up -d" -ForegroundColor Yellow
    Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Run test suites
$testSuites = @(
    @{ Name = "API Integration Tests"; Script = "test_phase4c_apis.ps1" },
    @{ Name = "Edge Cases and Error Handling"; Script = "test_phase4c_edge_cases.ps1" },
    @{ Name = "Statistics Calculation Tests"; Script = "test_phase4c_statistics.ps1" }
)

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path

foreach ($suite in $testSuites) {
    Write-Host "----------------------------------------" -ForegroundColor Cyan
    Write-Host "Running: $($suite.Name)" -ForegroundColor Cyan
    Write-Host "----------------------------------------" -ForegroundColor Cyan
    Write-Host ""
    
    $testScript = Join-Path $scriptPath $suite.Script
    if (Test-Path $testScript) {
        & $testScript
        Write-Host ""
    } else {
        Write-Host "ERROR Test script not found: $testScript" -ForegroundColor Red
        Write-Host ""
    }
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "All Phase 4C Tests Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan


