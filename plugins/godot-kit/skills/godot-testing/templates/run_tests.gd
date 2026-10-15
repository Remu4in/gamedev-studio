extends SceneTree
## Запуск всех юнит-тестов:
##   godot --headless --path . --script res://tests/run_tests.gd
## Находит tests/test_*.gd, вызывает все методы test_*, печатает PASS/FAIL. Код выхода 1, если есть падения.

const TEST_DIR := "res://tests/"


func _initialize() -> void:
	# Ждём кадр, чтобы autoload (Game) успел инициализироваться.
	await process_frame
	var total := 0
	var failed := 0
	var files := DirAccess.get_files_at(TEST_DIR)
	files.sort()
	for f in files:
		if not (f.begins_with("test_") and f.ends_with(".gd")) or f == "test_case.gd":
			continue
		var script := load(TEST_DIR + f) as GDScript
		if script == null:
			print("FAIL  %s — не загрузился (ошибка компиляции?)" % f)
			failed += 1
			continue
		for m in script.get_script_method_list():
			var name: String = m["name"]
			if not name.begins_with("test_"):
				continue
			total += 1
			var inst: Object = script.new()
			await inst.call(name)
			var errs: Array = inst.failures
			if errs.is_empty():
				print("PASS  %s :: %s" % [f, name])
			else:
				failed += 1
				print("FAIL  %s :: %s" % [f, name])
				for e in errs:
					print("        - " + str(e))
	print("\nИТОГО: %d тестов, упало %d" % [total, failed])
	quit(1 if failed > 0 else 0)
