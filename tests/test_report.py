from argparse import Namespace

import pytest
from pypdf import PdfReader

from bittytax.audit import AuditRecords
from bittytax.bt_types import TaxRules
from bittytax.config import config
from bittytax.report import ReportPdf


@pytest.mark.parametrize("report_type", ["audit", "summary", "full"])
@pytest.mark.parametrize("legacy_report", [False, True])
def test_report_embeds_logo(tmp_path, monkeypatch, report_type, legacy_report):
    monkeypatch.setitem(config.config, "legacy_report", legacy_report)
    args = Namespace(
        audit_only=report_type == "audit",
        summary_only=report_type == "summary",
        output_filename=str(tmp_path / "report"),
        filename="transactions.xlsx",
        tax_rules=TaxRules.US_INDIVIDUAL_FIFO,
        tax_year=None,
    )

    ReportPdf("BittyTax", args, AuditRecords([]), tax_report={}, price_report={})

    pdf = PdfReader(tmp_path / "report.pdf")
    assert any(page.images for page in pdf.pages)
