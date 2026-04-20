"""
Fonctions SDF des primitives de base

Toutes les fonctions acceptent p sous deux formes :
  - un point unique : np.array([x, y, z]) -> retourne un float
  - un batch : np.array([[x,y,z], ...]) -> retourne np.array (N,)
"""

import numpy as np


def _length(v):
    """
    Norme euclidienne, compatible point unique ET batch.
      - v shape (3,) -> retourne float
      - v shape (N, 3) -> retourne array (N,)
    """
    return np.linalg.norm(v, axis=-1)


def sdf_sphere(p, radius=1.0):
    """
    SDF d'une sphère centrée à l'origine.

    Args:
        p : (3,) ou (N, 3)
        radius : float

    Returns:
        float ou (N,)
    """
    return _length(p) - radius


def sdf_box(p, half_extents=(1.0, 1.0, 1.0)):
    """
    SDF d'une boîte axe-alignée centrée à l'origine.

    Args:
        p : (3,) ou (N, 3)
        half_extents : (3,) - demi-dimensions

    Returns:
        float ou (N,)
    """
    p = np.asarray(p, dtype=float)
    half_extents = np.asarray(half_extents, dtype=float)
    q = np.abs(p) - half_extents
    outer = _length(np.maximum(q, 0.0))
    inner = np.minimum(np.amax(q, axis=-1), 0.0)
    return outer + inner


def sdf_cylinder(p, radius=1.0, half_height=1.0):
    """
    SDF d'un cylindre vertical (axe Y) centré à l'origine.

    Args:
        p : (3,) ou (N, 3)
        radius : float
        half_height : float

    Returns:
        float ou (N,)
    """
    p = np.asarray(p, dtype=float)
    xz = p[..., [0, 2]]
    r  = _length(xz) - radius
    y  = np.abs(p[..., 1]) - half_height
    d  = np.stack([r, y], axis=-1)
    outer = _length(np.maximum(d, 0.0))
    inner = np.minimum(np.amax(d, axis=-1), 0.0)
    return outer + inner


def sdf_torus(p, major_radius=1.0, minor_radius=0.25):
    """
    SDF d'un tore dans le plan XZ centré à l'origine.

    Args:
        p : (3,) ou (N, 3)
        major_radius : float - R, rayon du centre du tube
        minor_radius : float - r, rayon du tube

    Returns:
        float ou (N,)
    """
    p = np.asarray(p, dtype=float)
    xz = p[..., [0, 2]]
    q = np.stack([_length(xz) - major_radius, p[..., 1]], axis=-1)
    return _length(q) - minor_radius


def sdf_capsule(p, half_height=1.0, radius=0.25):
    """
    SDF d'une capsule verticale (axe Y) centrée à l'origine.

    Args:
        p : (3,) ou (N, 3)
        half_height : float
        radius : float

    Returns:
        float ou (N,)
    """
    p = np.asarray(p, dtype=float)
    py = np.clip(p[..., 1], -half_height, half_height)
    zeros = np.zeros_like(py)
    closest = np.stack([zeros, py, zeros], axis=-1)
    return _length(p - closest) - radius


def sdf_plane(p, normal=(0.0, 1.0, 0.0), offset=0.0):
    """
    SDF d'un plan infini.

    Args:
        p : (3,) ou (N, 3)
        normal : (3,) - normale unitaire
        offset : float

    Returns:
        float ou (N,)
    """
    p = np.asarray(p, dtype=float)
    normal = np.asarray(normal, dtype=float)
    normal = normal / np.linalg.norm(normal)
    return np.dot(p, normal) - offset
