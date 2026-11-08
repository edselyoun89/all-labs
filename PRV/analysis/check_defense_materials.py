"""Check the defense handouts and the bundled local parser demonstration."""
import functools
import http.server
import json
import logging
from pathlib import Path
import sys
import tempfile
import threading
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]


def main():
    """Verify every handout and exercise HTTP parsing and document publication."""
    folders = sorted(ROOT.glob('Lab_*'))
    handouts = []
    for folder in folders:
        path = folder / 'Защита_лабораторной.txt'
        text = path.read_text(encoding='utf-8')
        assert len(text) > 2500, path
        assert '\ufffd' not in text and ('python ' in text or 'python.exe ' in text), path
        handouts.append(dict(folder=folder.name, file=path.name, characters=len(text)))
    assert len(handouts) == 9
    reports = []
    for folder in (ROOT / 'Lab_01_variant_22', ROOT / 'Lab_02_variant_22'):
        for name in ('report.docx', 'report.pdf'):
            path = folder / name
            assert path.stat().st_size > 50000, path
            if name.endswith('.docx'):
                with ZipFile(path) as archive:
                    assert archive.testzip() is None
            else:
                assert path.read_bytes().startswith(b'%PDF-')
            reports.append(str(path.relative_to(ROOT)))

    sys.path.insert(0, str(ROOT / 'Lab_06_variant_24'))
    from server import SharedDocumentServer
    sys.path.insert(0, str(ROOT / 'Lab_07_variant_24'))
    from parser import parse_site, publish_to_shared_document, save_results

    handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                                directory=str(ROOT / 'Lab_07_variant_24'))
    http_server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    http_thread = threading.Thread(target=http_server.serve_forever, daemon=True)
    shared_server = SharedDocumentServer('127.0.0.1', 0, logging.getLogger('defense-check'))
    shared_thread = threading.Thread(target=shared_server.start, daemon=True)
    http_thread.start()
    shared_thread.start()
    try:
        assert shared_server.ready_event.wait(3)
        url = f'http://127.0.0.1:{http_server.server_port}/demo.html'
        data = parse_site(url)
        assert data['title'] == 'Демонстрация лабораторной ПРВ'
        assert len(data['headings']) == 1 and len(data['paragraphs']) == 3 and len(data['links']) == 1
        filtered = parse_site(url, keyword='MPI', tag='paragraphs')
        assert filtered['paragraphs'] == ['MPI распределяет вычисления между процессами.']
        assert not filtered['headings'] and not filtered['links']
        with tempfile.TemporaryDirectory() as directory:
            paths = save_results(data, Path(directory))
            assert all(path.exists() for path in paths)
        publish_to_shared_document(data, '127.0.0.1', shared_server.port, 'Parser')
        assert shared_server.roles['Parser'] == 'admin'
        assert data['paragraphs'][0] in shared_server.document
    finally:
        http_server.shutdown()
        http_server.server_close()
        shared_server.stop()
        http_thread.join(3)
        shared_thread.join(3)
    result = dict(handouts=handouts, reports=reports,
                  local_http_demo=True, mpi_paragraph_filter=True,
                  exports_json_csv_html=True, shared_document_publication=True)
    (ROOT / 'analysis' / 'defense_materials_check.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'OK: {len(handouts)} handouts, {len(reports)} reports, HTTP/filter/export/publication')


if __name__ == '__main__':
    main()
