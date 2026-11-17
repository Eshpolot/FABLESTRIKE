class_name BombState
extends RefCounted
## Типизированное состояние бомбы — замена Dictionary bomb в match.gd.
## До рефактора: bomb = {"state":"none","pos":...} — опечатка в ключе = молчаливый баг.

enum State { NONE, CARRIED, DROPPED, PLANTED, EXPLODED, DEFUSED }

var state: State = State.NONE
var pos: Vector3 = Vector3.ZERO
var carrier: Actor = null          # кто несёт (null = на земле/заложена)
var site: String = ""              # "a" | "b" | ""
var t: float = 0.0                 # таймер до взрыва (когда PLANTED)
var node: Node3D = null            # 3D-модель C4 в мире
var planter: Actor = null          # кто заложил
var beep: float = 0.0              # таймер писка

func is_carried() -> bool: return state == State.CARRIED
func is_dropped() -> bool: return state == State.DROPPED
func is_planted() -> bool: return state == State.PLANTED

func to_dict() -> Dictionary:
	return {"state": state, "pos": pos, "carrier": carrier, "site": site, "t": t, "node": node, "planter": planter, "beep": beep}

static func str_to_state(s: String) -> State:
	match s:
		"carried": return State.CARRIED
		"dropped": return State.DROPPED
		"planted": return State.PLANTED
		"exploded": return State.EXPLODED
		"defused": return State.DEFUSED
		_: return State.NONE

static func state_to_str(st: State) -> String:
	match st:
		State.CARRIED: return "carried"
		State.DROPPED: return "dropped"
		State.PLANTED: return "planted"
		State.EXPLODED: return "exploded"
		State.DEFUSED: return "defused"
		_: return "none"
