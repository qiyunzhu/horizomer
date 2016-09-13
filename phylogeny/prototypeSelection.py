"""
Prototype selection

Given a set of n elements (S) and their pairwise distances in terms of a
skbio distance matrix (DM) and a given number (k << n), find the sub-set (s)
consisting of exactly k elements, such that s best represents the full set S.

Here, we define "best represents" as maximizing the sum of distances between
all points, i.e. sum {over a,b in S} DM[a,b]. This is our objective function.

This problem is known to be NP-hard [1], thus we need to resort to heuristics.
This module implements several heuristics, whose quality can be measured by
the objective function for each problem instance, since there is no global
winner. Currently implemented are:
 - prototype_selection_constructive_maxdist
 - prototype_selection_constructive_protoclass
For completeness, the exact but exponential algorithm is implemented, too.
  "prototype_selection_exhaustive"

[1] Gamez, J. Esteban, François Modave, and Olga Kosheleva.
    "Selecting the most representative sample is NP-hard:
     Need for expert (fuzzy) knowledge."
    Fuzzy Systems, 2008. FUZZ-IEEE 2008.
"""

# needed for signature type annotations, but only works for python >= 3.5
# from typing import Sequence, Tuple
from itertools import combinations

import numpy as np
import scipy as sp
from skbio.stats.distance import DistanceMatrix


def distance_sum(elements, dm):
    '''Compute the sum of pairwise distances for the given elements according to
    the given distance matrix.

    Parameters
    ----------
    elements: sequence of str
        List or elements for which the sum of distances is computed.
    dm: skbio.stats.distance.DistanceMatrix
        Pairwise distance matrix.

    Returns
    -------
    float:
        The sum of all pairwise distances of dm for IDs in elements.

    Notes
    -----
    function signature with type annotation for future use with python >= 3.5
    def distance_sum(elements: Sequence[str], dm: DistanceMatrix) -> float:
    '''

    return np.tril(dm.filter(elements).data).sum()


def prototype_selection_exhaustive(dm, num_prototypes,
                                   max_combinations_to_test=200000):
    '''Select k prototypes for given distance matrix

    Parameters
    ----------
    dm: skbio.stats.distance.DistanceMatrix
        Pairwise distances for all elements in the full set S.
    num_prototypes: int
        Number of prototypes to select for distance matrix.
        Must be >= 2, since a single prototype is useless.
        Must be smaller than the number of elements in the distance matrix,
        otherwise no reduction is necessary.
    max_combinations_to_test: int
        The maximal number of combinations to test. If exceeding, the function
        declines execution.

    Returns
    -------
    list of str
        A sequence holding selected prototypes, i.e. a sub-set of the
        elements in the distance matrix.

    Raises
    ------
    RuntimeError
        Combinatorics explode even for small instances. To save the user from
        waiting (almost) forever, this function declines execution if the
        number of combinations to test are too high,
        i.e. > max_combinations_to_test
    ValueError
        The number of prototypes to be found should be at least 2 and at most
        one element smaller than elements in the distance matrix. Otherwise, a
        ValueError is raised.

    Notes
    -----
    This is the reference implementation for an exact algorithm for the
    prototype selection problem. It has an exponential runtime and will only
    operate on small instances (< max_combinations_to_test).
    Idea: test all (n over k) combinations of selecting k elements from n with-
          out replacement. Compute the objective for each such combination and
          report the combination with maximal value.

    function signature with type annotation for future use with python >= 3.5:
    def prototype_selection_exhaustive(dm: DistanceMatrix, num_prototypes: int,
    max_combinations_to_test: int=200000) -> List[str]:
    '''
    if num_prototypes < 2:
        raise ValueError(("'num_prototypes' must be >= 2, since a single "
                          "prototype is useless."))
    if num_prototypes >= len(dm.ids):
        raise ValueError(("'num_prototypes' must be smaller than the number of"
                          " elements in the distance matrix, otherwise no "
                          "reduction is necessary."))

    num_combinations = sp.special.binom(len(dm.ids), num_prototypes)
    if num_combinations >= max_combinations_to_test:
        raise RuntimeError(("Cowardly refuse to test %i combinations. Use a "
                            "heuristic implementation for instances with more "
                            "than %i combinations instead!")
                           % (num_combinations, max_combinations_to_test))

    max_dist, max_set = -1 * np.infty, None
    for s in set(combinations(dm.ids, num_prototypes)):
        d = distance_sum(s, dm)
        if d > max_dist:
            max_dist, max_set = d, s
    return list(max_set)


def prototype_selection_constructive_maxdist(dm, num_prototypes):
    '''Heuristically select k prototypes for given distance matrix.

       Prototype selection is NP-hard. This is an implementation of a greedy
       correctness heuristic: Greedily grow the set of prototypes by adding the
       element with the largest sum of distances to the non-prototype elements.
       Start with the two elements that are globally most distant from each
       other. The set of prototypes is then constructively grown by adding the
       element showing largest sum of distances to all non-prototype elements
       in the distance matrix in each iteration.

    Parameters
    ----------
    dm: skbio.stats.distance.DistanceMatrix
        Pairwise distances for all elements in the full set S.
    num_prototypes: int
        Number of prototypes to select for distance matrix.
        Must be >= 2, since a single prototype is useless.
        Must be smaller than the number of elements in the distance matrix,
        otherwise no reduction is necessary.

    Returns
    -------
    list of str
        A sequence holding selected prototypes, i.e. a sub-set of the
        elements in the distance matrix.

    Raises
    ------
    ValueError
        The number of prototypes to be found should be at least 2 and at most
        one element smaller than elements in the distance matrix. Otherwise, a
        ValueError is raised.

    Notes
    -----
    Timing: %timeit -n 100 prototype_selection_constructive_maxdist(dm, 100)
            100 loops, best of 3: 1.43 s per loop
            where the dm holds 27,398 elements
    function signature with type annotation for future use with python >= 3.5:
    def prototype_selection_constructive_maxdist(dm: DistanceMatrix,
    num_prototypes: int) -> List[str]:
    '''
    if num_prototypes < 2:
        raise ValueError(("'num_prototypes' must be >= 2, since a single "
                          "prototype is useless."))
    if num_prototypes >= len(dm.ids):
        raise ValueError(("'num_prototypes' must be smaller than the number of"
                          " elements in the distance matrix, otherwise no "
                          "reduction is necessary."))

    # initially mark all elements as uncovered, i.e. as not being a prototype
    uncovered = np.asarray([np.True_] * dm.shape[0])

    # the first two prototypes are those elements that have the globally
    # maximal distance in the distance matrix. Mark those two elements as
    # being covered, i.e. prototypes
    distance = dm.data.max()
    res_set = list(np.unravel_index(dm.data.argmax(), dm.data.shape))
    uncovered[res_set] = np.False_
    # counts the number of already found prototypes
    num_found_prototypes = len(res_set)

    # repeat until enough prototypes have been selected:
    #  the new prototype is the element that has maximal distance sum to all
    #  non-prototype elements in the distance matrix.
    while num_found_prototypes < num_prototypes:
        max_elm_idx = (dm.data[res_set, :].sum(axis=0) * uncovered).argmax()
        uncovered[max_elm_idx] = np.False_
        num_found_prototypes += 1
        res_set.append(max_elm_idx)

    # return the ids of the selected prototype elements
    return [dm.ids[idx] for idx, x in enumerate(uncovered) if not x]


def _protoclass(dm, epsilon):
    '''Heuristically select n prototypes for a fixed epsilon radius.

       A ball is drawn around every element in the distance matrix with radius
       epsilon. The element whoes ball covers most other elements is selected
       as prototype. All such covered elements and the new prototype are
       removed for the next round. This is repeated until no balls cover more
       than its center element.
       This idea is adapted from [1] with the difference that we only deal with
       a single class.

    Parameters
    ----------
    dm: skbio.stats.distance.DistanceMatrix
        Pairwise distances for all elements in the full set S.
    epsilon: float
        Radius for the balls to be "drawn". As a rule of thumb, the larger
        epsilon, the less prototypes are found.

    Returns
    -------
    list of str
        A sequence holding selected prototypes, i.e. a sub-set of the
        elements in the distance matrix.

    Notes
    -----
    function signature with type annotation for future use with python >= 3.5:
    def _protoclass(dm: DistanceMatrix, epsilon: float) -> List[str]:

    [1] Jacob Bien and Robert Tibshirani.
        "Prototype selection for interpretable classification."
        The Annals of Applied Statistics (2011): 2403-2424.
    '''

    # is an element (column) covered by the epsilon ball of another element
    # (row)
    B = dm.data < epsilon
    # tracks which elements are covered by prototypes
    covered = [0] * dm.shape[0]
    # score is the number of other elements that falls within the epsilon ball
    scores = B.sum(axis=0)
    # found prototypes
    prototypes = []

    i = 0
    while(True):
        i += 1

        # candidate for a new prototype is the element whose epsilon ball
        # covers most other elements.
        idx_max = scores.argmax()
        if (scores[idx_max] > 0):
            # candidate is new prototype, add it to the list
            prototypes.append(idx_max)
            # which elements have been just covered by the new prototype
            justcovered = B[:, idx_max] & np.logical_not(covered)
            # update the global list of ever covered elements
            covered += justcovered
            # update the scores, i.e. which epsilon balls cover how many
            # uncovered elements
            scores -= B[justcovered, :].sum(axis=0)
        else:
            # break if no epsilon balls cover other elements
            break
    return np.array(dm.ids)[prototypes]


def prototype_selection_constructive_protoclass(dm, num_prototypes, steps=100):
    '''Heuristically select k prototypes for given distance matrix.

       Prototype selection is NP-hard. This is an implementation of a greedy
       correctness heuristic from [1]: A ball is drawn around every element in
       the distance matrix with radius epsilon. The element whoes ball covers
       most other elements is selected as prototype. All such covered elements
       and the new prototype are removed for the next round. This is repeated
       until no balls cover more than its center element.

       Unfortunately, we need to vary epsilon such that the desired number of
       prototypes is found. It is very likely that we cannot find the optimal
       value for epsilon and we try at most <steps> times.

    Parameters
    ----------
    dm: skbio.stats.distance.DistanceMatrix
        Pairwise distances for all elements in the full set S.
    num_prototypes: int
        Number of prototypes to select for distance matrix.
        Must be >= 2, since a single prototype is useless.
        Must be smaller than the number of elements in the distance matrix,
        otherwise no reduction is necessary.
    steps: int
        Maximal number of steps used to find a suitable epsilon.

    Returns
    -------
    list of str
        A sequence holding selected prototypes, i.e. a sub-set of the
        elements in the distance matrix.

    Raises
    ------
    RuntimeError
        There is a very naive optimization strategy in place to find a suitable
        epsilon to find the desired number of prototypes. It will abort after
        <steps> unsuccessful tries. Default is 100.
    ValueError
        The number of prototypes to be found should be at least 2 and at most
        one element smaller than elements in the distance matrix. Otherwise, a
        ValueError is raised.

    Notes
    -----
    Timing: %timeit -n 100 prototype_selection_constructive_maxdist(dm, 100)
            100 loops, best of 3: 1.43 s per loop
            where the dm holds 27,398 elements
    function signature with type annotation for future use with python >= 3.5:
    def prototype_selection_constructive_protoclass(dm: DistanceMatrix,
    num_prototypes: int, steps=100: int) -> List[str]:
    '''
    if num_prototypes < 2:
        raise ValueError(("'num_prototypes' must be >= 2, since a single "
                          "prototype is useless."))
    if num_prototypes >= len(dm.ids):
        raise ValueError(("'num_prototypes' must be smaller than the number of"
                          " elements in the distance matrix, otherwise no "
                          "reduction is necessary."))

    # this function is basically a search for a suitable epsilon and wraps
    # the protoclass function

    # initiate epsilon with a more or less arbitrary value
    epsilon = dm.data.mean()
    # define how much epsilon should be changes in an interation
    stepSize = 0.2

    # must epsilon be increased (+1) or decreased (-1). Initiallz no change
    # take place, thus the direction is neutral.
    direction = 0
    # list of prototypes
    prototypes = []
    for i in range(steps):
        oldDirection = direction
        oldEpsilon = epsilon

        # increase the stepsize in each iteration to converge faster
        stepSize *= 1.1
        # call the protoclass with a defined epsilon
        prototypes = _protoclass(dm, epsilon)
        # check if direction of epsilon changes has changed
        if len(prototypes) > num_prototypes:
            direction = +1
        elif len(prototypes) < num_prototypes:
            direction = -1

        #  make smaller steps on epsilion whenever the direction changed
        if direction != oldDirection:
            stepSize /= 10
        epsilon += direction * stepSize

        # end iteration when the desired number of prototypes have been found
        if len(prototypes) == num_prototypes:
            break
    if len(prototypes) < num_prototypes:
        raise RuntimeError(("Number of iterations exceeded before the desired"
                            " number of prototypes could be found."))

    return list(prototypes[:num_prototypes])
