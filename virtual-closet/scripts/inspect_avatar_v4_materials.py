"""Report the approved avatar's material nodes and image links for export work."""
import bpy


OBJECTS = (
    "avatar-v4.body",
    "avatar-v4.elvs_lady_hippy_hair",
    "avatar-v4.fitted-wispy-fringe",
    "avatar-v4.low-poly",
)

for object_name in OBJECTS:
    obj = bpy.data.objects[object_name]
    print(f"\nOBJECT {object_name}")
    print(
        " UVS",
        [
            (uv.name, uv.active, uv.active_render)
            for uv in obj.data.uv_layers
        ],
    )
    for slot in obj.material_slots:
        material = slot.material
        print(
            " MATERIAL",
            material.name,
            "surface",
            getattr(material, "surface_render_method", None),
            "diffuse",
            tuple(round(value, 4) for value in material.diffuse_color),
        )
        if not material.use_nodes:
            continue
        for node in material.node_tree.nodes:
            if node.type == "TEX_IMAGE":
                image = node.image
                print(
                    "  IMAGE",
                    node.name,
                    image.name if image else None,
                    image.filepath if image else None,
                    "colorspace",
                    image.colorspace_settings.name if image else None,
                )
            elif node.type == "BSDF_PRINCIPLED":
                for socket_name in ("Base Color", "Alpha", "Roughness", "Normal"):
                    socket = node.inputs.get(socket_name)
                    if not socket:
                        continue
                    links = [
                        f"{link.from_node.name}:{link.from_socket.name}"
                        for link in socket.links
                    ]
                    default = socket.default_value
                    try:
                        default = tuple(round(value, 4) for value in default)
                    except TypeError:
                        default = round(default, 4)
                    print("  PRINCIPLED", socket_name, "default", default, "links", links)
