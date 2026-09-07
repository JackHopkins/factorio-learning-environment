def test_print_tuple(game):
    """
    Print a tuple
    """
    r = game.print("Hello", "World", (1, 2, 3))

    assert r == "Hello\tWorld\t(1, 2, 3)"


def test_reset_restores_print_tool(game):
    """A loaded legacy namespace must not poison the next episode."""
    game.print = None

    game.instance.reset()

    assert game.print("Hello", "World") == "Hello\tWorld"
