import numpy as np


def LU(M):
    """
    Decompose a square matrix M into upper and lower triangular matrices

    Implements Crout's method of LU decomposition with partial pivoting to
    decompose a matrix M such that L * U = P * M, where P is the permutation
    matrix. Also returns n as either -1 or 1 and is the determinant of P.

    Params:
        M: np.matrix of ints or floats. Square
            Matrix to be decomposed

    Returns:
        P: np.matrix of ints. Square
            Permutation matrix
        n: int. -1 or 1
            Determinant of P
        L: np.matrix of floats. Square
            Lower triangular matrix. Unity along the diagonal
        U: np.matrix of floats. Square
            Upper triangular matrix
    """
    # The algorithm used decomposed M inplace, but I try to write function with
    # minimal side effects. Therefore create a copy of M
    M = M.astype('float').copy()
    # P is permutation matrix. n is +/- 1 depending on number of swaps made
    P, n = _pivot(M)
    # We decompose a row-wise permutation of the original matrix
    M = P * M
    for j in range(len(M)):
        for i in range(j + 1):
            # Here we calculate each element of the upper matrix
            mij = M[i, j]
            if i != 0:
                for k in range(0, i):
                    mij -= M[i, k] * M[k, j]
            # Then overwrite the entry in the original matrix
            M[i, j] = mij
        for i in range(j + 1, len(M)):
            # Calculate the entries in the lower matirx
            mij = M[i, j]
            for k in range(j):
                mij -= M[i, k] * M[k, j]
            # Normalize to make the lower matrix unity along the diagonal
            mij /= M[j, j]
            M[i, j] = mij
    # We decompose M in-place since this is faster and less memory-intensive
    # so we end up with M being a combined matrix, which we need to split
    # into L and U
    return P, n, _Lower(M), _Upper(M)


def _Lower(LU):
    # Find the lower matrix from the combined matrix
    n = len(LU)
    return np.reshape(np.matrix([((LU[i, j], 0)[i < j], 1)[i == j]
                                 for i in range(n) for j in range(n)]), (n, n))


def _Upper(LU):
    # Find the upper matrix from the combined matrix
    n = len(LU)
    return np.reshape(np.matrix([(LU[i, j], 0)[i > j]
                                 for i in range(n) for j in range(n)]), (n, n))


def LU_det(n, U):
    """Calculate the determinant from the trace of the upper diagonal matrix

    Params:
        n: int. -1 or 1
            Determinant of permutation matrix
        U: Upper diagonal matrix from LU()

    Returns:
        det: float
            trace of U multiplied by n
    """
    det = n
    for i in range(len(U)):
        det *= U[i, i]
    return det


def _pivot(M):
    # Row-wise permutation to maximise the leading diagonal of *M* while
    # ensuring there are no 0's on the diagonal

    # store used rows
    used = []
    # Permutations
    P = []
    for col in range(len(M)):
        if _check_unused(col, M, used, P):
            continue
        elif _repivot_used(col, M, used, P):
            continue
        else:
            raise ValueError("Col of 0's!")
    return _matrix_P(P), _det_P(P)


def _check_unused(col, M, used, P):
    entries = []
    # find any unused rows that have a non-zero entry for col
    for row in [i for i in range(len(M)) if i not in used and
                M[i, col] != 0]:
        entries.append((M[row, col], row))
    if not entries:
        # give up if there aren't any suitable
        return False
    entries.sort(reverse=True)
    # Choose the biggest entry and put it in the appropriate places
    used.append(entries[0][1])
    try:
        # If it is replacing an existing entry
        P[col] = entries[0][1]
    except IndexError:
        # If it is at the end of the new matrix
        P.append(entries[0][1])
    return True


def _repivot_used(col, M, used, P):
    entries = []
    # find all the rows in *used* with a non-zero entry for column *col*
    # apart from the row which is already being used for *col*
    for row in used:
        if M[row, col] != 0 and P.index(row) != col:
            entries.append((M[row, col], row))
    # sort them by their value for *col* to check the most preferable values
    # first
    entries.sort(reverse=True)
    for entry in entries:
        used_col = P.index(entry[1])
        # See if you can replace the used row with an unused one
        if _check_unused(used_col, M, used, P):
            # If you have freed up the used row, you can use it where it was
            # needed
            try:
                P[col] = entry[1]
            except IndexError:
                P.append(entry[1])
            return True
    # If the used row can't be replaced by an unused row
    else:
        # See if we can use another used row to replace the one we want
        for entry in entries:
            used_col = P.index(entry[1])
            if _repivot_used(used_col, M, used, P):
                try:
                    P[col] = entry[1]
                except IndexError:
                    P.append(entry[1])
                return True
        else:
            return False


def _det_P(v):
    # Calculate permutation matrix determinant from a list of integers.
    # Because of the pivoting implementation, this is easier than keeping
    # track of the number of swaps
    n = 1
    n *= (-1) ** v[0]

    # This method adapts the general determinant method to take advantage
    # of the fact that all entries are either one or zero and there is only
    # one non-zero entry per row.
    # This performed better than a bubble sort approch in timing tests, and was
    # further optimzed using line by line timing analysis.
    for i, vi in enumerate(v[1:-1]):
        viold = vi
        for vj in v[:i + 1]:
            if vj < viold:
                vi -= 1
        n *= (-1) ** vi
    return n


def _matrix_P(P):
    # Create a permutation matrix from an ordered list of row numbers
    return np.matrix([[(0, 1)[i == P[n]] for i in range(len(P))]
                      for n in range(len(P))])


def fb_sub(L, U, P, b):
    """
    Performs forward- and back-substitution to solve simultaneous equations

    Solve a system of simultaneous equations using forward- and back-
    substitution given an upper- and lower-triangular matrix and a vector

    Designed to be called with output from LU(). Unless you have a good reason,
    it is better to use simul_solve() which does all the legwork for you.

    Params:
        L: np.matrix of ints or floats. Square
            Lower triangular matrix from LU decomposition. From LU(M)
        U: np.matrix of ints or floats. Square
            Upper triangular matrix from LU decomposition. From LU(M)
        P: np.matrix of ints. Square row-wise permutation of the identity
            Permutation matrix from LU decomposition. From LU(M) or pivot(M)
        b: np.array of ints or floats
            column vector containing the right hand side vector of the
            simultaneous equation

    Returns:
        x: np.array of floats
            array containing the solutions to the simultaneous equations
    """
    # Cast input to floats
    L = L.astype(float)
    U = U.astype(float)
    b = b.astype(float)
    # attempt to make b into a column vector if provided as a row vector.
    try:
        if b.shape[1] != 1:
            b = b.reshape(len(b), 1)
    except IndexError:
        b = b.reshape(len(b), 1)
    # permute b to match L and U
    b = P * b
    # forward substitution for y:
    y = [b[0] / L[0, 0]]
    for i in range(1, len(b)):
        yi = b[i]
        for j in range(i):
            yi -= L[i, j] * y[j]
        yi /= L[i, i]
        y.append(yi)
    # back substitution for x:
    N = len(b) - 1
    x = np.zeros((N + 1, 1), dtype='float')
    x[N, 0] = y[N] / U[N, N]
    for i in range(N - 1, -1, -1):
        xi = y[i]
        for j in range(N, i, -1):
            xi -= U[i, j] * x[j]
        xi /= U[i, i]
        x[i, 0] = xi
    return x


def simul_solve(M, b, P=None, n=None, L=None, U=None):
    """Helper function to solve simultaenous equations in matrix form

    Does not implement any new functionality, but rather takes the work
    out of solving equtations by calling the appropritate functions for you.
    Solves equations of the form M x = b for x.

    Params:
        M: np.matrix of ints or floats. Square (n, n)
            Coeffecients of variables in x in simultaenous equation
        b: np.array of ints of floats. Should have shape = (n, 1)
            Right-hand-side of equations.

    Returns:
        x: np.array of floats. Shape = (n, 1)
            Values of variables which solve simultaneous equations
    """
    try:
        if b.shape[1] != 1:
            b = b.reshape(len(b), 1)
    except IndexError:
        b = b.reshape(len(b), 1)
    M = M.astype(float)
    if P is None:
        P, n, L, U = LU(M)
    x = fb_sub(L, U, P, b)
    return x


def invert(A):
    """Finds inverse of matrix A

    Params:
        A: np.matrix. Sqaure

    Returns:
        A_inv: np.matrix. Square
    """
    A_inv = []
    P, n, L, U = LU(A)
    for i in range(len(A)):
        # ith unit vector
        b = np.array([(0, 1)[j == i] for j in range(len(A))])
        # ith column of the inverse
        A_inv.append(simul_solve(A, b, P, n, L, U).reshape(len(A)))
    # rearrange things so they're in the right order and make into a matrix
    A_inv = np.matrix(A_inv).T
    return A_inv


