global.actions.load_blueprint = function(player_index, bp, offset_x, offset_y)
    --- https://forums.factorio.com/viewtopic.php?t=111437
    --- by CharacterOverflow @ Wed Feb 21, 2024 2:34 pm

    local s = game.get_surface('nauvis');
    local f = global.agent_characters[player_index].force
    f.research_all_technologies();

    -- Creates a blueprint entitiy in-game - it's weird, but it works. This blueprint entity has the blueprint loaded we want to run.
    local bp_entity = s.create_entity { name = 'item-on-ground', position = { offset_x, offset_y }, stack = 'blueprint' }
    local stack_id = bp_entity.stack.import_stack(bp)

    -- Now we call build_blueprint - this does not do *anything* like what you'd expect though. The force_build options is
    -- only there simply to hold 'shift' while the blueprint is placed, meaning the blueprint itself still does not get
    -- spawned, only the ghosts do. So, we then have much more actual work to do.
    -- #TODO - Try to talk to factorio devs and have them either make an additional function (like auto_build_blueprint) or parameter. Would eliminate most of the lua code below, and likely be a speed boost
    local bp_ghost = bp_entity.stack.build_blueprint { surface = s, force = f, position = { offset_x, offset_y }, force_build = true }
    bp_entity.destroy()

    -- Go through and spawn the actual entities - except for ones that REQUIRE other entities, such as locomotives
    local afterSpawns = {}
    for _, entity in pairs(bp_ghost) do

        -- Should change this to go by ghost_type, if that's even a valid field.
        if (entity.ghost_name == 'locomotive' or entity.ghost_name == 'cargo-wagon' or entity.ghost_name == 'fluid-wagon') then
            table.insert(afterSpawns, entity)
        else
            if (entity ~= nil and entity.name == 'entity-ghost' and entity.ghost_type ~= nil and entity.item_requests ~= nil) then
                local items = util.table.deepcopy(entity.item_requests)
                -- game.print(serpent.block(entity.items))
                local p, ri = entity.revive();
                if (ri ~= nil) then
                    for k, v in pairs(items) do
                        ri.get_module_inventory().insert({ name = k, count = v })
                    end
                end
            else
                -- it's a normal thing like a belt or arm - we can just 'revive' the ghost, which will place the entity with all of the correct settings from the blueprint
                entity.revive();
            end
        end

    end

    -- This is used to place all locomotives and other train objects AFTER rails have been placed
    for _, entity in pairs(afterSpawns) do
        local r, to = entity.revive();
    end

    -- Set all trains to AUTOMATIC mode (manual = false)
    for _, locomotive in pairs(game.surfaces["nauvis"].get_trains()) do
        locomotive.manual_mode = false
    end

    -- Add logistic bots to each roboport, based on input. One of the few variables, as some designs may be self-sufficient on bots
    if (BOTS ~= nil and BOTS > 0) then
        for _, roboport in pairs(game.surfaces["nauvis"].find_entities_filtered({ type = "roboport" })) do
            roboport.insert({ name = "logistic-robot", count = BOTS })
        end
    end

    return stack_id

end
