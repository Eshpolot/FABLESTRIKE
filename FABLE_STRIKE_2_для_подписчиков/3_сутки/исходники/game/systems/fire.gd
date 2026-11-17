class_name Fire
extends RefCounted
## Огонь от молотовой — tip.

var pos: Vector3
var r: float        # радиус поражения
var t: float        # осталось секунд горения
var node: Node3D
var owner: Actor    # кто кинул — для ассистов/урона
var tick: float     # таймер периодического урона (0.25с)

func _init(p_pos: Vector3, p_r: float, p_t: float, p_node: Node3D, p_owner: Actor) -> void:
	pos = p_pos
	r = p_r
	t = p_t
	node = p_node
	owner = p_owner
	tick = 0.0
