from __future__ import annotations
from typing import Iterable
import csv
from pathlib import Path
from openpyxl import load_workbook
import xlrd
from app.parsers.base_parser import BaseParser
from app.models.schemas import ContentUnit

class TabularParser(BaseParser):
    supported_extensions = ("csv", "tsv", "xlsx", "xls")
    supported_mime_types = (
        "text/csv",
        "text/tab-separated-values",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
    )

    def parse(self, path: str, metadata: dict[str, object]) -> Iterable[ContentUnit]:
        suffix = Path(path).suffix.lower().lstrip(".")
        if suffix in ("csv", "tsv"):
            delimiter = "," if suffix == "csv" else "\t"
            yield from self._parse_delimited(path, delimiter, metadata)
        elif suffix in ("xlsx", "xls"):
            yield from self._parse_excel(path, metadata)

    def _parse_delimited(self, path: str, delimiter: str, metadata: dict[str, object]) -> Iterable[ContentUnit]:
        with open(path, newline="", encoding="utf-8", errors="ignore") as handle:
            reader = csv.reader(handle, delimiter=delimiter)
            rows = [" | ".join(row) for row in reader if any(cell.strip() for cell in row)]
            if rows:
                yield ContentUnit(text="\n".join(rows), metadata=metadata)

    def _parse_excel(self, path: str, metadata: dict[str, object]) -> Iterable[ContentUnit]:
        suffix = Path(path).suffix.lower().lstrip(".")
        if suffix == "xlsx":
            workbook = load_workbook(path, read_only=True, data_only=True)
            for sheet_name in workbook.sheetnames:
                sheet = workbook[sheet_name]
                rows = []
                for row in sheet.iter_rows(values_only=True):
                    row_text = " | ".join(str(cell).strip() if cell is not None else "" for cell in row)
                    if row_text.strip():
                        rows.append(row_text)
                if rows:
                    unit_metadata = {**metadata, "sheet_name": sheet_name}
                    yield ContentUnit(text="\n".join(rows), metadata=unit_metadata)
        else:
            workbook = xlrd.open_workbook(path)
            for sheet in workbook.sheets():
                rows = []
                for r in range(sheet.nrows):
                    row = sheet.row_values(r)
                    row_text = " | ".join(str(cell).strip() for cell in row if str(cell).strip())
                    if row_text:
                        rows.append(row_text)
                if rows:
                    unit_metadata = {**metadata, "sheet_name": sheet.name}
                    yield ContentUnit(text="\n".join(rows), metadata=unit_metadata)
