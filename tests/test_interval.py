import pytest

import numpy as np
import portion as P

pos_infs = [P.inf, *(t("inf") for t in (float, np.float64, np.float32, np.float16))]
parametrize_pinf = pytest.mark.parametrize("pinf", pos_infs)
parametrize_ninf = pytest.mark.parametrize("ninf", [-inf for inf in pos_infs])


class TestHelpers:
    def test_bounds(self):
        assert P.closed(0, 1) == P.Interval.from_atomic(P.CLOSED, 0, 1, P.CLOSED)
        assert P.open(0, 1) == P.Interval.from_atomic(P.OPEN, 0, 1, P.OPEN)
        assert P.openclosed(0, 1) == P.Interval.from_atomic(P.OPEN, 0, 1, P.CLOSED)
        assert P.closedopen(0, 1) == P.Interval.from_atomic(P.CLOSED, 0, 1, P.OPEN)
        assert P.singleton(2) == P.closed(2, 2)

    @parametrize_pinf
    @parametrize_ninf
    def test_with_infinities(self, pinf, ninf):
        assert P.closed(ninf, pinf) == P.open(ninf, pinf)
        assert P.closed(ninf, 0) == P.openclosed(ninf, 0)
        assert P.closed(0, pinf) == P.closedopen(0, pinf)

    @parametrize_pinf
    @parametrize_ninf
    def test_empty(self, pinf, ninf):
        assert P.empty() == P.Interval.from_atomic(P.OPEN, pinf, ninf, P.open)
        assert P.closed(3, -3) == P.empty()

        assert P.openclosed(0, 0) == P.empty()
        assert P.closedopen(0, 0) == P.empty()
        assert P.open(0, 0) == P.empty()
        assert P.closed(0, 0) != P.empty()

        assert P.singleton(pinf) == P.empty()
        assert P.singleton(ninf) == P.empty()


class TestRepr:
    def test_simple(self):
        assert repr(P.closed(0, 1)) == '[0,1]'
        assert repr(P.openclosed(0, 1)) == '(0,1]'
        assert repr(P.closedopen(0, 1)) == '[0,1)'
        assert repr(P.open(0, 1)) == '(0,1)'

    @parametrize_pinf
    @parametrize_ninf
    def test_infinities(self, pinf, ninf):
        assert repr(P.closed(ninf, pinf)) == '(-inf,+inf)'

    def test_empty(self):
        assert repr(P.empty()) == '()'

    def test_singleton(self):
        assert repr(P.singleton(4)) == '[4]'

    def test_union(self):
        assert repr(P.closed(0, 1) | P.open(3, 4)) == '[0,1] | (3,4)'
        # https://github.com/AlexandreDecan/portion/issues/22
        assert repr(P.singleton(1) | P.singleton(2)) == '[1] | [2]'


class TestInterval:
    def test_creation(self):
        assert P.Interval() == P.empty()
        assert P.Interval(P.closed(0, 1)) == P.closed(0, 1)
        assert P.Interval(P.closed(0, 1)) == P.closed(0, 1)
        assert P.Interval(P.closed(0, 1), P.closed(2, 3)) == P.closed(0, 1) | P.closed(2, 3)
        assert P.Interval(P.closed(0, 1) | P.closed(2, 3)) == P.closed(0, 1) | P.closed(2, 3)

        with pytest.raises(TypeError):
            P.Interval(1)

    def test_creation_issue_19(self):
        # https://github.com/AlexandreDecan/python-intervals/issues/19
        assert P.Interval(P.empty(), P.empty()) == P.empty()

    def test_bounds(self):
        i = P.openclosed(1, 2)
        assert i.left == P.OPEN
        assert i.right == P.CLOSED
        assert i.lower == 1
        assert i.upper == 2

    def test_bounds_on_empty(self):
        i = P.empty()
        assert i.left == P.OPEN
        assert i.right == P.OPEN
        assert i.lower == P.inf
        assert i.upper == -P.inf

        i = P.openclosed(10, -10)
        assert i.left == P.OPEN
        assert i.right == P.OPEN
        assert i.lower == P.inf
        assert i.upper == -P.inf

        i = P.open(0, 1) | P.closed(3, 4)
        assert i.left == P.OPEN
        assert i.right == P.CLOSED
        assert i.lower == 0
        assert i.upper == 4

    def test_bounds_on_union(self):
        i = P.closedopen(0, 1) | P.openclosed(3, 4)
        assert i.left == P.CLOSED
        assert i.right == P.CLOSED
        assert i.lower == 0
        assert i.upper == 4

    def test_is_empty(self):
        assert P.openclosed(1, 1).empty
        assert P.closedopen(1, 1).empty
        assert P.open(1, 1).empty
        assert not P.closed(1, 1).empty
        assert P.Interval().empty
        assert P.empty().empty

    @parametrize_pinf
    @parametrize_ninf
    def test_hash_with_hashable(self, pinf, ninf):
        assert hash(P.closed(0, 1)) is not None
        assert hash(P.closed(0, 1)) != hash(P.closed(1, 2))

        assert hash(P.openclosed(ninf, 0)) is not None
        assert hash(P.closedopen(0, pinf)) is not None
        assert hash(P.empty()) is not None

        assert hash(P.closed(0, 1) | P.closed(3, 4)) is not None
        assert hash(P.closed(0, 1) | P.closed(3, 4)) != hash(P.closed(0, 1))
        assert hash(P.closed(0, 1) | P.closed(3, 4)) != hash(P.closed(3, 4))

    def test_hash_with_unhashable(self):
        # Let's create a comparable but no hashable object
        class T(int):
            def __hash__(self):
                raise TypeError()

        x = P.closed(T(1), T(2))
        with pytest.raises(TypeError):
            hash(x)

        with pytest.raises(TypeError):
            hash(x | P.closed(3, 4))

        with pytest.raises(TypeError):
            hash(P.closed(-1, 0) | x)

        # Not guaranteed to work
        assert hash(P.closed(-1, 0) | x | P.closed(3, 4)) is not None

    def test_enclosure(self):
        assert P.closed(0, 1) == P.closed(0, 1).enclosure
        assert P.open(0, 1) == P.open(0, 1).enclosure
        assert P.closed(0, 4) == (P.closed(0, 1) | P.closed(3, 4)).enclosure
        assert P.openclosed(0, 4) == (P.open(0, 1) | P.closed(3, 4)).enclosure


class TestIntervalReplace:
    @parametrize_pinf
    @parametrize_ninf
    def test_replace_bounds(self, pinf, ninf):
        i = P.open(ninf, pinf)
        assert i.replace(lower=lambda v: 1, upper=lambda v: 1) == P.open(ninf, pinf)
        assert i.replace(lower=lambda v: 1, upper=lambda v: 2, ignore_inf=False) == P.open(1, 2)

    def test_replace_values(self):
        i = P.open(0, 1)
        assert i.replace(left=P.CLOSED, right=P.CLOSED) == P.closed(0, 1)
        assert i.replace(lower=1, upper=2) == P.open(1, 2)
        assert i.replace(lower=lambda v: 1, upper=lambda v: 2) == P.open(1, 2)

    @parametrize_pinf
    @parametrize_ninf
    def test_replace_values_on_infinities(self, pinf, ninf):
        i = P.open(ninf, pinf)
        assert i.replace(lower=lambda v: 1, upper=lambda v: 2) == i
        assert i.replace(lower=lambda v: 1, upper=lambda v: 2, ignore_inf=False) == P.open(1, 2)

    def test_replace_with_union(self):
        i = P.closed(0, 1) | P.open(2, 3)
        assert i.replace() == i
        assert i.replace(P.OPEN, -1, 4, P.OPEN) == P.openclosed(-1, 1) | P.open(2, 4)
        assert i.replace(lower=2) == P.closedopen(2, 3)
        assert i.replace(upper=1) == P.closedopen(0, 1)
        assert i.replace(lower=5) == P.empty()
        assert i.replace(upper=-5) == P.empty()
        assert i.replace(left=lambda v: ~v, lower=lambda v: v - 1, upper=lambda v: v + 1, right=lambda v: ~v) == P.openclosed(-1, 1) | P.openclosed(2, 4)

    def test_replace_with_empty(self):
        assert P.empty().replace(left=P.CLOSED, right=P.CLOSED) == P.empty()
        assert P.empty().replace(lower=1, upper=2) == P.open(1, 2)
        assert P.empty().replace(lower=lambda v: 1, upper=lambda v: 2) == P.empty()
        assert P.empty().replace(lower=lambda v: 1, upper=lambda v: 2, ignore_inf=False) == P.open(1, 2)


class TestIntervalApply:
    def test_apply(self):
        i = P.closed(0, 1)
        assert i.apply(lambda s: s) == i
        assert i.apply(lambda s: (P.OPEN, -1, 2, P.OPEN)) == P.open(-1, 2)
        assert i.apply(lambda s: P.Interval.from_atomic(P.OPEN, -1, 2, P.OPEN)) == P.open(-1, 2)
        assert i.apply(lambda s: P.open(-1, 2)) == P.open(-1, 2)

    def test_apply_on_unions(self):
        i = P.closed(0, 1) | P.closed(2, 3)
        assert i.apply(lambda s: s) == i
        assert i.apply(lambda s: (P.OPEN, -1, 2, P.OPEN)) == P.open(-1, 2)
        assert i.apply(lambda s: (~s.left, s.lower - 1, s.upper - 1, ~s.right)) == P.open(-1, 0) | P.open(1, 2)
        assert i.apply(lambda s: P.Interval.from_atomic(P.OPEN, -1, 2, P.OPEN)) == P.open(-1, 2)
        assert i.apply(lambda s: P.open(-1, 2)) == P.open(-1, 2)

        assert i.apply(lambda s: (s.left, s.lower, s.upper * 2, s.right)) == P.closed(0, 6)

    def test_apply_on_empty(self):
        assert P.empty().apply(lambda s: (P.CLOSED, 1, 2, P.CLOSED)) == P.empty()

    def test_apply_with_incorrect_types(self):
        i = P.closed(0, 1)
        with pytest.raises(TypeError):
            i.apply(lambda s: None)

        with pytest.raises(TypeError):
            i.apply(lambda s: 'unsupported')


class TestIntervalAdjacent:
    def test_adjacent(self):
        assert P.closedopen(0, 1).adjacent(P.closedopen(1, 2))
        assert P.closed(0, 1).adjacent(P.open(1, 2))
        assert not P.closed(0, 1).adjacent(P.closed(1, 2))
        assert not P.open(0, 1).adjacent(P.open(1, 2))

    def test_reversed_adjacent(self):
        assert P.closedopen(1, 2).adjacent(P.closedopen(0, 1))
        assert P.open(1, 2).adjacent(P.closed(0, 1))
        assert not P.closed(1, 2).adjacent(P.closed(0, 1))
        assert not P.open(1, 2).adjacent(P.open(0, 1))

    def test_non_adjacent(self):
        assert not P.closedopen(0, 1).adjacent(P.closedopen(3, 4))
        assert not P.closed(0, 1).adjacent(P.open(3, 4))
        assert not P.closed(0, 1).adjacent(P.closed(3, 4))
        assert not P.open(0, 1).adjacent(P.open(3, 4))

        assert not P.closedopen(3, 4).adjacent(P.closedopen(0, 1))
        assert not P.open(3, 4).adjacent(P.closed(0, 1))
        assert not P.closed(3, 4).adjacent(P.closed(0, 1))
        assert not P.open(3, 4).adjacent(P.open(0, 1))

    def test_overlapping(self):
        assert not P.openclosed(0, 2).adjacent(P.closedopen(2, 3))
        assert not P.closed(0, 2).adjacent(P.closedopen(2, 3))
        assert not P.closed(0, 2).adjacent(P.closed(2, 3))
        assert not P.open(0, 2).adjacent(P.open(2, 3))

        assert not P.closedopen(2, 3).adjacent(P.openclosed(0, 2))
        assert not P.closedopen(2, 3).adjacent(P.closed(0, 2))
        assert not P.closed(2, 3).adjacent(P.closed(0, 2))
        assert not P.open(2, 3).adjacent(P.open(0, 2))

    def test_contained(self):
        assert not P.closed(0, 4).adjacent(P.closed(0, 2))
        assert not P.closed(0, 4).adjacent(P.closed(2, 4))
        assert not P.closed(0, 4).adjacent(P.open(0, 2))
        assert not P.closed(0, 4).adjacent(P.open(2, 4))

        assert not P.closed(0, 2).adjacent(P.closed(0, 4))
        assert not P.closed(2, 4).adjacent(P.closed(0, 4))
        assert not P.closed(0, 2).adjacent(P.open(0, 4))
        assert not P.closed(2, 4).adjacent(P.open(0, 4))

        assert not P.closed(0, 2).adjacent(P.closed(0, 2))
        assert not P.open(0, 2).adjacent(P.open(0, 2))
        assert not P.openclosed(0, 2).adjacent(P.openclosed(0, 2))
        assert not P.closedopen(0, 2).adjacent(P.closedopen(0, 2))

    def test_same_bounds(self):
        assert not P.closed(0, 2).adjacent(P.open(0, 2))
        assert not P.open(0, 2).adjacent(P.closed(0, 2))
        assert not P.openclosed(0, 2).adjacent(P.closedopen(0, 2))
        assert not P.closedopen(0, 2).adjacent(P.openclosed(0, 2))

    def test_empty(self):
        assert P.empty().adjacent(P.closed(0, 2))
        assert P.empty().adjacent(P.empty())
        assert P.closed(0, 2).adjacent(P.empty())

        assert not P.empty().adjacent(P.closed(0, 1) | P.closed(2, 3))
        assert not (P.closed(0, 1) | P.closed(2, 3)).adjacent(P.empty())

    def test_nonatomic_interval(self):
        assert (P.closed(0, 1) | P.closed(2, 3)).adjacent(P.open(1, 2))
        assert P.open(1, 2).adjacent(P.closed(0, 1) | P.closed(2, 3))
        assert not (P.closed(0, 1) | P.closed(2, 3)).adjacent(P.closed(1, 2))
        assert (P.closedopen(0, 1) | P.openclosed(2, 3)).adjacent(P.open(-1, 0) | P.closed(1, 2) | P.openclosed(3, 4))


class TestIntervalOverlaps:
    def test_overlaps(self):
        assert P.closed(1, 2).overlaps(P.closed(2, 3))
        assert P.closed(1, 2).overlaps(P.closedopen(2, 3))
        assert P.openclosed(1, 2).overlaps(P.closed(2, 3))
        assert P.openclosed(1, 2).overlaps(P.closedopen(2, 3))

    def test_overlaps_with_nonoverlaping(self):
        assert not P.closed(0, 1).overlaps(P.closed(3, 4))
        assert not P.closed(3, 4).overlaps(P.closed(0, 1))

    def test_overlaps_with_edge_cases(self):
        assert not P.closed(0, 1).overlaps(P.open(1, 2))
        assert not P.closed(0, 1).overlaps(P.openclosed(1, 2))
        assert not P.closedopen(0, 1).overlaps(P.closed(1, 2))
        assert not P.closedopen(0, 1).overlaps(P.closedopen(1, 2))
        assert not P.closedopen(0, 1).overlaps(P.openclosed(1, 2))
        assert not P.closedopen(0, 1).overlaps(P.open(1, 2))
        assert not P.open(0, 1).overlaps(P.open(1, 2))
        assert P.open(0, 2).overlaps(P.open(0, 1))
        assert P.open(0, 1).overlaps(P.open(0, 2))

    @parametrize_pinf
    @parametrize_ninf
    def test_overlaps_with_empty(self, pinf, ninf):
        assert not P.empty().overlaps(P.open(ninf, pinf))
        assert not P.open(ninf, pinf).overlaps(P.empty())

    def test_overlaps_with_itself(self):
        assert P.closed(0, 1).overlaps(P.closed(0, 1))
        assert P.closed(0, 1).overlaps(P.open(0, 1))
        assert P.open(0, 1).overlaps(P.closed(0, 1))
        assert P.closed(0, 1).overlaps(P.openclosed(0, 1))
        assert P.closed(0, 1).overlaps(P.closedopen(0, 1))

    def test_overlaps_with_incompatible_types(self):
        with pytest.raises(TypeError):
            P.closed(0, 1).overlaps(1)


class TestIntervalComparison:
    @pytest.mark.parametrize('i1,i2,i3', [
        (P.closed(0, 1), P.closed(1, 2), P.closed(2, 3)),
        (P.open(0, 2), P.open(1, 3), P.open(2, 4)),
    ])
    def test_equalities(self, i1, i2, i3):
        assert i1 == i1
        assert i1 != i2 and i2 != i1
        assert i1 != i3 and i3 != i1
        assert i2 != i3 and i3 != i2

        assert not i1 == 1

    @pytest.mark.parametrize('i1,i2,i3', [
        (P.closed(0, 1), P.closed(1, 2), P.closed(2, 3)),
        (P.open(0, 2), P.open(1, 3), P.open(2, 4)),
    ])
    def test_inequalities(self, i1, i2, i3):
        assert i1 < i3 and i3 > i1
        assert i1 <= i2 and i2 >= i1
        assert i1 <= i3 and i3 >= i1
        assert not i1 < i2 and not i2 > i1

    def test_with_intervals(self):
        i1, i2, i3 = P.closed(0, 1), P.closed(1, 2), P.closed(2, 3)

        i4 = i1 | i3

        assert i4 != i2 and i2 != i4
        assert not i4 < i2 and not i2 > i4
        assert not i4 > i2 and not i2 < i4
        assert not i4 <= i2
        assert not i4 >= i2
        assert i2 <= i4
        assert i2 >= i4

        i5 = P.closed(5, 6) | P.closed(7, 8)

        assert i4 != i5 and i5 != i4
        assert i4 < i5 and i5 > i4
        assert not i4 > i5 and not i5 < i4
        assert i4 <= i5
        assert i5 >= i4
        assert not i4 >= i5
        assert not i5 <= i4

    def test_with_empty(self):
        assert not (P.empty() < P.empty())
        assert not (P.empty() <= P.empty())
        assert not (P.empty() > P.empty())
        assert not (P.empty() >= P.empty())

        assert not (P.empty() < P.closed(2, 3))
        assert not (P.empty() <= P.closed(2, 3))
        assert not (P.empty() > P.closed(2, 3))
        assert not (P.empty() >= P.closed(2, 3))

        assert not (P.closed(2, 3) < P.empty())
        assert not (P.closed(2, 3) > P.empty())
        assert not (P.closed(2, 3) <= P.empty())
        assert not (P.closed(2, 3) >= P.empty())

    @parametrize_pinf
    def test_with_empty_and_infinities(self, pinf):
        assert not (P.empty() < P.closedopen(0, pinf))
        assert not (P.empty() <= P.closedopen(0, pinf))
        assert not (P.empty() > P.closedopen(0, pinf))
        assert not (P.empty() >= P.closedopen(0, pinf))

        assert not (P.closedopen(0, pinf) < P.empty())
        assert not (P.closedopen(0, pinf) > P.empty())
        assert not (P.closedopen(0, pinf) <= P.empty())
        assert not (P.closedopen(0, pinf) >= P.empty())

    def test_edge_cases(self):
        assert not (P.closed(0, 2) >= P.open(0, 1))
        assert not (P.closed(0, 2) >= P.openclosed(0, 1))

    def test_with_values(self):
        with pytest.deprecated_call():
            assert 0 < P.closed(1, 2)

        with pytest.deprecated_call():
            assert not (0 < P.closed(-1, 1))

        with pytest.deprecated_call():
            assert not (0 < P.closed(0, 1))

        with pytest.deprecated_call():
            assert 0 < P.open(0, 1)
            # assert 0 <= P.closed(1, 2)
            # assert 0 <= P.open(0, 1)
            # assert 0 <= P.closed(-1, 1)
            # assert not (0 <= P.closed(-2, -1))
            # assert not (0 <= P.open(-1, 0))

        with pytest.deprecated_call():
            assert P.closed(1, 2) > 0

        with pytest.deprecated_call():
            assert not (P.closed(-1, 1) > 0)

        with pytest.deprecated_call():
            assert not (P.closed(0, 1) > 0)

        with pytest.deprecated_call():
            assert P.open(0, 1) > 0

        with pytest.deprecated_call():
            assert P.closed(1, 2) >= 0

        with pytest.deprecated_call():
            assert P.open(0, 1) >= 0

        with pytest.deprecated_call():
            assert not (P.closed(-1, 1) >= 0)

        with pytest.deprecated_call():
            assert not (P.closed(-2, -1) >= 0)

        with pytest.deprecated_call():
            assert not (P.open(-1, 0) >= 0)

        with pytest.deprecated_call():
            assert not (0 < P.empty())

        with pytest.deprecated_call():
            assert not (0 <= P.empty())

        with pytest.deprecated_call():
            assert not (0 > P.empty())

        with pytest.deprecated_call():
            assert not (0 >= P.empty())

        with pytest.deprecated_call():
            assert not (P.empty() < 0)

        with pytest.deprecated_call():
            assert not (P.empty() <= 0)

        with pytest.deprecated_call():
            assert not (P.empty() > 0)

        with pytest.deprecated_call():
            assert not (P.empty() >= 0)


class TestIntervalContainment:
    def test_with_values(self):
        assert 1 in P.closed(0, 2)
        assert 1 in P.closed(1, 2)
        assert 1 in P.closed(0, 1)

        assert 1 in P.open(0, 2)
        assert 1 not in P.open(0, 1)
        assert 1 not in P.open(1, 2)

        assert 1 in P.closed(0, 2) | P.closed(4, 6) | P.closed(8, 10)
        assert 5 in P.closed(0, 2) | P.closed(4, 6) | P.closed(8, 10)
        assert 10 in P.closed(0, 2) | P.closed(4, 6) | P.closed(8, 10)

        assert -1 not in P.closed(0, 2) | P.closed(4, 6) | P.closed(8, 10)
        assert 3 not in P.closed(0, 2) | P.closed(4, 6) | P.closed(8, 10)
        assert 7 not in P.closed(0, 2) | P.closed(4, 6) | P.closed(8, 10)
        assert 11 not in P.closed(0, 2) | P.closed(4, 6) | P.closed(8, 10)

    @parametrize_pinf
    @parametrize_ninf
    def test_with_infinities(self, pinf, ninf):
        assert 1 in P.closed(ninf, pinf)
        assert 1 in P.closed(ninf, 1)
        assert 1 in P.closed(1, pinf)
        assert 1 not in P.closed(ninf, 0)
        assert 1 not in P.closed(2, pinf)

        assert P.inf not in P.closed(ninf, pinf)
        assert -P.inf not in P.closed(ninf, pinf)

        assert P.inf not in P.closed(0, 1)

    @parametrize_pinf
    @parametrize_ninf
    def test_with_empty(self, pinf, ninf):
        assert 1 not in P.empty()
        assert pinf not in P.empty()
        assert ninf not in P.empty()

    @parametrize_pinf
    @parametrize_ninf
    def test_with_intervals(self, pinf, ninf):
        assert P.closed(1, 2) in P.closed(0, 3)
        assert P.closed(1, 2) in P.closed(1, 2)
        assert P.open(1, 2) in P.closed(1, 2)
        assert P.closed(1, 2) not in P.open(1, 2)
        assert P.closed(0, 1) not in P.closed(1, 2)
        assert P.closed(0, 2) not in P.closed(1, 3)
        assert P.closed(ninf, pinf) in P.closed(ninf, pinf)
        assert P.closed(0, 1) in P.closed(ninf, pinf)
        assert P.closed(ninf, pinf) not in P.closed(0, 1)
        assert P.singleton(0) | P.singleton(5) in P.closed(0, 5)
        assert P.singleton(0) | P.singleton(5) in P.closed(0, 1) | P.closed(4, 5)

        # https://github.com/AlexandreDecan/portion/issues/28
        assert P.closed(5, 6) not in P.closed(1, 2) | P.closed(3, 4)
        assert P.singleton(0) | P.singleton(6) not in P.closed(0, 1) | P.closed(4, 5)

    def test_with_unions(self):
        assert P.closed(0, 1) | P.closed(2, 3) in P.closed(0, 4)
        assert P.closed(0, 1) | P.closed(2, 3) in P.closed(0, 1) | P.closed(2, 3)
        assert P.closed(0, 1) | P.closed(2, 3) in P.closed(0, 0) | P.closed(0, 1) | P.closed(2, 3)

        assert P.closed(0, 1) | P.closed(2, 3) not in P.closed(0, 2)
        assert P.closed(0, 1) | P.closed(2, 3) not in P.closed(0, 1) | P.closedopen(2, 3)
        assert P.closed(0, 1) | P.closed(2, 3) not in P.closed(0, 1) | P.closedopen(2, 3) | P.openclosed(3, 4)

    def test_with_empty_intervals(self):
        assert P.empty() in P.closed(0, 3)
        assert P.empty() in P.empty()
        assert P.closed(0, 0) not in P.empty()
        assert P.singleton(0) | P.singleton(1) not in P.empty()

    def test_proxy_method(self):
        i1, i2 = P.closed(0, 1), P.closed(2, 3)
        assert (1 in i1) == i1.contains(1)
        assert (i1 in i2) == i2.contains(i1)

    def test_issue_41(self):
        # https://github.com/AlexandreDecan/portion/issues/41
        assert P.empty() in P.closed(0, 1)
        assert P.empty() in P.closed(0, 1) | P.closed(2, 3)


class TestIntervalIntersection:
    def test_with_itself(self):
        assert P.closed(0, 1) & P.closed(0, 1) == P.closed(0, 1)
        assert P.closed(0, 1) & P.open(0, 1) == P.open(0, 1)
        assert P.openclosed(0, 1) & P.closedopen(0, 1) == P.open(0, 1)

    def test_with_adjacent(self):
        assert P.closed(0, 2) & P.closed(2, 4) == P.singleton(2)
        assert P.open(0, 2) & P.open(2, 4) == P.empty()

    def test_with_containment(self):
        assert P.closed(0, 4) & P.closed(2, 3) == P.closed(2, 3)
        assert P.closed(0, 4) & P.closed(0, 3) == P.closed(0, 3)
        assert P.closed(0, 4) & P.open(2, 3) == P.open(2, 3)
        assert P.open(0, 4) & P.closed(2, 3) == P.closed(2, 3)
        assert P.open(0, 4) & P.closed(3, 4) == P.closedopen(3, 4)

    def test_with_overlap(self):
        assert P.closed(0, 3) & P.closed(2, 4) == P.closed(2, 3)
        assert P.open(0, 3) & P.closed(2, 4) == P.closedopen(2, 3)

    def test_with_union(self):
        assert (P.closed(0, 2) | P.closed(4, 6)) & (P.closed(0, 1) | P.closed(4, 5)) == P.closed(0, 1) | P.closed(4, 5)
        assert (P.closed(0, 2) | P.closed(4, 6)) & (P.closed(-1, 1) | P.closed(3, 6)) == P.closed(0, 1) | P.closed(4, 6)
        assert (P.closed(0, 2) | P.closed(4, 6)) & (P.closed(1, 4) | P.singleton(5)) == P.closed(1, 2) | P.singleton(4) | P.singleton(5)

    def test_empty(self):
        assert (P.closed(0, 1) & P.closed(2, 3)).empty
        assert P.closed(0, 1) & P.empty() == P.empty()

    def test_proxy_method(self):
        i1, i2 = P.closed(0, 1), P.closed(2, 3)
        assert i1 & i2 == i1.intersection(i2)

    def test_with_invalid_type(self):
        with pytest.raises(TypeError):
            P.closed(0, 1) & 1


class TestIntervalUnion:
    def test_atomic(self):
        assert P.closed(1, 2) | P.closed(1, 2) == P.closed(1, 2)
        assert P.closed(1, 4) | P.closed(2, 3) == P.closed(1, 4)
        assert P.closed(1, 2) | P.closed(2, 3) == P.closed(2, 3) | P.closed(1, 2)
        assert P.closed(1, 2) | P.closed(3, 4) == P.closed(1, 2) | P.closed(3, 4)

    def test_with_itself(self):
        assert P.closed(1, 2) | P.closed(1, 2) == P.closed(1, 2)
        assert P.open(1, 2) | P.closed(1, 2) == P.closed(1, 2)
        assert P.closedopen(1, 2) | P.openclosed(1, 2) == P.closed(1, 2)

    def test_with_containment(self):
        assert P.closed(1, 4) | P.closed(2, 3) == P.closed(1, 4)
        assert P.open(1, 4) | P.closed(2, 3) == P.open(1, 4)

    def test_with_overlap(self):
        assert P.closed(1, 3) | P.closed(2, 4) == P.closed(1, 4)

    def test_with_adjacent(self):
        assert P.closed(1, 2) | P.closed(2, 3) == P.closed(1, 3)
        assert P.closed(1, 2) | P.open(2, 3) == P.closedopen(1, 3)
        assert P.open(1, 2) | P.closed(2, 3) == P.openclosed(1, 3)
        assert P.open(1, 3) | P.open(2, 4) == P.open(1, 4)
        assert P.closedopen(1, 2) | P.closed(2, 3) == P.closed(1, 3)
        assert P.open(1, 2) | P.closed(2, 4) == P.openclosed(1, 4)

    def test_with_disjoint(self):
        assert P.closed(1, 2) | P.closed(3, 4) != P.closed(1, 4)
        assert (P.closed(1, 2) | P.closed(3, 4) | P.closed(2, 3)).atomic
        assert P.closed(1, 2) | P.closed(3, 4) | P.closed(2, 3) == P.closed(1, 4)
        assert P.closed(1, 2) | P.closed(0, 4) == P.closed(0, 4)

        assert (P.closed(0, 1) | P.closed(2, 3) | P.closed(1, 2)).atomic
        assert P.closed(0, 1) | P.closed(2, 3) | P.closed(1, 2) == P.closed(0, 3)

    def test_with_empty(self):
        assert P.closed(0, 1) | P.empty() == P.closed(0, 1)

    def test_issue_12(self):
        # https://github.com/AlexandreDecan/python-intervals/issues/12
        assert P.open(0, 2) | P.closed(0, 2) == P.closed(0, 2)
        assert P.open(0, 2) | P.closed(1, 2) == P.openclosed(0, 2)
        assert P.open(0, 2) | P.closed(0, 1) == P.closedopen(0, 2)

        assert P.closed(0, 2) | P.open(0, 2) == P.closed(0, 2)
        assert P.closed(1, 2) | P.open(0, 2) == P.openclosed(0, 2)
        assert P.closed(0, 1) | P.open(0, 2) == P.closedopen(0, 2)

        assert P.closed(0, 2) | P.singleton(2) == P.closed(0, 2)
        assert P.closedopen(0, 2) | P.singleton(2) == P.closed(0, 2)
        assert P.openclosed(0, 2) | P.singleton(2) == P.openclosed(0, 2)
        assert P.openclosed(0, 2) | P.singleton(0) == P.closed(0, 2)

        assert P.singleton(2) | P.closed(0, 2) == P.closed(0, 2)
        assert P.singleton(2) | P.closedopen(0, 2) == P.closed(0, 2)
        assert P.singleton(2) | P.openclosed(0, 2) == P.openclosed(0, 2)
        assert P.singleton(0) | P.openclosed(0, 2) == P.closed(0, 2)

    def test_issue_13(self):
        # https://github.com/AlexandreDecan/python-intervals/issues/13
        assert P.closed(1, 1) | P.openclosed(1, 2) == P.closed(1, 2)
        assert P.openclosed(1, 2) | P.closed(1, 1) == P.closed(1, 2)
        assert P.closed(0, 1) | P.openclosed(1, 2) == P.closed(0, 2)
        assert P.openclosed(1, 2) | P.closed(0, 1) == P.closed(0, 2)

        assert P.openclosed(1, 2) | P.closed(1, 1) == P.closed(1, 2)
        assert P.closed(1, 1) | P.openclosed(1, 2) == P.closed(1, 2)
        assert P.openclosed(1, 2) | P.closed(0, 1) == P.closed(0, 2)
        assert P.closed(0, 1) | P.openclosed(1, 2) == P.closed(0, 2)

    def test_issue_38(self):
        # https://github.com/AlexandreDecan/portion/issues/38
        assert P.open(1, 2) | P.open(2, 3) | P.singleton(2) == P.open(1, 3)
        assert P.open(2, 3) | P.open(1, 2) | P.singleton(2) == P.open(1, 3)

        assert P.open(1, 2) | P.singleton(2) | P.open(2, 3) == P.open(1, 3)
        assert P.open(2, 3) | P.singleton(2) | P.open(1, 2) == P.open(1, 3)

        assert P.singleton(2) | P.open(2, 3) | P.open(1, 2) == P.open(1, 3)
        assert P.singleton(2) | P.open(1, 2) | P.open(2, 3) == P.open(1, 3)

    def test_proxy_method(self):
        i1, i2 = P.closed(0, 1), P.closed(2, 3)
        assert i1 | i2 == i1.union(i2)

    def test_with_invalid_type(self):
        with pytest.raises(TypeError):
            P.closed(0, 1) | 1


class TestIntervalComplement:
    @parametrize_pinf
    @parametrize_ninf
    def test_singleton(self, pinf, ninf):
        assert ~P.singleton(0) == P.open(ninf, 0) | P.open(0, pinf)
        assert ~(P.open(ninf, 0) | P.open(0, pinf)) == P.singleton(0)

    @parametrize_pinf
    @parametrize_ninf
    def test_nonempty(self, pinf, ninf):
        assert ~P.closed(1, 2) == P.open(ninf, 1) | P.open(2, pinf)
        assert ~P.open(1, 2) == P.openclosed(ninf, 1) | P.closedopen(2, pinf)

    @parametrize_pinf
    @parametrize_ninf
    def test_union(self, pinf, ninf):
        assert ~(P.singleton(0) | P.singleton(5) | P.singleton(10)) == P.open(ninf, 0) | P.open(0, 5) | P.open(5, 10) | P.open(10, pinf)
        assert ~(P.open(0, 1) | P.closed(2, 3) | P.open(4, 5)) == P.openclosed(ninf, 0) | P.closedopen(1, 2) | P.openclosed(3, 4) | P.closedopen(5, pinf)

    @pytest.mark.parametrize('i', [P.closed(0, 1), P.open(0, 1), P.openclosed(0, 1), P.closedopen(0, 1)])
    def test_identity(self, i):
        for interval in i:
            assert ~(~interval) == interval

    @parametrize_pinf
    @parametrize_ninf
    def test_empty(self, pinf, ninf):
        assert ~P.open(1, 1) == P.open(ninf, pinf)
        assert (~P.closed(ninf, pinf)).empty
        assert ~P.empty() == P.open(ninf, pinf)

    def test_proxy_method(self):
        i1, i2 = P.closed(0, 1), P.closed(2, 3)
        assert ~i1 == i1.complement()
        assert ~i2 == i2.complement()


class TestIntervalDifference:
    @pytest.mark.parametrize('i', [P.closed(0, 1), P.open(0, 1), P.openclosed(0, 1), P.closedopen(0, 1), P.empty(), P.singleton(0)])
    def test_with_itself(self, i):
        assert i - i == P.empty()

    def test_with_disjoint(self):
        assert P.closed(0, 1) - P.closed(2, 3) == P.closed(0, 1)
        assert P.closed(0, 4) - P.empty() == P.closed(0, 4)
        assert P.empty() - P.closed(0, 4) == P.empty()

    def test_with_smaller(self):
        assert P.closed(0, 4) - P.closed(2, 3) == P.closedopen(0, 2) | P.openclosed(3, 4)
        assert P.closed(1, 4) - P.closed(1, 3) == P.openclosed(3, 4)
        assert P.closed(1, 4) - P.closed(2, 4) == P.closedopen(1, 2)
        assert P.closed(0, 4) - P.open(1, 2) == P.closed(0, 1) | P.closed(2, 4)
        assert P.closed(0, 2) - P.open(0, 2) == P.singleton(0) | P.singleton(2)

    def test_with_larger(self):
        assert P.closed(0, 2) - P.closed(0, 4) == P.empty()
        assert P.closed(0, 2) - P.closed(-2, 2) == P.empty()
        assert P.closed(0, 2) - P.closed(-2, 4) == P.empty()
        assert P.open(0, 2) - P.closed(0, 2) == P.empty()

    def test_with_overlap(self):
        assert P.closed(0, 2) - P.closed(1, 3) == P.closedopen(0, 1)
        assert P.closed(0, 2) - P.open(1, 3) == P.closed(0, 1)
        assert P.closed(0, 2) - P.closed(-2, 1) == P.openclosed(1, 2)
        assert P.closed(0, 2) - P.open(-2, 1) == P.closed(1, 2)

    def test_proxy_method(self):
        i1, i2 = P.closed(0, 1), P.closed(2, 3)
        assert i1 - i2 == i1.difference(i2)

    def test_with_invalid_type(self):
        with pytest.raises(TypeError):
            P.closed(0, 1) - 1


class TestIntervalIteration:
    def test_length(self):
        i1 = P.closed(10, 10) | P.closed(5, 6) | P.closed(7, 8) | P.closed(8, 9)
        assert len(i1) == 3

    def test_containment(self):
        i1 = P.closed(10, 10) | P.closed(5, 6) | P.closed(7, 8) | P.closed(8, 9)
        for i in i1:
            assert i in i1

    def test_order(self):
        i1 = P.closed(10, 10) | P.closed(5, 6) | P.closed(7, 8) | P.closed(8, 9)
        assert sorted(i1, key=lambda i: i.lower) == list(i1)
        assert sorted(i1, key=lambda i: i.upper) == list(i1)

    def test_indexes(self):
        i1 = P.closed(10, 10) | P.closed(5, 6) | P.closed(7, 8) | P.closed(8, 9)
        assert i1[0] == P.closed(5, 6)
        assert i1[1] == P.closed(7, 9)
        assert i1[2] == P.closed(10, 10)
        assert i1[-1] == P.closed(10, 10)

    def test_slices(self):
        items = [P.closed(5, 6), P.closed(7, 9), P.singleton(10)]
        interval = P.Interval(*items)
        assert interval[:] == P.Interval(*items)
        assert interval[:2] == P.Interval(*items[:2])
        assert interval[::-1] == P.Interval(*items[::-1])
        assert interval[::2] == P.Interval(*items[::2])

    def test_missing_index(self):
        i1 = P.closed(10, 10) | P.closed(5, 6) | P.closed(7, 8) | P.closed(8, 9)
        with pytest.raises(IndexError):
            i1[3]

    def test_empty(self):
        assert len(P.empty()) == 0
        assert list(P.empty()) == []
        with pytest.raises(IndexError):
            P.empty()[0]
