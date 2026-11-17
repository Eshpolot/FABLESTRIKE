class_name BombSystem
extends Node
## Бомба: выдача, подбор, закладка, разминирование, взрыв.
## P1.1: bomb: BombState (типизирован) вместо Dictionary.

var game # Match
var bomb: BombState
var dropped_c4: Node3D
var t_plan := "a"

func setup(g, rng: RandomNumberGenerator) -> void:
	game = g
	bomb = BombState.new()
	t_plan = "a" if rng.randf() < 0.5 else "b"
	reset()

func reset() -> void:
	if bomb and bomb.node and is_instance_valid(bomb.node):
		bomb.node.queue_free()
	if dropped_c4 and is_instance_valid(dropped_c4):
		dropped_c4.queue_free()
	bomb = BombState.new()
	bomb.state = BombState.State.CARRIED
	# сохраняем совместимость: game.bomb как Dictionary остаётся через геттер в match.gd,
	# но внутри уже типизировано.

func assign_carrier(candidates: Array) -> void:
	if candidates.is_empty():
		return
	var rng := RandomNumberGenerator.new()
	rng.randomize()
	var carrier: Actor = candidates[randi() % candidates.size()]
	carrier.inv[5] = "c4"
	bomb.carrier = carrier
	bomb.state = BombState.State.CARRIED

func drop_bomb(pos: Vector3) -> void:
	bomb.state = BombState.State.DROPPED
	bomb.carrier = null
	bomb.pos = Vector3(pos.x, 0.02, pos.z)
	dropped_c4 = _c4_node()
	dropped_c4.global_position = bomb.pos
	dropped_c4.rotation = Vector3(-PI / 2.0, randf() * TAU, 0)
	game.hud.announce("Бомба брошена", 2.0)

func plant_spot(site: String, a: Actor) -> Vector3:
	var r: Array = game.world.data["site_" + site]
	var c := game.world.rect_center(r)
	var h := hash(a.nick + str(game.round_no))
	var p := c + Vector3(float(h % 7) - 3.0, 0, float((h / 7) % 7) - 3.0)
	var cell := game.world.free_cell(game.world.cell(p))
	return game.world.cell_center(cell)

func try_plant(a: Actor, holding: bool) -> void:
	if not holding or game.state != game.S.LIVE or a.inv[5] != "c4" or a.cur != "c4" or not a.is_on_floor() or game.world.site_at(a.global_position) == "":
		if a.plant_t >= 0.0:
			a.plant_t = -1.0
		return
	if a.plant_t < 0.0:
		a.plant_t = 0.0
		game.sound_at("bomb_plant", a.global_position, -4.0, a)
		game.intel.noise(a.global_position, a)
	a.plant_t += game.get_physics_process_delta_time()
	if a.plant_t >= DB.T_PLANT:
		a.plant_t = -1.0
		a.inv[5] = ""
		a.cur = ""
		a.switch_to(a.inv[1] if a.inv[1] != "" else a.inv[2])
		a.money = mini(DB.MAX_MONEY, a.money + DB.PLANT_BONUS)
		a.score += 2
		bomb.state = BombState.State.PLANTED
		bomb.site = game.world.site_at(a.global_position)
		bomb.pos = Vector3(a.global_position.x, a.global_position.y + 0.02, a.global_position.z) - Basis(Vector3.UP, a.view_yaw).z * 0.5
		bomb.t = DB.T_BOMB
		bomb.planter = a
		bomb.carrier = null
		var n := _c4_node()
		n.global_position = bomb.pos
		n.rotation = Vector3(-PI / 2.0, a.view_yaw, 0)
		bomb.node = n
		game.state = game.S.PLANTED
		game.hud.announce("Бомба заложена", 3.0)
		Sfx.play("bomb_planted", -3.0)
		Sfx.music("action_theme", 0.6, -13.0)
		G.log_line("bomb planted at %s by %s" % [bomb.site, a.nick])

func try_defuse(a: Actor, holding: bool) -> void:
	if not holding or game.state != game.S.PLANTED or a.team != "ct" or not a.alive or a.global_position.distance_to(bomb.pos) > 1.7:
		if a.defuse_t >= 0.0:
			a.defuse_t = -1.0
		return
	if a.defuse_t < 0.0:
		a.defuse_t = 0.0
		game.sound_at("defuse_start", a.global_position, -4.0, a)
	a.defuse_t += game.get_physics_process_delta_time()
	var need := DB.T_DEFUSE_KIT if a.kit else DB.T_DEFUSE
	if a.defuse_t >= need:
		a.defuse_t = -1.0
		a.score += 2
		bomb.state = BombState.State.DEFUSED
		if bomb.node:
			(bomb.node.get_node("Blink") as OmniLight3D).light_energy = 0.0
		Sfx.play("bomb_defused", -3.0)
		game._end_round("ct", "Бомба обезврежена")

func tick(dt: float) -> void:
	if bomb.state == BombState.State.DROPPED:
		for a in game.alive_of("t"):
			if a.global_position.distance_to(bomb.pos) < 1.1:
				a.inv[5] = "c4"
				bomb.state = BombState.State.CARRIED
				bomb.carrier = a
				if dropped_c4 and is_instance_valid(dropped_c4):
					dropped_c4.queue_free()
				if a == game.player:
					game.hud.announce("Вы подобрали бомбу", 2.0)
				break
	elif bomb.state == BombState.State.PLANTED and game.state == game.S.PLANTED:
		bomb.t -= dt
		bomb.beep -= dt
		if bomb.beep <= 0.0:
			var tl: float = bomb.t
			bomb.beep = clampf(0.1 + 0.9 * tl / DB.T_BOMB, 0.12, 1.0)
			Sfx.at("bomb_beep", bomb.pos, 2.0, 1.0, 7.0, 80.0)
			var l := bomb.node.get_node("Blink") as OmniLight3D
			l.light_energy = 3.0
			game.create_tween().tween_property(l, "light_energy", 0.0, 0.12)
		if bomb.t <= 0.0:
			_explode()

func _explode() -> void:
	bomb.state = BombState.State.EXPLODED
	var p: Vector3 = bomb.pos
	game.fx.explosion(p, 11.0)
	Sfx.at("explosion_big", p, 8.0, 1.0, 30.0, 300.0)
	Sfx.play("explosion_big", -6.0, 1.0)
	if bomb.node:
		bomb.node.visible = false
	for a in game.actors:
		if a.alive:
			var d: float = a.global_position.distance_to(p)
			if d < 17.0:
				a.take_damage(500.0 * pow(1.0 - d / 17.0, 1.4), bomb.planter, "c4", "chest", p)
	if game.player:
		game.player.shake(1.0)
	game._end_round("t", "Бомба взорвана")

func _c4_node() -> Node3D:
	var n: Node3D
	if ResourceLoader.exists("res://assets/models/weapons/c4.glb"):
		n = (load("res://assets/models/weapons/c4.glb") as PackedScene).instantiate()
	else:
		n = Node3D.new()
	var l := OmniLight3D.new()
	l.name = "Blink"
	l.light_color = Color(1.0, 0.1, 0.05)
	l.omni_range = 2.5
	l.light_energy = 0.0
	l.position = Vector3(0, 0.15, 0)
	n.add_child(l)
	game.add_child(n)
	return n

## Совместимость: старый код читает bomb["state"], bomb["pos"] — даём прокси.
func _get_bomb_dict() -> Dictionary:
	return {"state": BombState.state_to_str(bomb.state), "pos": bomb.pos, "carrier": bomb.carrier, "site": bomb.site, "t": bomb.t, "node": bomb.node, "planter": bomb.planter, "beep": bomb.beep}
