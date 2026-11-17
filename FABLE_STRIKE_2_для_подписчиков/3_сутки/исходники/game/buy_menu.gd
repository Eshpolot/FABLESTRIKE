extends Control
## Меню закупки: пять столбцов (пистолеты, ПП и дробовик, винтовки, гранаты, снаряжение), справа — выбранный предмет и его показатели.

var game
var items := {}            # id -> Button
var money_l: Label
var info_name: Label
var info_icon: TextureRect
var info_bars: Control
var info_note: Label
var sel := ""

func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP
	var dim := ColorRect.new()
	dim.color = Color(0, 0, 0, 0.45)
	dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	dim.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(dim)
	var panel := PanelContainer.new()
	panel.add_theme_stylebox_override("panel", UI.box(Color(0.05, 0.06, 0.075, 0.95), 16, 1))
	panel.custom_minimum_size = Vector2(1320, 640)
	var cc := CenterContainer.new()
	cc.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	cc.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(cc)
	cc.add_child(panel)
	var vb := VBoxContainer.new()
	vb.add_theme_constant_override("separation", 12)
	panel.add_child(vb)
	var top := HBoxContainer.new()
	vb.add_child(top)
	top.add_child(UI.label("ЗАКУПКА", 28, UI.TEXT, true))
	var sp := Control.new()
	sp.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	top.add_child(sp)
	money_l = UI.label("$0", 28, UI.GREEN, true)
	top.add_child(money_l)
	var hb := HBoxContainer.new()
	hb.add_theme_constant_override("separation", 12)
	hb.size_flags_vertical = Control.SIZE_EXPAND_FILL
	vb.add_child(hb)
	for col in DB.BUY:
		var cb := VBoxContainer.new()
		cb.custom_minimum_size = Vector2(190, 0)
		cb.add_theme_constant_override("separation", 8)
		hb.add_child(cb)
		var head := UI.label(col[0], 17, UI.DIM, true)
		cb.add_child(head)
		for id in col[1]:
			var b := UI.button("", 17, UI.TEAL, Vector2(190, 78))
			b.alignment = HORIZONTAL_ALIGNMENT_LEFT
			b.pressed.connect(_buy.bind(id))
			b.mouse_entered.connect(_show.bind(id))
			var ic := UI.icon(id)
			if ic:
				b.icon = ic
				b.expand_icon = true
				b.icon_alignment = HORIZONTAL_ALIGNMENT_RIGHT
				b.add_theme_constant_override("icon_max_width", 84)
			cb.add_child(b)
			items[id] = b
	var right := PanelContainer.new()
	right.add_theme_stylebox_override("panel", UI.box(UI.PANEL2, 12))
	right.custom_minimum_size = Vector2(300, 0)
	right.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	hb.add_child(right)
	var rv := VBoxContainer.new()
	rv.add_theme_constant_override("separation", 10)
	right.add_child(rv)
	info_name = UI.label("", 26, UI.TEXT, true)
	rv.add_child(info_name)
	info_icon = TextureRect.new()
	info_icon.custom_minimum_size = Vector2(280, 120)
	info_icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	info_icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	rv.add_child(info_icon)
	info_bars = Control.new()
	info_bars.custom_minimum_size = Vector2(280, 170)
	info_bars.draw.connect(_draw_bars)
	rv.add_child(info_bars)
	info_note = UI.label("", 15, UI.DIM)
	info_note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	rv.add_child(info_note)
	var hint := UI.label("B или Esc — закрыть. Закупка доступна в начале раунда на своей базе.", 14, UI.DIM)
	vb.add_child(hint)

func refresh() -> void:
	var p: Player = game.player
	money_l.text = UI.money(p.money)
	for id in items:
		var b: Button = items[id]
		var nm: String = DB.GEAR[id]["name"] if DB.GEAR.has(id) else DB.W[id]["name"]
		var why := p.can_buy(id)
		b.text = "%s\n%s" % [nm, UI.money(p.price_of(id))]
		b.disabled = why != ""
		b.tooltip_text = why
		var other := false
		if DB.W.has(id) and DB.W[id].has("team") and DB.W[id]["team"] != p.team:
			other = true
		if DB.GEAR.has(id) and DB.GEAR[id].has("team") and DB.GEAR[id]["team"] != p.team:
			other = true
		b.visible = not other

func _buy(id: String) -> void:
	var p: Player = game.player
	if not game.can_buy(p):
		return
	if p.buy(id):
		Sfx.ui("buy", -6.0)
	else:
		Sfx.ui("ui_error", -8.0)
	refresh()

func _show(id: String) -> void:
	sel = id
	info_name.text = DB.GEAR[id]["name"] if DB.GEAR.has(id) else DB.W[id]["name"]
	info_icon.texture = UI.icon(id)
	var notes := {"kevlar": "Снижает урон по корпусу.", "helmet": "Бронежилет и шлем: защищает и голову.", "kit": "Разминирование за 5 секунд вместо 10.",
		"he": "Взрыв с уроном по области.", "flash": "Ослепляет всех, кто смотрит на вспышку.", "smoke": "Дымовая завеса на 18 секунд.",
		"molotov": "Огонь на земле: 7 секунд.", "decoy": "Имитирует выстрелы."}
	info_note.text = notes.get(id, "")
	if DB.W.has(id) and DB.W[id].has("dmg"):
		var d: Dictionary = DB.W[id]
		info_note.text = "Магазин %d / запас %d. Награда за убийство %s." % [d["mag"], d["res"], UI.money(d["reward"])]
	info_bars.queue_redraw()

func _draw_bars() -> void:
	if not DB.W.has(sel) or not DB.W[sel].has("dmg"):
		return
	var d: Dictionary = DB.W[sel]
	var rows := [["Урон", clampf(float(d["dmg"]) * float(d.get("pellets", 1)) / 120.0, 0, 1)], ["Пробитие брони", float(d["pen"])],
		["Скорострельность", clampf(float(d["rpm"]) / 900.0, 0, 1)], ["Подвижность", clampf((float(d["speed"]) - 4.5) / 1.9, 0, 1)],
		["Контроль отдачи", clampf(1.0 - float(d.get("rec", [1.0])[0]) / 6.0, 0, 1)]]
	var y := 6.0
	for r in rows:
		info_bars.draw_string(UI.font(), Vector2(0, y + 12), r[0], HORIZONTAL_ALIGNMENT_LEFT, -1, 14, UI.DIM)
		info_bars.draw_rect(Rect2(0, y + 18, 280, 7), Color(1, 1, 1, 0.1))
		info_bars.draw_rect(Rect2(0, y + 18, 280 * float(r[1]), 7), UI.AMBER)
		y += 33
