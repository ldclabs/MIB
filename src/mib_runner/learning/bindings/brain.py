"""Brain-specific P5 tokenizer and native record identity constraints."""
import re
from ...adapter_contract import AdapterLifecycleError


def validate_budget(recall):
    if recall.get('tokenizer') != 'o200k_base@tiktoken-rs-0.12.0':
        raise AdapterLifecycleError('missing pinned P5 Recall tokenizer')


def valid_reference(kind, value):
    prefix = 'C' if kind in {'skill', 'revision'} else 'X'
    return re.fullmatch(prefix + r'-[1-9][0-9]*', str(value)) is not None
