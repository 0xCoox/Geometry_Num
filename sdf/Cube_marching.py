import bpy
import sys
import numpy as np

sys.path.append("/adhome/m/ms/mschellenbaum/Bureau/Projet_Geo_num/SDF/sdf") # Changer le nom du répertoire

from sdf import Sphere, Box, Torus
from skimage.measure import marching_cubes

# -------------------------------------------------------
# 1. Construire la scène SDF
# -------------------------------------------------------
scene = Sphere(radius=1.0) - Box(half_extents=(0.6, 0.6, 0.6))

# -------------------------------------------------------
# 2. Évaluer sur une grille 3D
# -------------------------------------------------------
resolution = 64
coords = np.linspace(-2.0, 2.0, resolution)
gx, gy, gz = np.meshgrid(coords, coords, coords, indexing='ij')
pts = np.stack([gx.ravel(), gy.ravel(), gz.ravel()], axis=-1)
grid = scene.evaluate(pts).reshape(resolution, resolution, resolution)
print(f"Grille évaluée : {grid.shape}")

# -------------------------------------------------------
# 3. Marching Cubes (scikit-image)
#    level=0.0 -> on cherche la surface où SDF = 0
# -------------------------------------------------------
verts, faces, normals, _ = marching_cubes(grid, level=0.0, spacing=(
    coords[1] - coords[0],
    coords[1] - coords[0],
    coords[1] - coords[0],
))

# Recentrer les vertices autour de l'origine
verts -= verts.mean(axis=0)
print(f"Marching Cubes : {len(verts)} vertices, {len(faces)} faces")

# -------------------------------------------------------
# 4. Créer l'objet dans Blender
# -------------------------------------------------------
if "SDF_Result" in bpy.data.objects:
    bpy.data.objects.remove(bpy.data.objects["SDF_Result"])

mesh = bpy.data.meshes.new("SDF_Result")
mesh.from_pydata(verts.tolist(), [], faces.tolist())
mesh.update()

obj = bpy.data.objects.new("SDF_Result", mesh)
bpy.context.collection.objects.link(obj)
bpy.context.view_layer.objects.active = obj
obj.select_set(True)

print("Objet affiché dans Blender !")