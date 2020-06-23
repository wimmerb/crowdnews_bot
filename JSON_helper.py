def listify(dctin):
    dct = dctin.copy()
    for k, v in dct.items():
        dct[k] = list(v)
    return dct


def setify(dctin):
    dct = dctin.copy()
    for k, v in dct.items():
        dct[k] = set(v)
    return dct