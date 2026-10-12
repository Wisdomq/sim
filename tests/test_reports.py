"""Tests for reporting and export functionality (Phase 9)."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest


def _login(client, email, password):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def _setup_reporting_accounts(client):
    """Setup test accounts for reporting tests."""
    # Create dealer
    signup = client.post(
        "/api/v1/onboarding/dealers",
        json={
            "dealer_name": "Report Dealer",
            "safaricom_dealer_shortcode": "RPT001",
            "hq_email": "report@example.com",
            "hq_password": "supersecret",
        },
    )
    assert signup.status_code == 201
    hq_token = _login(client, "report@example.com", "supersecret")

    # Create branch
    branch = client.post(
        "/api/v1/branches",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={
            "name": "Report Branch",
            "type": "SHOP",
            "id_number": "RPT-BR-001",
            "photo_url": "https://example.com/report-branch.jpg",
            "email": "report-branch@example.com",
            "password": "branchsecret",
        },
    )
    assert branch.status_code == 201
    branch_token = _login(client, "report-branch@example.com", "branchsecret")

    # Create BA
    ba = client.post(
        "/api/v1/brand-ambassadors",
        headers={"Authorization": f"Bearer {branch_token}"},
        json={
            "name": "Report BA",
            "email": "report-ba@example.com",
            "password": "basecret123",
            "phone_msisdn": "254700000004",
            "id_number": "RPT-BA-001",
            "photo_url": "https://example.com/report-ba.jpg",
        },
    )
    assert ba.status_code == 201

    return hq_token, branch_token


def _setup_stock_and_sales(client, hq_token, branch_token):
    """Setup minimal data for reporting tests."""
    # Create commission rule
    commission_response = client.post(
        "/api/v1/commission/rules",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={
            "name": "Test Commission Rule",
            "amount_per_sim": "50.00",
            "effective_from": (datetime.now() - timedelta(days=30)).isoformat(),
        },
    )
    assert commission_response.status_code == 201


def test_hq_can_generate_report(client):
    """Test that HQ users can generate comprehensive reports."""
    hq_token, branch_token = _setup_reporting_accounts(client)
    _setup_stock_and_sales(client, hq_token, branch_token)

    # Generate report
    response = client.post(
        "/api/v1/reports",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={
            "period_type": "DAILY",
            "period_start": (date.today() - timedelta(days=1)).isoformat(),
            "period_end": date.today().isoformat(),
            "branch_id": None,  # All branches
        },
    )

    assert response.status_code == 200
    report_data = response.json()

    # Verify report structure
    assert "period_type" in report_data
    assert "period_start" in report_data
    assert "period_end" in report_data
    assert "total_stock_counts" in report_data
    assert "total_sales_count" in report_data
    assert "total_commission_owed" in report_data
    assert "overall_performance_percentage" in report_data
    assert "branch_reports" in report_data
    assert "reconciliation_headlines" in report_data
    assert "generated_at" in report_data


def test_branch_can_generate_own_report(client):
    """Test that Branch users can generate reports for their own branch only."""
    hq_token, branch_token = _setup_reporting_accounts(client)

    # Generate report as branch user
    response = client.post(
        "/api/v1/reports",
        headers={"Authorization": f"Bearer {branch_token}"},
        json={
            "period_type": "DAILY",
            "period_start": (date.today() - timedelta(days=1)).isoformat(),
            "period_end": date.today().isoformat(),
            "branch_id": None,  # Should be ignored for branch users
        },
    )

    assert response.status_code == 200
    report_data = response.json()

    # Branch should only see their own branch
    assert len(report_data["branch_reports"]) == 1
    assert report_data["branch_reports"][0]["branch_name"] == "Report Branch"


def test_branch_cannot_access_other_branch_data(client):
    """Test that Branch users cannot access other branches' data."""
    hq_token, branch_token = _setup_reporting_accounts(client)

    # Try to generate report for different branch (should fail)
    response = client.post(
        "/api/v1/reports",
        headers={"Authorization": f"Bearer {branch_token}"},
        json={
            "period_type": "DAILY",
            "period_start": (date.today() - timedelta(days=1)).isoformat(),
            "period_end": date.today().isoformat(),
            "branch_id": 999,  # Invalid branch ID
        },
    )

    assert response.status_code == 403


def test_hq_can_filter_by_branch(client):
    """Test that HQ users can filter reports by specific branch."""
    hq_token, branch_token = _setup_reporting_accounts(client)

    # Get branch ID from branch reports
    all_branches_response = client.post(
        "/api/v1/reports",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={
            "period_type": "DAILY",
            "period_start": (date.today() - timedelta(days=1)).isoformat(),
            "period_end": date.today().isoformat(),
            "branch_id": None,
        },
    )
    branch_id = all_branches_response.json()["branch_reports"][0]["branch_id"]

    # Generate report filtered by branch
    response = client.post(
        "/api/v1/reports",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={
            "period_type": "DAILY",
            "period_start": (date.today() - timedelta(days=1)).isoformat(),
            "period_end": date.today().isoformat(),
            "branch_id": branch_id,
        },
    )

    assert response.status_code == 200
    report_data = response.json()

    # Should only return the specified branch
    assert len(report_data["branch_reports"]) == 1
    assert report_data["branch_reports"][0]["branch_id"] == branch_id


def test_report_includes_ba_summaries(client):
    """Test that branch reports include BA-level summaries."""
    hq_token, branch_token = _setup_reporting_accounts(client)

    response = client.post(
        "/api/v1/reports",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={
            "period_type": "DAILY",
            "period_start": (date.today() - timedelta(days=1)).isoformat(),
            "period_end": date.today().isoformat(),
            "branch_id": None,
        },
    )

    assert response.status_code == 200
    report_data = response.json()

    # Check that branch reports include BA summaries
    if report_data["branch_reports"]:
        branch_report = report_data["branch_reports"][0]
        assert "ba_summaries" in branch_report
        assert isinstance(branch_report["ba_summaries"], list)


def test_pdf_export_generation(client):
    """Test PDF report export generation."""
    hq_token, branch_token = _setup_reporting_accounts(client)

    response = client.post(
        "/api/v1/reports/export",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={
            "period_type": "DAILY",
            "period_start": (date.today() - timedelta(days=1)).isoformat(),
            "period_end": date.today().isoformat(),
            "branch_id": None,
            "export_format": "PDF",
        },
    )

    assert response.status_code == 202
    export_data = response.json()

    assert "task_id" in export_data
    assert "export_format" in export_data
    assert export_data["export_format"] == "PDF"
    assert "file_reference" in export_data
    assert "status" in export_data


def test_excel_export_generation(client):
    """Test Excel report export generation."""
    hq_token, branch_token = _setup_reporting_accounts(client)

    response = client.post(
        "/api/v1/reports/export",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={
            "period_type": "DAILY",
            "period_start": (date.today() - timedelta(days=1)).isoformat(),
            "period_end": date.today().isoformat(),
            "branch_id": None,
            "export_format": "XLSX",
        },
    )

    # Debug: print error if 500
    if response.status_code == 500:
        print(f"Error response: {response.text}")
    
    assert response.status_code == 202
    export_data = response.json()

    assert "task_id" in export_data
    assert "export_format" in export_data
    assert export_data["export_format"] == "XLSX"
    assert "file_reference" in export_data
    assert "status" in export_data


def test_invalid_export_format(client):
    """Test that invalid export formats are rejected."""
    hq_token, branch_token = _setup_reporting_accounts(client)

    response = client.post(
        "/api/v1/reports/export",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={
            "period_type": "DAILY",
            "period_start": (date.today() - timedelta(days=1)).isoformat(),
            "period_end": date.today().isoformat(),
            "branch_id": None,
            "export_format": "INVALID",
        },
    )

    assert response.status_code == 422


def test_list_available_reports(client):
    """Test listing available report files."""
    hq_token, branch_token = _setup_reporting_accounts(client)

    # First generate a report to have files
    client.post(
        "/api/v1/reports/export",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={
            "period_type": "DAILY",
            "period_start": (date.today() - timedelta(days=1)).isoformat(),
            "period_end": date.today().isoformat(),
            "branch_id": None,
            "export_format": "PDF",
        },
    )

    # List available reports
    response = client.get(
        "/api/v1/reports/list",
        headers={"Authorization": f"Bearer {hq_token}"},
    )

    assert response.status_code == 200
    list_data = response.json()

    assert "reports" in list_data
    assert isinstance(list_data["reports"], list)


def test_ba_cannot_access_reports(client):
    """Test that BA users cannot access reporting endpoints."""
    hq_token, branch_token = _setup_reporting_accounts(client)

    # Get BA token
    ba_response = client.post(
        "/api/v1/auth/login",
        json={"email": "report-ba@example.com", "password": "basecret123"},
    )
    ba_token = ba_response.json()["access_token"]

    # Try to generate report (should fail)
    response = client.post(
        "/api/v1/reports",
        headers={"Authorization": f"Bearer {ba_token}"},
        json={
            "period_type": "DAILY",
            "period_start": (date.today() - timedelta(days=1)).isoformat(),
            "period_end": date.today().isoformat(),
        },
    )

    assert response.status_code == 403


def test_report_data_integrity(client):
    """Test that report data maintains integrity and accuracy."""
    hq_token, branch_token = _setup_reporting_accounts(client)

    response = client.post(
        "/api/v1/reports",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={
            "period_type": "DAILY",
            "period_start": (date.today() - timedelta(days=1)).isoformat(),
            "period_end": date.today().isoformat(),
            "branch_id": None,
        },
    )

    assert response.status_code == 200
    report_data = response.json()

    # Verify data types
    assert isinstance(report_data["total_sales_count"], int)
    assert isinstance(report_data["total_commission_owed"], str)
    assert isinstance(report_data["overall_performance_percentage"], str)

    # Verify that stock counts are non-negative
    stock_counts = report_data["total_stock_counts"]
    for count in stock_counts.values():
        assert count >= 0


def test_weekly_and_monthly_reports(client):
    """Test that weekly and monthly reports work correctly."""
    hq_token, branch_token = _setup_reporting_accounts(client)

    for period_type in ["WEEKLY", "MONTHLY"]:
        response = client.post(
            "/api/v1/reports",
            headers={"Authorization": f"Bearer {hq_token}"},
            json={
                "period_type": period_type,
                "period_start": (date.today() - timedelta(days=7)).isoformat(),
                "period_end": date.today().isoformat(),
                "branch_id": None,
            },
        )

        assert response.status_code == 200
        report_data = response.json()
        assert report_data["period_type"] == period_type


def test_reconciliation_headlines_in_report(client):
    """Test that reconciliation headlines are included when available."""
    hq_token, branch_token = _setup_reporting_accounts(client)

    # For now, just test that the field exists and can be None
    response = client.post(
        "/api/v1/reports",
        headers={"Authorization": f"Bearer {hq_token}"},
        json={
            "period_type": "DAILY",
            "period_start": (date.today() - timedelta(days=1)).isoformat(),
            "period_end": date.today().isoformat(),
            "branch_id": None,
        },
    )

    assert response.status_code == 200
    report_data = response.json()

    # reconciliation_headlines can be None if no imports exist
    assert "reconciliation_headlines" in report_data
