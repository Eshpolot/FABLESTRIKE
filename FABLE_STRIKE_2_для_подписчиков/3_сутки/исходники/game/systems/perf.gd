class_name Perf
extends Node
## P2: Профилирование производительности — счётчики кадра.
## Включается G.args["perf"] или G.settings["show_fps"].

var frame_raycasts := 0
var frame_checks := 0
var fps_avg := 0.0
var t := 0.0

func _process(dt: float) -> void:
	tt += dt
	if t < 0.5:
		return
	t = 0.0
	fps_avg = lerpf(fps_avg, float(Engine.get_frames_per_second()), 0.15)
	if G.args.has("perf"):
		G.log_line("PERF fps %d raycasts %d checks %d mem %dKB" % [int(fps_avg), frame_raycasts, frame_checks, OS.get_static_memory_usage()/1024])
	frame_raycasts = 0
	frame_checks = 0

func inc_raycast(n:=1) -> void: frame_raycasts += n
func inc_check(n:=1) -> void: frame_checks += n
