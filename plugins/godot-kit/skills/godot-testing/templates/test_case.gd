extends RefCounted
## Базовый класс тестов. Каждый метод test_* в наследнике — отдельный тест.
## Своя мини-библиотека вместо внешних аддонов (меньше зависимостей = меньше риска цепочки поставок).

var failures: Array[String] = []


func check(cond: bool, msg: String) -> void:
	if not cond:
		failures.append(msg)


func check_eq(actual: Variant, expected: Variant, msg: String) -> void:
	if actual != expected:
		failures.append("%s (ожидали %s, получили %s)" % [msg, str(expected), str(actual)])


func check_near(actual: float, expected: float, eps: float, msg: String) -> void:
	if absf(actual - expected) > eps:
		failures.append("%s (ожидали ~%s, получили %s)" % [msg, str(expected), str(actual)])
