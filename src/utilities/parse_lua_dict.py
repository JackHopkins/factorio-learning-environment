def parse_lua_dict(d):
    if all(isinstance(k, int) for k in d.keys()):
        # Convert to list if all keys are numeric
        return [parse_lua_dict(d[k]) for k in sorted(d.keys())]
    else:
        # Process dictionaries with mixed keys
        new_dict = {}
        last_key = None

        for key in d.keys():
            if isinstance(key, int):
                if last_key is not None and isinstance(d[key], str):
                    # Concatenate the value to the previous key's value
                    new_dict[last_key] += '-' + d[key]
            else:
                last_key = key
                if isinstance(d[key], dict):
                    # Recursively process nested dictionaries
                    new_dict[key] = parse_lua_dict(d[key])
                else:
                    new_dict[key] = d[key]

        return new_dict
        #return [new_dict] if any(isinstance(k, int) for k in d.keys()) else new_dict


if __name__ == "__main__":
    data = {1: {'name': 'iron', 1: 'plate', 'type': 'item', 'amount': 2}}

    response = parse_lua_dict(data)

    assert response == [{'amount': 2, 'name': 'iron-plate', 'type': 'item'}]