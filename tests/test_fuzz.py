import string

from hypothesis import given
from hypothesis import settings as hyp_settings
from hypothesis import strategies as st

from arapy.cli.parser import _normalize_flag_name, parse_cli
from arapy.core.config import SECRET_FIELDS
from arapy.core.resolver import query_params_for_action
from arapy.io.output import sanitize_secrets

BOOLEAN_FLAGS = {
    "verbose",
    "version",
    "debug",
    "console",
    "all",
    "decrypt",
    "help",
}

SAFE_VALUE_ALPHABET = string.ascii_letters + string.digits + "_-.:/="
POSITIONAL_ALPHABET = string.ascii_letters + string.digits + "._/"

flag_keys = st.from_regex(r"[a-z][a-z0-9_-]{0,11}", fullmatch=True).filter(
    lambda key: key not in BOOLEAN_FLAGS and not key.startswith("_")
)
flag_values = st.text(alphabet=SAFE_VALUE_ALPHABET, min_size=0, max_size=20)
positionals = st.from_regex(
    r"[A-Za-z0-9][A-Za-z0-9._/]{0,15}", fullmatch=True
)

leaf_values = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(),
    st.text(
        alphabet=st.characters(blacklist_categories=("Cs",)),
        min_size=0,
        max_size=12,
    ),
)
plain_keys = st.from_regex(r"[a-z][a-z0-9_]{0,10}", fullmatch=True).filter(
    lambda key: key not in SECRET_FIELDS
)
nested_values = st.recursive(
    leaf_values,
    lambda children: st.one_of(
        st.lists(children, max_size=4),
        st.dictionaries(
            st.one_of(plain_keys, st.sampled_from(SECRET_FIELDS)),
            children,
            max_size=4,
        ),
    ),
    max_leaves=20,
)


@st.composite
def valid_cli_cases(draw):
    bool_flags = draw(
        st.lists(st.sampled_from(sorted(BOOLEAN_FLAGS)), unique=True, max_size=4)
    )
    key_values = draw(
        st.dictionaries(flag_keys, flag_values, max_size=4)
    )
    args = ["arapy"]
    args.extend(f"--{flag}" for flag in bool_flags)
    args.extend(f"--{key}={value}" for key, value in key_values.items())
    positional_args = draw(st.lists(positionals, max_size=4))
    args.extend(positional_args)
    return args, bool_flags, key_values, positional_args


@st.composite
def completion_cli_cases(draw):
    long_flags = draw(
        st.lists(flag_keys, unique=True, max_size=4)
    )
    short_flags = draw(
        st.lists(st.sampled_from(list(string.ascii_lowercase)), unique=True, max_size=4)
    )
    positional_args = draw(st.lists(positionals, max_size=4))
    args = ["arapy", "--_complete"]
    args.extend(f"--{flag}" for flag in long_flags)
    args.extend(f"-{flag}" for flag in short_flags)
    args.extend(positional_args)
    return args, positional_args


def _assert_secret_masking(original, sanitized):
    if isinstance(original, dict):
        assert isinstance(sanitized, dict)
        assert set(original) == set(sanitized)
        for key, value in original.items():
            if key in SECRET_FIELDS:
                assert sanitized[key] == ""
            else:
                _assert_secret_masking(value, sanitized[key])
        return

    if isinstance(original, list):
        assert isinstance(sanitized, list)
        assert len(original) == len(sanitized)
        for left, right in zip(original, sanitized):
            _assert_secret_masking(left, right)
        return

    assert original == sanitized


class FakeCP:
    def get_action_definition(self, api_catalog, module, service, action):
        return {"params": ["calculate_count"]}


@hyp_settings(max_examples=150, deadline=None)
@given(valid_cli_cases())
def test_parse_cli_property_valid_inputs(case):
    argv, bool_flags, key_values, positional_args = case

    parsed = parse_cli(argv)

    for flag in bool_flags:
        assert parsed[_normalize_flag_name(flag)] is True

    for key, value in key_values.items():
        assert parsed[_normalize_flag_name(key)] == value

    if len(positional_args) >= 1:
        assert parsed["module"] == positional_args[0]
    if len(positional_args) >= 2:
        assert parsed["service"] == positional_args[1]
    if len(positional_args) >= 3:
        assert parsed["action"] == positional_args[2]


@hyp_settings(max_examples=150, deadline=None)
@given(completion_cli_cases())
def test_parse_cli_property_completion_ignores_unknown_flags(case):
    argv, positional_args = case

    parsed = parse_cli(argv)

    assert parsed["_complete"] is True
    if len(positional_args) >= 1:
        assert parsed["module"] == positional_args[0]
    if len(positional_args) >= 2:
        assert parsed["service"] == positional_args[1]
    if len(positional_args) >= 3:
        assert parsed["action"] == positional_args[2]


@hyp_settings(max_examples=150, deadline=None)
@given(
    secret_key=st.sampled_from(SECRET_FIELDS),
    secret_value=nested_values,
    other_value=nested_values,
)
def test_sanitize_secrets_property_masks_recursive_secret_fields(
    secret_key, secret_value, other_value
):
    payload = {secret_key: secret_value, "other": other_value}

    sanitized = sanitize_secrets(payload, mask_secrets=True)

    _assert_secret_masking(payload, sanitized)


@hyp_settings(max_examples=150, deadline=None)
@given(raw_value=st.one_of(st.booleans(), flag_values))
def test_query_params_property_calculate_count_is_lowercase_boolean_string(raw_value):
    parsed = query_params_for_action(
        FakeCP(),
        {},
        {
            "module": "m",
            "service": "s",
            "action": "list",
            "calculate_count": raw_value,
        },
        "list",
    )

    assert parsed["calculate_count"] in {"true", "false"}

    if isinstance(raw_value, str):
        enabled = raw_value.strip().lower() in {"1", "true", "yes", "on"}
    else:
        enabled = bool(raw_value)
    assert parsed["calculate_count"] == ("true" if enabled else "false")
