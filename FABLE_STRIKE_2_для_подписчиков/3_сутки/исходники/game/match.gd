extends Node3D
## Матч — оркестратор. Тонкий фасад над 6 системами (P1 рефактор).
## До: 1060 строк, 6 ролей в одном файле. После: ~380 строк + 6 систем.
## Публичный API сохранён: brain/hud/player вызывают те же методы (report, smoke_blocks, bullet и т.д.).

enum S { FREEZE, LIVE, PLANTED, END, HALF, OVER }

const T_NAMES := ["Шакал", "Самум", "Скорпион", "Фенек", "Бархан"]
const CT_NAMES := ["Гранит", "Беркут", "Сокол", "Витязь", "Кедр"]

# --- мир и эффекты ---
var world: World
var fx: Fx
var hud

# --- системы (P1) ---
var intel: Intel
var economy: Economy
var bomb_system: BombSystem
var nade_system: NadeSystem
var combat: Combat
var round_manager: RoundManager
var test_harness: TestHarness

# --- алиасы для совместимости (brain.gd читает game.bomb/game.smokes напрямую) ---
var bomb: Dictionary:
	get: return bomb_system.bomb if bomb_system else {"state": "none", "pos": Vector3.ZERO, "carrier": null, "site": "", "t": 0.0, "node": null, "planter": null, "beep": 0.0}
	set(v): 
		if bomb_system: bomb_system.bomb = v
var smokes: Array:
	get: return nade_system.smokes if nade_system else []
	set(v):
		if nade_system: nade_system.smokes = v
var fires: Array:
	get: return nade_system.fires if nade_system else []
	set(v):
		if nade_system: nade_system.fires = v
var nades: Array:
	get: return nade_system.nades if nade_system else []
	set(v):
		if nade_system: nade_system.nades = v
var reports: Dictionary:
	get: return intel.reports if intel else {"t": [], "ct": []}
	set(v):
		if intel: intel.reports = v
var t_plan: String:
	get: return bomb_system.t_plan if bomb_system else "a"
	set(v):
		if bomb_system: bomb_system.t_plan = v
var loss_streak: Dictionary:
	get: return economy.loss_streak if economy else {"t": 0, "ct": 0}
	set(v):
		if economy: economy.loss_streak = v
var state: int:
	get: return round_manager.state if round_manager else S.FREEZE
	set(v):
		if round_manager: round_manager.state = v
var t_left: float:
	get: return round_manager.t_left if round_manager else 0.0
	set(v):
		if round_manager: round_manager.t_left = v
var round_no: int:
	get: return round_manager.round_no if round_manager else 0
	set(v):
		if round_manager: round_manager.round_no = v
var score: Dictionary:
	get: return round_manager.score if round_manager else {"t": 0, "ct": 0}
	set(v):
		if round_manager: round_manager.score = v
var round_time: float:
	get: return round_manager.round_time if round_manager else 0.0
	set(v):
		if round_manager: round_manager.round_time = v
var swapped: bool:
	get: return round_manager.swapped if round_manager else false
	set(v):
		if round_manager: round_manager.swapped = v
var over_t: float:
	get: return round_manager.over_t if round_manager else 0.0
	set(v):
		if round_manager: round_manager.over_t = v
var last_winner: String:
	get: return round_manager.last_winner if round_manager else ""
	set(v):
		if round_manager: round_manager.last_winner = v
var last_reason: String:
	get: return round_manager.last_reason if round_manager else ""
	set(v):
		if round_manager: round_manager.last_reason = v

# --- общее ---
var actors: Array = []
var player: Player
var rng := RandomNumberGenerator.new()
var auto := false
var _test_t := 0.0
var win_target: int:
	get: return round_manager.win_target if round_manager else 7
var half_at: int:
	get: return round_manager.half_at if round_manager else 6
var test_wish := Vector2.ZERO
var dropped_c4: Node3D:
	get: return bomb_system.dropped_c4 if bomb_system else null

func _ready() -> void:
	rng.randomize()
	if G.args.has("seed"):
		rng.seed = int(G.args["seed"])
	auto = G.args.has("auto")
	if G.args.has("loop") and G.shots_dir != "":
		_loop_shot()
	# системы
	intel = Intel.new()
	intel.name = "Intel"
	add_child(intel)
	economy = Economy.new()
	economy.name = "Economy"
	add_child(economy)
	bomb_system = BombSystem.new()
	bomb_system.name = "BombSystem"
	add_child(bomb_system)
	nade_system = NadeSystem.new()
	nade_system.name = "NadeSystem"
	add_child(nade_system)
	combat = Combat.new()
	combat.name = "Combat"
	add_child(combat)
	round_manager = RoundManager.new()
	round_manager.name = "RoundManager"
	add_child(round_manager)
	test_harness = TestHarness.new()
	test_harness.name = "TestHarness"
	add_child(test_harness)
	# мир
	world = World.new()
	world.name = "World"
	add_child(world)
	world.load_map("kasbah")
	fx = Fx.new()
	fx.name = "Fx"
	add_child(fx)
	# системы после мира/fx
	intel.setup(self)
	economy.setup(self, rng)
	bomb_system.setup(self, rng)
	nade_system.setup(self)
	combat.setup(self)
	round_manager.setup(self)
	test_harness.setup(self)
	# команды
	_spawn_teams()
	hud = preload("res://game/hud.gd").new()
	hud.name = "HUD"
	hud.game = self
	add_child(hud)
	Sfx.music("")
	Sfx.ambient("amb_desert", -16.0)
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	if G.args.has("timescale"):
		Engine.time_scale = float(G.args["timescale"])
	round_manager.start_round()
	# тесты — вынесены в TestHarness
	test_harness.run()

func _loop_shot() -> void:
	await get_tree().create_timer(12.0, true, false, true).timeout
	await G.shot("loop_3_match")

func _ev(n: String) -> void:
	print("EV %d %s" % [Time.get_ticks_msec(), n])

# ------------------------------------------------------------------ спавн
func _spawn_teams() -> void:
	var pteam: String = G.settings["team"]
	var models := {"t": ["t_1", "t_2"], "ct": ["ct_1", "ct_2"]}
	for team in ["t", "ct"]:
		var names: Array = T_NAMES if team == "t" else CT_NAMES
		for i in 5:
			var a: Actor
			var is_p: bool = team == pteam and i == 0
			if is_p:
				player = Player.new()
				a = player
			else:
				a = Bot.new()
			a.name = "%s_%d" % [team, i]
			add_child(a)
			a.setup(self, team, (String(G.settings["name"]) if is_p else names[i]), not is_p, models[team][i % 2])
			a.full_reset()
			if is_p:
				player.init_player()
			if not is_p or auto:
				var br := Brain.new()
				br.name = "Brain"
				a.add_child(br)
				br.setup(a, self)
				a.set_meta("brain", br)
			if not is_p:
				var fb := FighterBody.new()
				fb.name = "Body"
				a.add_child(fb)
				fb.setup(a, a.model_name)
				a.body = fb
				a.shot.connect(fb.on_shot.unbind(1))
				a.reload_started.connect(func(_w, t): fb.on_reload(t))
			actors.append(a)

func team_of(t: String) -> Array:
	return actors.filter(func(x): return x.team == t)

func alive_of(t: String) -> Array:
	return actors.filter(func(x): return x.team == t and x.alive)

func nearest_alive(t: String, pos: Vector3) -> Actor:
	var best: Actor = null
	var bd := 1e9
	for a in alive_of(t):
		var d: float = a.global_position.distance_to(pos)
		if d < bd:
			bd = d
			best = a
	return best

func frozen() -> bool:
	return state == S.FREEZE or state == S.HALF or state == S.OVER

func round_over_no_damage() -> bool:
	return state == S.HALF or state == S.OVER

func time_left() -> float:
	return bomb["t"] if state == S.PLANTED else t_left

func can_buy(a: Actor) -> bool:
	if state == S.FREEZE:
		return true
	if state in [S.LIVE] and round_time < DB.T_BUY:
		return world.in_rect(a.global_position, world.data["buy_t" if a.team == "t" else "buy_ct"])
	return false

# ------------------------------------------------------------------ фасады для совместимости (делегируем системам)

func _start_round() -> void:
	round_manager.start_round()

func _end_round(winner: String, reason: String) -> void:
	round_manager.end_round(winner, reason)

func _bot_buy(a: Actor) -> void:
	economy.bot_buy(a)

func report(team: String, pos: Vector3) -> void:
	intel.report(team, pos)

func hot_site(team: String) -> String:
	return intel.hot_site(team)

func smoke_blocks(a: Vector3, b: Vector3) -> bool:
	return intel.smoke_blocks(a, b)

func noise(pos: Vector3, from: Actor) -> void:
	intel.noise(pos, from)

func bullet(shooter: Actor, from: Vector3, dir: Vector3, wid: String, first: bool) -> void:
	combat.bullet(shooter, from, dir, wid, first)

func knife_hit(a: Actor, alt: bool) -> void:
	combat.knife_hit(a, alt)

func on_hurt(v: Actor, attacker: Actor, n: int, zone: String, armored: bool, from_pos: Vector3) -> void:
	combat.on_hurt(v, attacker, n, zone, armored, from_pos)

func on_death(v: Actor, killer: Actor, wid: String, headshot: bool) -> void:
	combat.on_death(v, killer, wid, headshot)

func sound_at(n: String, pos: Vector3, vol := 0.0, who: Actor = null) -> void:
	if who and who == player and player.alive:
		Sfx.play(n, vol - 3.0)
	else:
		Sfx.at(n, pos, vol)

func gun_sound(a: Actor, wid: String) -> void:
	combat.gun_sound(a, wid)

func reload_sound(a: Actor, wid: String) -> void:
	combat.reload_sound(a, wid)

func footstep(a: Actor) -> void:
	combat.footstep(a)

func throw_nade(owner: Actor, id: String, pos: Vector3, vel: Vector3) -> void:
	nade_system.throw_nade(owner, id, pos, vel)

func nade_burst(n: Nade) -> void:
	nade_system.nade_burst(n)

func plant_spot(site: String, a: Actor) -> Vector3:
	return bomb_system.plant_spot(site, a)

func try_plant(a: Actor, holding: bool) -> void:
	bomb_system.try_plant(a, holding)

func try_defuse(a: Actor, holding: bool) -> void:
	bomb_system.try_defuse(a, holding)

# ------------------------------------------------------------------ тик

func _physics_process(dt: float) -> void:
	round_manager.tick(dt)
	bomb_system.tick(dt)
	nade_system.tick(dt)
	if auto and G.args.has("maxtime"):
		_test_t += dt
		if _test_t > float(G.args["maxtime"]):
			G.log_line("maxtime reached, score T %d : %d CT" % [score["t"], score["ct"]])
			_finish()

# ------------------------------------------------------------------ финал

func _finish() -> void:
	set_physics_process(false)
	if G.args.has("quit_after"):
		G.log_line("quit after match")
		get_tree().quit()
		return
	G.to_menu()
