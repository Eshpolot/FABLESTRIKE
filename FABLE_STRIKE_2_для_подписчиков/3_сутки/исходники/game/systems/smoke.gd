class_name Smoke
extends RefCounted
## Дымовая завеса — типизированная замена Dictionary {"pos":..., "r":...}
## P1.1: вместо s["pos"] → s.pos, опечатка ловится парсером.

var pos: Vector3
var r: float        # радиус блокировки видимости
var t: float        # осталось секунд
var node: Node3D    # визуальный узел из Fx

func _init(p_pos: Vector3, p_r: float, p_t: float, p_node: Node3D) -> void:
	pos = p_pos
	r = p_r
	t = p_t
	node = p_node
