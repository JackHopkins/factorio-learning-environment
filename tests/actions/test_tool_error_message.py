from fle.env.tools.tool import Tool


def parse_error(response: str) -> str:
    return Tool.get_error_message(object.__new__(Tool), response)


def test_error_message_preserves_inventory_reason_and_contents() -> None:
    response = (
        '[string "storage.actions.place_entity"]:148: '
        '"No solar_panel in inventory. Current inventory: '
        'wooden-chest=9, boiler=2"'
    )

    assert parse_error(response) == (
        "No solar_panel in inventory. Current inventory: wooden-chest=9, boiler=2"
    )


def test_error_message_without_lua_prefix_is_not_split_at_colon() -> None:
    response = "Current inventory: wooden-chest=9, boiler=2"

    assert parse_error(response) == response


def test_error_message_preserves_apostrophes_and_inner_colons() -> None:
    response = r'''[string "place_entity"]:12: "solar_panel isn't placeable: blocked by entity"'''

    assert parse_error(response) == "solar_panel isn't placeable: blocked by entity"


def test_error_message_strips_file_path_prefix() -> None:
    response = "__fle__/tools/place_entity/server.lua:148: placement failed"

    assert parse_error(response) == "placement failed"


def test_error_message_does_not_treat_message_error_code_as_source_prefix() -> None:
    response = "Factorio error code:12: placement failed"

    assert parse_error(response) == response
