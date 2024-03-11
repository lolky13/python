tmp = data.split(' ')
    """if not tmp[1].isdigit() or not tmp[2].isdigit():
        print('1')
        return 9999,9999, True"""
    tmp[1] = int(tmp[1])
    tmp[2] = int(tmp[2])
    tmp1 = tmp[0] + ' ' + str(tmp[1]) + ' ' + str(tmp[2])
    if len(tmp) != 3 or tmp1 != data:
        print('2')
        return 9999,9999, True
    return tmp[1], tmp[2], False