"""Extract original PRV assignments without changing the source documents."""
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'analysis' / 'assignments'

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    word = None
    try:
        for path in sorted(ROOT.glob('Lab_*_variant_24/*')):
            if path.name.startswith('~$') or path.suffix.lower() not in {'.doc', '.docx'}:
                continue
            if path.suffix.lower() == '.docx':
                with ZipFile(path) as archive:
                    root = ET.fromstring(archive.read('word/document.xml'))
                ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                text = '\n'.join(''.join(t.text or '' for t in p.findall('.//w:t', ns)) for p in root.findall('.//w:p', ns))
            else:
                if word is None:
                    import win32com.client
                    word = win32com.client.DispatchEx('Word.Application')
                    word.Visible = False
                    word.DisplayAlerts = 0
                doc = word.Documents.Open(str(path), ReadOnly=True, AddToRecentFiles=False)
                try:
                    text = doc.Content.Text.replace('\r', '\n').replace('\x07', '\t')
                finally:
                    doc.Close(False)
            target = OUT / (path.parent.name + '.txt')
            text = '\n'.join(line.rstrip() for line in text.splitlines()).rstrip() + '\n'
            target.write_text(text, encoding='utf-8')
            print(target.name, len(text))
    finally:
        if word is not None:
            word.Quit()

if __name__ == '__main__':
    main()
