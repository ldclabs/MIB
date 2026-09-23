"""Optional host audit bindings; none grants native learning standing."""
from __future__ import annotations
import re
from ...adapter_contract import AdapterLifecycleError


def validate_budget(binding, recall):
    if binding == 'brain_native_v1':
        from .brain import validate_budget as validate
        validate(recall)
    elif binding == 'portable_v1':
        tokenizer = recall.get('tokenizer')
        if not isinstance(tokenizer, str) or not re.fullmatch(r'[^\s@]+@[^\s@]+', tokenizer):
            raise AdapterLifecycleError('portable audit requires a versioned tokenizer identity')
    else:
        raise AdapterLifecycleError('unknown learning audit binding')


def valid_reference(binding, kind, value):
    if binding == 'brain_native_v1':
        from .brain import valid_reference as validate
        return validate(kind, value)
    if binding == 'portable_v1':
        return isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_:/.-]{0,255}', value) is not None
    raise AdapterLifecycleError('unknown learning audit binding')
