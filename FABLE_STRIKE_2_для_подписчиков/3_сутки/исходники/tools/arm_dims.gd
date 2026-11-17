extends SceneTree
func _init() -> void:
	var a: Node = (load("res://assets/models/chars/arms_ct.glb") as PackedScene).instantiate()
	var sk: Skeleton3D = a.find_child("Skeleton3D", true, false)
	var g := {}
	for i in sk.get_bone_count():
		g[sk.get_bone_name(i)] = sk.get_bone_global_rest(i)
	for n in ["forearm_r", "hand_r", "thumb1_r", "thumb2_r", "thumb3_r", "index1_r", "index2_r", "index3_r", "middle1_r", "middle2_r", "middle3_r", "pinky1_r", "pinky3_r"]:
		var t: Transform3D = g[n]
		print(n, " o=", t.origin.snapped(Vector3.ONE * 0.001), " y=", t.basis.y.snapped(Vector3.ONE * 0.01), " z=", t.basis.z.snapped(Vector3.ONE * 0.01))
	print("palm width ", (g["index1_r"].origin - g["pinky1_r"].origin).length(), " palm len ", (g["middle1_r"].origin - g["hand_r"].origin).length(), " mid finger ", (g["middle3_r"].origin - g["middle1_r"].origin).length())
	var mi: MeshInstance3D = a.find_child("*", true, false) as MeshInstance3D
	for c in a.find_children("*", "MeshInstance3D", true, false):
		print(c.name, " aabb ", (c as MeshInstance3D).get_aabb())
	quit()
