# Демонстрационная программа на Ruby для анализа метрик Холстеда: содержит
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
