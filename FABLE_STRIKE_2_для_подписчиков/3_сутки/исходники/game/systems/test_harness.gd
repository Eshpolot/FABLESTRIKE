class_name TestHarness
extends Node
## Тестовый харнесс — все режимы проверки, вынесенные из match.gd.
## Запускается по ключам: --vmtest, --hudtest, --sndtest, --tptest, --walltest, --loop

var game # Match

func setup(g) -> void:
	game = g

func run() -> void:
	if G.args.has("vmtest"):
		_vm_test()
	elif G.args.has("hudtest"):
		_hud_test()
	elif G.args.has("sndtest"):
		_snd_test()
	elif G.args.has("tptest"):
		_tp_test()
	elif G.args.has("walltest"):
		_wall_test()
	elif G.shots_dir != "":
		_auto_shots()

# === vmtest: руки+ствол от первого лица ===
func _vm_test() -> void:
	game.t_left = 9999.0
	game.player.money = 16000
	var p: Player = game.player
	p.view_yaw = deg_to_rad(float(G.args.get("yaw", "-70")))
	var list: Array = String(G.args.get("vmtest", "1")).split(",") if String(G.args.get("vmtest", "1")) != "1" else ["ak", "m4", "awp", "shotgun", "mac10", "mp9", "glock", "usp", "deagle", "knife", "he", "c4"]
	await game.get_tree().create_timer(1.0).timeout
	for wid in list:
		var d: Dictionary = DB.W[wid]
		if d["cls"] == "nade":
			p.nades.append(wid)
		elif d["cls"] == "c4":
			p.inv[5] = "c4"
		elif wid != "knife":
			p.inv[d["slot"]] = wid
			p._fill(wid)
		p.cur = ""
		p.switch_to(wid, true)
		await game.get_tree().create_timer(0.9).timeout
		await G.shot("vm_%s" % wid)
		if G.args.has("vmdbg"):
			game.hud.visible = false
			var c: Vector3 = p.vm.grip_cam + Vector3(0, 0.05, -0.14)
			var views := [["L", Basis(Vector3.UP, PI / 2)], ["R", Basis(Vector3.UP, -PI / 2)], ["T", Basis(Vector3.RIGHT, PI / 2)],
				["U", Basis(Vector3.RIGHT, -PI / 2)], ["Q", Basis(Vector3.RIGHT, deg_to_rad(25.0)) * Basis(Vector3.UP, deg_to_rad(40.0))]]
			for v in views:
				var vb: Basis = v[1]
				p.vm.transform = Transform3D(vb, Vector3(0, 0, float(G.args.get("vmdist", "-0.62"))) - vb * c)
				await game.get_tree().process_frame
				await game.get_tree().process_frame
				await G.shot("vm_%s_%s" % [wid, v[0]])
			p.vm.transform = Transform3D.IDENTITY
			game.hud.visible = true
		if G.args.has("vmact"):
			game.state = game.S.LIVE
			var cl: String = d["cls"]
			if cl in ["sniper", "shotgun"]:
				p._fill(wid)
				p.try_fire()
				for k in 4:
					await game.get_tree().create_timer(0.16).timeout
					await G.shot("vm_%s_c%d" % [wid, k])
				await game.get_tree().create_timer(0.8).timeout
			if cl == "knife":
				p.try_fire(false)
				for k in 3:
					await game.get_tree().create_timer(0.09).timeout
					await G.shot("vm_%s_a%d" % [wid, k])
				await game.get_tree().create_timer(0.6).timeout
				p.try_fire(true)
				for k in 4:
					await game.get_tree().create_timer(0.14).timeout
					await G.shot("vm_%s_b%d" % [wid, k])
				await game.get_tree().create_timer(0.8).timeout
			if cl == "nade":
				p.try_fire(false)
				for k in 4:
					await game.get_tree().create_timer(0.13).timeout
					await G.shot("vm_%s_t%d" % [wid, k])
				await game.get_tree().create_timer(0.6).timeout
			elif p.vm.hold in ["rifle", "smg", "pistol", "knife"]:
				p.vm.inspect()
				for k in 4:
					await game.get_tree().create_timer(0.72).timeout
					await G.shot("vm_%s_i%d" % [wid, k])
				await game.get_tree().create_timer(0.8).timeout
			game.state = game.S.FREEZE
		if d.has("mag") and d["mag"] > 0 and G.args.has("vmfull"):
			game.state = game.S.LIVE
			p.try_fire()
			await game.get_tree().process_frame
			await game.get_tree().process_frame
			await G.shot("vm_%s_fire" % wid)
			p.ammo[wid][0] = 3
			p.start_reload()
			if G.args.has("vmstrip"):
				for k in 8:
					await game.get_tree().create_timer(d["reload"] * 0.118).timeout
					await G.shot("vm_%s_r%d" % [wid, k])
			else:
				for k in [0.3, 0.55, 0.85]:
					await game.get_tree().create_timer(d["reload"] * 0.27).timeout
					await G.shot("vm_%s_rel%d" % [wid, int(k * 100)])
			await game.get_tree().create_timer(1.2).timeout
			game.state = game.S.FREEZE
	game.get_tree().quit()

# === tptest ===
func _tp_test() -> void:
	game.t_left = 9999.0
	await game.get_tree().create_timer(1.0).timeout
	game.hud.visible = false
	game.player.layer.visible = false
	var cam := Camera3D.new()
	game.add_child(cam)
	cam.fov = 38.0
	cam.current = true
	var list: Array = String(G.args.get("tptest", "1")).split(",") if String(G.args.get("tptest", "1")) != "1" else ["ak", "m4", "awp", "usp", "knife", "shotgun", "mp9", "deagle"]
	var i := 0
	for a in game.actors:
		if a == game.player or i >= list.size() or (G.args.has("tpteam") and a.team != String(G.args["tpteam"])):
			continue
		var wid: String = list[i]
		i += 1
		var d: Dictionary = DB.W[wid]
		if wid != "knife":
			a.inv[d["slot"]] = wid
			a._fill(wid)
		a.cur = ""
		a.switch_to(wid, true)
		await game.get_tree().create_timer(0.6).timeout
		var fwd: Vector3 = -Basis(Vector3.UP, a.view_yaw).z
		var right: Vector3 = Basis(Vector3.UP, a.view_yaw).x
		for v in [["f", fwd * 1.5 + right * 0.9], ["s", right * 1.7 + fwd * 0.25], ["l", -right * 1.7 + fwd * 0.25]]:
			cam.global_position = a.global_position + Vector3(0, 1.4, 0) + (v[1] as Vector3)
			cam.look_at(a.global_position + Vector3(0, 1.22, 0))
			await game.get_tree().process_frame
			await game.get_tree().process_frame
			await G.shot("tp_%s_%s_%s" % [a.team, wid, v[0]])
	game.get_tree().quit()

# === sndtest ===
func _snd_test() -> void:
	game.t_left = 9999.0
	G.args["sndlog"] = "1"
	for a in game.actors:
		if a != game.player:
			a.set_physics_process(false)
	Sfx.ambient("")
	Sfx.music("", 0.1)
	var p: Player = game.player
	p.money = 16000
	p.view_yaw = deg_to_rad(float(G.args.get("yaw", "-70")))
	await game.get_tree().create_timer(1.5).timeout
	var rec := AudioEffectRecord.new()
	AudioServer.add_bus_effect(0, rec)
	rec.set_recording_active(true)
	game._ev("rec_start")
	game.state = game.S.LIVE
	var guns := ["m4" if p.team == "ct" else "ak", "usp" if p.team == "ct" else "glock"]
	for wid in guns:
		var d: Dictionary = DB.W[wid]
		p.inv[d["slot"]] = wid
		p._fill(wid)
		p.cur = ""
		p.switch_to(wid, true)
		await game.get_tree().create_timer(1.2).timeout
		for gi in 3:
			game._ev("shot_" + wid)
			p.try_fire()
			await game.get_tree().create_timer(0.6).timeout
		p.ammo[wid][0] = 3
		game._ev("reload_" + wid)
		p.start_reload()
		await game.get_tree().create_timer(float(d["reload"]) + 0.6).timeout
	p.switch_to("knife", true)
	await game.get_tree().create_timer(0.8).timeout
	game.test_wish = Vector2(0, 1)
	await game.get_tree().create_timer(2.6).timeout
	game.test_wish = Vector2.ZERO
	await game.get_tree().create_timer(0.6).timeout
	rec.set_recording_active(false)
	game._ev("rec_stop")
	var wav := rec.get_recording()
	if wav and G.shots_dir != "":
		wav.save_to_wav(G.shots_dir + "/sndtest.wav")
		print("WAV saved ", wav.get_length())
	game.get_tree().quit()

# === walltest ===
func _wall_test() -> void:
	game.t_left = 9999.0
	await game.get_tree().create_timer(0.5).timeout
	var space := game.get_world_3d().direct_space_state
	var cap := CapsuleShape3D.new()
	cap.radius = 0.3
	cap.height = 1.7
	var q := PhysicsShapeQueryParameters3D.new()
	q.shape = cap
	q.collision_mask = 1
	var open_n := 0
	var open_bad := 0
	var wall_n := 0
	var wall_bad := 0
	var bad_list := []
	var rows: Array = game.world.data["open"]
	var nav: Array = game.world.data["nav"]
	for y in game.world.size.y:
		for x in game.world.size.x:
			if rows[y][x] != "1":
				continue
			var c := Vector3(x + 0.5, 0.0, -(y + 0.5))
			if nav[y][x] == "1":
				open_n += 1
				q.transform = Transform3D(Basis.IDENTITY, c + Vector3(0, 0.95, 0))
				if not space.intersect_shape(q, 1).is_empty():
					open_bad += 1
					if bad_list.size() < 200:
						bad_list.append("занято %d,%d" % [x, y])
			for d in [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1)]:
				var nx: int = x + d.x
				var ny: int = y + d.y
				var solid: bool = nx < 0 or ny < 0 or nx >= game.world.size.x or ny >= game.world.size.y or rows[ny][nx] != "1"
				if solid:
					wall_n += 1
					var to := Vector3(nx + 0.5, 0.0, -(ny + 0.5))
					for h in [0.3, 1.0, 1.7]:
						var rq := PhysicsRayQueryParameters3D.create(c + Vector3(0, h, 0), to + Vector3(0, h, 0), 1)
						if space.intersect_ray(rq).is_empty():
							wall_bad += 1
							if bad_list.size() < 200:
								bad_list.append("дыра %d,%d -> %d,%d h=%.1f" % [x, y, nx, ny, h])
							break
	var pa := game.world.path(game.world.spawn("t", 0).origin, game.world.rect_center(game.world.data["site_a"])).size()
	var pb := game.world.path(game.world.spawn("t", 0).origin, game.world.rect_center(game.world.data["site_b"])).size()
	var ca := game.world.path(game.world.spawn("ct", 0).origin, game.world.rect_center(game.world.data["site_a"])).size()
	var cb := game.world.path(game.world.spawn("ct", 0).origin, game.world.rect_center(game.world.data["site_b"])).size()
	G.log_line("WALLTEST open %d bad %d | walls %d holes %d | paths T->A %d T->B %d CT->A %d CT->B %d | %s" % [open_n, open_bad, wall_n, wall_bad, pa, pb, ca, cb, ", ".join(bad_list)])
	game.get_tree().quit()

# === hudtest ===
func _hud_test() -> void:
	game.t_left = 30.0
	game.player.money = 9000
	await game.get_tree().create_timer(1.2).timeout
	game.hud._set_buy(true)
	game.hud.buy._show("m4" if game.player.team == "ct" else "ak")
	await game.get_tree().create_timer(0.4).timeout
	await G.shot("hud_buy")
	game.player.buy("m4" if game.player.team == "ct" else "ak")
	game.player.buy("helmet")
	game.player.buy("he")
	game.player.buy("smoke")
	game.hud.buy.refresh()
	await game.get_tree().create_timer(0.3).timeout
	await G.shot("hud_buy2")
	game.hud._set_buy(false)
	game.hud.show_score = true
	game.set_meta("force_score", true)
	await game.get_tree().create_timer(0.3).timeout
	await G.shot("hud_score")
	game.remove_meta("force_score")
	game.hud._set_pause(true)
	await game.get_tree().create_timer(0.3).timeout
	await G.shot("hud_pause")
	game.hud._set_pause(false)
	game.t_left = 0.5
	await game.get_tree().create_timer(2.5).timeout
	await G.shot("hud_live")
	game.get_tree().quit()

func _auto_shots() -> void:
	var n := 0
	var every := float(G.args.get("every", "6"))
	while n < int(G.args.get("shots_n", "12")):
		await game.get_tree().create_timer(every, true, false, true).timeout
		await G.shot("match_%02d" % n)
		G.log_line("fps %d  objects %d  draws %d" % [Engine.get_frames_per_second(), int(RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_OBJECTS_IN_FRAME)), int(RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME))])
		n += 1
