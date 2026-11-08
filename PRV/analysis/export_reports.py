"""Export DOCX reports with an isolated Word instance, preserving open documents."""
from pathlib import Path
import win32com.client

ROOT = Path(__file__).resolve().parents[1]


def main():
    """Export the reports and print Word's page counts."""
    word = win32com.client.DispatchEx('Word.Application')
    word.Visible = False
    word.DisplayAlerts = 0
    try:
        for folder in ('Lab_01_variant_22', 'Lab_02_variant_22'):
            path = ROOT / folder / 'report.docx'
            doc = word.Documents.Open(str(path), ReadOnly=True, AddToRecentFiles=False)
            try:
                doc.Repaginate()
                doc.ExportAsFixedFormat(str(path.with_suffix('.pdf')), 17)
                print(folder, 'pages=', doc.ComputeStatistics(2))
            finally:
                doc.Close(False)
    finally:
        word.Quit()


if __name__ == '__main__':
    main()
