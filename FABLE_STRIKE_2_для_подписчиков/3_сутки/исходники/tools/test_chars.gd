extends Node3D
## Проверка: общий набор анимаций на разных бойцах. Кадры -> user://t_<clip>.png

var names := ["ct_1", "t_1"]
var clips := ["rifle_idle_aiming", "rifle_run_forward", "rifle_walk_crouching_forward", "pistol_idle", "reloading", "rifle_death_from_the_front", "toss_grenade"]
var players: Array[AnimationPlayer] = []

func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.45, 0.47, 0.5)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.7, 0.7, 0.75)
	env.environment.ambient_light_energy = 0.8
	add_child(env)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-40, 30, 0)
	add_child(sun)
	var cam := Camera3D.new()
	cam.position = Vector3(0, 1.0, 3.6)
	cam.fov = 40
	add_child(cam)
	var lib: AnimationLibrary
	var x := -0.8
	for n in names:
		var inst: Node3D = (load("res://assets/models/chars/%s.glb" % n) as PackedScene).instantiate()
		add_child(inst)
		inst.position.x = x
		x += 1.6
		var sk: Skeleton3D = inst.find_child("Skeleton3D", true, false)
		print(n, " bones ", sk.get_bone_count(), " parent ", sk.get_parent().name, " scale ", sk.global_transform.basis.get_scale())
		lib = AnimLib.lib_for(sk, n)
		var ap := AnimationPlayer.new()
		sk.get_parent().add_child(ap)
		ap.root_node = NodePath("..")
		ap.add_animation_library("", lib)
		players.append(ap)
	var a0: Animation = lib.get_animation("rifle_run_forward")
	print("tracks ", a0.get_track_count(), " len ", a0.length, " path0 ", a0.track_get_path(0))
	_run()

func _run() -> void:
	for c in clips:
		for ap in players:
			ap.play(c)
			var L := ap.current_animation_length
			ap.seek(L * (0.98 if c.contains("death") else 0.45), true)
			ap.pause()
		for i in 4:
			await get_tree().process_frame
		var img := get_viewport().get_texture().get_image()
		img.save_png("user://t_%s.png" % c)
		print("shot ", c)
	get_tree().quit()
