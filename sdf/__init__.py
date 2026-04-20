"""
Package Signed Distance Functions

Importer depuis ce package expose directement toutes les classes et fonctions
utiles sans avoir à connaître la structure interne des fichiers.

Exemple :
    from sdf import Sphere, Box, Torus
    from sdf import op_smooth_union
    from sdf import compute_normal
"""

from .primitives import (
    sdf_sphere,
    sdf_box,
    sdf_cylinder,
    sdf_torus,
    sdf_capsule,
    sdf_plane,
)

from .operations import (
    op_union,
    op_intersection,
    op_subtraction,
    op_smooth_union,
    op_smooth_intersection,
    op_smooth_subtraction,
)

from .csg import (
    SDFNode,
    Sphere,
    Box,
    Cylinder,
    Torus,
    Capsule,
    Plane,
    UnionNode,
    IntersectionNode,
    SubtractionNode,
    SmoothUnionNode,
    SmoothIntersectionNode,
    SmoothSubtractionNode,
    TranslateNode,
    ScaleNode,
)

from .utils import compute_normal

__all__ = [
    # Fonctions primitives brutes
    "sdf_sphere", "sdf_box", "sdf_cylinder",
    "sdf_torus", "sdf_capsule", "sdf_plane",
    # Opérations brutes
    "op_union", "op_intersection", "op_subtraction",
    "op_smooth_union", "op_smooth_intersection", "op_smooth_subtraction",
    # Arbre CSG
    "SDFNode",
    "Sphere", "Box", "Cylinder", "Torus", "Capsule", "Plane",
    "UnionNode", "IntersectionNode", "SubtractionNode",
    "SmoothUnionNode", "SmoothIntersectionNode", "SmoothSubtractionNode",
    "TranslateNode", "ScaleNode",
    # Utilitaires
    "compute_normal",
]
