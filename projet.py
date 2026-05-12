import bpy
import sys
import subprocess
import importlib
import numpy as np
from mathutils import Vector

# --- CONFIGURATION DES CHEMINS ---
user_packages = r"C:\Users\mathi\AppData\Roaming\Python\Python311\site-packages"
sdf_path = r"C:\Users\mathi\Desktop\Projets\S8\Geometry_Num"

if user_packages not in sys.path:
    sys.path.insert(0, user_packages)
if sdf_path not in sys.path:
    sys.path.insert(0, sdf_path)

# --- IMPORTS ---
"""
=============================================================================
BIBLIOTHÈQUE SDF (Signed Distance Functions) - LOGIQUE MÈRE
=============================================================================
STRUCTURE DU PACKAGE :
1. PRIMITIVES (primitives.py) : Contient les formules mathématiques de base 
   (Sphère, Boîte, Tore, etc.). Elles sont centrées à l'origine (0,0,0).

2. OPÉRATIONS (operations.py) : Gère les interactions entre deux formes.
   - Nettes : Union (min), Soustraction (max(a,-b)), Intersection (max).
   - Lissées : Utilise une interpolation polynomiale (k) pour fusionner les bords.

3. ARBRE CSG (csg.py) : Organise les formes en hiérarchie. Chaque "Nœud" peut être 
   une forme simple ou le résultat d'une opération/transformation. 
   La méthode .evaluate(p) parcourt tout l'arbre pour calculer la distance finale.

4. UTILITAIRES (utils.py) : Fonctions de support comme le calcul des normales 
   via le gradient numérique pour la gestion de l'ombrage.

Toutes les fonctions sont vectorisées avec NumPy pour permettre le calcul 
simultané de milliers de points (indispensable pour Marching Cubes).
=============================================================================
"""
try:
    import sdf, sdf.csg, sdf.operations, sdf.primitives

    importlib.reload(sdf.primitives)
    importlib.reload(sdf.operations)
    importlib.reload(sdf.csg)
    importlib.reload(sdf)
    from sdf import Sphere, Box, Torus, Cylinder
except ImportError:
    print("ERREUR : Le package 'sdf' est introuvable.")

# Installation automatique de scikit-image si absent (nécessaire pour Marching Cubes).
try:
    from skimage.measure import marching_cubes
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "scikit-image", "--target", user_packages])
    from skimage.measure import marching_cubes

is_updating = False


# --- UTILITAIRE DE RÉSOLUTION ---
# Permet de toujours cibler l'objet de contrôle (Empty) même si l'utilisateur
# clique sur le maillage résultant dans la vue 3D.
def resolve_active_ctrl(active):
    """Si active est un SDF_RESULT_, retourne son CTRL_ correspondant. Sinon retourne active."""
    if active is None:
        return None
    if active.name.startswith("SDF_RESULT_"):
        ctrl_name = active.name.replace("SDF_RESULT_", "")
        return bpy.data.objects.get(ctrl_name)
    if active.name.startswith("CTRL_"):
        return active
    return None


# --- LOGIQUE SDF ---

class _ScaledNode:
    """Applique un scaling non-uniforme (sx, sy, sz) à un noeud SDF unitaire.
    Divise les coordonnées par le scale avant d'évaluer, puis multiplie le résultat
    par le scale minimum pour conserver une distance approximativement correcte."""

    def __init__(self, child, scale):
        self.child = child
        self.scale = np.array(scale, dtype=float)

    def evaluate(self, p):
        p = np.asarray(p, dtype=float)
        # Déforme l'espace : divise chaque axe par son facteur de scale
        p_local = p / self.scale
        # Compense la distance (approximation — exacte seulement si scale uniforme)
        return self.child.evaluate(p_local) * self.scale.min()

    def __add__(self, other):      return _BinOp(self, other, 'union')

    def __sub__(self, other):      return _BinOp(self, other, 'sub')

    def __and__(self, other):      return _BinOp(self, other, 'intersect')

    def smooth_union(self, other, k=0.3):        return _BinOp(self, other, 'smooth_union', k)

    def smooth_subtraction(self, other, k=0.3):  return _BinOp(self, other, 'smooth_sub', k)

    def smooth_intersection(self, other, k=0.3): return _BinOp(self, other, 'smooth_inter', k)


class RotatedNode:
    """Applique une rotation + translation à un noeud SDF.
    Transforme les points dans l'espace local de l'objet avant d'évaluer."""

    def __init__(self, child, rot_inv, center):
        self.child = child
        self.rot_inv = rot_inv  # matrice 3x3 rotation inverse
        self.center = center  # position monde de l'objet

    def evaluate(self, p):
        p = np.asarray(p, dtype=float)
        # Translate vers l'origine de l'objet puis applique rotation inverse
        p_local = (p - self.center) @ self.rot_inv.T
        return self.child.evaluate(p_local)

    # Reprend les mêmes opérateurs que SDFNode pour la compatibilité
    def __add__(self, other):      return _BinOp(self, other, 'union')

    def __sub__(self, other):      return _BinOp(self, other, 'sub')

    def __and__(self, other):      return _BinOp(self, other, 'intersect')

    def smooth_union(self, other, k=0.3):        return _BinOp(self, other, 'smooth_union', k)

    def smooth_subtraction(self, other, k=0.3):  return _BinOp(self, other, 'smooth_sub', k)

    def smooth_intersection(self, other, k=0.3): return _BinOp(self, other, 'smooth_inter', k)

    def translate(self, offset):   return TranslatedNode(self, offset)


class TranslatedNode:
    """Noeud de translation simple pour RotatedNode."""

    def __init__(self, child, offset):
        self.child = child
        self.offset = np.asarray(offset, dtype=float)

    def evaluate(self, p):
        return self.child.evaluate(np.asarray(p, dtype=float) - self.offset)

    def __add__(self, other):      return _BinOp(self, other, 'union')

    def __sub__(self, other):      return _BinOp(self, other, 'sub')

    def __and__(self, other):      return _BinOp(self, other, 'intersect')

    def smooth_union(self, other, k=0.3):        return _BinOp(self, other, 'smooth_union', k)

    def smooth_subtraction(self, other, k=0.3):  return _BinOp(self, other, 'smooth_sub', k)

    def smooth_intersection(self, other, k=0.3): return _BinOp(self, other, 'smooth_inter', k)


class _BinOp:
    """Opération binaire générique entre deux noeuds."""

    def __init__(self, a, b, op, k=0.3):
        self.a, self.b, self.op, self.k = a, b, op, k

    def evaluate(self, p):
        a, b = self.a.evaluate(p), self.b.evaluate(p)
        if self.op == 'union':       return np.minimum(a, b)
        if self.op == 'sub':         return np.maximum(a, -b)
        if self.op == 'intersect':   return np.maximum(a, b)
        k = self.k
        if self.op == 'smooth_union':
            h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
            return a + (b - a) * h - k * h * (1 - h)
        if self.op == 'smooth_sub':
            h = np.clip(0.5 - 0.5 * (a + b) / k, 0, 1)
            return a + (-b - a) * h + k * h * (1 - h)
        if self.op == 'smooth_inter':
            h = np.clip(0.5 - 0.5 * (b - a) / k, 0, 1)
            return a + (b - a) * h + k * h * (1 - h)
        return np.minimum(a, b)

    def __add__(self, other):
        return _BinOp(self, other, 'union')

    def __sub__(self, other):
        return _BinOp(self, other, 'sub')

    def __and__(self, other):
        return _BinOp(self, other, 'intersect')

    def smooth_union(self, other, k=0.3):
        return _BinOp(self, other, 'smooth_union', k)

    def smooth_subtraction(self, other, k=0.3):
        return _BinOp(self, other, 'smooth_sub', k)

    def smooth_intersection(self, other, k=0.3):
        return _BinOp(self, other, 'smooth_inter', k)


# --- LOGIQUE DE CONSTRUCTION DE L'ARBRE SDF ---
# Parcourt récursivement les objets Blender (Empties) pour créer un arbre CSG
def get_node(obj):
    if not obj.name.startswith("CTRL_"):
        return None
    t = obj.get("sdf_type_enum")
    node = None
    if t:
        world_pos = obj.matrix_world.to_translation()
        s = obj.matrix_world.to_scale()
        # Rotation : on extrait la matrice rotation pure (sans échelle ni translation)
        rot = obj.matrix_world.to_quaternion().to_matrix()
        rot_inv = np.array(rot.transposed())  # rotation inverse = transposée

        if t == "BOX":
            node = Box(half_extents=(s.x, s.y, s.z))
        elif t == "TORUS":
            # Scale non-uniforme : on déforme l'espace avant d'évaluer
            node = _ScaledNode(Torus(major_radius=1.0, minor_radius=0.2), (s.x, s.y, s.z))
        elif t == "CYLINDER":
            node = _ScaledNode(Cylinder(radius=1.0, half_height=1.0), (s.x, s.z, s.y))
        else:
            # Sphere : scale non-uniforme -> ellipsoïde
            node = _ScaledNode(Sphere(radius=1.0), (s.x, s.y, s.z))

        # Applique rotation + translation via un noeud custom
        center = np.array([world_pos.x, world_pos.y, world_pos.z])
        # Pour Box et _ScaledNode le scale est déjà intégré — RotatedNode gère translation + rotation
        node = RotatedNode(node, rot_inv, center)

    children = [c for c in obj.children if c.name.startswith("CTRL_")]
    children.sort(key=lambda o: o.get("sdf_op_enum", "UNION") != "UNION")

    for child in children:
        child_node = get_node(child)
        if child_node:
            if node is None:
                node = child_node
            else:
                op = child.get("sdf_op_enum", "UNION")
                k = child.get("sdf_smooth_k", 0.5)
                if op == "SUB":
                    node = _BinOp(node, child_node, 'sub')
                elif op == "SMOOTH":
                    node = _BinOp(node, child_node, 'smooth_union', k)
                elif op == "INTERSECT":
                    node = _BinOp(node, child_node, 'intersect')
                elif op == "SMOOTH_SUB":
                    node = _BinOp(node, child_node, 'smooth_sub', k)
                elif op == "SMOOTH_INTER":
                    node = _BinOp(node, child_node, 'smooth_inter', k)
                else:
                    node = _BinOp(node, child_node, 'union')
    return node


# --- POST-TRAITEMENT DU MAILLAGE ---
# Nettoie le résultat de Marching Cubes : fusion des sommets proches (doubles)
# et application d'un lissage laplacien itératif.
def clean_mesh(obj):
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
    smooth_iter = bpy.context.scene.sdf_smooth_iter
    for _ in range(smooth_iter):
        for v in bm.verts:
            if not v.is_boundary:
                neighbors = [e.other_vert(v).co for e in v.link_edges]
                if neighbors:
                    avg = sum(neighbors, Vector()) / len(neighbors)
                    v.co = v.co.lerp(avg, 0.5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


# --- GÉNÉRATION DU MAILLAGE (REBUILD) ---
# Crée une grille de points 3D, évalue l'arbre SDF sur chaque point,
# puis extrait la surface 0 via l'algorithme Marching Cubes.
def execute_rebuild():
    global is_updating
    if is_updating:
        return None
    for o in list(bpy.context.scene.objects):
        if o.name.startswith("SDF_RESULT"):
            mesh = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            if mesh and mesh.users == 0:
                bpy.data.meshes.remove(mesh)
    roots = [o for o in bpy.context.scene.objects
             if o.name.startswith("CTRL_")
             and (o.parent is None or not o.parent.name.startswith("CTRL_"))]
    if not roots:
        return None
    is_updating = True
    try:
        res, bounds = bpy.context.scene.sdf_resolution, bpy.context.scene.sdf_bounds
        c = np.linspace(-bounds, bounds, res)
        pts = np.stack(np.meshgrid(c, c, c, indexing='ij'), axis=-1).reshape(-1, 3)
        for r in roots:
            try:
                print(f"[REBUILD] Traitement de {r.name}")
                print(f"  sdf_type_enum={r.get('sdf_type_enum')}")
                print(f"  children={[c.name for c in r.children]}")
                for child_dbg in r.children:
                    print(
                        f"    enfant {child_dbg.name}: op={child_dbg.get('sdf_op_enum')} type={child_dbg.get('sdf_type_enum')}")
                node = get_node(r)
                print(f"  node={node}")
                if not node:
                    print(f"  [SKIP] node est None")
                    continue
                grid = node.evaluate(pts).reshape(res, res, res)
                print(f"  grid min={grid.min():.3f} max={grid.max():.3f}")
                v, f, _, _ = marching_cubes(grid, level=0.0, spacing=((c[1] - c[0]),) * 3)
                v -= bounds
                print(f"  OK -> {len(v)} vertices")
                print(f"  v min={v.min(axis=0)} max={v.max(axis=0)}")
                mesh = bpy.data.meshes.new(f"Mesh_{r.name}")
                obj_res = bpy.data.objects.new(f"SDF_RESULT_{r.name}", mesh)
                bpy.context.collection.objects.link(obj_res)
                print(f"  Linke dans la scene: {obj_res.name}, users={obj_res.data.users}")
                obj_res.display_type = 'WIRE'
                obj_res.hide_select = True
                obj_res.hide_set(False)
                obj_res.hide_viewport = False
                obj_res.data.from_pydata(v.tolist(), [], f.tolist())
                obj_res.data.update()
                print(f"  Avant clean_mesh")
                clean_mesh(obj_res)
                print(f"  Apres clean_mesh -> OK")
            except Exception as e:
                import traceback
                print(f"[ERREUR] {r.name} : {e}")
                traceback.print_exc()
    finally:
        is_updating = False
    return None


# --- GESTIONNAIRES D'ÉVÉNEMENTS (HANDLERS) ---
# Le timer surveille la sélection pour empêcher de cliquer sur le maillage final.
# Le handler surveille les transformations (G,R,S) pour relancer le calcul en temps réel.
def selection_timer():
    """
    Toutes les 0.1s : désélectionne les SDF_RESULT_ et redirige vers leur CTRL_.
    C'est la clé pour que Shift+clic en viewport ne sélectionne jamais un SDF_RESULT_.
    """
    try:
        if bpy.context.mode != 'OBJECT':
            return 0.1
        changed = False
        new_active = None
        for o in list(bpy.context.selected_objects):
            if o.name.startswith("SDF_RESULT_"):
                ctrl_name = o.name.replace("SDF_RESULT_", "")
                ctrl_obj = bpy.data.objects.get(ctrl_name)
                o.select_set(False)
                if ctrl_obj:
                    ctrl_obj.select_set(True)
                    new_active = ctrl_obj
                changed = True
        if changed:
            if new_active:
                bpy.context.view_layer.objects.active = new_active
            for area in bpy.context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
    except:
        pass
    return 0.1


@bpy.app.handlers.persistent
def sdf_handler(scene, depsgraph):
    global is_updating
    if is_updating:
        return
    should_rebuild = False
    for update in depsgraph.updates:
        try:
            name = update.id.name
            if name.startswith("CTRL_") and (update.is_updated_transform or update.is_updated_geometry):
                should_rebuild = True
                break
        except:
            continue

    # Supprime les SDF_RESULT orphelins
    # Un root valide = CTRL_ sans parent CTRL_, avec soit un sdf_type_enum (primitive)
    # soit des enfants CTRL_ (groupe) — CTRL_GROUP n'a pas de sdf_type_enum !
    existing_ctrl_roots = {
        o.name for o in bpy.context.scene.objects
        if o.name.startswith("CTRL_")
           and (o.parent is None or not o.parent.name.startswith("CTRL_"))
           and (o.get("sdf_type_enum") is not None
                or any(c.name.startswith("CTRL_") for c in o.children))
    }
    for o in list(bpy.context.scene.objects):
        if not o.name.startswith("SDF_RESULT_"):
            continue
        ctrl_name = o.name.replace("SDF_RESULT_", "")
        if ctrl_name not in existing_ctrl_roots:
            mesh = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            if mesh and mesh.users == 0:
                bpy.data.meshes.remove(mesh)

    if should_rebuild:
        if not bpy.app.timers.is_registered(execute_rebuild):
            bpy.app.timers.register(execute_rebuild, first_interval=0.01)


# --- OPÉRATEURS (OUTILS) ---
# Définit les actions comme 'Ajouter une forme', 'Grouper' ou 'Dégrouper'.
class SDF_OT_Help(bpy.types.Operator):
    bl_idname = "sdf.show_help"
    bl_label = "Aide & Instructions"
    bl_description = "Afficher le guide d'utilisation"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Guide Rapide :", icon='INFO')
        layout.label(text="- Cliquez 'Ajouter' pour créer une primitive.")
        layout.label(text="- G / R / S pour déplacer, tourner, redimensionner.")
        layout.label(text="- Pour grouper : Shift+Clic sur 2 CTRL_ dans la scène.")
        layout.label(text="  Le dernier cliqué (jaune) = BASE de l'opération.")

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=420)


class SDF_OT_AddPrimitive(bpy.types.Operator):
    bl_idname = "sdf.add_primitive"
    bl_label = "Ajouter"
    bl_description = "Crée une nouvelle forme SDF contrôlable"

    def execute(self, context):
        global is_updating
        is_updating = True
        p_type = context.scene.sdf_creation_type
        bpy.ops.object.empty_add(type='CUBE', radius=0.5)
        obj = context.active_object
        obj["sdf_type_enum"] = p_type
        obj["sdf_op_enum"] = "UNION"
        obj["sdf_smooth_k"] = 0.5
        obj.name = f"CTRL_{p_type}"
        is_updating = False
        execute_rebuild()
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        return {'FINISHED'}


class SDF_OT_Group(bpy.types.Operator):
    bl_idname = "sdf.group_selection"
    bl_label = "Grouper"
    op: bpy.props.StringProperty()
    base_name: bpy.props.StringProperty()

    def execute(self, context):
        global is_updating
        sel = [o for o in context.selected_objects if o.name.startswith("CTRL_")]
        if len(sel) < 2:
            return {'CANCELLED'}
        is_updating = True
        bpy.ops.object.empty_add(type='ARROWS', radius=0.7)
        group_ctrl = context.active_object
        group_ctrl.name = "CTRL_GROUP"
        for o in sel:
            mw = o.matrix_world.copy()
            o.parent = group_ctrl
            o.matrix_world = mw
            o["sdf_op_enum"] = "UNION" if o.name == self.base_name else self.op
            o["sdf_smooth_k"] = 0.5
        is_updating = False
        # Force la mise à jour des matrices AVANT le rebuild
        # (le reparentage change les matrix_world mais Blender ne les recalcule
        #  pas immédiatement — sans ça, get_node() lit des positions incorrectes)
        bpy.context.view_layer.update()
        execute_rebuild()
        return {'FINISHED'}


class SDF_OT_Ungroup(bpy.types.Operator):
    bl_idname = "sdf.ungroup"
    bl_label = "Dégrouper"

    def execute(self, context):
        group_ctrl = context.active_object
        if not group_ctrl:
            return {'CANCELLED'}
        for child in [c for c in group_ctrl.children if c.name.startswith("CTRL_")]:
            mw = child.matrix_world.copy()
            child.parent = None
            child.matrix_world = mw
        bpy.data.objects.remove(group_ctrl, do_unlink=True)
        execute_rebuild()
        return {'FINISHED'}


# --- INTERFACE UTILISATEUR (PANEL) ---
# Gère l'affichage du menu dans la barre latérale (N) de la vue 3D.
class SDF_PT_Panel(bpy.types.Panel):
    bl_label = "SDF Logic Studio"
    bl_idname = "SDF_PT_Panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'SDF Tool'

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # FIX : on filtre la sélection pour ne garder QUE les vrais CTRL_
        # (ignore les SDF_RESULT_ même s'ils sont encore dans la sélection
        #  avant que le timer les ait nettoyés)
        ctrl_sel = [o for o in context.selected_objects if o.name.startswith("CTRL_")]

        # FIX : si l'objet actif est un SDF_RESULT_, on résout son CTRL_ correspondant
        active = resolve_active_ctrl(context.active_object)
        active_is_ctrl = active is not None and active.name.startswith("CTRL_")

        # 1. Aide
        layout.operator("sdf.show_help", icon='HELP')
        layout.separator()

        # 2. Construction
        box_add = layout.box()
        box_add.label(text="Construction", icon='MESH_CUBE')
        row = box_add.row(align=True)
        row.prop(scene, "sdf_creation_type", text="")
        row.operator("sdf.add_primitive", text="Ajouter", icon='ADD')

        # 3. Booléens
        box_op = layout.box()
        box_op.label(text="Booléens (Base = dernier sélectionné)", icon='MOD_BOOLEAN')

        if len(ctrl_sel) >= 2 and active_is_ctrl:
            box_op.prop(scene, "sdf_use_smooth", text="Mode Lissage", icon='MOD_SMOOTH')
            col = box_op.column(align=True)

            if not scene.sdf_use_smooth:
                op = col.operator("sdf.group_selection", text="Union", icon='SELECT_EXTEND')
                op.op = 'UNION';
                op.base_name = active.name

                op = col.operator("sdf.group_selection", text="Soustraction", icon='SELECT_SUBTRACT')
                op.op = 'SUB';
                op.base_name = active.name

                op = col.operator("sdf.group_selection", text="Intersection", icon='SELECT_INTERSECT')
                op.op = 'INTERSECT';
                op.base_name = active.name
            else:
                op = col.operator("sdf.group_selection", text="Union Lissée", icon='SPHERECURVE')
                op.op = 'SMOOTH';
                op.base_name = active.name

                op = col.operator("sdf.group_selection", text="Soustr. Lissée", icon='SELECT_DIFFERENCE')
                op.op = 'SMOOTH_SUB';
                op.base_name = active.name

                op = col.operator("sdf.group_selection", text="Inter. Lissée", icon='SPHERE')
                op.op = 'SMOOTH_INTER';
                op.base_name = active.name
        else:
            box_op.label(text="Sélectionnez 2 CTRL_ (Shift+Clic)", icon='INFO')
            box_op.label(text="Le dernier cliqué = BASE de l'opération", icon='MOUSE_LMB')

        # 4. Paramètres mesh
        box_mesh = layout.box()
        box_mesh.label(text="Rendu & Maillage", icon='STRANDS')
        box_mesh.prop(scene, "sdf_resolution")
        box_mesh.prop(scene, "sdf_bounds", text="Taille Scène")
        box_mesh.prop(scene, "sdf_smooth_iter", text="Lissage Mesh")

        # 5. Dégrouper
        if active_is_ctrl and "GROUP" in active.name:
            layout.separator()
            layout.operator("sdf.ungroup", icon='X')


# --- REGISTRATION ---
classes = (SDF_OT_AddPrimitive, SDF_OT_Group, SDF_OT_Ungroup, SDF_OT_Help, SDF_PT_Panel)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.sdf_creation_type = bpy.props.EnumProperty(
        items=[('SPHERE', "Sphère", ""), ('BOX', "Boîte", ""),
               ('TORUS', "Tore", ""), ('CYLINDER', "Cylindre", "")])
    bpy.types.Scene.sdf_use_smooth = bpy.props.BoolProperty(name="Lissage", default=False)
    bpy.types.Scene.sdf_resolution = bpy.props.IntProperty(
        name="Résolution", default=32, min=8, max=128,
        update=lambda s, c: execute_rebuild())
    bpy.types.Scene.sdf_bounds = bpy.props.FloatProperty(
        name="Bounds", default=5.0, min=1.0, max=20.0,
        update=lambda s, c: execute_rebuild())
    bpy.types.Scene.sdf_smooth_iter = bpy.props.IntProperty(
        name="Lissage", default=3, min=0, max=20,
        update=lambda s, c: execute_rebuild())

    bpy.app.handlers.depsgraph_update_post.append(sdf_handler)
    if not bpy.app.timers.is_registered(selection_timer):
        bpy.app.timers.register(selection_timer)


def unregister():
    if bpy.app.timers.is_registered(selection_timer):
        bpy.app.timers.unregister(selection_timer)
    if sdf_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(sdf_handler)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    try:
        unregister()
    except:
        pass
    register()
