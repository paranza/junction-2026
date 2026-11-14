"""Prevent a projected drawing from being mistaken for its complete BIM model."""
from pathlib import Path
import re


def unavailable_model_scope(question, document, source):
    from .extraction import linked_model
    from .native_qa import _MODEL_WORDS, _without_model_titles

    source = Path(source)
    if source.suffix.lower() == '.ifc' or linked_model(source):
        return None
    # This applies to semantic IFC projections, not every drawing that mentions
    # a building. An attached native model is the authority for model totals.
    metadata = document.get('metadata', {})
    projection = bool(metadata.get('semantic_svg')) or any(
        str(obj.get('type', '')).startswith('Ifc') and obj.get('guid')
        for obj in document.get('objects', []))
    if not projection:
        return None
    q = _without_model_titles(question)
    if not re.search(r'\b' + _MODEL_WORDS + r'\b', q):
        return None
    if re.search(r'this floor|selected floor|on this plan|shown|drawn|visible|grundriss|dargestellt', q):
        return None
    return {
        'answer': 'This file contains a floor-plan view, not the complete BIM model. Attach the IFC to answer for the whole model, or ask about objects shown on this plan.',
        'value': None, 'unit': None, 'operation': 'unknown',
        'method': 'source_scope_check', 'status': 'needs_input',
        'evidence': [], 'can_review': False,
        'warnings': ['Whole-model coverage is unavailable from this projected drawing. Visible object counts cannot establish a model total.'],
    }
