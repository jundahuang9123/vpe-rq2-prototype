"""Spike B: scripts/shacl_delta.py on a small synthetic base/profile pair."""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'tests' / 'fixtures' / 'shacl_delta'
spec = importlib.util.spec_from_file_location('shacl_delta', ROOT / 'scripts' / 'shacl_delta.py')
shacl_delta = importlib.util.module_from_spec(spec)
sys.modules['shacl_delta'] = shacl_delta
spec.loader.exec_module(shacl_delta)

DCAT = 'http://www.w3.org/ns/dcat#'
DCT = 'http://purl.org/dc/terms/'
EX = 'http://example.org/profile#'


@pytest.fixture(scope='module')
def result():
    return shacl_delta.compute_delta(
        shacl_delta.load_graph([FIXTURES / 'base.ttl']),
        shacl_delta.load_graph([FIXTURES / 'profile.ttl']),
        'synthetic', ['synthetic-base'], profile_namespace=EX,
    )


def _by_key(delta):
    return {(e['target_class'], e.get('path')): e for e in delta['elements']}


def test_unchanged_elements_are_excluded(result):
    delta, report = result
    assert (DCAT + 'Dataset', DCT + 'title') not in _by_key(delta)
    assert report['counts']['unchanged'] == 1


def test_added_elements_with_reuse_and_mint(result):
    elements = _by_key(result[0])
    citation = elements[(DCAT + 'Dataset', DCT + 'bibliographicCitation')]
    assert citation['delta_status'] == 'added'
    assert citation['kind'] == 'reuse'
    assert citation['obligation'] == 'mandatory'
    assert citation['range_datatype'] == 'http://www.w3.org/2001/XMLSchema#string'
    minted = elements[(DCAT + 'Dataset', EX + 'sampleSize')]
    assert minted['kind'] == 'mint' and minted['max_count'] == 1 and minted['severity'] == 'Info'


@pytest.mark.parametrize('cls, path, facet', [
    ('Dataset', 'issued', 'minCount'),
    ('Dataset', 'accrualPeriodicity', 'nodeKind'),
    ('Distribution', 'format', 'in'),
])
def test_tightened_elements(result, cls, path, facet):
    element = _by_key(result[0])[(DCAT + cls, DCT + path)]
    assert element['delta_status'] == 'tightened'
    assert element['kind'] == 'refine'
    assert facet in element['notes']


def test_loosened_element_is_flagged(result):
    element = _by_key(result[0])[(DCAT + 'Dataset', DCAT + 'keyword')]
    assert element['delta_status'] == 'loosened'
    assert 'severity' in element['notes']


def test_class_addition(result):
    elements = _by_key(result[0])
    assert elements[(EX + 'Assessment', None)]['kind'] == 'class_addition'
    date = elements[(EX + 'Assessment', DCT + 'date')]
    assert date['delta_status'] == 'added' and date['obligation'] == 'recommended'


def test_unhandled_constructs_are_reported(result):
    unhandled = ' | '.join(result[1]['unhandled_profile'])
    assert 'sh:or' in unhandled
    assert 'non-IRI sh:path' in unhandled
    assert 'without sh:targetClass' in unhandled


def test_base_only_elements_are_inherited_not_loosened(result):
    assert (DCAT + 'Dataset', DCT + 'description') not in _by_key(result[0])


def test_cli_writes_delta(tmp_path):
    out = tmp_path / 'delta.yaml'
    code = shacl_delta.main(['--base', str(FIXTURES / 'base.ttl'), '--profile', str(FIXTURES / 'profile.ttl'),
                             '--profile-id', 'synthetic', '--base-id', 'synthetic-base', '-o', str(out)])
    assert code == 0 and 'delta_status' in out.read_text(encoding='utf-8')
