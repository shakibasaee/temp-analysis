"""Generate machine-readable and presentation-ready model reports."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


class ModelReportGenerator:
    """Build and save reports for a fitted temperature forecasting model."""

    def __init__(self, output_dir: str | Path = "plots") -> None:
        self.output_dir = Path(output_dir)

    @staticmethod
    def _dataset_summary(model: Any, dataset: pd.DataFrame) -> dict[str, Any]:
        config = model.config
        dates = pd.to_datetime(dataset[config.date_column], errors="coerce")
        target = pd.to_numeric(dataset[config.target_column], errors="coerce")
        cities = sorted(dataset[config.city_column].dropna().astype(str).unique())
        target_summary = target.describe()
        return {
            "rows": int(len(dataset)),
            "columns": int(len(dataset.columns)),
            "column_names": [str(column) for column in dataset.columns],
            "date_range": {
                "start": dates.min().isoformat() if dates.notna().any() else None,
                "end": dates.max().isoformat() if dates.notna().any() else None,
            },
            "cities": cities,
            "city_count": len(cities),
            "missing_values": {
                str(column): int(count)
                for column, count in dataset.isna().sum().items()
            },
            "target_summary": {
                str(key): float(value)
                for key, value in target_summary.items()
                if np.isfinite(value)
            },
            "split": {
                "train_rows": int(model.train_rows_),
                "test_rows": int(model.test_rows_),
                "strategy": (
                    "random" if config.shuffle else "chronological_by_unique_date"
                ),
            },
        }

    @staticmethod
    def _feature_importance(model: Any) -> dict[str, Any] | None:
        pipeline = getattr(model, "pipeline_", None)
        if pipeline is None or "regressor" not in pipeline.named_steps:
            return None
        regressor = pipeline.named_steps["regressor"]
        coefficients = np.asarray(getattr(regressor, "coef_", [])).reshape(-1)
        names = model.feature_names_
        if len(coefficients) != len(names):
            return None
        values = sorted(
            (
                {
                    "feature": name,
                    "coefficient": float(coefficient),
                    "absolute_coefficient": float(abs(coefficient)),
                }
                for name, coefficient in zip(names, coefficients)
            ),
            key=lambda item: item["absolute_coefficient"],
            reverse=True,
        )
        return {
            "method": "linear_regression_coefficients",
            "intercept": float(np.asarray(regressor.intercept_).reshape(-1)[0]),
            "interpretation_note": (
                "Magnitude is affected by preprocessing. Numeric temporal features "
                "are standardized when normalize_features is enabled."
            ),
            "values": values,
        }

    def build_report(self, model: Any, dataset: pd.DataFrame) -> dict[str, Any]:
        """Build a serializable report from a fitted and evaluated model."""
        required = [
            "pipeline_",
            "train_metrics_report_",
            "test_metrics_report_",
            "train_rows_",
            "test_rows_",
        ]
        missing = [attribute for attribute in required if not hasattr(model, attribute)]
        if missing:
            raise ValueError(
                "Model must be fitted with fit_evaluate before reporting; "
                f"missing attributes: {missing}"
            )
        if dataset.empty:
            raise ValueError("Cannot report on an empty dataset")

        return {
            "report_metadata": {
                "title": "Temperature Linear Regression Model Report",
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "schema_version": "1.0",
            },
            "model": {
                "class": type(model).__name__,
                "estimator": type(model.pipeline_.named_steps["regressor"]).__name__,
                "configuration": model.config.to_dict(),
            },
            "dataset_summary": self._dataset_summary(model, dataset),
            "metrics": {
                "train": model.train_metrics_report_,
                "test": model.test_metrics_report_,
            },
            "feature_importance": self._feature_importance(model),
        }

    def save_json(
        self, report: dict[str, Any], filename: str = "model_report.json"
    ) -> Path:
        """Save a report as UTF-8 JSON."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / filename
        path.write_text(json.dumps(report, indent=2, allow_nan=True), encoding="utf-8")
        return path

    def save_yaml(
        self, report: dict[str, Any], filename: str = "model_report.yaml"
    ) -> Path:
        """Save a report as YAML when PyYAML is installed."""
        try:
            import yaml
        except ImportError as exc:
            raise RuntimeError("PyYAML is required to generate YAML reports") from exc
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / filename
        path.write_text(
            yaml.safe_dump(report, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        return path

    def save_markdown(
        self, report: dict[str, Any], filename: str = "RESULTS.md"
    ) -> Path:
        """Save a concise human-readable model result summary."""
        test_metrics = report["metrics"]["test"]
        lines = [
            "# Model Results",
            "",
            f"Generated: {report['report_metadata']['generated_at_utc']}",
            "",
            "## Dataset",
            "",
            f"- Rows: {report['dataset_summary']['rows']}",
            f"- Cities: {report['dataset_summary']['city_count']}",
            f"- Train rows: {report['dataset_summary']['split']['train_rows']}",
            f"- Test rows: {report['dataset_summary']['split']['test_rows']}",
            "",
            "## Test Metrics",
            "",
            "| Metric | Value | Confidence interval |",
            "|---|---:|---:|",
        ]
        for name, result in test_metrics["metrics"].items():
            interval = result["confidence_interval"]
            lines.append(
                f"| {name.upper()} | {result['value']:.4f} | "
                f"[{interval['lower']:.4f}, {interval['upper']:.4f}] |"
            )
        lines.extend(
            [
                "",
                "## Interpretation",
                "",
                "Feature rankings are linear coefficients, not causal effects. "
                "MAPE can be unstable when actual temperatures are close to zero.",
                "",
            ]
        )
        path = self.output_dir / filename
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def save_pdf(
        self, report: dict[str, Any], filename: str = "model_report.pdf"
    ) -> Path:
        """Render a polished PDF report using ReportLab."""
        try:
            from reportlab.lib import colors
            from reportlab.lib.enums import TA_CENTER
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.lib.units import mm
            from reportlab.platypus import (
                PageBreak,
                Paragraph,
                SimpleDocTemplate,
                Spacer,
                Table,
                TableStyle,
            )
        except ImportError as exc:
            raise RuntimeError("ReportLab is required to generate PDF reports") from exc

        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / filename
        styles = getSampleStyleSheet()
        styles.add(
            ParagraphStyle(
                name="ReportTitle",
                parent=styles["Title"],
                alignment=TA_CENTER,
                textColor=colors.HexColor("#17324D"),
                spaceAfter=12,
            )
        )
        styles.add(
            ParagraphStyle(
                name="Section",
                parent=styles["Heading2"],
                textColor=colors.HexColor("#176B87"),
                spaceBefore=10,
                spaceAfter=7,
            )
        )
        doc = SimpleDocTemplate(
            str(path),
            pagesize=A4,
            rightMargin=18 * mm,
            leftMargin=18 * mm,
            topMargin=20 * mm,
            bottomMargin=18 * mm,
            title=report["report_metadata"]["title"],
            author="Temp Analysis",
        )

        def table(data: list[list[Any]], widths: list[float]) -> Table:
            result = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
            result.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#176B87")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B8C4CC")),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1F6F8")]),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 5),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ]
                )
            )
            return result

        story = [
            Paragraph(report["report_metadata"]["title"], styles["ReportTitle"]),
            Paragraph(
                f"Generated {report['report_metadata']['generated_at_utc']}",
                styles["BodyText"],
            ),
            Spacer(1, 8),
            Paragraph("Dataset Summary", styles["Section"]),
        ]
        summary = report["dataset_summary"]
        story.append(
            table(
                [
                    ["Measure", "Value"],
                    ["Rows", f"{summary['rows']:,}"],
                    ["Columns", summary["columns"]],
                    ["Cities", summary["city_count"]],
                    ["Date range", f"{summary['date_range']['start']} to {summary['date_range']['end']}"],
                    ["Split", f"{summary['split']['train_rows']} train / {summary['split']['test_rows']} test"],
                ],
                [45 * mm, 110 * mm],
            )
        )

        for split_name in ("train", "test"):
            story.append(Paragraph(f"{split_name.title()} Metrics", styles["Section"]))
            metric_rows = [["Metric", "Value", "Confidence interval"]]
            for name, result in report["metrics"][split_name]["metrics"].items():
                interval = result["confidence_interval"]
                metric_rows.append(
                    [
                        name.upper(),
                        f"{result['value']:.4f}",
                        f"{interval['lower']:.4f} to {interval['upper']:.4f}",
                    ]
                )
            story.append(table(metric_rows, [38 * mm, 45 * mm, 72 * mm]))

        story.extend([PageBreak(), Paragraph("Model Configuration", styles["Section"])])
        config_rows = [["Setting", "Value"]] + [
            [str(key), str(value)]
            for key, value in report["model"]["configuration"].items()
        ]
        story.append(table(config_rows, [65 * mm, 90 * mm]))

        importance = report.get("feature_importance")
        if importance:
            story.append(Paragraph("Top Feature Coefficients", styles["Section"]))
            importance_rows = [["Feature", "Coefficient", "Absolute"]]
            for item in importance["values"][:15]:
                importance_rows.append(
                    [
                        item["feature"],
                        f"{item['coefficient']:.4f}",
                        f"{item['absolute_coefficient']:.4f}",
                    ]
                )
            story.append(table(importance_rows, [85 * mm, 35 * mm, 35 * mm]))
            story.append(Spacer(1, 6))
            story.append(Paragraph(importance["interpretation_note"], styles["BodyText"]))

        def add_page_number(canvas, document) -> None:
            canvas.saveState()
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(colors.HexColor("#667784"))
            canvas.drawString(18 * mm, 10 * mm, "Temp Analysis - Model Report")
            canvas.drawRightString(192 * mm, 10 * mm, f"Page {document.page}")
            canvas.restoreState()

        doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
        return path

    def generate_all(
        self,
        model: Any,
        dataset: pd.DataFrame,
        *,
        include_markdown: bool = False,
    ) -> dict[str, Path]:
        """Build and save JSON, YAML, PDF, and optionally Markdown outputs."""
        report = self.build_report(model, dataset)
        outputs = {
            "json": self.save_json(report),
            "yaml": self.save_yaml(report),
            "pdf": self.save_pdf(report),
        }
        if include_markdown:
            outputs["markdown"] = self.save_markdown(report)
        return outputs
