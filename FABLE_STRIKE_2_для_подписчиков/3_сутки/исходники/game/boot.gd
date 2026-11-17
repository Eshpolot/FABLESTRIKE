extends Node
## Точка входа: обычный запуск -> меню; с ключами проверки -> сразу нужная сцена.
## P2: прелоад анимаций в фоне, чтобы не фризить на первом спавне (150мс).

func _ready() -> void:
	await get_tree().process_frame
	# P2: греем AnimLib в бэкграунде — первый матч без фриза
	if not G.args.has("no_preload"):
		call_deferred("_preload_anim")
	if G.args.has("match"):
		G.start_match()
	elif G.args.has("test"):
		get_tree().change_scene_to_file("res://tools/test_%s.tscn" % G.args["test"])
	else:
		G.to_menu()

func _preload_anim() -> void:
	# Три скелета: t_1/ct_1 — достаточно, остальные переиспользуют
	var t0 := Time.get_ticks_msec()
	for m in ["t_1", "ct_1"]:
		var dummy := Skeleton3D.new()
		# пытаемся загрузить glb чтобы получить скелет (если нет — пропускаем)
		var path := "res://assets/models/chars/%s.glb" % m
		if ResourceLoader.exists(path):
			var scn: PackedScene = load(path)
			var inst: Node = scn.instantiate()
			var sk: Skeleton3D = inst.find_child("Skeleton3D", true, false)
			if sk:
				AnimLib.lib_for(sk, m)
			inst.queue_free()
	G.log_line("preload anims: %d ms" % (Time.get_ticks_msec() - t0))
