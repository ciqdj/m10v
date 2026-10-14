# Copyright (C) 2026 zhaoo
# SPDX-License-Identifier: GPL-2.0-only
"""Preserve pristine native entries before installing the registry wrappers.

The upstream registry compiler expects branch continuations inherited from an
older research image. Official 1.11.10.7 starts with native instructions instead.
These exact entries contain no PC-relative loads or branches: each displaced
word is replayed once, with the original LR and flags, then resumes at site+4.
"""
import hashlib

OFFICIAL_RTOS_SHA = 'a9a9a51530c35819df47dee1cce9f4f560a17eeed1da258950167d282884fce1'


def initialize_filter_entries(patch):
    from .slots import GETTERS, SETTERS, DEFAULT_ENTRIES, _branch
    if hashlib.sha256(patch.image).hexdigest() != OFFICIAL_RTOS_SHA:
        raise ValueError('GR IV official entry identity differs before initialization')
    entries = [(site, 0xE1A0C00D) for site in GETTERS + SETTERS + DEFAULT_ENTRIES]
    entries.extend(((0x53912CF4, 0xE352001E), (0x539113FC, 0xE352000B),
                    (0x5375F0B0, 0xE3510000), (0x533CC6E0, 0xE3520000),
                    (0x53373BC0, 0xE241100B), (0x53373F84, 0xE1A0C00D),
                    (0x53374118, 0xE1A0C00D), (0x53370738, 0xE1A0C00D)))
    for site, expected in entries:
        if patch.word(site) != expected:
            raise ValueError(f'GR IV official entry preimage differs at {site:#x}')
    continuations = []
    for site, original in entries:
        target = patch.append(lambda at, site=site, original=original:
                              [original, _branch(at + 4, site + 4)], 16)
        patch.set_word(site, _branch(site, target), 'M10V preserve original filter entry continuation')
        continuations.append({'site': hex(site), 'continuation': hex(target),
                              'displaced': hex(original), 'resume': hex(site + 4)})
    return {'source': 'official-1.11.10.7', 'continuations': continuations,
            'hardware': 'not_tested'}
