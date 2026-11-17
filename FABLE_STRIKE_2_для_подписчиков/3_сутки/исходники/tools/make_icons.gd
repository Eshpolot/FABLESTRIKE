extends Node
## Значки оружия: белый силуэт сбоку на прозрачном фоне -> assets/ui/icons/<id>.png

func _ready() -> void:
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path("res://assets/ui/icons"))
	var svp := SubViewport.new()
	svp.size = Vector2i(768, 384)
	svp.transparent_bg = true
	svp.own_world_3d = true
	svp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	svp.msaa_3d = Viewport.MSAA_4X
	add_child(svp)
	var cam := Camera3D.new()
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	svp.add_child(cam)
	var env := Environment.new()
	env.background_mode = Environment.BG_CLEAR_COLOR
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color.WHITE
	env.ambient_light_energy = 1.0
	cam.environment = env
	var mat := StandardMaterial3D.new()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	mat.albedo_color = Color.WHITE
	var ids: Array = DB.W.keys()
	ids.append("defuser")
	for id in ids:
		var path := "res://assets/models/weapons/%s.glb" % id
		if not ResourceLoader.exists(path):
			continue
		var w := (load(path) as PackedScene).instantiate() as Node3D
		svp.add_child(w)
		var aabb := AABB()
		var first := true
		for mi in w.find_children("*", "MeshInstance3D", true, false):
			var m := mi as MeshInstance3D
			m.material_override = mat
			var a: AABB = m.transform * m.get_aabb()
			aabb = a if first else aabb.merge(a)
			first = false
		var c := aabb.get_center()
		# вид на правый борт: камера справа (+X), ствол (-Z) смотрит влево на значке
		cam.position = c + Vector3(3.0, 0, 0)
		cam.look_at(c, Vector3.UP)
		var wz := aabb.size.z
		var hy := aabb.size.y
		cam.size = maxf(hy * 1.08, wz * 1.08 * 384.0 / 768.0)
		await get_tree().process_frame
		await get_tree().process_frame
		await RenderingServer.frame_post_draw
		var img := svp.get_texture().get_image()
		var used := img.get_used_rect()
		if used.size.x > 2 and used.size.y > 2:
			img = img.get_region(used.grow(4).intersection(Rect2i(Vector2i.ZERO, img.get_size())))
		img.save_png("res://assets/ui/icons/%s.png" % id)
		print("icon ", id, " ", img.get_size())
		w.queue_free()
		await get_tree().process_frame
	get_tree().quit()
