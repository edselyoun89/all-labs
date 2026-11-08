"""Render every report page and verify the source appendices and report data."""
import csv
import json
from pathlib import Path
from docx import Document
import pypdfium2 as pdfium
from pypdf import PdfReader
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis' / 'rendered'


def main():
    """Check textual invariants, render pages and create complete contact sheets."""
    OUT.mkdir(exist_ok=True)
    results = []
    for folder_name in ('Lab_01_variant_22', 'Lab_02_variant_22'):
        folder = ROOT / folder_name
        source = (folder / 'main.py').read_text(encoding='utf-8')
        doc = Document(folder / 'report.docx')
        code_paragraphs = doc.paragraphs[-len(source.splitlines()):]
        recovered = '\n'.join(p.text for p in code_paragraphs) + '\n'
        assert recovered == source, folder_name + ': code appendix differs'
        reader = PdfReader(folder / 'report.pdf')
        pdf = pdfium.PdfDocument(folder / 'report.pdf')
        all_text = '\n'.join(p.extract_text() or '' for p in reader.pages)
        assert 'Вариант 22' in all_text
        assert not any(s in all_text for s in ('Вариант 24', '\ufffd', '\u25a0'))
        counts, thumbs = [], []
        for index, page in enumerate(pdf):
            text = reader.pages[index].extract_text() or ''
            counts.append(len(text.strip()))
            assert len(text.strip()) > 50, f'{folder_name}: blank page {index+1}'
            image = page.render(scale=1.2).to_pil()
            image.save(OUT / f'{folder_name}_page_{index+1:02}.png')
            image.thumbnail((330, 468))
            thumb = Image.new('RGB', (350, 500), '#dadde2')
            thumb.paste(image, ((350-image.width)//2, 22))
            ImageDraw.Draw(thumb).text((10, 4), f'Page {index+1}', fill='black')
            thumbs.append(thumb)
        sheet = Image.new('RGB', (1050, 500*((len(thumbs)+2)//3)), 'white')
        for index, thumb in enumerate(thumbs):
            sheet.paste(thumb, ((index%3)*350, (index//3)*500))
        sheet.save(OUT / f'{folder_name}_contact.png')
        results.append(dict(folder=folder_name, pages=len(reader.pages), characters_per_page=counts,
                            full_source_appendix_matches=True, variant=22, all_pages_rendered=True))
        print(results[-1])
    (ROOT / 'analysis' / 'report_quality.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
