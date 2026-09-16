# def yield_test():
#     for i in range(5):
#         yield i
#         print(i, '번째 호출!')

# print(type(yield_test()))  # <class `generator`>

# for k in yield_test():
#     print(k)


def counter():
    print("1 만들기 전")
    yield 1
    print("2 만들기 전")
    yield 2
    print("3 만들기 전")
    yield 3


for i in counter():
    print("받은 값:", i)
    