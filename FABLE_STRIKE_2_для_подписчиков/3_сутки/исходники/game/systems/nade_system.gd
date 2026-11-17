class_name NadeSystem
extends Node
## Гранаты, дым, огонь — вся площадная логика.
## P1.1: smokes: Array[Smoke], fires: Array[Fire] — вместо Dictionary.

var game # Match
var smokes: Array[Smoke] = []
var fires: Array[Fire] = []
var nades: Array = []  # Nade ноды

func setup(g) -> void:
	game = g

func clear_round() -> void:
	for n in nades:
		if is_instance_valid(n):
			n.queue_free()
	nades.clear()
	for s in smokes:
		if is_instance_valid(s.node):
			s.node.queue_free()
	smokes.clear()
	for f in fires:
		if is_instance_valid(f.node):
			f.node.queue_free()
	fires.clear()

func throw_nade(owner: Actor, id: String, pos: Vector3, vel: Vector3) -> void:
	var n := Nade.new()
	game.add_child(n)
	n.launch(game, owner, id, pos, vel)
	nades.append(n)
	game.sound_at("nade_throw", pos, -6.0, owner)

func nade_burst(n: Nade) -> void:
	var p := n.global_position
	var id := n.id
	if id == "he":
		game.fx.explosion(p, 4.5)
		game.combat.play3d("explosion", p, 6.0, 1.15, 16.0, 160.0)
		for a in game.actors:
			if a.alive:
				var d: float = (a.global_position + Vector3(0, 0.9, 0)).distance_to(p)
				if d < 8.5 and game.world.los(p + Vector3(0, 0.2, 0), a.eye(), []):
					a.take_damage(98.0 * pow(1.0 - d / 8.5, 1.2), n.thrower, "he", "chest", p)
		if game.player and game.player.global_position.distance_to(p) < 14.0:
			game.player.shake(0.5)
	elif id == "flash":
		game.fx.flash(p, 60.0, 40.0, 0.25, Color(1, 1, 1))
		game.combat.play3d("flash_bang", p, 6.0, 1.0, 14.0, 140.0)
		for a in game.actors:
			if not a.alive:
				continue
			var d2: float = a.eye().distance_to(p)
			if d2 > 38.0 or not game.world.los(p, a.eye(), []):
				continue
			var facing: float = (-a.aim_basis(false).z).dot((p - a.eye()).normalized())
			var t: float = clampf(4.2 * (0.35 + 0.65 * clampf(facing * 0.5 + 0.5, 0.0, 1.0)) * (1.0 - d2 / 45.0), 0.0, 4.5)
			if facing < -0.2:
				t *= 0.3
			a.flash_t = maxf(a.flash_t, t)
			if a == game.player:
				game.hud.flash(t)
	elif id == "smoke":
		var node := game.fx.smoke_cloud(p, 4.6, 18.0)
		smokes.append(Smoke.new(p, 4.3, 18.0, node))
		game.combat.play3d("smoke_hiss", p, 0.0, 1.0, 7.0, 60.0)
	elif id == "molotov":
		var gp := Vector3(p.x, maxf(0.05, p.y - 0.1), p.z)
		var node2 := game.fx.fire_area(gp, 3.2, 7.0)
		fires.append(Fire.new(gp, 3.2, 7.0, node2, n.thrower))
		game.combat.play3d("molotov", p, 2.0, 1.0, 8.0, 70.0)
	elif id == "decoy":
		game.fx.flash(p, 3.0, 5.0, 0.2)
		game.combat.play3d("pistol_shot", p, 0.0, 1.0, 9.0, 120.0)

func tick(dt: float) -> void:
	for s in smokes.duplicate():
		s.t -= dt
		if s.t <= 0.0:
			smokes.erase(s)
	for f in fires.duplicate():
		f.t -= dt
		f.tick -= dt
		if f.tick <= 0.0:
			f.tick = 0.25
			for a in game.actors:
				if a.alive and Vector2(a.global_position.x - f.pos.x, a.global_position.z - f.pos.z).length() < f.r and absf(a.global_position.y - f.pos.y) < 1.5:
					a.take_damage(9.0, f.owner, "fire", "legs", f.pos)
		if f.t <= 0.0:
			fires.erase(f)
