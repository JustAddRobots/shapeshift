import bpy
from bpy.types import Operator
from bpy.types import Panel

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
    bl_category = "shapeshift"

    def draw(self, context):
        layout = self.layout
        layout.operator(UnwrapMesh.bl_idname, text="Unwrap")


# <--- END Panel
# ---> START Operators


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
            name = image_name,
            width = 1024,
            height = 1024,
            color = (0.0, 0.0, 0.0, 1.0),
            alpha = True,
            generated_type = 'UV_GRID',
            float = False,
            use_stereo_3d = False,
            tiled = False
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


class UnwrapMesh(Operator):
    """Unwrap Mesh"""
    bl_idname = "opr.unwrap_mesh"
    bl_label = "UnwrapMesh"

    def execute(self, context):
        bpy.context.window.workspace = bpy.data.workspaces['UV Editing']
        bpy.context.space_data.shading.type = 'MATERIAL'
        col = bpy.context.collection
        mesh_objs = [obj for obj in col.all_objects if obj.type == 'MESH']
        for obj in mesh_objs:
            if bpy.context.mode == 'EDIT_MESH':
                bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            remove_uv_maps(obj)
            unwrap_mesh(obj)
            image = create_test_grid()
            show_image_in_UV_editor(image)
            material = assign_material(obj)
            add_texture_to_material(image, material)
        bpy.ops.object.select_all(action='DESELECT')
        return {'FINISHED'}


# <--- END Operators

classes = (
    UnwrapMesh,
    UnwrapMeshPanel
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.register_class(cls)


if __name__ == "__main__":
    register()
