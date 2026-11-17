extends SceneTree
func _init() -> void:
	for p in ["res://assets/models/chars/ct_1.glb", "res://assets/models/chars/t_2.glb", "res://assets/models/chars/anims.glb"]:
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
	if d > 3:
		return
	var extra := ""
	if n is Skeleton3D:
		extra = " bones=%d" % (n as Skeleton3D).get_bone_count()
	if n is AnimationPlayer:
		extra = " anims=%d" % (n as AnimationPlayer).get_animation_list().size()
	print("  ".repeat(d), n.name, " [", n.get_class(), "]", extra)
	for c in n.get_children():
		_dump(c, d + 1)
