def digit_sum(num):
    total = 0
    while num > 0:
        total += remainder
        num //= 10
    return total

print(digit_sum(123))
