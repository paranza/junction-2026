"""Natural-language highlight requests reuse constrained native source queries."""
import re

from .native_qa import answer_native


def highlight_target(question):
    match = re.fullmatch(
        r'\s*(?:(?:can|could|would)\s+you\s+)?(?:please\s+)?'
        r'(?:highlight|mark|outline|locate)\s+(?:all\s+)?(?:the\s+)?(.+?)\s*[?!.]?\s*',
        question, re.I)
    return match.group(1).strip().rstrip('?!') if match else None


def native_highlight(question, document, source_path, data_root):
    target = highlight_target(question)
    if not target:
        return None
    # The native parser must still understand every constraint. Never select an
    # entire class merely because an unsupported filtered request names it.
    result = answer_native('How many ' + target + '?', document, source_path, data_root)
    if result is not None:
        return result
    identifier = re.fullmatch(r'(room|space|element|object)\s+[\'\"]?([\w.$-]+)[\'\"]?', target, re.I)
    if not identifier:
        return None
    kind, wanted = identifier.groups()
    selected = []
    for obj in document.get('objects', []):
        if kind.lower() in {'room', 'space'} and obj.get('type') not in {'room', 'IfcSpace', 'schedule_room'}:
            continue
        properties = obj.get('properties', {})
        aliases = [obj.get('guid'), obj.get('id'), properties.get('room_number'), properties.get('name')]
        if wanted.casefold() in {str(a).casefold() for a in aliases if a is not None}:
            selected.append(obj)
    if not selected:
        return None
    keys = {'id', 'label', 'type', 'page', 'bbox', 'polygon', 'source_path', 'guid', 'properties'}
    return {'answer': f'{len(selected)} matching source objects.', 'value': len(selected), 'unit': 'count',
            'method': 'native_object_selection', 'operation': 'count', 'status': 'supported',
            'scope': 'Matching objects in selected source', 'evidence': [{k: v for k, v in o.items() if k in keys} for o in selected],
            'warnings': [], 'calculation': {'operation': 'select_exact_identifier', 'identifier': wanted}}


def describe_highlights(result):
    """Report actual drawable evidence separately from BIM-only source records."""
    evidence = result.get('evidence', [])
    spatial = sum(bool(e.get('bbox') or e.get('polygon')) for e in evidence)
    result['action'] = 'highlight'
    result['highlighted_count'] = spatial
    result['matched_source_count'] = len(evidence)
    if not evidence:
        return result
    if spatial == len(evidence):
        noun = 'element' if spatial == 1 else 'elements'
        result['answer'] = f'{spatial} located {noun} marked on the source drawings. Select an evidence item to inspect it.'
    elif spatial:
        result['answer'] = f'{len(evidence)} matching source objects; {spatial} have drawing locations. The remaining objects can be inspected as source records.'
        result.setdefault('warnings', []).append('Some source objects have no usable 2D projection and cannot be highlighted on a drawing.')
    else:
        result['answer'] = f'{len(evidence)} matching source records. This source has no usable 2D locations for these objects, so drawing highlights are unavailable.'
        result['status'] = 'needs_review'
    return result
