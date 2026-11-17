class_name RoundManager
extends Node
## Машина состояний раунда: FREEZE → LIVE → (PLANTED) → END → HALF → OVER.
## Вынесено из match.gd — теперь таймеры и переходы в одном месте.

enum S { FREEZE, LIVE, PLANTED, END, HALF, OVER }

var game # Match
var state: int = S.FREEZE
var t_left: float = 0.0
var round_no: int = 0
var round_time: float = 0.0
var score := {"t": 0, "ct": 0}
var win_target: int = 7
var half_at: int = 6
var swapped: bool = false
var last_winner: String = ""
var last_reason: String = ""
var over_t: float = 0.0
var stats_first_blood: bool = false
var _fresh_half: bool = true

func setup(g) -> void:
	game = g
	win_target = int(G.settings["match_len"])
	half_at = win_target - 1

func start_round() -> void:
	round_no += 1
	state = S.FREEZE
	t_left = DB.T_FREEZE
	round_time = 0.0
	stats_first_blood = false
	game.intel.clear()
	# делегируем очистку гранат/бомбы системам
	game.nade_system.clear_round()
	game.fx.clear_round()
	game.bomb_system.reset()
	if game.bomb_system.dropped_c4 and is_instance_valid(game.bomb_system.dropped_c4):
		game.bomb_system.dropped_c4.queue_free()
	# выбираем план атаки
	game.bomb_system.t_plan = "a" if game.rng.randf() < 0.5 else "b"
	var idx := {"t": 0, "ct": 0}
	var order := game.actors.duplicate()
	for a in order:
		var keep: bool = a.alive and round_no > 1 and not _fresh_half
		var i: int = idx[a.team]
		idx[a.team] += 1
		var xf := game.world.spawn(a.team, i)
		a.spawn_at(xf.origin, game.world.spawn_yaw(a.team, i), keep)
		if a.has_meta("brain"):
			(a.get_meta("brain") as Brain).new_round()
	_fresh_half = false
	# бомба — случайному атакующему
	var ts := game.team_of("t")
	var carrier: Actor = ts[game.rng.randi() % ts.size()]
	carrier.inv[5] = "c4"
	game.bomb_system.bomb.carrier = carrier
	game.bomb_system.bomb.state = BombState.State.CARRIED
	# роли защиты
	var roles := ["a", "b", "a", "b", "mid"]
	roles.shuffle()
	var k := 0
	for a in game.team_of("ct"):
		if a.has_meta("brain"):
			(a.get_meta("brain") as Brain).role = roles[k % roles.size()]
		k += 1
	for a in game.actors:
		if a.is_bot or game.auto:
			game.economy.bot_buy(a)
	game.hud.round_start()
	Sfx.play("round_start", -6.0)
	G.log_line("round %d start  T %d : %d CT  plan=%s" % [round_no, score["t"], score["ct"], game.bomb_system.t_plan])
	# синхронизируем с Match для совместимости
	game.state = state
	game.t_left = t_left
	game.round_no = round_no
	game.score = score

func tick(dt: float) -> void:
	match state:
		S.FREEZE:
			t_left -= dt
			if t_left <= 0.0:
				state = S.LIVE
				t_left = DB.T_ROUND
				game.hud.announce("", 0.1)
				Sfx.play("go", -8.0)
		S.LIVE:
			t_left -= dt
			round_time += dt
			_check_win()
			if state == S.LIVE and t_left <= 0.0:
				end_round("ct", "Время вышло")
		S.PLANTED:
			round_time += dt
			_check_win()
		S.END:
			t_left -= dt
			if t_left <= 0.0:
				_after_round()
		S.HALF:
			t_left -= dt
			if t_left <= 0.0:
				start_round()
		S.OVER:
			over_t += dt
			if over_t > (4.0 if game.auto else 14.0) or (over_t > 2.0 and Input.is_action_just_pressed("jump")):
				game._finish()
	# синхронизация для HUD/Actor
	game.state = state
	game.t_left = t_left
	game.round_time = round_time
	game.over_t = over_t
	game.last_winner = last_winner
	game.last_reason = last_reason
	game.score = score
	game.swapped = swapped

func _check_win() -> void:
	var ta := game.alive_of("t").size()
	var ca := game.alive_of("ct").size()
	if state == S.LIVE:
		if ta == 0 and ca == 0:
			end_round("ct", "Все погибли")
		elif ta == 0:
			end_round("ct", "Атака уничтожена")
		elif ca == 0:
			end_round("t", "Защита уничтожена")
	elif state == S.PLANTED:
		if ca == 0:
			end_round("t", "Защита уничтожена")

func end_round(winner: String, reason: String) -> void:
	if state == S.END or state == S.OVER or state == S.HALF:
		return
	state = S.END
	t_left = DB.T_END
	last_winner = winner
	last_reason = reason
	score[winner] += 1
	game.economy.on_round_end(winner, reason)
	# MVP
	var best: Actor = null
	for a in game.team_of(winner):
		if best == null or a.round_kills > best.round_kills:
			best = a
	var planter = game.bomb.planter if game.bomb is BombState else game.bomb["planter"]
	if planter and winner == "t" and reason == "Бомба взорвана":
		best = planter
	if best:
		best.mvps += 1
	game.hud.round_end(winner, reason, best)
	Sfx.music("", 1.2)
	Sfx.play("win" if winner == game.player.team else "lose", -5.0)
	G.log_line("round %d end: %s (%s)  T %d : %d CT" % [round_no, winner, reason, score["t"], score["ct"]])

func _after_round() -> void:
	var total: int = score["t"] + score["ct"]
	if score["t"] >= win_target or score["ct"] >= win_target or total >= 2 * half_at:
		_match_over()
		return
	if total == half_at and not swapped:
		_halftime()
		return
	start_round()

func _halftime() -> void:
	swapped = true
	state = S.HALF
	t_left = 6.0
	for a in game.actors:
		a.team = "ct" if a.team == "t" else "t"
		a.alive = false
		a.money = DB.START_MONEY
	var s: int = score["t"]
	score["t"] = score["ct"]
	score["ct"] = s
	game.economy.reset_half()
	_fresh_half = true
	game.hud.announce("Смена сторон", 5.0)
	Sfx.play("round_start", -6.0)

func _match_over() -> void:
	state = S.OVER
	over_t = 0.0
	var pt := game.player.team
	var ot := "ct" if pt == "t" else "t"
	var res := "draw"
	if score[pt] > score[ot]:
		res = "win"
	elif score[pt] < score[ot]:
		res = "lose"
	var credits := 150 + game.player.kills * 25 + game.player.mvps * 40 + (300 if res == "win" else (120 if res == "draw" else 0))
	G.profile["matches"] = int(G.profile["matches"]) + 1
	G.profile["kills"] = int(G.profile["kills"]) + game.player.kills
	if res == "win":
		G.profile["wins"] = int(G.profile["wins"]) + 1
	G.add_credits(credits)
	G.last_result = {"res": res, "score": [score[pt], score[ot]], "credits": credits, "kills": game.player.kills, "deaths": game.player.deaths}
	game.hud.match_over(res, credits)
	Sfx.music("win_theme" if res == "win" else "menu_theme", 2.0, -8.0)
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	G.log_line("MATCH OVER %s  %d : %d  credits +%d" % [res, score[pt], score[ot], credits])
	for a in game.actors:
		G.log_line("  %s %s  K %d  D %d  A %d  dmg %d" % [a.team, a.nick, a.kills, a.deaths, a.assists, a.dmg_given])
