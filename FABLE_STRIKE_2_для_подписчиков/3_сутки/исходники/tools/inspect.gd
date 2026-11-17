extends SceneTree
func _init() -> void:
	for p in ["res://assets/models/weapons/ak.glb", "res://assets/models/weapons/glock.glb", "res://assets/models/weapons/awp.glb", "res://assets/models/weapons/knife.glb", "res://assets/models/weapons/he.glb", "res://assets/models/weapons/c4.glb", "res://assets/models/weapons/shotgun.glb", "res://assets/models/chars/arms_ct.glb"]:
		var s: PackedScene = load(p)
		if s == null:
			print("FAIL ", p)
			continue
		var n := s.instantiate()
		print("== ", p)
		_dump(n, 0)
		n.free()
	quit()

func _dump(n: Node, d: int) -> void:
	var extra := ""
	if n is Node3D:
		var t := (n as Node3D).transform
		extra = " pos=%s" % [t.origin.snapped(Vector3(0.001, 0.001, 0.001))]
		if not t.basis.is_equal_approx(Basis.IDENTITY):
			extra += " rot=%s" % [t.basis.get_euler().snapped(Vector3(0.01, 0.01, 0.01))]
	if n is MeshInstance3D:
		var aabb := (n as MeshInstance3D).get_aabb()
		extra += " aabb=%s..%s surf=%d" % [aabb.position.snapped(Vector3(0.001, 0.001, 0.001)), aabb.end.snapped(Vector3(0.001, 0.001, 0.001)), (n as MeshInstance3D).mesh.get_surface_count()]
	if n is Skeleton3D:
		var sk := n as Skeleton3D
		extra += " bones=%d" % sk.get_bone_count()
		for i in sk.get_bone_count():
			var r := sk.get_bone_global_rest(i)
			print("      bone ", sk.get_bone_name(i), " parent ", sk.get_bone_parent(i), " o=", r.origin.snapped(Vector3(0.001, 0.001, 0.001)), " y=", r.basis.y.snapped(Vector3(0.01, 0.01, 0.01)), " z=", r.basis.z.snapped(Vector3(0.01, 0.01, 0.01)))
	print("  ".repeat(d), n.name, " [", n.get_class(), "]", extra)
	for c in n.get_children():
		_dump(c, d + 1)
