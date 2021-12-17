import bpy
from bpy.types import Operator
from bpy.types import Panel
from bpy.types import PropertyGroup
from datetime import datetime
from datetime import timezone

bl_info = {
    "name": "Unwrap Mesh",
    "description": "Tools for UV Unwrapping",
    "author": "Roderick Constance",
    "version": (0, 1, 0),
    "blender": (2, 80, 0),
    "warning": "",
    "support": 'TESTING',
    "category": 'Mesh'
}

# ---> START Panel


class UnwrapMeshPanel(Panel):
    """Unwrap Mesh"""
    bl_label = "Unwrap Mesh"
    bl_idname = "VIEW3D_PT_unwrap_mesh"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Shapeshift"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        my_props = scene.myprops

        box = layout.box()
        col = box.column(align=True)
        title_pct = 0.3

        row = col.split(factor=title_pct, align=True)
        row.label(text="Prefix")
        row.prop(my_props, 'prefix', text="")

        row = col.split(factor=title_pct, align=True)
        row.label(text="Destination")
        row.prop(my_props, 'dest_collection', text="")

        row = col.split(factor=title_pct, align=True)
        row.label(text="")
        row.prop(my_props, 'existing', text="")

        row = col.row(align=True)
        row.operator(UnwrapMesh.bl_idname, text="Unwrap")

        row = col.split(factor=title_pct, align=True)
        row.label(text="Export Dir")
        row.prop(my_props, 'filepath', text="")

        row = col.row(align=True)
        row.operator(ExportMesh.bl_idname, text="Export")

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
    """Create an empty collection.

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
        prefix (str): Prefix for collections. Default is UE4 "SM_" convention.

    Returns:
        mesh_collections (list): Collections to export.
    """
    prefix = kwargs.setdefault("prefix", "SM_")
    mesh_collections = [
        col for col in bpy.data.collections if col.name.startswith(prefix)
    ]
    return mesh_collections


def clone_collection(collection, **kwargs):
    clone_suffix = kwargs.setdefault("suffix", "TMP")
    cloned_collection_name = f"{collection.name}_{clone_suffix}"
    cloned_collection = create_collection(cloned_collection_name)
    mesh_objs = [obj for obj in collection.all_objects if obj.type == 'MESH']
    clone_meshes(mesh_objs, cloned_collection.name)
    return cloned_collection


def flatten_collection_to_mesh(collection):
    mesh_objs = [obj for obj in collection.all_objects if obj.type == 'MESH']
    joined_mesh = join_mesh(mesh_objs, collection.name)
    cleaned_mesh = clean_mesh(joined_mesh)
    return cleaned_mesh


def make_texture_mesh(collection, dest_collection_name):
    cloned_collection = clone_collection(collection)
    mesh = flatten_collection_to_mesh(cloned_collection)
    move_mesh_to_collection(mesh, dest_collection_name)
    remove_collection(cloned_collection)
    if bpy.context.mode == 'EDIT_MESH':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    mesh.select_set(True)
    remove_uv_maps(mesh)
    unwrap_mesh(mesh)
    image = create_test_grid()
    show_image_in_UV_editor(image)
    material = assign_material(mesh)
    add_texture_to_material(image, material)
    return mesh


def clone_meshes(mesh_objs, col_name):
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
    if bpy.context.mode == 'EDIT_MESH':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    for obj in mesh_objs:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = mesh_objs[0]
    bpy.ops.object.join()
    joined_obj = bpy.context.selected_objects[0]
    joined_obj.name = joined_name.rstrip("_TMP")
    return joined_obj


def clean_mesh(obj):
    """Clean up static mesh.

    Removes duplicate verticies, applies transformations.

    Args:
        obj (bpy.types.Object): Mesh to clean up.

    Returns:
        obj (bpy.types.Object): Cleaned mesh.
    """
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    if bpy.context.mode == 'OBJECT':
        bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.remove_doubles()
    if bpy.context.mode == 'EDIT_MESH':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.transform_apply()
    return obj


def move_mesh_to_collection(obj, dest_collection_name):
    """Move static mesh into collection.

    Args:
        obj (bpy.types.Object): Mesh to move.
        dest_collection_name (str): Destination collection name.

    Returns:
        None
    """
    for col in obj.users_collection:
        col.objects.unlink(obj)
    bpy.data.collections[dest_collection_name].objects.link(obj)
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


def remove_uv_maps(mesh_obj):
    """Remove all UV maps from mesh.

    Args:
        mesh_object (bpy.types.Object): Mesh from which to remove UV maps.

    Returns:
        None
    """
    mesh_data = mesh_obj.data
    uv_maps = [uv for uv in mesh_data.uv_layers]
    while uv_maps:
        mesh_data.uv_layers.remove(uv_maps.pop())
    return None


def unwrap_mesh(mesh_obj):
    """Unwrap Mesh.

    Args:
        mesh_object (bpy.types.Object): Mesh to UV unwrap.

    Returns:
        None
    """
    bpy.context.view_layer.objects.active = mesh_obj
    if bpy.context.mode == 'OBJECT':
        bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.unwrap(method='CONFORMAL', margin=0.03)
    mesh_obj.data.uv_layers[0].name = f"UV_{mesh_obj.name}"
    return None


def create_test_grid(**kwargs):
    """Create UV test grid.

    Args:
        None

    Kwargs:
        name (str): Name of test grid image, default is "I_UV_Test_Grid".

    Returns:
        image (bpy.types.Image)
    """
    image_name = kwargs.setdefault("name", "I_UV_Test_Grid")
    image = bpy.data.images.get(image_name)
    if not image:
        bpy.ops.image.new(
            name=image_name,
            width=1024,
            height=1024,
            color=(0.0, 0.0, 0.0, 1.0),
            alpha=True,
            generated_type='UV_GRID',
            float=False,
            use_stereo_3d=False,
            tiled=False
        )
        image = bpy.data.images.get(image_name)
    return image


def show_image_in_UV_editor(image):
    """Show texture image in UV Editor.

    Args:
        image (bpy.types.Image): Image to show.

    Returns:
        None
    """
    for area in bpy.data.screens['UV Editing'].areas:
        if area.type == 'IMAGE_EDITOR':
            area.spaces.active.image = image
    return None


def delete_material(name):
    """Delete material from project.

    Args:
        material (bpy.types.Material): Material to delete.

    Returns:
        None
    """
    material = bpy.data.materials.get(name)
    if material:
        bpy.data.materials.remove(
            material,
            do_unlink=True,
            do_id_user=True,
            do_ui_user=True
        )
    return None


def delete_image(name):
    """Delete image from project.

    Args:
        image (bpy.types.Texture): Image to delete.

    Returns:
        None
    """
    image = bpy.data.images.get(name)
    if image:
        bpy.data.images.remove(
            image,
            do_unlink=True,
            do_id_user=True,
            do_ui_user=True
        )
    return None


def remove_defaults():
    """Remove the default objects created in this module."""
    for i in ("I_UV_Test_Grid", "M_UV_Test_Grid"):
        if i.startswith("I_"):
            delete_image(i)
        elif i.startswith("M_"):
            delete_material(i)
    return None


def add_texture_to_material(image, material):
    """Add image texture to material using BSDF shader node.

    Args:
        image (bpy.types.Image): Image to use in texture.
        material (bpy.types.Material): Material to which texture is applied.

    Returns:
        None
    """
    material.use_nodes = True
    texture = material.node_tree.nodes.get("Image Texture")
    if not texture:
        bsdf = material.node_tree.nodes['Principled BSDF']
        texture = material.node_tree.nodes.new('ShaderNodeTexImage')
        texture.image = image
        texture.location = (-300, 300)
        material.node_tree.links.new(
            bsdf.inputs['Base Color'],
            texture.outputs['Color']
        )
    return None


def assign_material(mesh_obj, **kwargs):
    """Assign material to mesh.

    Args:
        mesh_obj (bpy.types.Object): mesh to which material is assigned.

    Kwargs:
        material (str): Material name, default is "M_UV_Test_Grid".

    Returns:
        material (bpy.types.Material): Assigned material.
    """
    material_name = kwargs.setdefault("material", "M_UV_Test_Grid")
    material = bpy.data.materials.get(material_name)
    if not material:
        material = bpy.data.materials.new(name=material_name)

    mesh_data = mesh_obj.data
    if mesh_data.materials:
        mesh_data.materials[0] = material
    else:
        mesh_data.materials.append(material)
    return material


def export_fbx(mesh_obj, export_dir):
    export_path = f"{export_dir}/{mesh_obj.name}.fbx"
    if bpy.context.mode == 'EDIT_MESH':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = mesh_obj
    bpy.ops.export_scene.fbx(
        filepath=export_path,
        check_existing=False,
        use_selection=True,
        global_scale=1.00,
        apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_NONE',
        use_space_transform=True,
        object_types={'MESH'},
        path_mode='AUTO',
        batch_mode='OFF',
        axis_forward='-Z',
        axis_up='Y',
    )
    return None


class MyProperties(PropertyGroup):
    prefix: bpy.props.StringProperty(
        name="Prefix",
        default="SM_"
    )
    dest_collection: bpy.props.StringProperty(
        name="Destination",
        default="SHAPESHIFT"
    )
    existing: bpy.props.EnumProperty(
        items=[
            ("overwrite", "Overwrite", "Overwrite existing collection", '', 0),
            ("timestamp", "Timestamp", "Append timestamp to collection", '', 1)
        ],
        default="timestamp"
    )
    filepath: bpy.props.StringProperty(
        name="Export Folder",
        subtype='DIR_PATH',
        default="/tmp"
    )


class ExportMesh(Operator):
    bl_idname = "opr.export_mesh"
    bl_label = "ExportMesh"

#    filename_ext = "."
#    use_filter_folder = True

    def execute(self, context):
        scene = context.scene
        my_props = scene.myprops
        collection = bpy.context.collection
        mesh_objs = [obj for obj in collection.all_objects if obj.type == 'MESH']
        for obj in mesh_objs:
            export_fbx(obj, my_props.filepath)
        return {'FINISHED'}


class UnwrapMesh(Operator):
    """Unwrap Mesh"""
    bl_idname = "opr.unwrap_mesh"
    bl_label = "UnwrapMesh"

    def execute(self, context):
        scene = context.scene
        my_props = scene.myprops
        prefix = my_props.prefix
        dest_collection_name = my_props.dest_collection
        existing = my_props.existing
        if existing == "timestamp":
            dest_collection_name = "-".join(
                [dest_collection_name, get_timestamp()]
            )
        create_collection(dest_collection_name)
        mesh_collections = get_mesh_collections(prefix=prefix)
        bpy.context.window.workspace = bpy.data.workspaces['UV Editing']
        bpy.context.space_data.shading.type = 'MATERIAL'
        for collection in mesh_collections:
            make_texture_mesh(collection, dest_collection_name)

        return {'FINISHED'}


# <--- END Operators

CLASSES = (
    MyProperties,
    ExportMesh,
    UnwrapMesh,
    UnwrapMeshPanel
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.myprops = bpy.props.PointerProperty(type=MyProperties)


def unregister():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    del bpy.types.Scene.myprops


if __name__ == "__main__":
    register()
