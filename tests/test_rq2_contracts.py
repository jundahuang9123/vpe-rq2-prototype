"""WP0 contract tests: RQ2 schemas load and the example instances validate.

Uses a small structural validator over the YAML schema (required slots, enum
values, integer minimums, patterns, nested classes, unknown keys) instead of
linkml.validator, which does not import with the pinned pydantic 2.10.x.
"""
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / 'requirement-reuse-service' / 'schema'
EXAMPLES = ROOT / 'examples' / 'rq2-benchmark'

PROFILE_ELEMENT = SCHEMA_DIR / 'profile_element.linkml.yaml'
RQ2_ATOM = SCHEMA_DIR / 'rq2_atom.linkml.yaml'


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding='utf-8'))


def _errors(schema: dict, class_name: str, instance, where: str = '$') -> list[str]:
    if not isinstance(instance, dict):
        return [f'{where}: expected object for {class_name}']
    attributes = schema['classes'][class_name].get('attributes', {})
    errors = [f'{where}.{key}: unknown slot' for key in instance if key not in attributes]
    for name, slot in attributes.items():
        slot = slot or {}
        value = instance.get(name)
        if value is None:
            if slot.get('required'):
                errors.append(f'{where}.{name}: required')
            continue
        values = value if slot.get('multivalued') else [value]
        if slot.get('multivalued') and not isinstance(value, list):
            errors.append(f'{where}.{name}: expected list')
            continue
        target = slot.get('range', schema.get('default_range', 'string'))
        for index, item in enumerate(values):
            path = f'{where}.{name}[{index}]'
            if target in schema.get('classes', {}):
                errors += _errors(schema, target, item, path)
            elif target in schema.get('enums', {}):
                if item not in schema['enums'][target]['permissible_values']:
                    errors.append(f'{path}: {item!r} not in {target}')
            elif target == 'integer':
                if not isinstance(item, int) or item < slot.get('minimum_value', item):
                    errors.append(f'{path}: invalid integer {item!r}')
            elif not isinstance(item, str):
                errors.append(f'{path}: expected string')
            elif 'pattern' in slot and not re.search(slot['pattern'], item):
                errors.append(f'{path}: does not match pattern')
    return errors


@pytest.mark.parametrize('schema_path, expected', [
    (PROFILE_ELEMENT, {'ProfileElement', 'ProfileDelta'}),
    (RQ2_ATOM, {'RQ2AtomSet', 'Atom', 'SourceReference'}),
])
def test_rq2_schema_loads(schema_path, expected):
    schema = _load(schema_path)
    assert expected <= set(schema['classes'])
    for cls in schema['classes'].values():
        for slot in (cls.get('attributes') or {}).values():
            target = (slot or {}).get('range')
            assert target is None or target in schema['classes'] or target in schema['enums'] \
                or target in {'string', 'integer', 'uri', 'boolean', 'datetime'}, target


def test_profile_delta_example_validates():
    errors = _errors(_load(PROFILE_ELEMENT), 'ProfileDelta', _load(EXAMPLES / 'profile-delta.example.yaml'))
    assert not errors, errors


def test_atom_set_example_validates():
    errors = _errors(_load(RQ2_ATOM), 'RQ2AtomSet', _load(EXAMPLES / 'atom-set.example.yaml'))
    assert not errors, errors


@pytest.mark.parametrize('statement', [
    'A dataset must have a dct:bibliographicCitation.',
    'See http://purl.org/dc/terms/ for the property.',
])
def test_atom_statement_rejects_iris_and_prefixed_names(statement):
    instance = {
        'benchmark_id': 'x', 'base_profile_ids': ['b'],
        'atoms': [{'id': 'a', 'statement': statement, 'subject': 'dataset', 'modality': 'must'}],
    }
    assert _errors(_load(RQ2_ATOM), 'RQ2AtomSet', instance)


def test_invalid_enum_and_missing_required_are_reported():
    instance = {'profile_id': 'x', 'elements': [{'target_class': 'http://x/C', 'kind': 'invent'}]}
    errors = _errors(_load(PROFILE_ELEMENT), 'ProfileDelta', instance)
    assert any('base_profile_ids: required' in e for e in errors)
    assert any('not in ElementKind' in e for e in errors)


def test_profile_change_types_map_to_element_kinds():
    """Every ProfileChangeType is covered by the mapping comment in profile_element.linkml.yaml."""
    change_types = _load(SCHEMA_DIR / 'profile_change.linkml.yaml')['enums']['ProfileChangeType']['permissible_values']
    header = PROFILE_ELEMENT.read_text(encoding='utf-8').split('\nid:')[0]
    for change_type in change_types:
        assert change_type in header, change_type
