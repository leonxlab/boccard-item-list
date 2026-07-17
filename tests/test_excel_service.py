import os
import tempfile
import unittest

from app.services.excel_service import parse_excel_file


class ExcelServiceTests(unittest.TestCase):
    def test_parse_excel_file_reads_expected_columns(self):
        sample_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "250507-100-P&ID-001_P32 Aminolat_V2.xlsx",
        )

        if not os.path.exists(sample_path):
            self.skipTest("Sample Excel file is not available in workspace")

        rows = parse_excel_file(sample_path)

        self.assertGreaterEqual(len(rows), 1)
        self.assertIn("remarks_in_pid", rows[0])
        self.assertIn("tag_number", rows[0])
        self.assertIn("designation", rows[0])
        self.assertTrue(any(row["remarks_in_pid"] for row in rows))
        self.assertTrue(any(row["boccard_item_number"] for row in rows))
        self.assertTrue(any(row["tag_number"] for row in rows))
        self.assertTrue(any(row["designation"] for row in rows))


if __name__ == "__main__":
    unittest.main()
