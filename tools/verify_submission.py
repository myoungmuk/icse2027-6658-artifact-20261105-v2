#!/usr/bin/env python3
"""Compare the versioned candidate with supplied portal PDF/title evidence.

Default paths follow this checkout's submission_metadata.json and paper/main.pdf.
No network request, account access, or conference upload is performed.
Requires PyMuPDF (pymupdf or the legacy fitz import).
"""
import argparse,hashlib,html,json,re,sys,unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize_title(value):
    return re.sub(r'\s+','',unicodedata.normalize('NFKC',html.unescape(value)))


def load_pdf_module():
    try:import pymupdf;return pymupdf
    except ImportError:
        try:import fitz;return fitz
        except ImportError:
            raise SystemExit('PyMuPDF is required. Use the environment with PyMuPDF installed; no files were submitted.')


def title_lines(page,expected):
    lines=[s.strip() for s in page.get_text().splitlines() if s.strip()]
    # The candidate's title is placed before the confirmed first author's name.
    # Inspect only that title region, so body occurrences cannot repair a missing title.
    stop=next((i for i,line in enumerate(lines) if 'Myeongmuk' in line and 'Kang' in line),None)
    observed='\n'.join(lines[:stop]) if stop is not None else ''
    return {'visible_title_region':observed,'author_boundary_found':stop is not None,
        'matches':bool(stop is not None and normalize_title(observed)==normalize_title(expected))}


def inspect(path,expected,fitz):
    doc=fitz.open(path)
    if not len(doc):raise ValueError('PDF contains no pages')
    title=title_lines(doc[0],expected)
    return {'path':str(path),'sha256':sha(path),'pages':len(doc),'metadata_title':doc.metadata.get('title',''),
        'visible_title':title,'first_page_text':doc[0].get_text()}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--metadata',type=Path,default=ROOT/'submission_metadata.json')
    ap.add_argument('--prepared-pdf',type=Path,default=ROOT/'paper/main.pdf')
    ap.add_argument('--downloaded-pdf',type=Path,help='PDF actually downloaded from the submission portal.')
    ap.add_argument('--system-title-file',type=Path,help='UTF-8 copy of the portal title field.')
    ap.add_argument('--output',type=Path,required=True,help='New JSON output; existing files are not overwritten.')
    args=ap.parse_args()
    if args.output.exists():ap.error('Output exists; choose a new filename to preserve prior evidence.')
    if ROOT in [args.output.resolve(),*args.output.resolve().parents]:
        ap.error('Choose an output path outside the preserved release checkout.')
    fitz=load_pdf_module();metadata=json.loads(args.metadata.read_text());expected=metadata['title']
    prepared=inspect(args.prepared_pdf,expected,fitz)
    expected_pages=metadata['body_pages']+metadata['reference_pages']
    checks={'prepared_sha_matches_versioned_record':prepared['sha256']==metadata['pdf_sha256'],
        'prepared_page_count':prepared['pages']==expected_pages,
        'prepared_metadata_title_exact':prepared['metadata_title']==expected,
        'prepared_visible_title_matches':prepared['visible_title']['matches'],
        'both_orcids_on_first_page':all(a['orcid'] in prepared['first_page_text'] for a in metadata['authors']),
        'confirmed_corresponding_author':('Corresponding author: '+metadata['corresponding_author']['given_name']+' '+metadata['corresponding_author']['family_name']) in prepared['first_page_text']}
    observed=None
    if args.downloaded_pdf:
        observed=inspect(args.downloaded_pdf,expected,fitz)
        checks.update({'downloaded_pdf_bytes_match_candidate':observed['sha256']==prepared['sha256'],
            'downloaded_pdf_expected_pages':observed['pages']==expected_pages,
            'downloaded_pdf_metadata_title_matches':normalize_title(observed['metadata_title'])==normalize_title(expected),
            'downloaded_pdf_visible_title_matches':observed['visible_title']['matches']})
    title=None
    if args.system_title_file:
        title=args.system_title_file.read_text(encoding='utf-8').strip()
        checks['portal_title_matches_normalized']=normalize_title(title)==normalize_title(expected)
    for item in [prepared,observed]:
        if item:item.pop('first_page_text',None)
    result={'release':metadata['public_release_id'],'checks':checks,'pass':all(checks.values()),
        'expected_title':expected,'prepared':prepared,'downloaded':observed,
        'supplied_portal_title':title,'portal_title_literal_equal':title==expected if title is not None else None,
        'normalization':'Unicode NFKC and HTML entity decoding, then removal of layout whitespace; words are preserved.',
        'evidence_files_supplied':bool(args.downloaded_pdf and args.system_title_file),
        'live_portal_accessed':False,'conference_submission_confirmed':False,
        'scope':'Local comparison only. Supplied files do not independently authenticate portal origin or completed submission.'}
    with args.output.open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({'pass':result['pass'],'release':result['release'],'checks':checks,
        'evidence_files_supplied':result['evidence_files_supplied'],'conference_submission_confirmed':False},indent=2))
    return 0 if result['pass'] else 1


if __name__=='__main__':sys.exit(main())
