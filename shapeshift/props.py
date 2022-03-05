import bpy
import numpy as np
import sys
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


class SHAPESHIFT_PT_assign_seam(bpy.types.Panel):
    """Assign Seam Panel"""
    bl_label = "Assign Seam"
    bl_idname = "shapeshift.assign_seam_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = 'UI'
    bl_category = "Shapeshift"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        my_props = scene.myprops

        col = layout.column(align=True)
        title_pct = 0.4

        row = col.split(factor=title_pct, align=True)
        row.label(text="Vertex Group")
        row.prop(my_props, 'vg_name', text="")

        row = col.row(align=True)
        row.operator(SHAPESHIFT_OT_assign_seam.bl_idname, text="Assign")


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
        title_pct = 0.4

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
        row.label(text="Thickness")
        row.prop(my_props, 'thickness', text="")

        row = col.split(factor=title_pct, align=True)
        row.label(text="UV Margin")
        row.prop(my_props, 'uv_margin', text="")

        row = col.split(factor=title_pct, align=True)
        row.label(text="Lightmap Size")
        row.prop(my_props, 'lightmap_size', text="")

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
        boolean_pct = 0.90

        row = col.split(factor=title_pct, align=True)
        row.label(text="Export Dir")
        row.prop(my_props, 'filepath', text="")

        row = col.split(factor=title_pct, align=True)
        row.label(text="Normals")
        row.prop(my_props, 'normals', text="")

        row = col.split(factor=title_pct, align=True)
        row.label(text="Pivot")
        row.prop(my_props, 'pivot', text="")

        row = col.split(factor=boolean_pct, align=True)
        row.label(text="Strip Instance Number")
        row.prop(my_props, 'strip_instnum', text="")

        row = col.split(factor=boolean_pct, align=True)
        row.label(text="Enable Scene Export")
        row.prop(my_props, 'export_scene', text="")

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


def get_selected_collections(**kwargs):
    prefix = kwargs.setdefault("prefix", "SM_")
    mesh_collections = [
        collection for selected in bpy.context.selected_ids
        if (
            isinstance(selected, bpy.types.Collection)
            and selected.name.startswith(prefix)
        )
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


def flatten_collection_to_mesh(collection, **kwargs):
    """Flatten collection to similarly-named joined and cleaned up mesh.

    Args:
        collection (bpy.types.Collection): Collection to flatten.

    Returns:
        cleaned_mesh (bpy.types.Object): Joined and cleaned mesh.
    """
    thickness = kwargs.setdefault("thickness", 0.04)
    mesh_objs = [obj for obj in collection.all_objects if obj.type == 'MESH']
    modded_objs = apply_mods(mesh_objs)
    baked_objs = bake_scale(modded_objs)
    joined_mesh = join_mesh(baked_objs, collection.name)
    solid_mesh = solidify_mesh(joined_mesh, thickness=thickness)
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
        uv_margin (float): UV island margin.

    Returns:
        mesh (bpy.types.Object): Textured mesh.
    """
    pivot = kwargs.setdefault("pivot", "bbox")
    thickness = kwargs.setdefault("thickness", 0.04)
    uv_margin = kwargs.setdefault("uv_margin", 0.02)
    lightmap_size = kwargs.setdefault("lightmap_size", 128)
    cloned_collection = clone_collection(collection)
    mesh = flatten_collection_to_mesh(cloned_collection, thickness=thickness)
    set_pivot(mesh, pivot)
    move_mesh_to_collection(mesh, dest_collection_name)
    remove_collection(cloned_collection)
    if bpy.context.mode == 'EDIT_MESH':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    mesh.select_set(True)
    remove_uv_maps(mesh)
    make_uv_map(mesh, uv_margin=uv_margin)  # Texture UVs
    make_uv_map(mesh, lightmap_size=lightmap_size)  # Lightmap UVs
    mesh = clean_mesh(mesh)  # unwrap adds vertices
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

    Kwargs:
        suffix (str): Suffix for cloned mesh.

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


def apply_mods(objs):
    """Apply all modifiers to object.

    Args:
        objs (list): Objects to apply mods.

    Reurns:
        modded_objs (list): Modded objects.
    """
    if bpy.context.mode == 'EDIT_MESH':
        bpy.ops.object.mode_set(mode='OBJECT')
    modded_objs = []
    for obj in objs:
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        for mod in obj.modifiers:
            bpy.ops.object.modifier_apply(
                modifier=mod.name,
                report=True
            )
        modded_objs.append(obj)
    return modded_objs


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


def solidify_mesh(obj, **kwargs):
    """Add solidify modifier to mesh.

    Args:
        obj (bpy.types.Object): Mesh to solidify.

    Returns:
        obj (bpy.types.Object): Solidified mesh..
    """
    thickness = kwargs.setdefault("thickness", 0.004)
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    mod = obj.modifiers.new("Solidify", 'SOLIDIFY')
    mod.solidify_mode = 'NON_MANIFOLD'
    mod.nonmanifold_thickness_mode = 'EVEN'
    mod.use_quality_normals = True
    mod.thickness = thickness
    return obj


def clean_mesh(obj):
    """Clean up static mesh.

    Removes duplicate vertices, applies transformations.

    Args:
        obj (bpy.types.Object): Mesh to clean up.

    Returns:
        obj (bpy.types.Object): Cleaned mesh.
    """
    if bpy.context.mode == 'EDIT_MESH':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply()
    if bpy.context.mode == 'OBJECT':
        bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.remove_doubles()
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


def make_uv_map(mesh_obj, **kwargs):
    """UV unwrap mesh.

    Args:
        mesh_object (bpy.types.Object): Mesh to UV unwrap.

    Kwargs:
        lightmap_size (int): Lightmap size.
        uv_margin (float): UV island margin.

    Returns:
        None
    """
    bpy.context.view_layer.objects.active = mesh_obj
    if bpy.context.mode == 'OBJECT':
        bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    if "lightmap_size" in kwargs.keys():
        prefix = "LM"
        margin = round(1.0 / kwargs["lightmap_size"] * 2, 3)
        bpy.ops.mesh.mark_seam(clear=True)
        bpy.ops.mesh.mark_seam()
    elif "uv_margin" in kwargs.keys():
        prefix = "UV"
        margin = kwargs["uv_margin"]
    layer_name = f"{prefix}_{mesh_obj.name}"
    layer = mesh_obj.data.uv_layers.get(layer_name)
    if not layer:
        layer = mesh_obj.data.uv_layers.new(name=layer_name)
    layer.active = True
    bpy.ops.uv.unwrap(
        method = 'CONFORMAL',
        margin = margin,
        correct_aspect = True,
        fill_holes = False,
    )
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


def snap_to_origin(mesh_obj):
    if bpy.context.mode == 'EDIT_MESH':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = mesh_obj
    mesh_obj.select_set(True)
    bpy.context.scene.cursor.location = Vector((0.0, 0.0, 0.0))
    bpy.ops.view3d.snap_selected_to_cursor()
    return None


def assign_seam_to_vertex_groups(target_vg_name):
    mode = bpy.context.active_object.mode
    if bpy.context.mode == 'OBJECT':
        bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_similar(type='SEAM')
    seamed_meshes = bpy.context.selected_objects
    bpy.ops.object.mode_set(mode='OBJECT')
    for mesh_obj in seamed_meshes:
        bpy.context.view_layer.objects.active = mesh_obj
        selected_verts = [v.index for v in mesh_obj.data.vertices if v.select]
        vert_groups = {}
        for vg in mesh_obj.vertex_groups:
            vert_groups[vg.name] = vg

        if target_vg_name not in vert_groups.keys():
            vert_groups[target_vg_name] = mesh_obj.vertex_groups.new(name=target_vg_name)

        bpy.ops.object.vertex_group_set_active(group=target_vg_name)
        active_index = mesh_obj.vertex_groups.active_index
        vg = mesh_obj.vertex_groups[active_index]
        bpy.ops.object.mode_set(mode='OBJECT')
        vg.add(selected_verts, 1.0, 'ADD')
    bpy.ops.object.mode_set(mode=mode)
    return None


def export_fbx(mesh_obj, export_dir, strip_instnum):
    """Export mesh.

    Args:
        mesh_obj (bpy.types.Object): Mesh to export.
        export_dir (str): Export directory (absolute).
        strip_instnum (bool): Strip Blender mesh instance suffix.

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
        mesh_smooth_type='FACE',
        path_mode='AUTO',
        batch_mode='OFF',
        axis_forward='-Z',
        axis_up='Y',
    )
    return None


def update_progress(task_name, progress):
    length = 20
    block = int(round(length * progress))
    msg = (
        f"\r{task_name}: {'#' * block + '-' * (length - block)} "
        f"{round(progress * 100, 2)}"
    )
    if progress >= 1:
        msg += " DONE\r\n"
    sys.stdout.write(msg)
    sys.stdout.flush()
    return None


class MyProperties(bpy.types.PropertyGroup):
    vg_name: bpy.props.StringProperty(
        name="Volume Group",
        default="SEAM_UV"
    )
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
    thickness: bpy.props.FloatProperty(
        name="thickness",
        default=0.004,
        min=0,
        max=1,
        precision=2,
        step=1
    )
    uv_margin: bpy.props.FloatProperty(
        name="uv_margin",
        default=0.02,
        min=0,
        max=1,
        precision=2,
        step=1
    )
    lightmap_size: bpy.props.IntProperty(
        name="lightmap_size",
        default=128,
        min=64,
        max=1024,
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
    export_scene: bpy.props.BoolProperty(
        name="Enable Scene Export",
        default=False
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


class SHAPESHIFT_OT_assign_seam(bpy.types.Operator):
    """Assign Seam"""
    bl_label = "Assign Seam"
    bl_idname = "shapeshift.assign_seam"

    def execute(self, context):
        scene = context.scene
        my_props = scene.myprops
        vg_name = my_props.vg_name
        assign_seam_to_vertex_groups(vg_name)

        self.report({'INFO'}, "Assign Complete")
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
        # source_collections = get_selected_collections(prefix=prefix)
        bpy.context.window.workspace = bpy.data.workspaces['UV Editing']
        bpy.context.space_data.shading.type = 'MATERIAL'
        for i, collection in enumerate(source_collections):
            update_progress("Texturing Meshes", i / 100.0)
            make_texture_mesh(
                collection,
                dest_collection_name,
                pivot = my_props.pivot,
                thickness = my_props.thickness,
                uv_margin = my_props.uv_margin,
                lightmap_size = my_props.lightmap_size,
            )
        self.report({'INFO'}, "Texture Complete")
        return {'FINISHED'}


class SHAPESHIFT_OT_export_mesh(bpy.types.Operator):
    """Export Mesh"""
    bl_label = "Export Mesh"
    bl_idname = "shapeshift.export_mesh"

    def execute(self, context):
        scene = context.scene
        my_props = scene.myprops
        sel_objs = bpy.context.selected_objects
        mesh_objs = []
        if len(sel_objs) > 0:
            mesh_objs = [obj for obj in sel_objs if obj.type == 'MESH']
        elif (
            bpy.context.collection.name == "Scene Collection"
            and my_props.export_scene is False
        ):
            self.report({'INFO'}, "Export Scene Collection Disabled")
        else:
            mesh_objs = [
                obj for obj in bpy.context.collection.all_objects if obj.type == 'MESH'
            ]

        if len(mesh_objs) > 0:
            collection_export = create_collection(f"EXPORT-{get_timestamp()}")
            for i, obj in enumerate(mesh_objs):
                update_progress("Exporting Meshes", i / 100.0)
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
                snap_to_origin(obj_export)
                export_fbx(
                    obj_export,
                    my_props.filepath,
                    my_props.strip_instnum
                )
            remove_collection(collection_export)
            self.report({'INFO'}, "Export Complete")
        return {'FINISHED'}


# <--- END Operators

CLASSES = (
    MyProperties,
    SHAPESHIFT_OT_texture_mesh,
    SHAPESHIFT_PT_texture_mesh,
    SHAPESHIFT_OT_export_mesh,
    SHAPESHIFT_PT_export_mesh,
    SHAPESHIFT_OT_assign_seam,
    SHAPESHIFT_PT_assign_seam,
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
