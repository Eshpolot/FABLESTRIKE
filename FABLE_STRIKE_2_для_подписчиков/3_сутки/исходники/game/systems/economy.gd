class_name Economy
extends Node
## Экономика матча: награды, потерянные серии, закуп ботов.
## Вынесено из match.gd — теперь баланс правится в одном месте без касания Combat.

var game # Match
var rng: RandomNumberGenerator
var loss_streak := {"t": 0, "ct": 0}

func setup(g, r: RandomNumberGenerator) -> void:
	game = g
	rng = r
	loss_streak = {"t": 0, "ct": 0}

func on_round_end(winner: String, reason: String) -> void:
	var loser := "ct" if winner == "t" else "t"
	var win_money := DB.WIN_BOMB if reason in ["Бомба взорвана", "Бомба обезврежена"] else DB.WIN_ELIM
	for a in game.team_of(winner):
		a.money = mini(DB.MAX_MONEY, a.money + win_money)
	var lb: int = DB.LOSS[mini(loss_streak[loser], DB.LOSS.size() - 1)]
	# бонус за закладку проигравшим (даже если потом обезвредили)
	var bstate = game.bomb.state if game.bomb is BombState else game.bomb["state"]
	var is_planted_bonus := false
	if bstate is int:
		is_planted_bonus = bstate in [BombState.State.PLANTED, BombState.State.DEFUSED]
	else:
		is_planted_bonus = str(bstate) in ["planted", "defused"]
	if loser == "t" and is_planted_bonus:
		lb += DB.PLANT_LOSS_BONUS
	for a in game.team_of(loser):
		if loser == "t" and a.alive and reason == "Время вышло":
			continue
		a.money = mini(DB.MAX_MONEY, a.money + lb)
	loss_streak[loser] = mini(loss_streak[loser] + 1, 4)
	loss_streak[winner] = maxi(loss_streak[winner] - 1, 0)

func bot_buy(a: Actor) -> void:
	var m := a.money
	var t := a.team
	if a.inv[1] == "":
		if m >= 4750 + 1000 and rng.randf() < 0.12:
			a.buy("awp")
		elif m >= (2700 if t == "t" else 2900) + 650:
			a.buy("ak" if t == "t" else "m4")
		elif m >= 1050 + 650 + 300 and (loss_streak[t] >= 2 or m < 2400) and rng.randf() < 0.7:
			a.buy(("mac10" if t == "t" else "mp9") if rng.randf() < 0.75 else "shotgun")
		elif m >= 700 and m < 1500 and rng.randf() < 0.35:
			a.buy("deagle")
	if a.armor < 100 and a.money >= 1000 and a.inv[1] != "":
		a.buy("helmet")
	elif a.armor < 100 and a.money >= 650 and (a.inv[1] != "" or a.money >= 1400):
		a.buy("kevlar")
	if t == "ct" and not a.kit and a.money >= 400 + 300 and a.inv[1] != "":
		a.buy("kit")
	if a.money >= 600 and a.inv[1] != "" and rng.randf() < 0.5:
		a.buy(["he", "flash", "smoke"][rng.randi() % 3])

func reset_half() -> void:
	loss_streak = {"t": 0, "ct": 0}
