class_name Intel
extends Node
## Система разведки: куда докладывают боты, где горячая точка, блокирует ли дым линию огня.
## Вынесено из match.gd (reports, hot_site, smoke_blocks, noise) — чтобы Combat и Brain
## не зависели от монолита Match.

var game # Match — слабая ссылка, задаётся в setup()

# reports[team] = Array[[msec:int, pos:Vector3]]
var reports := {"t": [], "ct": []}

func setup(g) -> void:
	game = g

func report(team: String, pos: Vector3) -> void:
	var arr: Array = reports[team]
	arr.append([Time.get_ticks_msec(), pos])
	if arr.size() > 32:
		arr.pop_front()
	# чистим старые, чтобы hot_site не считала 2-минутный мусор
	var now := Time.get_ticks_msec()
	var i := 0
	while i < arr.size():
		if now - int(arr[i][0]) > 9000:
			arr.remove_at(i)
		else:
			i += 1

func hot_site(team: String) -> String:
	var now := Time.get_ticks_msec()
	var na := 0
	var nb := 0
	for r in reports[team]:
		if now - int(r[0]) > 9000:
			continue
		var p: Vector3 = r[1]
		if p.distance_to(game.world.rect_center(game.world.data["site_a"])) < 24.0:
			na += 1
		if p.distance_to(game.world.rect_center(game.world.data["site_b"])) < 24.0:
			nb += 1
	if na == 0 and nb == 0:
		return ""
	return "a" if na >= nb else "b"

func smoke_blocks(a: Vector3, b: Vector3) -> bool:
	# нужен доступ к game.smokes — делегируем через game.nade_system если есть
	var smokes: Array = game.smokes if "smokes" in game else (game.nade_system.smokes if game.nade_system else [])
	for s in smokes:
		var c: Vector3 = s["pos"] + Vector3(0, 1.4, 0)
		var r: float = s["r"]
		var ab := b - a
		var t := clampf((c - a).dot(ab) / maxf(ab.length_squared(), 0.0001), 0.0, 1.0)
		if (a + ab * t).distance_to(c) < r:
			return true
	return false

func noise(pos: Vector3, from: Actor) -> void:
	for a in game.actors:
		if a != from and a.alive and a.team != from.team and a.has_meta("brain"):
			(a.get_meta("brain") as Brain).hear(pos)

func clear() -> void:
	reports = {"t": [], "ct": []}
