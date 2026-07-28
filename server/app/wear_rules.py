"""Validation for wear context. Pure functions, no I/O, no database.

Split out of `wear.py` deliberately: that module imports asyncpg, so anything
living beside it can only be tested where a driver is installed. These are the
rules that decide whether the data going into the training set is meaningful,
which makes them the part most worth testing on a laptop with nothing running.
Same reasoning as `engine/` — the rules are pure, the plumbing is not.
"""


class WearError(ValueError):
    """Bad input from the client — surfaces as a 400, never a 500."""


# Stable slugs; the page renders the labels. Work SPLITS into from-home and out
# (her call 07-28) — the published looks' vocabulary has a single 'work', under
# which a work-from-home day is ambiguous between 'work' and 'home / lounge',
# and that is the majority of her logging. Her standing rule "weekday wears are
# work-from-home, comfort-first, not a style preference" is unrepresentable
# without this split.
OCCASIONS = ("work_home", "work_out", "day_out", "dinner", "event", "home")


def clean_occasion(value):
    if value in (None, ""):
        return None
    if value not in OCCASIONS:
        raise WearError("occasion must be one of: %s" % ", ".join(OCCASIONS))
    return value


def clean_swap(nearly_wore, instead_of, garment_ids):
    """The near-miss pair, validated against the outfit it is a near-miss FOR.

    Both halves or neither: a "nearly wore" with nothing displaced is not a
    comparison, and the entire value of this field is that the two are matched
    within one day, one occasion, one set of weather.

    The direction matters and is checked, not assumed. `instead_of` must be IN
    the outfit and `nearly_wore` must be OUT of it — reversed, the pair records
    a true negative with its sign flipped, which is worse than collecting
    nothing, and on a phone at the end of a day the two are easy to transpose.
    """
    if nearly_wore in (None, "") and instead_of in (None, ""):
        return None, None
    if not nearly_wore or not instead_of:
        raise WearError("a swap needs both nearly_wore and instead_of")
    if nearly_wore == instead_of:
        raise WearError("a garment cannot be its own alternative")
    worn = set(garment_ids)
    if instead_of not in worn:
        raise WearError("instead_of must be a garment you actually wore")
    if nearly_wore in worn:
        raise WearError("nearly_wore must be a garment you did NOT wear")
    return nearly_wore, instead_of
