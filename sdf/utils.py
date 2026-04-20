"""
Utilitaires SDF
"""

import numpy as np


def compute_normal(scene, p, eps=0.001):
    """
    Calcule la normale à la surface en p par gradient numérique.
    Fonctionne pour un point unique (3,) et un batch (N, 3).

    Args:
        scene : SDFNode
        p : (3,) ou (N, 3)
        eps : float - pas des différences finies

    Returns:
        (3,) ou (N, 3) - normales normalisées
    """
    p = np.asarray(p, dtype=float)

    # Vecteurs unitaires réutilisés pour les 6 évaluations
    ex = np.array([eps, 0.0, 0.0])
    ey = np.array([0.0, eps, 0.0])
    ez = np.array([0.0, 0.0, eps])

    dx = scene.evaluate(p + ex) - scene.evaluate(p - ex)
    dy = scene.evaluate(p + ey) - scene.evaluate(p - ey)
    dz = scene.evaluate(p + ez) - scene.evaluate(p - ez)

    # Assembler le gradient
    if p.ndim == 1:
        # Point unique : gradient est un vecteur (3,)
        n = np.array([dx, dy, dz])
    else:
        # Batch : gradient est (N, 3)
        n = np.stack([dx, dy, dz], axis=-1)

    norm = np.linalg.norm(n, axis=-1, keepdims=True)
    # Eviter la division par zéro (point trop loin de la surface)
    norm = np.where(norm < 1e-10, 1.0, norm)
    return n / norm
