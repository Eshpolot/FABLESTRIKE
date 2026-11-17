extends Node
## Точка входа: обычный запуск -> меню; с ключами проверки -> сразу нужная сцена.

func _ready() -> void:
	await get_tree().process_frame
	if G.args.has("match"):
		G.start_match()
	elif G.args.has("test"):
		get_tree().change_scene_to_file("res://tools/test_%s.tscn" % G.args["test"])
	else:
		G.to_menu()
