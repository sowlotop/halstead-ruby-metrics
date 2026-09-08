# -*- coding: utf-8 -*-
"""
Анализатор метрик Холстеда для программ на языке Ruby.

Программа-парсер с графическим интерфейсом (Tkinter).
Читает исходный код на Ruby, выделяет ОПЕРАТОРЫ и ОПЕРАНДЫ,
подсчитывает 6 базовых и 3 расширенные метрики Холстеда и
выводит результат в виде таблицы (аналог Таблицы 2 из методических
указаний), а также отдельно три расширенные (производные) метрики.

Автор: лабораторная работа "Метрики размера программ".
"""

import re
import math
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font as tkfont


# ======================================================================
#  ЯДРО: ТОКЕНИЗАТОР RUBY + РАСЧЁТ МЕТРИК ХОЛСТЕДА
# ======================================================================
#
#  Правила выделения операторов и операндов (интерпретация Холстеда,
#  адаптированная под язык Ruby):
#
#  Не учитываются:
#     - пробелы, символы перевода строки;
#     - комментарии (# ... до конца строки и блок =begin ... =end).
#
#  ОПЕРАНДЫ (словарь операндов):
#     - имена переменных: локальные, @переменная, @@переменная, $глобальная;
#     - константы-значения (идентификаторы с заглавной буквы, кроме вызовов);
#     - литералы: целые и вещественные числа, строки, символы (:foo),
#       регулярные выражения, а также true, false, nil.
#     Именем операнда служит его текст; частота f2i — число вхождений.
#
#  ОПЕРАТОРЫ (словарь операторов):
#     - символьные операции (по «жадному» правилу, длинные — раньше):
#       + - * / % **  = += -= *= /= %= **=  == != <=> === < > <= >=
#       && || ! and or not  & | ^ ~ << >>  .. ...  ? :  => ->  =~ !~
#       . &. ::  ,  ;
#     - парные скобки, учитываются как ОДИН оператор на пару:
#         ( )  — группировка подвыражения,
#         name( ) — вызов метода/функции (скобки входят в имя вызова),
#         [ ]  — индексация / литерал массива,
#         { }  — блок / литерал хэша;
#     - имена методов/функций (вызовы) считаются операторами
#       (аналог Readln, Writeln, abs в примере методички);
#     - управляющие «составные» операторы — одно вхождение на пару
#       «открывающее слово … end»:
#         def…end, class…end, module…end, begin…end, case…end,
#         if…end, unless…end, while…end, until…end, for…end, do…end.
#       Промежуточные слова (then, else, elsif, when, in, rescue,
#       ensure) входят в составной оператор и отдельно НЕ считаются;
#     - постфиксные модификаторы if/unless/while/until (без end) и
#       отдельные ключевые слова (return, yield, break, next, and, or,
#       not, …) — каждое считается самостоятельным оператором.
#
#  Метки к операторам и операндам не относятся.
# ======================================================================


# Ключевые слова, открывающие «составной» оператор с закрытием end
OPENERS = {"def", "class", "module", "begin", "case", "do",
           "if", "unless", "while", "until", "for"}

# Слова, которые всегда открывают блок (закрываются end)
ALWAYS_OPENER = {"def", "class", "module", "begin", "case", "do"}

# Слова if/unless/while/until/for могут быть модификаторами (без end)
MODIFIABLE = {"if", "unless", "while", "until"}

# Промежуточные части составных операторов — отдельно не считаем
INNER_KEYWORDS = {"then", "else", "elsif", "when", "in", "rescue", "ensure"}

# Ключевые слова-операторы, стоящие обособленно
KEYWORD_OPERATORS = {"return", "yield", "break", "next", "redo", "retry",
                     "and", "or", "not", "defined?", "super", "__method__"}

# Значения-литералы, считающиеся операндами
KEYWORD_OPERANDS = {"true", "false", "nil", "self", "__FILE__", "__LINE__"}

# Встроенные команды, считающиеся операторами даже без скобок
BUILTIN_COMMANDS = {"puts", "print", "p", "pp", "gets", "require",
                    "require_relative", "load", "raise", "sleep", "rand",
                    "srand", "loop", "attr_accessor", "attr_reader",
                    "attr_writer", "include", "extend", "private", "public",
                    "protected", "exit", "abort", "catch", "throw", "lambda",
                    "proc", "format", "sprintf", "printf"}

# Символьные операторы — порядок важен (длинные раньше коротких)
SYMBOL_OPERATORS = [
    "**=", "<<=", ">>=", "&&=", "||=", "<=>", "===", "...",
    "**", "==", "!=", "<=", ">=", "&&", "||", "<<", ">>",
    "=~", "!~", "&.", "::", "=>", "->", "+=", "-=", "*=", "/=",
    "%=", "&=", "|=", "^=", "..",
    "=", "+", "-", "*", "/", "%", "<", ">", "!", "&", "|",
    "^", "~", "?", ",", ".", ":", ";",
]


class RubyHalsteadAnalyzer:
    """Токенизирует Ruby-код и вычисляет метрики Холстеда."""

    def __init__(self):
        self.operators = {}   # имя оператора -> частота f1j
        self.operands = {}    # имя операнда  -> частота f2i
        self.tokens = []      # список (категория, текст) для отладки

    # ------------------------------------------------------------------
    def analyze(self, source: str) -> dict:
        """Полный анализ. Возвращает словарь с метриками и таблицами."""
        self.operators = {}
        self.operands = {}
        self.tokens = []

        raw = self._tokenize(source)
        self._classify(raw)

        eta1 = len(self.operators)             # словарь операторов
        eta2 = len(self.operands)              # словарь операндов
        N1 = sum(self.operators.values())      # общее число операторов
        N2 = sum(self.operands.values())       # общее число операндов

        eta = eta1 + eta2                       # словарь программы
        N = N1 + N2                             # длина программы
        V = N * math.log2(eta) if eta > 0 else 0.0   # объём программы

        # Таблицы, отсортированные по убыванию частоты (как в примере)
        op_table = sorted(self.operators.items(),
                          key=lambda kv: (-kv[1], kv[0]))
        opnd_table = sorted(self.operands.items(),
                            key=lambda kv: (-kv[1], kv[0]))

        return {
            "operators": op_table,     # [(имя, f1j), ...]
            "operands": opnd_table,    # [(имя, f2i), ...]
            "eta1": eta1, "eta2": eta2,
            "N1": N1, "N2": N2,
            "eta": eta, "N": N, "V": V,
        }

    # ------------------------------------------------------------------
    #  Шаг 1. Разбиение исходного текста на «сырые» токены
    # ------------------------------------------------------------------
    def _tokenize(self, s: str):
        tokens = []          # список кортежей (тип, текст, at_stmt_start)
        i = 0
        n = len(s)
        at_line_start = True    # первый значимый токен в строке?

        # Регулярные выражения для отдельных видов токенов
        re_ws = re.compile(r"[ \t\r]+")
        re_ident = re.compile(r"[A-Za-z_][A-Za-z0-9_]*[?!]?")
        re_ivar = re.compile(r"@@?[A-Za-z_][A-Za-z0-9_]*")
        re_gvar = re.compile(r"\$[A-Za-z_][A-Za-z0-9_]*")
        re_num = re.compile(
            r"0[xX][0-9a-fA-F_]+|0[bB][01_]+|"
            r"\d[\d_]*\.\d[\d_]*(?:[eE][+-]?\d+)?|"
            r"\d[\d_]*(?:[eE][+-]?\d+)?")
        re_symbol = re.compile(r":[A-Za-z_][A-Za-z0-9_]*[?!]?")

        while i < n:
            c = s[i]

            # --- перевод строки ---
            if c == "\n":
                at_line_start = True
                i += 1
                continue

            # --- пробелы/табуляции ---
            m = re_ws.match(s, i)
            if m:
                i = m.end()
                continue

            # --- блочный комментарий =begin ... =end ---
            if at_line_start and s.startswith("=begin", i):
                end = s.find("\n=end", i)
                if end == -1:
                    break
                nl = s.find("\n", end + 1)
                i = nl + 1 if nl != -1 else n
                at_line_start = True
                continue

            # --- строчный комментарий # ... ---
            if c == "#":
                nl = s.find("\n", i)
                i = nl if nl != -1 else n
                continue

            stmt_start = at_line_start
            at_line_start = False

            # --- строковые литералы ---
            if c == '"' or c == "'":
                j = self._scan_string(s, i, c)
                tokens.append(("operand", s[i:j], stmt_start))
                i = j
                continue

            # --- регулярное выражение вида /.../ (эвристика) ---
            if c == "/" and self._regex_allowed(tokens):
                j = self._scan_regex(s, i)
                if j > i + 1:
                    tokens.append(("operand", s[i:j], stmt_start))
                    i = j
                    continue

            # --- символ :foo ---
            if c == ":" and not s.startswith("::", i):
                m = re_symbol.match(s, i)
                if m:
                    tokens.append(("operand", m.group(), stmt_start))
                    i = m.end()
                    continue

            # --- @переменная / @@переменная ---
            m = re_ivar.match(s, i)
            if m:
                tokens.append(("operand", m.group(), stmt_start))
                i = m.end()
                continue

            # --- $глобальная ---
            m = re_gvar.match(s, i)
            if m:
                tokens.append(("operand", m.group(), stmt_start))
                i = m.end()
                continue

            # --- число ---
            m = re_num.match(s, i)
            if m and (c.isdigit()):
                tokens.append(("number", m.group(), stmt_start))
                i = m.end()
                continue

            # --- идентификатор / ключевое слово ---
            m = re_ident.match(s, i)
            if m:
                tokens.append(("ident", m.group(), stmt_start))
                i = m.end()
                continue

            # --- скобки ---
            if c in "()[]{}":
                tokens.append(("bracket", c, stmt_start))
                i += 1
                continue

            # --- символьные операторы ---
            matched = None
            for op in SYMBOL_OPERATORS:
                if s.startswith(op, i):
                    matched = op
                    break
            if matched:
                tokens.append(("sym", matched, stmt_start))
                i += len(matched)
                continue

            # --- неизвестный символ — пропускаем ---
            i += 1

        return tokens

    # ------------------------------------------------------------------
    def _scan_string(self, s, i, quote):
        """Пропускает строковый литерал, возвращает индекс после него."""
        j = i + 1
        n = len(s)
        while j < n:
            if s[j] == "\\":
                j += 2
                continue
            if s[j] == quote:
                return j + 1
            j += 1
        return n

    def _scan_regex(self, s, i):
        """Пропускает /.../ регулярное выражение."""
        j = i + 1
        n = len(s)
        while j < n:
            if s[j] == "\\":
                j += 2
                continue
            if s[j] == "\n":
                return i + 1          # не регэксп
            if s[j] == "/":
                j += 1
                while j < n and s[j].isalpha():   # флаги imxo
                    j += 1
                return j
            j += 1
        return i + 1

    def _regex_allowed(self, tokens):
        """Эвристика: / — начало регэкспа, если перед ним не операнд."""
        # ищем последний значимый токен
        for typ, txt, _ in reversed(tokens):
            if typ in ("operand", "number", "ident"):
                return False
            if typ == "bracket" and txt in ")]}":
                return False
            return True
        return True

    # ------------------------------------------------------------------
    #  Шаг 2. Классификация токенов на операторы и операнды
    # ------------------------------------------------------------------
    def _classify(self, tokens):
        stack = []          # стек открытых составных операторов
        i = 0
        m = len(tokens)

        def prev_significant(idx):
            k = idx - 1
            while k >= 0:
                return tokens[k]
            return None

        while i < m:
            typ, txt, stmt_start = tokens[i]
            nxt = tokens[i + 1] if i + 1 < m else None
            prev = tokens[i - 1] if i - 1 >= 0 else None

            # ---------- числа ----------
            if typ == "number":
                self._add_operand(txt)
                i += 1
                continue

            # ---------- готовые операнды (строки, символы, @/$ перем.) --
            if typ == "operand":
                self._add_operand(txt)
                i += 1
                continue

            # ---------- идентификаторы / ключевые слова ----------
            if typ == "ident":
                word = txt

                # end закрывает составной оператор
                if word == "end":
                    if stack:
                        opener = stack.pop()
                        self._add_operator(opener + "…end")
                    else:
                        self._add_operator("end")
                    i += 1
                    continue

                # промежуточные слова составного оператора — пропускаем
                if word in INNER_KEYWORDS:
                    i += 1
                    continue

                # значения-литералы (true/false/nil/self)
                if word in KEYWORD_OPERANDS:
                    self._add_operand(word)
                    i += 1
                    continue

                # управляющие ключевые слова
                if word in OPENERS:
                    is_opener = True
                    if word in MODIFIABLE:
                        is_opener = self._is_block_opener(prev, stmt_start)
                    if is_opener:
                        stack.append(word)
                    else:
                        # постфиксный модификатор
                        self._add_operator(word + "(mod)")
                    i += 1
                    continue

                # отдельные ключевые слова-операторы
                if word in KEYWORD_OPERATORS:
                    self._add_operator(word)
                    i += 1
                    continue

                # вызов метода: name( ... )
                if nxt and nxt[0] == "bracket" and nxt[1] == "(":
                    self._add_operator(word + "( )")
                    # пропускаем скобку вызова (пара учтена в имени)
                    self._skip_pair(tokens, i + 1)
                    i += 1
                    continue

                # метод после точки:  obj.method  /  obj&.method
                if prev and prev[0] == "sym" and prev[1] in (".", "&.", "::"):
                    self._add_operator(word)
                    i += 1
                    continue

                # встроенная команда без скобок (puts x и т.п.)
                if word in BUILTIN_COMMANDS:
                    self._add_operator(word)
                    i += 1
                    continue

                # иначе — переменная/константа (операнд)
                self._add_operand(word)
                i += 1
                continue

            # ---------- скобки ----------
            if typ == "bracket":
                if txt == "(":
                    self._add_operator("( )")
                    self._skip_pair(tokens, i)
                elif txt == "[":
                    self._add_operator("[ ]")
                    self._skip_pair(tokens, i)
                elif txt == "{":
                    self._add_operator("{ }")
                    self._skip_pair(tokens, i)
                # закрывающие скобки пропускаются skip_pair-ом,
                # но если встретились «одиночно» — игнорируем
                i += 1
                continue

            # ---------- символьные операторы ----------
            if typ == "sym":
                self._add_operator(txt)
                i += 1
                continue

            i += 1

    # ------------------------------------------------------------------
    def _is_block_opener(self, prev, stmt_start):
        """Определяет, открывает ли if/unless/while/until блок (…end).

        Блок, если слово в начале инструкции ИЛИ перед ним стоит
        оператор, ожидающий значение (=, (, ',', return, and, or …).
        Модификатор — если перед ним завершённое выражение.
        """
        if stmt_start:
            return True
        if prev is None:
            return True
        ptyp, ptxt, _ = prev
        # завершённое выражение перед словом => модификатор
        if ptyp in ("operand", "number", "ident"):
            return False
        if ptyp == "bracket" and ptxt in ")]}":
            return False
        # перед словом стоит символьный оператор => блок-выражение
        return True

    def _skip_pair(self, tokens, open_idx):
        """Ставит пометку, чтобы соответствующая закрывающая скобка
        не была посчитана повторно (реализовано через замену токена)."""
        depth = 0
        open_ch = tokens[open_idx][1]
        close_ch = {"(": ")", "[": "]", "{": "}"}[open_ch]
        j = open_idx
        m = len(tokens)
        while j < m:
            t = tokens[j]
            if t[0] == "bracket" and t[1] == open_ch:
                depth += 1
            elif t[0] == "bracket" and t[1] == close_ch:
                depth -= 1
                if depth == 0:
                    # «гасим» закрывающую скобку
                    tokens[j] = ("consumed", close_ch, t[2])
                    return
            j += 1

    # ------------------------------------------------------------------
    def _add_operator(self, name):
        self.operators[name] = self.operators.get(name, 0) + 1

    def _add_operand(self, name):
        self.operands[name] = self.operands.get(name, 0) + 1


# ======================================================================
#  ГРАФИЧЕСКИЙ ИНТЕРФЕЙС (Tkinter)
# ======================================================================

SAMPLE_RUBY = '''# Демонстрационная программа на Ruby для анализа метрик Холстеда: содержит
# все основные операторы языка и пользовательские подпрограммы (def...end).
# Подпрограмма: факториал (рекурсия, условный оператор-модификатор)
def factorial(n)
  return 1 if n <= 1
  n * factorial(n - 1)
end
# Подпрограмма: sin(x) через разложение в ряд Тейлора
def sin_series(x, eps = 0.0001)
  term = x
  result = x
  k = 1
  while term.abs > eps
    term = -term * x * x / ((2 * k) * (2 * k + 1))
    result += term
    k += 1
  end
  result
end
# Подпрограмма: наибольший общий делитель (цикл until, остаток от деления)
def gcd(a, b)
  until b == 0
    a, b = b, a % b
  end
  a.abs
end
# Подпрограмма: классификация числа (оператор выбора case...when)
def classify(num)
  case
  when num < 0 then "отрицательное"
  when num == 0 then "ноль"
  when num.even? then "чётное положительное"
  else "нечётное положительное"
  end
end
# Подпрограмма с блоком: возводит элементы в квадрат (yield, цикл for)
def each_squared(list)
  count = 0
  for item in list
    yield(item ** 2)
    count += 1
  end
  count
end
# Подпрограмма: побитовые операции (& | ^ ~ << >>)
def bitwise_demo(a, b)
  res = {}
  res[:and] = a & b
  res[:or]  = a | b
  res[:xor] = a ^ b
  res[:not] = ~a
  res[:shl] = a << 2
  res[:shr] = a >> 1
  res
end

# ------------------------- Основная программа -------------------------
numbers = [5, -3, 8, 0, 12, 7]
total = 0
product = 1
numbers.each do |value|
  total += value
  product *= value unless value == 0
end
average = numbers.length > 0 ? total.to_f / numbers.length : 0.0
valid = !numbers.empty? && (total >= 0 || product < 0)
sorted = numbers.sort { |a, b| a <=> b }
puts "Числа: #{numbers.join(', ')}"
puts "Сумма = #{total}, произведение = #{product}, среднее = #{average.round(2)}"
puts "Мин = #{sorted.first}, макс = #{sorted.last}, признак = #{valid}"
puts "Все положительные" if sorted.first > 0 and sorted.last > 0
puts "Есть нули" if not numbers.all? { |v| v != 0 }
step = total
step -= sorted.first
step /= 2
puts "Контрольное значение = #{step}"
for k in 0...numbers.length
  n = numbers[k]
  sign = n >= 0 ? "+" : "-"
  puts "#{sign} #{n} — #{classify(n)}"
end
puts "5! = #{factorial(5)}"
puts "sin(1.0) ≈ #{sin_series(1.0).round(5)}"
puts "НОД(48, 36) = #{gcd(48, 36)}"
processed = each_squared(1..3) do |sq|
  print "#{sq} "
end
puts
puts "Обработано элементов: #{processed}"
bitwise_demo(12, 10).each do |name, val|
  puts "#{name} => #{val}"
end
begin
  risky = 10 / (numbers.length - numbers.length)
rescue ZeroDivisionError => e
  puts "Ошибка: деление на ноль"
ensure
  puts "Готово."
end
'''


class HalsteadApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Метрики Холстеда — анализатор кода на Ruby")
        self.geometry("1000x720")
        self.minsize(820, 600)
        self.analyzer = RubyHalsteadAnalyzer()

        self._build_widgets()

    # ------------------------------------------------------------------
    def _build_widgets(self):
        # ---- Заголовок ----
        header = ttk.Frame(self, padding=(12, 10, 12, 4))
        header.pack(fill="x")
        ttk.Label(header,
                  text="Расчёт метрик Холстеда для программы на языке Ruby",
                  font=("Helvetica", 15, "bold")).pack(anchor="w")
        ttk.Label(header,
                  text="Введите или загрузите исходный код на Ruby и нажмите "
                       "«Анализировать».",
                  foreground="#555").pack(anchor="w")

        # ---- Панель кнопок ----
        toolbar = ttk.Frame(self, padding=(12, 4))
        toolbar.pack(fill="x")
        ttk.Button(toolbar, text="Открыть .rb…",
                   command=self._open_file).pack(side="left")
        ttk.Button(toolbar, text="Вставить пример",
                   command=self._load_sample).pack(side="left", padx=6)
        ttk.Button(toolbar, text="Очистить",
                   command=self._clear).pack(side="left")
        ttk.Button(toolbar, text="Анализировать  ▶",
                   command=self._analyze).pack(side="right")

        # ---- Блок расширенных метрик (всегда внизу окна) ----
        ext = ttk.LabelFrame(
            self, text="Расширенные (производные) метрики Холстеда")
        ext.pack(side="bottom", fill="x", padx=12, pady=(0, 12))
        self.ext_label = ttk.Label(
            ext, justify="left", font=("Helvetica", 12),
            text="Словарь программы     η  = η₁ + η₂ = —\n"
                 "Длина программы       N  = N₁ + N₂ = —\n"
                 "Объём программы       V  = N · log₂ η = —")
        self.ext_label.pack(anchor="w", padx=10, pady=8)

        # ---- Разделённая область: ввод сверху, результаты снизу ----
        paned = ttk.PanedWindow(self, orient="vertical")
        paned.pack(fill="both", expand=True, padx=12, pady=(4, 8))

        # Поле ввода кода
        code_frame = ttk.LabelFrame(paned, text="Исходный код на Ruby")
        mono = tkfont.Font(family="Menlo", size=12)
        self.code_text = tk.Text(code_frame, wrap="none", undo=True,
                                 font=mono, height=12)
        yscroll = ttk.Scrollbar(code_frame, orient="vertical",
                                command=self.code_text.yview)
        self.code_text.configure(yscrollcommand=yscroll.set)
        self.code_text.pack(side="left", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")
        paned.add(code_frame, weight=3)

        # Результаты
        result_frame = ttk.Frame(paned)
        paned.add(result_frame, weight=4)
        self._build_results(result_frame)

        # предзаполним примером
        self.code_text.insert("1.0", SAMPLE_RUBY)

    # ------------------------------------------------------------------
    def _build_results(self, parent):
        # Таблицы операторов и операндов бок о бок
        tables = ttk.Frame(parent)
        tables.pack(fill="both", expand=True)
        tables.columnconfigure(0, weight=1)
        tables.columnconfigure(1, weight=1)
        tables.rowconfigure(0, weight=1)

        # --- Операторы ---
        op_box = ttk.LabelFrame(tables, text="Операторы")
        op_box.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self.op_tree = self._make_tree(op_box,
                                       ("j", "Оператор", "f1j"),
                                       (50, 200, 70))
        self.op_footer = ttk.Label(op_box, text="η₁ = 0        N₁ = 0",
                                   font=("Helvetica", 11, "bold"),
                                   foreground="#0a5")
        self.op_footer.pack(fill="x", padx=6, pady=(0, 6))

        # --- Операнды ---
        opnd_box = ttk.LabelFrame(tables, text="Операнды")
        opnd_box.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self.opnd_tree = self._make_tree(opnd_box,
                                         ("i", "Операнд", "f2i"),
                                         (50, 200, 70))
        self.opnd_footer = ttk.Label(opnd_box, text="η₂ = 0        N₂ = 0",
                                     font=("Helvetica", 11, "bold"),
                                     foreground="#0a5")
        self.opnd_footer.pack(fill="x", padx=6, pady=(0, 6))

    def _make_tree(self, parent, columns, widths):
        wrap = ttk.Frame(parent)
        wrap.pack(fill="both", expand=True, padx=6, pady=6)
        tree = ttk.Treeview(wrap, columns=columns, show="headings",
                            height=10)
        headers = {"j": "j", "i": "i", "Оператор": "Оператор",
                   "Операнд": "Операнд", "f1j": "f1j", "f2i": "f2i"}
        for col, w in zip(columns, widths):
            tree.heading(col, text=headers.get(col, col))
            anchor = "center" if col in ("j", "i", "f1j", "f2i") else "w"
            tree.column(col, width=w, anchor=anchor,
                        stretch=(col in ("Оператор", "Операнд")))
        vs = ttk.Scrollbar(wrap, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vs.set)
        tree.pack(side="left", fill="both", expand=True)
        vs.pack(side="right", fill="y")
        return tree

    # ------------------------------------------------------------------
    #  Обработчики
    # ------------------------------------------------------------------
    def _open_file(self):
        path = filedialog.askopenfilename(
            title="Выберите файл Ruby",
            filetypes=[("Ruby", "*.rb"), ("Все файлы", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = f.read()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть файл:\n{e}")
            return
        self.code_text.delete("1.0", "end")
        self.code_text.insert("1.0", data)

    def _load_sample(self):
        self.code_text.delete("1.0", "end")
        self.code_text.insert("1.0", SAMPLE_RUBY)

    def _clear(self):
        self.code_text.delete("1.0", "end")

    def _analyze(self):
        source = self.code_text.get("1.0", "end")
        if not source.strip():
            messagebox.showwarning("Пусто", "Введите исходный код на Ruby.")
            return
        res = self.analyzer.analyze(source)
        self._fill_tables(res)

    def _fill_tables(self, res):
        # операторы
        for row in self.op_tree.get_children():
            self.op_tree.delete(row)
        for idx, (name, freq) in enumerate(res["operators"], start=1):
            self.op_tree.insert("", "end", values=(idx, name, freq))
        self.op_footer.config(
            text=f"η₁ = {res['eta1']}        N₁ = {res['N1']}")

        # операнды
        for row in self.opnd_tree.get_children():
            self.opnd_tree.delete(row)
        for idx, (name, freq) in enumerate(res["operands"], start=1):
            self.opnd_tree.insert("", "end", values=(idx, name, freq))
        self.opnd_footer.config(
            text=f"η₂ = {res['eta2']}        N₂ = {res['N2']}")

        # расширенные метрики
        self.ext_label.config(
            text=(f"Словарь программы     η  = η₁ + η₂ = "
                  f"{res['eta1']} + {res['eta2']} = {res['eta']}\n"
                  f"Длина программы       N  = N₁ + N₂ = "
                  f"{res['N1']} + {res['N2']} = {res['N']}\n"
                  f"Объём программы       V  = N · log₂ η = "
                  f"{res['N']} · log₂ {res['eta']} = {res['V']:.2f} бит"))


def main():
    app = HalsteadApp()
    app.mainloop()


if __name__ == "__main__":
    main()
