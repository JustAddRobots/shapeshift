import bpy
from datetime import datetime
from datetime import timezone
from bpy.types import Operator
from bpy.types import Panel

bl_info = {
    "name": "Prepare Unwrap",
    "description": "Tools for Preparing Meshes for UV Unwrap",
    "author": "Roderick Constance",
    "version": (0, 1, 0),
    "blender": (2, 80, 0),
    "warning": "",
    "support": 'TESTING',
    "category": 'Mesh'
}

# ---> START Panel


class PrepUnwrapPanel(Panel):
    """Prep Mesh Unwrap"""
    bl_label = "Prepare Mesh Unwrap"
    bl_idname = "VIEW3D_PT_prep_unwrap"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "shapeshift"

    def draw(self, context):
        layout = self.layout
        layout.operator(PrepUnwrap.bl_idname, text="Prepare")

# <--- END Panel
# ---> START Operators


def get_timestamp():
    """Get ISO formatted timestamp.

    Args:
        None

    Returns:
        timestamp (str): ISO formatted timestamp.
    """
    timestamp = datetime.now(timezone.utc).astimezone().isoformat()
    return timestamp


def create_collection(col_name):
    """Create a collection.

    Args:
        col_name (str): Name of collection.

    Returns:
        col (bpy.types.Collection): Created collection.
    """
    col = bpy.data.collections.new(col_name)
    bpy.context.scene.collection.children.link(col)
    return col


def get_mesh_collections(**kwargs):
    """Get all collections from which to prepare static meshes for unwrap/export.

    Args:
        None

    Kwargs:
        prefix (str): Prefix for collections. Default is "SM_" convention.

    Returns:
        mesh_collections (list): Collections to export.
    """
    prefix = kwargs.setdefault("prefix", "SM_")
    mesh_collections = [
        col for col in bpy.data.collections if col.name.startswith(prefix)
    ]
    return mesh_collections


def prep_mesh_for_unwrap(mesh_collections, export_col_name):
    """Prepare static meshes for UV unwrapping.

    Meshes inside each collection are joined, renamed to its respective
    collection name, cleaned up, and moved to the export collection.

    Args:
        mesh_collections (list): Collections containing static meshes.
        export_col_name (str): Collection into which static mesh is placed.

    Returns:
        None
    """
    clone_suffix = "TMP"
    for col in mesh_collections:
        tmp_col_name = f"{col.name}_{clone_suffix}"
        tmp_col = create_collection(tmp_col_name)
        mesh_objs = [obj for obj in col.all_objects if obj.type == 'MESH']
        cloned_meshes = clone_mesh(mesh_objs, tmp_col.name)
        joined_mesh = join_mesh(cloned_meshes, col.name)
        cleaned_mesh = clean_mesh(joined_mesh)
        move_mesh_to_collection(cleaned_mesh, export_col_name)
        remove_collection(tmp_col)
    return None


def clone_mesh(mesh_objs, col_name):
    """Clone static meshes.

    Args:
        mesh_objs (list): Meshes to clone.
        col_name (str): Collection into which meshes will be moved.

    Returns:
        cloned_meshes (list): Cloned meshes.
    """
    clone_suffix = "TMP"
    cloned_meshes = []
    for obj in mesh_objs:
        clone = obj.copy()
        clone.data = clone.data.copy()
        clone.name = f"{obj.name}_{clone_suffix}"
        cloned_meshes.append(clone)
        bpy.data.collections[col_name].objects.link(clone)
    return cloned_meshes


def join_mesh(mesh_objs, joined_name):
    """Join static meshes.

    Args:
        mesh_objs (list): Mesh objects.
        joined_name (str): Name for joined meshes.

    Returns:
        joined_obj (bpy.types.Object): Joined mesh.
    """
    bpy.ops.object.select_all(action='DESELECT')
    for obj in mesh_objs:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = mesh_objs[0]
    bpy.ops.object.join()
    joined_obj = bpy.context.selected_objects[0]
    joined_obj.name = joined_name
    return joined_obj


def clean_mesh(obj):
    """Clean up static mesh.

    Removes duplicate verticies, applies scale.

    Args:
        obj (bpy.types.Object): Mesh to clean up.

    Returns:
        obj (bpy.types.Object): Cleaned mesh.
    """
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    if bpy.context.mode == 'OBJECT':
        bpy.ops.object.editmode_toggle()
    bpy.ops.mesh.remove_doubles()
    if bpy.context.mode == 'EDIT_MESH':
        bpy.ops.object.editmode_toggle()
    bpy.ops.object.transform_apply()
    return obj


def move_mesh_to_collection(obj, export_col_name):
    """Move static mesh into export collection.

    Args:
        obj (bpy.types.Object): Mesh to move.
        export_col_name (str): Export collection name.

    Returns:
        None
    """
    for col in obj.users_collection:
        col.objects.unlink(obj)
    bpy.data.collections[export_col_name].objects.link(obj)
    return None


def remove_collection(col):
    """Remove collection.

    Args:
        col (bpy.types.Collection): Collection to remove.

    Returns:
        None
    """
    for obj in col.objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(col)
    return None


class PrepUnwrap(Operator):
    """Prep UV Unwrap"""
    bl_idname = "opr.prep_unwrap"
    bl_label = "PrepUnwrap"

    def execute(self, context):
        export_col_name = f"PREP_UNWRAP-{get_timestamp()}"
        export_col = create_collection(export_col_name)
        mesh_collections = get_mesh_collections()
        prep_mesh_for_unwrap(mesh_collections, export_col.name)
        return {'FINISHED'}


# <--- END Operators

classes = (
    PrepUnwrap,
    PrepUnwrapPanel
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.register_class(cls)


if __name__ == "__main__":
    register()
