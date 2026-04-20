"""
Arbre CSG (Constructive Solid Geometry)

evaluate(p) accepte :
  - un point unique : np.array([x, y, z]) -> retourne float
  - un batch : np.array([[x,y,z], ...]) -> retourne np.array (N,)

Les transformations (Translate, Scale) utilisent p[..., :] pour
rester compatibles dans les deux cas sans aucun test de forme.
"""

import numpy as np

from .primitives import (
    sdf_sphere, sdf_box, sdf_cylinder,
    sdf_torus, sdf_capsule, sdf_plane
)
from .operations import (
    op_union, op_intersection, op_subtraction,
    op_smooth_union, op_smooth_intersection, op_smooth_subtraction
)


# =============================================================================
# CLASSE DE BASE
# =============================================================================

class SDFNode:
    """
    Nœud de base de l'arbre CSG.

    evaluate(p) :
        p peut être un point (3,) ou un batch (N, 3).
        Le retour est scalaire ou (N,) selon l'entrée.
    """

    def evaluate(self, p):
        raise NotImplementedError(f"{type(self).__name__} doit implémenter evaluate(p)")

    # --- Opérateurs booléens ---
    def __add__(self, other):
        return UnionNode(self, other)

    def __mul__(self, other):
        return IntersectionNode(self, other)
    def __sub__(self, other):
        return SubtractionNode(self, other)

    # --- Opérateurs lissés ---
    def smooth_union(self, other, k=0.3):
        return SmoothUnionNode(self, other, k)

    def smooth_intersection(self, other, k=0.3):
        return SmoothIntersectionNode(self, other, k)

    def smooth_subtraction(self, other, k=0.3):
        return SmoothSubtractionNode(self, other, k)

    # --- Transformations ---
    def translate(self, offset):
        return TranslateNode(self, offset)

    def scale(self, factor):
        return ScaleNode(self, factor)

# =============================================================================
# NŒUDS FEUILLES : PRIMITIVES
# =============================================================================

class Sphere(SDFNode):
    def __init__(self, radius=1.0):
        self.radius = radius

    def evaluate(self, p):
        return sdf_sphere(p, self.radius)

class Box(SDFNode):
    def __init__(self, half_extents=(1.0, 1.0, 1.0)):
        self.half_extents = half_extents

    def evaluate(self, p):
        return sdf_box(p, self.half_extents)

class Cylinder(SDFNode):
    def __init__(self, radius=1.0, half_height=1.0):
        self.radius = radius
        self.half_height = half_height

    def evaluate(self, p):
        return sdf_cylinder(p, self.radius, self.half_height)

class Torus(SDFNode):
    def __init__(self, major_radius=1.0, minor_radius=0.25):
        self.major_radius = major_radius
        self.minor_radius = minor_radius

    def evaluate(self, p):
        return sdf_torus(p, self.major_radius, self.minor_radius)

class Capsule(SDFNode):
    def __init__(self, half_height=1.0, radius=0.25):
        self.half_height = half_height
        self.radius = radius

    def evaluate(self, p):
        return sdf_capsule(p, self.half_height, self.radius)

class Plane(SDFNode):
    def __init__(self, normal=(0.0, 1.0, 0.0), offset=0.0):
        self.normal = normal
        self.offset = offset

    def evaluate(self, p):
        return sdf_plane(p, self.normal, self.offset)

# =============================================================================
# NŒUDS INTERNES : OPÉRATIONS NETTES
# =============================================================================

class UnionNode(SDFNode):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def evaluate(self, p):
        return op_union(self.left.evaluate(p), self.right.evaluate(p))

class IntersectionNode(SDFNode):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def evaluate(self, p):
        return op_intersection(self.left.evaluate(p), self.right.evaluate(p))

class SubtractionNode(SDFNode):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def evaluate(self, p):
        return op_subtraction(self.left.evaluate(p), self.right.evaluate(p))

# =============================================================================
# NŒUDS INTERNES : OPÉRATIONS LISSÉES
# =============================================================================

class SmoothUnionNode(SDFNode):
    def __init__(self, left, right, k=0.3):
        self.left = left
        self.right = right
        self.k = k

    def evaluate(self, p):
        return op_smooth_union(self.left.evaluate(p), self.right.evaluate(p), self.k)

class SmoothIntersectionNode(SDFNode):
    def __init__(self, left, right, k=0.3):
        self.left = left
        self.right = right
        self.k = k

    def evaluate(self, p):
        return op_smooth_intersection(self.left.evaluate(p), self.right.evaluate(p), self.k)

class SmoothSubtractionNode(SDFNode):
    def __init__(self, left, right, k=0.3):
        self.left = left
        self.right = right
        self.k = k

    def evaluate(self, p):
        return op_smooth_subtraction(self.left.evaluate(p), self.right.evaluate(p), self.k)

# =============================================================================
# NŒUDS DE TRANSFORMATION
# =============================================================================

class TranslateNode(SDFNode):
    """
    Déplace la forme.
    p[..., :] - offset fonctionne pour (3,) et (N, 3) sans condition.
    """
    def __init__(self, child, offset):
        self.child = child
        self.offset = np.asarray(offset, dtype=float)

    def evaluate(self, p):
        p = np.asarray(p, dtype=float)
        return self.child.evaluate(p - self.offset)

class ScaleNode(SDFNode):
    """
    Met à l'échelle la forme.
    La valeur est compensée par le facteur pour rester métriquement correcte.
    """
    def __init__(self, child, factor):
        self.child = child
        self.factor = factor

    def evaluate(self, p):
        p = np.asarray(p, dtype=float)
        return self.child.evaluate(p / self.factor) * self.factor