from indicators.haco import tema, zero_lag_from_tema, compute_haco


def test_tema_constant():
    data = [1.0] * 5
    t = tema(data, 3)
    assert all(abs(x - 1.0) < 1e-6 for x in t)


def test_zero_lag():
    t1 = [1, 2, 3]
    t2 = [0.5, 1.5, 2.5]
    zl = zero_lag_from_tema(t1, t2)
    assert zl == [1.5, 2.5, 3.5]


def test_compute_haco_transitions():
    candles = [
        {"time":1,"o":1,"h":1.1,"l":0.9,"c":1.05},
        {"time":2,"o":1.05,"h":1.2,"l":1.0,"c":1.15},
        {"time":3,"o":1.15,"h":1.2,"l":1.1,"c":1.12},
        {"time":4,"o":1.12,"h":1.15,"l":0.8,"c":0.85},
        {"time":5,"o":0.85,"h":0.9,"l":0.7,"c":0.75},
        {"time":6,"o":0.75,"h":0.95,"l":0.7,"c":0.92},
        {"time":7,"o":0.92,"h":1.0,"l":0.9,"c":0.96},
        {"time":8,"o":0.96,"h":1.2,"l":0.95,"c":1.1},
    ]
    res = compute_haco(candles, length_up=2, length_down=2)
    s = res["series"]
    assert s[4]["dnw"] is True
    assert s[7]["upw"] is True
    assert res["last"]["state"] == 1
