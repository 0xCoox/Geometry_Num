import sys
import bpy
import numpy as np

# Dossier PARENT qui CONTIENT le dossier sdf/
sys.path.append("/adhome/m/ms/mschellenbaum/Bureau/Projet_Geo_num/SDF")

# Vérification avant d'importer
import os
chemin_sdf = "/adhome/m/ms/mschellenbaum/Bureau/Projet_Geo_num/SDF/sdf"
if os.path.exists(chemin_sdf):
    print("✓ Dossier sdf/ trouvé")
else:
    print("✗ Dossier sdf/ introuvable — vérifie le chemin")

from sdf import Sphere, Box, Torus, Cylinder, compute_normal

# --- Construire une scène SDF ---
scene = Sphere(radius=1.0) - Box(half_extents=(0.6, 0.6, 0.6))

# --- Évaluer sur une grille 3D ---
resolution = 32   # commence petit pour tester
coords = np.linspace(-2, 2, resolution)
gx, gy, gz = np.meshgrid(coords, coords, coords, indexing='ij')
pts = np.stack([gx.ravel(), gy.ravel(), gz.ravel()], axis=-1)
grid = scene.evaluate(pts).reshape(resolution, resolution, resolution)

print("✓ Module SDF importé correctement")
print(f"  Grille shape : {grid.shape}")
print(f"  Valeurs : min={grid.min():.3f}  max={grid.max():.3f}")
print(f"  Points intérieurs : {(grid < 0).sum()} / {grid.size}")