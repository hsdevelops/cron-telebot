from bot.convos import convo


def test_convo_states():
    assert convo.states.s0 == 0
    assert convo.states.s1 == 1
    assert convo.states.s2 == 2
    assert convo.states.s3 == 3
    assert convo.states.s4 == 4
