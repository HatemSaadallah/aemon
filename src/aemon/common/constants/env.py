"""Rules of the investigation environment: limits, vocabularies and the stage table."""

from __future__ import annotations

MIN_QUOTE = 15

MAX_THEORIES = 5

MIN_LIMIT = 15

EVIDENCE_KINDS = ('company_assertion', 'customer_observation', 'independent_study', 'regulation', 'analogy', 'market_fact')

SYNTHETIC_CLASSES = ('synthetic',)

BELIEFS = ('very unlikely', 'unlikely', 'uncertain', 'likely', 'very likely')  # a within-run signal, not a calibrated probability

MIN_READ = 3

MIN_THEORIES = 2  # a theory and an alternative, as in the source paper. A third is optional

_LOOK_FURTHER = ('read_source', 'search_evidence', 'challenge_theory', 'assess_evidence')

# The same controller, written out for people: the stages in order, the tools each one opens, and what moves the
# investigation on. tests/test_strategy.py drives a scripted investigation through every stage and fails if this
# disagrees with current_stage, so the diagram in Aemon cannot drift from what the controller enforces.
WORKFLOW = (
    {'stage': 'brief', 'tools': ('read_brief',), 'moves_on': 'once the brief is read', 'group': 'problem'},
    {'stage': 'frame', 'tools': ('frame_problem',), 'moves_on': 'once objective, constraints and alternatives are stated', 'group': 'problem'},
    {'stage': 'evidence', 'tools': ('search_evidence', 'read_source'), 'moves_on': f'after {MIN_READ} sources are read', 'group': 'theory'},
    {
        'stage': 'theories',
        'tools': ('add_theory', 'search_evidence', 'read_source'),
        'moves_on': f'after {MIN_THEORIES} rival causal theories',
        'group': 'theory',
    },
    {
        'stage': 'assessment',
        'tools': ('assess_evidence', 'read_source', 'search_evidence', 'add_theory'),
        'moves_on': 'once every theory has a quoted assessment',
        'group': 'theory',
    },
    {'stage': 'challenge', 'tools': ('challenge_theory',), 'moves_on': 'after a search for what could prove the favoured theory wrong', 'group': 'theory'},
    {
        'stage': 'challenge_reading',
        'tools': ('read_source', 'challenge_theory'),
        'moves_on': 'once something the challenge found is read',
        'group': 'theory',
        'optional': True,
    },
    {
        'stage': 'test',
        'tools': ('propose_test', 'decline_test', 'add_theory', *_LOOK_FURTHER),
        'moves_on': 'after a discriminating test, or a reasoned decline',
        'group': 'experiment',
    },
    {
        'stage': 'position',
        'tools': ('state_position', *_LOOK_FURTHER),
        'moves_on': 'after a favoured theory, a recommendation and a belief for each theory',
        'group': 'experiment',
    },
    {'stage': 'new_evidence', 'tools': ('read_source',), 'moves_on': 'once the simulated result is read', 'group': 'revision', 'optional': True},
    {
        'stage': 'update',
        'tools': ('revise_theory',),
        'moves_on': 'after a revision that cites it: kept, revised or rejected',
        'group': 'revision',
        'optional': True,
    },
    {'stage': 'conclude', 'tools': ('finish', 'revise_theory', *_LOOK_FURTHER), 'moves_on': 'when the agent finishes', 'group': 'conclusion'},
)

DISTINCT = 0.6

# Reported, but not required. Each measures a real concern with a rule too blunt to gate on, as Codex's
# review of #17 found: judges score these. evidence_classes must not fail a sound "demand is unknown".
DIAGNOSTIC = ('causal_form', 'testable_predictions', 'evidence_kinds', 'evidence_classes')

CLASSES = ('verified_observation', 'company_claim', 'analyst_assumption', 'proposed_hypothesis', 'synthetic', 'web_page', 'user_document')  # web_page: live research only; user_document: files and links a person attached in Aemon
