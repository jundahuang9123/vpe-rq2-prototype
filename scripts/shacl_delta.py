#!/usr/bin/env python3
"""Compute an RQ2 ProfileDelta from base SHACL shapes and profile SHACL shapes.

Spike B (WP0). Normalises property shapes per (target class, path) into
ProfileElements (schema: requirement-reuse-service/schema/profile_element.linkml.yaml)
and classifies each against the base:

  added      (class, path) not constrained by the base
  tightened  base constrains it; the profile is stricter on at least one facet
  unchanged  same as the base -> excluded from the delta
  loosened   profile is weaker on at least one facet -> kept and flagged

Facets: sh:minCount, sh:maxCount, sh:class, sh:datatype, sh:nodeKind, sh:in,
sh:severity. Several property shapes on the same (class, path) are merged
(max of minCount, min of maxCount, strongest severity, union of class/datatype,
intersection of sh:in).

Not handled yet (reported under `unhandled`, never silently scored):
sh:or / sh:and / sh:xone / sh:not, nested sh:node shapes, node shapes without
sh:targetClass (incl. implicit class targets), non-IRI (complex) paths,
SPARQL constraints, sh:qualifiedValueShape. Base elements missing from the
profile are treated as inherited, not as loosening.

Usage:
  python scripts/shacl_delta.py --base base.ttl [--base more.ttl] --profile profile.ttl \
      --profile-id geo --base-id dcat-ap [--profile-namespace http://data.europa.eu/930/] \
      [-o delta.yaml]
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from rdflib import BNode, Graph, Literal, URIRef
from rdflib.collection import Collection
from rdflib.namespace import RDF, SH

SEVERITY_RANK = {'Info': 0, 'Warning': 1, 'Violation': 2}
# Each node kind as the set of term types it admits; a subset is tighter.
NODE_KINDS = {
    'IRI': {'I'}, 'BlankNode': {'B'}, 'Literal': {'L'},
    'BlankNodeOrIRI': {'B', 'I'}, 'BlankNodeOrLiteral': {'B', 'L'}, 'IRIOrLiteral': {'I', 'L'},
}
UNHANDLED_SHAPE_PREDICATES = {SH['or']: 'sh:or', SH['and']: 'sh:and', SH.xone: 'sh:xone',
                              SH['not']: 'sh:not', SH.node: 'sh:node', SH.sparql: 'sh:sparql',
                              SH.qualifiedValueShape: 'sh:qualifiedValueShape'}


@dataclass
class Facets:
    min_count: int | None = None
    max_count: int | None = None
    classes: set[str] = field(default_factory=set)
    datatypes: set[str] = field(default_factory=set)
    node_kind: str | None = None
    in_values: frozenset[str] | None = None
    severity: str = 'Violation'

    def merge(self, other: 'Facets') -> None:
        if other.min_count is not None:
            self.min_count = max(self.min_count or 0, other.min_count)
        if other.max_count is not None:
            self.max_count = other.max_count if self.max_count is None else min(self.max_count, other.max_count)
        self.classes |= other.classes
        self.datatypes |= other.datatypes
        if other.node_kind:
            if self.node_kind is None:
                self.node_kind = other.node_kind
            else:
                both = NODE_KINDS[self.node_kind] & NODE_KINDS[other.node_kind]
                self.node_kind = next((k for k, v in NODE_KINDS.items() if v == both), self.node_kind)
        if other.in_values is not None:
            self.in_values = other.in_values if self.in_values is None else self.in_values & other.in_values
        if SEVERITY_RANK[other.severity] > SEVERITY_RANK[self.severity]:
            self.severity = other.severity


def _local(term) -> str:
    text = str(term)
    return text.rsplit('#', 1)[-1].rsplit('/', 1)[-1]


def _int(graph: Graph, node, predicate) -> int | None:
    value = graph.value(node, predicate)
    return int(value) if isinstance(value, Literal) else None


def _value_text(term) -> str:
    return str(term) if isinstance(term, URIRef) else f'"{term}"'


def load_graph(paths: list[Path]) -> Graph:
    graph = Graph()
    for path in paths:
        graph.parse(path, format='turtle')
    return graph


def normalise(graph: Graph) -> tuple[dict[tuple[str, str], Facets], list[str]]:
    """Return facets per (target class, path) plus a list of unhandled constructs."""
    elements: dict[tuple[str, str], Facets] = {}
    unhandled: list[str] = []
    property_shapes_seen: set = set()
    for node_shape in set(graph.subjects(RDF.type, SH.NodeShape)) | set(graph.subjects(SH.property, None)):
        targets = [t for t in graph.objects(node_shape, SH.targetClass) if isinstance(t, URIRef)]
        label = _value_text(node_shape) if isinstance(node_shape, URIRef) else 'blank node shape'
        for predicate, name in UNHANDLED_SHAPE_PREDICATES.items():
            if (node_shape, predicate, None) in graph:
                unhandled.append(f'{name} on node shape {label}')
        if not targets:
            if (node_shape, SH.property, None) in graph:
                unhandled.append(f'node shape without sh:targetClass: {label}')
            continue
        for prop in graph.objects(node_shape, SH.property):
            property_shapes_seen.add(prop)
            path = graph.value(prop, SH.path)
            if not isinstance(path, URIRef):
                unhandled.append(f'non-IRI sh:path in a property shape of {label}')
                continue
            for predicate, name in UNHANDLED_SHAPE_PREDICATES.items():
                if (prop, predicate, None) in graph:
                    unhandled.append(f'{name} on property shape {_local(path)} of {label}')
            facets = Facets(
                min_count=_int(graph, prop, SH.minCount),
                max_count=_int(graph, prop, SH.maxCount),
                classes={str(o) for o in graph.objects(prop, SH['class'])},
                datatypes={str(o) for o in graph.objects(prop, SH.datatype)},
            )
            node_kind = graph.value(prop, SH.nodeKind)
            if node_kind is not None and _local(node_kind) in NODE_KINDS:
                facets.node_kind = _local(node_kind)
            in_list = graph.value(prop, SH['in'])
            if in_list is not None:
                facets.in_values = frozenset(_value_text(v) for v in Collection(graph, in_list))
            severity = graph.value(prop, SH.severity) or graph.value(node_shape, SH.severity)
            if severity is not None:
                facets.severity = _local(severity)
            for target in targets:
                key = (str(target), str(path))
                if key in elements:
                    elements[key].merge(facets)
                else:
                    elements[key] = Facets(facets.min_count, facets.max_count, set(facets.classes),
                                           set(facets.datatypes), facets.node_kind, facets.in_values,
                                           facets.severity)
    standalone = set(graph.subjects(RDF.type, SH.PropertyShape)) - property_shapes_seen
    for prop in standalone:
        unhandled.append(f'property shape not attached via sh:property: {_value_text(prop) if not isinstance(prop, BNode) else "blank node"}')
    return elements, sorted(set(unhandled))


def compare(base: Facets | None, profile: Facets) -> tuple[str, list[str]]:
    """Classify profile facets against base facets. Returns (status, notes)."""
    if base is None:
        return 'added', []
    tighter: list[str] = []
    looser: list[str] = []

    def check(name: str, is_tighter: bool, is_looser: bool) -> None:
        if is_tighter:
            tighter.append(name)
        if is_looser:
            looser.append(name)

    b_min, p_min = base.min_count or 0, profile.min_count or 0
    check('minCount', p_min > b_min, p_min < b_min)
    b_max, p_max = base.max_count, profile.max_count
    check('maxCount', b_max is None and p_max is not None or (None not in (b_max, p_max) and p_max < b_max),
          p_max is None and b_max is not None or (None not in (b_max, p_max) and p_max > b_max))
    for name, b_set, p_set in [('class', base.classes, profile.classes), ('datatype', base.datatypes, profile.datatypes)]:
        if b_set != p_set:
            if not b_set:
                tighter.append(name)
            elif not p_set:
                looser.append(name)
            else:
                tighter.append(f'{name} changed (verify: sub/superclass not checked)')
    b_nk = NODE_KINDS.get(base.node_kind or '', {'I', 'B', 'L'})
    p_nk = NODE_KINDS.get(profile.node_kind or '', {'I', 'B', 'L'})
    check('nodeKind', p_nk < b_nk, not p_nk <= b_nk)
    if base.in_values != profile.in_values:
        if base.in_values is None:
            tighter.append('in')
        elif profile.in_values is None or not profile.in_values <= base.in_values:
            looser.append('in')
        else:
            tighter.append('in')
    check('severity', SEVERITY_RANK[profile.severity] > SEVERITY_RANK[base.severity],
          SEVERITY_RANK[profile.severity] < SEVERITY_RANK[base.severity])
    if looser:
        return 'loosened', [f'loosened: {", ".join(looser)}'] + ([f'tightened: {", ".join(tighter)}'] if tighter else [])
    if tighter:
        return 'tightened', [f'tightened: {", ".join(tighter)}']
    return 'unchanged', []


def _obligation(facets: Facets) -> str:
    if (facets.min_count or 0) >= 1:
        return {'Violation': 'mandatory', 'Warning': 'recommended'}.get(facets.severity, 'optional')
    return 'unknown'


def _element(target: str, path: str, facets: Facets, status: str, notes: list[str],
             profile_namespace: str | None) -> dict:
    if profile_namespace and path.startswith(profile_namespace):
        kind = 'mint'
    else:
        kind = 'reuse' if status == 'added' else 'refine'
    element: dict = {'target_class': target, 'path': path, 'kind': kind, 'obligation': _obligation(facets)}
    if facets.min_count is not None:
        element['min_count'] = facets.min_count
    if facets.max_count is not None:
        element['max_count'] = facets.max_count
    if facets.classes:
        element['range_class'] = sorted(facets.classes)[0]
        if len(facets.classes) > 1:
            notes = notes + [f'multiple sh:class values: {sorted(facets.classes)}']
    if facets.datatypes:
        element['range_datatype'] = sorted(facets.datatypes)[0]
        if len(facets.datatypes) > 1:
            notes = notes + [f'multiple sh:datatype values: {sorted(facets.datatypes)}']
    if facets.node_kind:
        element['node_kind'] = facets.node_kind
    if facets.in_values is not None:
        element['controlled_vocabulary'] = sorted(facets.in_values)
    element['severity'] = facets.severity
    element['delta_status'] = status
    element['source'] = 'gold'
    if notes:
        element['notes'] = '; '.join(notes)
    return element


def compute_delta(base_graph: Graph, profile_graph: Graph, profile_id: str, base_ids: list[str],
                  profile_namespace: str | None = None) -> dict:
    base_elements, base_unhandled = normalise(base_graph)
    profile_elements, profile_unhandled = normalise(profile_graph)
    base_classes = {target for target, _ in base_elements}
    elements: list[dict] = []
    counts = {'added': 0, 'tightened': 0, 'unchanged': 0, 'loosened': 0}
    for target in sorted({t for t, _ in profile_elements} - base_classes):
        elements.append({'target_class': target, 'kind': 'class_addition', 'delta_status': 'added',
                         'source': 'gold', 'notes': 'class not targeted by any base shape'})
    for (target, path), facets in sorted(profile_elements.items()):
        status, notes = compare(base_elements.get((target, path)), facets)
        counts[status] += 1
        if status != 'unchanged':
            elements.append(_element(target, path, facets, status, notes, profile_namespace))
    return {
        'profile_id': profile_id,
        'base_profile_ids': base_ids,
        'source': 'gold',
        'elements': elements,
        'notes': (f"counts: {counts}. unhandled in profile: {len(profile_unhandled)}, "
                  f"in base: {len(base_unhandled)}"),
    }, {'counts': counts, 'unhandled_profile': profile_unhandled, 'unhandled_base': base_unhandled}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--base', action='append', required=True, type=Path, help='base shapes (Turtle); repeatable')
    parser.add_argument('--profile', action='append', required=True, type=Path, help='profile shapes (Turtle); repeatable')
    parser.add_argument('--profile-id', required=True)
    parser.add_argument('--base-id', action='append', required=True)
    parser.add_argument('--profile-namespace', help='IRIs under this namespace count as minted')
    parser.add_argument('-o', '--output', type=Path, help='write ProfileDelta YAML here (default: stdout)')
    parser.add_argument('--report', type=Path, help='write counts and unhandled constructs (YAML) here')
    args = parser.parse_args(argv)

    delta, report = compute_delta(load_graph(args.base), load_graph(args.profile), args.profile_id,
                                  args.base_id, args.profile_namespace)
    text = yaml.safe_dump(delta, sort_keys=False, allow_unicode=True)
    if args.output:
        args.output.write_text(text, encoding='utf-8')
    else:
        sys.stdout.write(text)
    if args.report:
        args.report.write_text(yaml.safe_dump(report, sort_keys=False, allow_unicode=True), encoding='utf-8')
    print(f"counts: {report['counts']}; unhandled (profile): {len(report['unhandled_profile'])}", file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
