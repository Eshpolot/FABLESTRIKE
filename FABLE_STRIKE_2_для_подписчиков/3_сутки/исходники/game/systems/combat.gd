class_name Combat
extends Node
## Боевая система: пули, урон, звук выстрелов, попадания.
## Вынесено из match.gd — теперь баланс оружия правится тут, без касания раундов.

var game # Match

func setup(g) -> void:
	game = g

# --- звуки ---

func play3d(n: String, pos: Vector3, vol := 0.0, pitch := 1.0, unit := 6.0, max_d := 90.0) -> void:
	Sfx.at(n, pos, vol, pitch, unit, max_d)

func gun_sound(a: Actor, wid: String) -> void:
	var d: Dictionary = DB.W[wid]
	var snd: String = d.get("snd", "pistol")
	var n := {"ak": "ak_shot", "m4": "m4_shot", "pistol": "pistol_shot", "usp": "usp_shot", "deagle": "deagle_shot", "smg": "smg_shot", "shotgun": "shotgun_shot", "sniper": "sniper_shot"}.get(snd, "pistol_shot") as String
	if not Sfx.has(n):
		n = "pistol_shot"
	var pitch := randf_range(0.96, 1.04)
	if a == game.player and game.player.alive:
		Sfx.play(n, -5.0, pitch)
	else:
		var dist := a.global_position.distance_to(game.player.global_position if game.player else Vector3.ZERO)
		Sfx.at(n, a.eye(), 2.0, pitch, 9.0, 140.0)
		if dist > 35.0 and Sfx.has("shot_far"):
			Sfx.at("shot_far", a.eye(), -4.0, pitch, 16.0, 200.0)
	if snd != "usp":
		game.intel.noise(a.global_position, a)
	game.fx.flash(a.eye() - Basis(Vector3.UP, a.view_yaw).z * 0.9, 2.2, 6.0, 0.05)

func reload_sound(a: Actor, wid: String) -> void:
	var cls: String = DB.W[wid]["cls"]
	if a == game.player and game.player.alive:
		return
	var n := "reload_pistol" if cls == "pistol" and Sfx.has("reload_pistol") else "reload"
	game.sound_at(n, a.eye(), -6.0, a)

func footstep(a: Actor) -> void:
	var surf := game.world.surface_at(a.global_position)
	var n := "step_sand" if surf == "sand" else ("step_tile" if surf == "tile" and Sfx.has("step_tile") else "step")
	if a == game.player and game.player.alive:
		if G.args.has("sndlog"):
			game._ev("step bob=%.2f" % absf(sin(game.player.step_ph)))
		Sfx.play(n, -13.0, randf_range(0.93, 1.07))
	else:
		Sfx.at(n, a.global_position, -3.0, randf_range(0.93, 1.07), 5.0, 38.0)
		for o in game.actors:
			if o != a and o.alive and o.team != a.team and o.has_meta("brain") and o.global_position.distance_to(a.global_position) < 16.0:
				(o.get_meta("brain") as Brain).hear(a.global_position)

# --- урон ---

func on_hurt(v: Actor, attacker: Actor, n: int, zone: String, armored: bool, from_pos: Vector3) -> void:
	if v == game.player:
		game.hud.damage_from(from_pos, n)
		Sfx.play("hurt", -6.0, randf_range(0.95, 1.05))
	if zone == "head":
		Sfx.at("headshot", v.eye(), 0.0 if attacker == game.player else -6.0, 1.0, 6.0, 60.0)
	elif armored:
		Sfx.at("hit_armor", v.eye(), -8.0, 1.0, 4.0, 40.0)
	else:
		Sfx.at("hit_body", v.eye(), -8.0, 1.0, 4.0, 40.0)
	if v.has_meta("brain") and attacker and attacker.alive:
		(v.get_meta("brain") as Brain).hear(attacker.global_position)

func on_death(v: Actor, killer: Actor, wid: String, headshot: bool) -> void:
	if killer and killer != v:
		killer.kills += 1
		killer.round_kills += 1
		killer.score += 2
		killer.money = mini(DB.MAX_MONEY, killer.money + int(DB.W.get(wid, {}).get("reward", 300)))
	for o in v.dmg_from:
		if o != killer and is_instance_valid(o) and int(v.dmg_from[o]) >= 40:
			o.assists += 1
			o.score += 1
	game.hud.kill(killer, v, wid, headshot)
	Sfx.at("death", v.global_position + Vector3(0, 1, 0), -4.0, randf_range(0.9, 1.1), 5.0, 45.0)
	if v.inv[5] == "c4":
		v.inv[5] = ""
		game.bomb_system.drop_bomb(v.global_position)
	if v == game.player:
		game.player.on_player_death(killer)
	if killer == game.player and game.player.alive:
		Sfx.play("kill", -8.0)

# --- пули ---

func bullet(shooter: Actor, from: Vector3, dir: Vector3, wid: String, first: bool) -> void:
	var d: Dictionary = DB.W[wid]
	var dmg: float = d["dmg"]
	var pen_left: float = d.get("wall", 0.5)
	var pos := from
	var space := game.get_world_3d().direct_space_state
	var remaining := 190.0
	var start_vis := from
	if shooter == game.player and game.player.vm:
		start_vis = game.player.vm.muzzle_world()
	elif shooter.body:
		start_vis = shooter.body.muzzle_pos()
	var end := from + dir * remaining
	for iter in 4:
		var q := PhysicsRayQueryParameters3D.create(pos, pos + dir * remaining, 5)
		q.exclude = shooter.hit_rids
		q.hit_from_inside = false
		var hit := space.intersect_ray(q)
		if hit.is_empty():
			break
		var hp: Vector3 = hit["position"]
		end = hp
		var col: Object = hit["collider"]
		var travelled := from.distance_to(hp)
		if col.has_meta("actor"):
			var v: Actor = col.get_meta("actor")
			var zone: String = col.get_meta("zone")
			if v.team != shooter.team and v.alive:
				var dm := dmg * pow(float(d["rmod"]), travelled / 12.7) * float(DB.ZONE[zone])
				game.fx.blood(hp, -dir)
				v.take_damage(dm, shooter, wid, zone, from)
				if shooter == game.player:
					game.hud.hit_marker(zone == "head", not v.alive)
			break
		var nrm: Vector3 = hit["normal"]
		game.fx.impact(hp, nrm, "stone")
		if first or iter == 0:
			Sfx.at("impact", hp, -10.0, randf_range(0.9, 1.15), 3.0, 30.0)
			if randf() < 0.1:
				Sfx.at("ricochet", hp, -12.0, randf_range(0.9, 1.1), 4.0, 40.0)
		var lim := pen_left * (1.0 if col.has_meta("wood") else 0.2)
		if lim < 0.12:
			break
		var exit_at := -1.0
		var pq := PhysicsPointQueryParameters3D.new()
		pq.collision_mask = 1
		var s := 0.12
		while s <= lim:
			pq.position = hp + dir * s
			if space.intersect_point(pq, 1).is_empty():
				exit_at = s
				break
			s += 0.12
		if exit_at < 0.0:
			break
		dmg *= 0.75 * (1.0 - 0.4 * exit_at / lim)
		pen_left -= exit_at * (1.0 if col.has_meta("wood") else 5.0)
		pos = hp + dir * (exit_at + 0.01)
		remaining -= travelled
		game.fx.impact(pos, dir, "stone")
		if remaining < 1.0 or dmg < 3.0:
			break
	if first:
		game.fx.tracer(start_vis, end)
		if shooter != game.player and game.player and game.player.alive and shooter.team != game.player.team:
			var pe := game.player.eye()
			var ab := end - from
			var tt := clampf((pe - from).dot(ab) / maxf(ab.length_squared(), 0.001), 0.0, 1.0)
			if tt > 0.05 and (from + ab * tt).distance_to(pe) < 1.7:
				Sfx.play("whiz", -7.0, randf_range(0.9, 1.1))

func knife_hit(a: Actor, alt: bool) -> void:
	var space := game.get_world_3d().direct_space_state
	var from := a.eye()
	var dir := -a.aim_basis(false).z
	var reach := 1.55 if not alt else 1.3
	var q := PhysicsRayQueryParameters3D.create(from, from + dir * reach, 5)
	q.exclude = a.hit_rids
	var hit := space.intersect_ray(q)
	if hit.is_empty():
		return
	var col: Object = hit["collider"]
	if col.has_meta("actor"):
		var v: Actor = col.get_meta("actor")
		if v.team != a.team and v.alive:
			var back := (-Basis(Vector3.UP, v.view_yaw).z).dot(dir) > 0.45
			var dm := 65.0 if alt else 40.0
			if back:
				dm = 180.0 if alt else 90.0
			game.fx.blood(hit["position"], -dir)
			game.sound_at("knife_hit", hit["position"], -2.0, a)
			v.take_damage(dm, a, "knife", "chest", from)
			if a == game.player:
				game.hud.hit_marker(false, not v.alive)
	else:
		game.fx.impact(hit["position"], hit["normal"])
		game.sound_at("knife_wall", hit["position"], -6.0, a)
