import bpy
import numpy as np
from datetime import datetime
from datetime import timezone
from mathutils import Matrix
from mathutils import Vector


bl_info = {
    "name": "Shapeshift",
    "description": "Tools for Static Mesh Export to UE4",
    "author": "Roderick Constance",
    "version": (0, 1, 0),
    "blender": (2, 80, 0),
    "warning": "",
    "support": 'TESTING',
    "category": 'Mesh'
}


class SHAPESHIFT_PT_texture_mesh(bpy.types.Panel):
    """Texture Mesh Panel"""
    bl_label = "Texture Mesh"
    bl_idname = "shapeshift.texture_mesh_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = 'UI'
    bl_category = "Shapeshift"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        my_props = scene.myprops

        col = layout.column(align=True)
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

        row = col.split(factor=title_pct, align=True)
        row.label(text="UV Margin")
        row.prop(my_props, 'margin', text="")

        row = col.split(factor=title_pct, align=True)
        row.label(text="Pivot")
        row.prop(my_props, 'pivot', text="")

        row = col.row(align=True)
        row.operator(SHAPESHIFT_OT_texture_mesh.bl_idname, text="Texture")


class SHAPESHIFT_PT_export_mesh(bpy.types.Panel):
    """Export Mesh Panel"""
    bl_label = "Export Mesh"
    bl_idname = "shapeshift.export_mesh_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = 'UI'
    bl_category = "Shapeshift"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        my_props = scene.myprops

        col = layout.column(align=True)
        title_pct = 0.3

        row = col.split(factor=title_pct, align=True)
        row.label(text="Export Dir")
        row.prop(my_props, 'filepath', text="")

        row = col.split(factor=title_pct, align=True)
        row.label(text="Normals")
        row.prop(my_props, 'normals', text="")

        row = col.split(factor=title_pct, align=True)
        row.label(text="Pivot")
        row.prop(my_props, 'pivot', text="")

        row = col.split(factor=title_pct, align=True)
        row.label(text="Strip Instance Number")
        row.prop(my_props, 'strip_instnum', text="")

        row = col.row(align=True)
        row.operator(SHAPESHIFT_OT_export_mesh.bl_idname, text="Export")


def get_timestamp():
    """Get ISO formatted timestamp.

    Args:
        None

    Returns:
        timestamp (str): ISO formatted timestamp.
    """
    timestamp = datetime.now(timezone.utc).astimezone().isoformat()
    return timestamp


def create_collection(collection_name):
    """Create an empty collection.

    Args:
        collection_name (str): Name of collection.

    Returns:
        collection (bpy.types.Collection): Created collection.
    """
    collection = bpy.data.collections.new(collection_name)
    bpy.context.scene.collection.children.link(collection)
    return collection


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
        collection for collection in bpy.data.collections
        if collection.name.startswith(prefix)
    ]
    return mesh_collections


def clone_collection(collection, **kwargs):
    """Clone collection with internal meshes intact.

    Args:
        collection (bpy.types.Collection): Collection to clone.

    Kwargs:
        suffix (str): Suffix for cloned collection.

    Returns:
        cloned_collection (bpy.types.Collection): Cloned collection.
    """
    clone_suffix = kwargs.setdefault("suffix", "TMP")
    cloned_collection_name = f"{collection.name}_{clone_suffix}"
    cloned_collection = create_collection(cloned_collection_name)
    mesh_objs = [obj for obj in collection.all_objects if obj.type == 'MESH']
    clone_meshes(mesh_objs, cloned_collection.name)
    return cloned_collection


def flatten_collection_to_mesh(collection):
    """Flatten collection to similarly-named joined and cleaned up mesh.

    Args:
        collection (bpy.types.Collection): Collection to flatten.

    Returns:
        cleaned_mesh (bpy.types.Object): Joined and cleaned mesh.
    """
    mesh_objs = [obj for obj in collection.all_objects if obj.type == 'MESH']
    baked_objs = bake_scale(mesh_objs)
    joined_mesh = join_mesh(baked_objs, collection.name)
    solid_mesh = solidify_mesh(joined_mesh)
    cleaned_mesh = clean_mesh(solid_mesh)
    return cleaned_mesh


def make_texture_mesh(collection, dest_collection_name, **kwargs):
    """Make a collection of meshes into a single mesh ready for export into UE4.

    Collections are joined, cleaned, unwrapped, and textured with a
    Blender test grid. This will allow easy visual inspection of the mesh
    before exporting.

    Args:
        collection (bpy.types.Collection): Collection to texture.
        dest_collection_name (str): Name of destination collection for mesh.

    Kwargs:
        pivot (str): Mesh pivot point.
        margin (float): UV island margin.

    Returns:
        mesh (bpy.types.Object): Textured mesh.
    """
    pivot = kwargs.setdefault("pivot", "bbox")
    margin = kwargs.setdefault("margin", 0.02)
    cloned_collection = clone_collection(collection)
    mesh = flatten_collection_to_mesh(cloned_collection)
    set_pivot(mesh, pivot)
    move_mesh_to_collection(mesh, dest_collection_name)
    remove_collection(cloned_collection)
    if bpy.context.mode == 'EDIT_MESH':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    mesh.select_set(True)
    remove_uv_maps(mesh)
    unwrap_mesh(mesh, margin)
    image = create_test_grid()
    show_image_in_UV_editor(image)
    material = assign_material(mesh)
    add_texture_to_material(image, material)
    return mesh


def clone_meshes(mesh_objs, collection_name, **kwargs):
    """Clone static meshes.

    Args:
        mesh_objs (list): Meshes to clone.
        collection_name (str): Collection into which meshes will be moved.

    Returns:
        cloned_meshes (list): Cloned meshes.
    """
    clone_suffix = kwargs.setdefault("suffix", "TMP")
    cloned_meshes = []
    for obj in mesh_objs:
        clone = obj.copy()
        clone.data = clone.data.copy()
        clone.name = f"{obj.name}_{clone_suffix}"
        cloned_meshes.append(clone)
        bpy.data.collections[collection_name].objects.link(clone)
    return cloned_meshes


def bake_scale(objs):
    """Apply scale.

    Args:
        objs (list): Objects to bake.

    Reurns:
        baked_objs (list): Baked objects.
    """
    if bpy.context.mode == 'EDIT_MESH':
        bpy.ops.object.mode_set(mode='OBJECT')
    baked_objs = []
    for obj in objs:
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.ops.object.make_single_user(
            type='SELECTED_OBJECTS',
            object=True,
            obdata=True,
            material=True,
            animation=True
        )
        bpy.ops.object.transform_apply(
            location=False,
            rotation=False,
            scale=True
        )
        baked_objs.append(obj)
    return baked_objs


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


def solidify_mesh(obj):
    """Add solidify modifier to mesh.

    Args:
        obj (bpy.types.Object): Mesh to solidify.

    Returns:
        obj (bpy.types.Object): Solidified mesh..
    """
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    mod = obj.modifiers.new("Solidify", 'SOLIDIFY')
    mod.solidify_mode = 'NON_MANIFOLD'
    mod.nonmanifold_thickness_mode = 'EVEN'
    mod.use_quality_normals = True
    mod.thickness = 0.001
    return obj


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
    for collection in obj.users_collection:
        collection.objects.unlink(obj)
    bpy.data.collections[dest_collection_name].objects.link(obj)
    return None


def remove_collection(collection):
    """Remove collection.

    Args:
        collection (bpy.types.Collection): Collection to remove.

    Returns:
        None
    """
    for obj in collection.objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(collection)
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


def unwrap_mesh(mesh_obj, uv_margin):
    """Unwrap Mesh.

    Args:
        mesh_object (bpy.types.Object): Mesh to UV unwrap.
        uv_margin (float): UV island margin.

    Returns:
        None
    """
    bpy.context.view_layer.objects.active = mesh_obj
    if bpy.context.mode == 'OBJECT':
        bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.unwrap(method='CONFORMAL', margin=uv_margin)
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


def set_normals(obj, state):
    """Set direction of normals.

    Args:
        obj (bpy.types.Object): Mesh object.
        state (str): State to set direction of normals..

    Returns:
        None
    """
    if bpy.context.mode == 'EDIT_MESH':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    if bpy.context.mode == 'OBJECT':
        bpy.ops.object.mode_set(mode='EDIT')

    if state in 'current':
        pass
    elif state in "flip":
        bpy.ops.mesh.flip_normals()
    elif state in "outside":
        bpy.ops.mesh.normals_make_consistent(inside=False)
    elif state in "inside":
        bpy.ops.mesh.normals_make_consistent(inside=True)

    if bpy.context.mode == 'EDIT_MESH':
        bpy.ops.object.mode_set(mode='OBJECT')
    return obj


def set_pivot(mesh_obj, pivot):
    """Set pivot point for mesh.

    Args:
        mesh_obj (bpy.types.Object): Mesh to set pivot.
        pivot (str): Pivot point type.

    Returns:
        None
    """
    if pivot == "bbox":  # bounding box center
        mesh_data = mesh_obj.data
        M_world = mesh_obj.matrix_world
        data = (Vector(v) for v in mesh_obj.bound_box)
        coords = np.array([Matrix() @ v for v in data])
        z = coords.T[2]
        mins = np.take(coords, np.where(z == z.min())[0], axis=0)
        v = Vector(np.mean(mins, axis=0))
        v = Matrix().inverted() @ v
        mesh_data.transform(Matrix.Translation(-v))
        M_world.translation = M_world @ v
    elif pivot == "world":  # world origin
        bpy.context.scene.cursor.location = Vector((0.0, 0.0, 0.0))
        bpy.context.scene.cursor.rotation_euler = Vector((0.0, 0.0, 0.0))
        mesh_obj.origin_set(type='ORIGIN_CURSOR')
    elif pivot == "current":
        pass
    return None


def export_fbx(mesh_obj, export_dir, strip_instnum):
    """Export mesh.

    Args:
        mesh_obj (bpy.types.Object): Mesh to export.
        export_dir (str): Export directory (absolute).

    Returns:
        None
    """
    basename = mesh_obj.name
    basename = basename.removesuffix("_EXPORT")
    if strip_instnum:
        list_ = basename.split(".")
        if len(list_) > 1 and list_[-1].isnumeric():
            basename = ".".join(list_[0:-1])
    export_path = f"{export_dir}/{basename}.fbx"
    if bpy.context.mode == 'EDIT_MESH':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = mesh_obj
    mesh_obj.select_set(True)
    bpy.ops.export_scene.fbx(
        filepath=export_path,
        check_existing=False,
        use_selection=True,
        global_scale=1.00,
        apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_NONE',
        use_space_transform=True,
        object_types={'MESH'},
        use_mesh_modifiers=True,
        path_mode='AUTO',
        batch_mode='OFF',
        axis_forward='-Z',
        axis_up='Y',
    )
    return None


class MyProperties(bpy.types.PropertyGroup):
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
    margin: bpy.props.FloatProperty(
        name="margin",
        default=0.02,
        min=0,
        max=1,
        precision=2,
        step=1
    )
    filepath: bpy.props.StringProperty(
        name="Export Folder",
        subtype='DIR_PATH',
        default="/tmp"
    )
    strip_instnum: bpy.props.BoolProperty(
        name="Strip Inst Num",
        default=True
    )
    normals: bpy.props.EnumProperty(
        items=[
            ("current", "Current", "Keep Current", '', 0),
            ("flip", "Flip", "Flip", '', 1),
            ("outside", "Outside", "All Outside", '', 2),
            ("inside", "Inside", "All Inside", '', 3),
        ],
        default="current"
    )
    pivot: bpy.props.EnumProperty(
        items=[
            ("world", "World", "World Origin", '', 0),
            ("bbox", "BBox", "Bounding Box Bottom", '', 1),
            ("current", "Current", "Keep Current", '', 2),
        ],
        default="bbox"
    )


class SHAPESHIFT_OT_export_mesh(bpy.types.Operator):
    """Export Mesh"""
    bl_label = "Export Mesh"
    bl_idname = "shapeshift.export_mesh"

    def execute(self, context):
        scene = context.scene
        my_props = scene.myprops
        sel_objs = bpy.context.selected_objects
        if len(sel_objs) > 0:
            mesh_objs = [obj for obj in sel_objs if obj.type == 'MESH']
        else:
            collection = bpy.context.collection
            mesh_objs = [
                obj for obj in collection.all_objects if obj.type == 'MESH'
            ]
        collection_export = create_collection(f"EXPORT-{get_timestamp()}")
        for obj in mesh_objs:
            clones = clone_meshes(
                [obj],
                collection_export.name,
                suffix="EXPORT",
            )
            obj_export = clones[0]
            if bpy.context.mode == 'EDIT_MESH':
                bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            bpy.context.view_layer.objects.active = obj_export
            obj_export.select_set(True)
            set_normals(obj_export, my_props.normals)
            set_pivot(obj_export, my_props.pivot)
            export_fbx(obj_export, my_props.filepath, my_props.strip_instnum)
        remove_collection(collection_export)
        return {'FINISHED'}


class SHAPESHIFT_OT_texture_mesh(bpy.types.Operator):
    """Texture Mesh"""
    bl_label = "Texture Mesh"
    bl_idname = "shapeshift.texture_mesh"

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
        source_collections = get_mesh_collections(prefix=prefix)
        bpy.context.window.workspace = bpy.data.workspaces['UV Editing']
        bpy.context.space_data.shading.type = 'MATERIAL'
        for collection in source_collections:
            make_texture_mesh(
                collection,
                dest_collection_name,
                pivot=my_props.pivot,
                margin=my_props.margin,
            )

        return {'FINISHED'}


# <--- END Operators

CLASSES = (
    MyProperties,
    SHAPESHIFT_OT_texture_mesh,
    SHAPESHIFT_PT_texture_mesh,
    SHAPESHIFT_OT_export_mesh,
    SHAPESHIFT_PT_export_mesh,
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
