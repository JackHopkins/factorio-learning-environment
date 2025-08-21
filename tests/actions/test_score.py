

def test_get_score(game):
    score, _ = game.score()
    assert isinstance(score, int)
