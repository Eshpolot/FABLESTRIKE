extends SceneTree
func _init() -> void:
	for w in ["m4", "ak", "usp", "knife"]:
		var a: Node = (load("res://assets/models/weapons/%s.glb" % w) as PackedScene).instantiate()
		var seen := {}
		for c in a.find_children("*", "MeshInstance3D", true, false):
			var mi := c as MeshInstance3D
			for s in mi.mesh.get_surface_count():
				var m := mi.mesh.surface_get_material(s) as StandardMaterial3D
				if m == null or seen.has(m):
					continue
				seen[m] = true
				print(w, " ", m.resource_name, " albedo=", m.albedo_color, " tex=", m.albedo_texture != null, " ao=", m.ao_enabled, " ao_tex=", m.ao_texture != null, " ao_ch=", m.ao_texture_channel, " metal=", m.metallic, " mtex=", m.metallic_texture != null, " rough=", m.roughness, " spec=", m.metallic_specular)
	for w in ["arms_ct", "arms_t"]:
		var a2: Node = (load("res://assets/models/chars/%s.glb" % w) as PackedScene).instantiate()
		for c in a2.find_children("*", "MeshInstance3D", true, false):
			var mi2 := c as MeshInstance3D
			var m2 := mi2.mesh.surface_get_material(0) as StandardMaterial3D
			print(w, " ", m2.resource_name, " albedo=", m2.albedo_color, " ao=", m2.ao_enabled, " metal=", m2.metallic, " rough=", m2.roughness)
	quit()
