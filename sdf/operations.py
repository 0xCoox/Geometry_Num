"""
Opérations booléennes sur les SDFs

Toutes les opérations acceptent a et b sous deux formes :
  - scalaires float (point unique)
  - arrays (N,) (batch de N points)

Les opérations utilisent np.minimum / np.maximum
"""

import numpy as np


def _clamp(x, lo, hi):
    return np.clip(x, lo, hi)

def _mix(a, b, t):
    return a + (b - a) * t


# =============================================================================
# OPÉRATIONS BOOLÉENNES NETTES
# =============================================================================

def op_union(a, b):
    """
    Union : enveloppe extérieure des deux formes.

        f = min(a, b)
    """
    return np.minimum(a, b)


def op_intersection(a, b):
    """
    Intersection : zone commune aux deux formes.

        f = max(a, b)
    """
    return np.maximum(a, b)


def op_subtraction(a, b):
    """
    Soustraction : creuse a avec b.

        f = max(a, -b)
    """
    return np.maximum(a, -b)


# =============================================================================
# OPÉRATIONS LISSÉES (smooth)
# =============================================================================

def op_smooth_union(a, b, k=0.3):
    """
    Union lissée : les deux formes se fondent progressivement.
    k contrôle le rayon de la jonction.

    Args:
        a, b : float ou (N,)
        k    : float - rayon de lissage (> 0)

    Returns:
        float ou (N,)
    """
    h = _clamp(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return _mix(b, a, h) - k * h * (1.0 - h)


def op_smooth_intersection(a, b, k=0.3):
    """
    Intersection lissée : bords de la zone commune adoucis.

    Args:
        a, b : float ou (N,)
        k    : float

    Returns:
        float ou (N,)
    """
    h = _clamp(0.5 - 0.5 * (b - a) / k, 0.0, 1.0)
    return _mix(b, a, h) + k * h * (1.0 - h)


def op_smooth_subtraction(a, b, k=0.3):
    """
    Soustraction lissée : bords du creux adoucis.

    Args:
        a, b : float ou (N,)
        k    : float

    Returns:
        float ou (N,)
    """
    h = _clamp(0.5 - 0.5 * (a + b) / k, 0.0, 1.0)
    return _mix(a, -b, h) + k * h * (1.0 - h)
