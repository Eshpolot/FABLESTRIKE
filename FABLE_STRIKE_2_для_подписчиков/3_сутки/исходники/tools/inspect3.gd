extends SceneTree
func _init() -> void:
	for id in ["ak", "m4", "awp", "shotgun", "mac10", "mp9", "glock", "usp", "deagle", "knife", "he", "flash", "smoke", "molotov", "decoy", "c4"]:
		var s: PackedScene = load("res://assets/models/weapons/%s.glb" % id)
		var n := s.instantiate()
		var r := n.get_child(0)
		var aabb := AABB()
		var first := true
		var pts := {}
		for c in r.get_children():
			if c is MeshInstance3D:
				var a: AABB = (c as MeshInstance3D).transform * (c as MeshInstance3D).get_aabb()
				aabb = a if first else aabb.merge(a)
				first = false
			if String(c.name).begins_with("p_") or String(c.name).begins_with("mv_"):
				pts[String(c.name)] = (c as Node3D).position.snapped(Vector3(0.001, 0.001, 0.001))
		print(id, " aabb ", aabb.position.snapped(Vector3(0.001, 0.001, 0.001)), " .. ", aabb.end.snapped(Vector3(0.001, 0.001, 0.001)), " grip_r ", pts.get("p_grip_r"), " grip_l ", pts.get("p_grip_l"), " mag ", pts.get("mv_mag"), " muzzle ", pts.get("p_muzzle"), " bolt ", pts.get("mv_bolt", pts.get("mv_slide")))
		n.free()
	quit()
