local player = game.players[arg1]
local surface = player.surface;

local function generate_new_world( player )

    debug_log( 'Generating new game plus...' )

    ---------------------------------------
    -- RSO INTEGRATION
    ---------------------------------------

    debug_log( 'Looking for RSO...' )

    if remote.interfaces[ 'RSO' ]
    then
        debug_log( 'Detected RSO' )

        if remote.interfaces[ 'RSO' ][ 'resetGeneration' ]
        then
            global.use_rso = true
        else
            player.print( { 'msg.new-game-plus-outdated-rso' } )

            return
        end
    else
        debug_log( 'No RSO found' )

        global.use_rso = false
    end

    ---------------------------------------
    -- MAP GEN SETTINGS
    ---------------------------------------

    debug_log( 'Making map gen settings...' )

    local map_gen_settings = make_map_gen_settings( player )

    if not map_gen_settings
    then
        debug_log( 'Aborted generating new game plus' )

        return
    end

    ---------------------------------------
    -- MAP SETTINGS
    ---------------------------------------

    debug_log( 'Changing map settings...' )

    if not change_map_settings( player )
    then
        debug_log( 'Aborted generating new game plus' )

        return
    end

    ---------------------------------------
    -- CREATE NEW SURFACE
    ---------------------------------------

    debug_log( 'Creating surface...' )

    local surface_number = util.get_valid_surface_number( global.next_nauvis_number )

    local nauvis_plus = game.create_surface( 'Nauvis plus ' .. surface_number, map_gen_settings )

    ---------------------------------------
    -- TELEPORT PLAYERS TO NEW SURFACE
    ---------------------------------------

    for _, player in pairs( game.players )
    do
        player.teleport( { 1, 1 }, nauvis_plus )

        player.force.chart( nauvis_plus, { { player.position.x - 200, player.position.y - 200 }, { player.position.x + 200, player.position.y + 200 } } )
    end

    ---------------------------------------
    -- SET SPAWN
    ---------------------------------------

    for _, force in pairs( game.forces )
    do
        force.set_spawn_position( { 1,1 }, nauvis_plus )
    end

    ---------------------------------------
    -- SET WHETHER THE TECH NEEDS TO BE RESET
    ---------------------------------------

    local frame_flow = mod_gui.get_frame_flow( player )

    if frame_flow[ 'new-game-plus-config-frame' ][ 'new-game-plus-config-option-table' ][ 'new-game-plus-reset-research-checkbox' ].state
    then
        global.tech_reset = true
    else
        global.tech_reset = false
    end

    ---------------------------------------
    -- KILL THE GUI, IT'S NOT NEEDED AND
    -- SHOULD NOT EXIST IN THE BACKGROUND
    ---------------------------------------

    debug_log( 'Destroying the gui...' )

    for _, player in pairs( game.players )
    do
        gui.kill( player )
    end

    ---------------------------------------
    -- DESTROY THE OTHER SURFACES
    ---------------------------------------

    debug_log( 'Removing surfaces...' )

    for _,surface in pairs( game.surfaces )
    do
        ---------------------------------------
        -- CAN NOT DELETE NAUVIS
        ---------------------------------------

        if surface.name == 'nauvis'
        then
            ---------------------------------------
            -- BE NICE TO OTHER MODS
            ---------------------------------------

            script.raise_event( on_pre_surface_cleared_event, { surface_index = surface.index } )

            ---------------------------------------
            -- SO I DELETE ITS CHUNKS
            ---------------------------------------

            for chunk in surface.get_chunks()
            do
                surface.delete_chunk( { chunk.x, chunk.y } )
            end

            debug_log( 'Deleted nauvis chunks.' )

        elseif not surface.name:find( 'Factory floor' ) and ( surface.name ~= 'Nauvis plus ' .. global.next_nauvis_number )
        then
            ---------------------------------------
            -- DON'T DELETE FACTORISSIMO STUFF OR
            -- THE NEW SURFACE
            ---------------------------------------

            game.delete_surface( surface )
        end
    end

    global.next_nauvis_number = global.next_nauvis_number + 1

    ---------------------------------------
    -- WE ACT LIKE NO ROCKET HAS BEEN
    -- LAUNCHED, SO THAT WE CAN DO THE
    -- WHOLE 'LAUNCH A SATELLITE AND
    -- MAKE GUI' THING AGAIN
    ---------------------------------------

    global.rocket_launched = false

    debug_log( 'New game plus has been generated' )
end

--generate_new_world(player)


player.surface.destroy_decoratives({})
player.force.clear_chart()
player.force.cancel_charting(surface);

local chunk_radius = 0;
for chunk in surface.get_chunks() do
  if (chunk.x < -chunk_radius or chunk.x > chunk_radius or chunk.y < -chunk_radius or chunk.y > chunk_radius) then
    surface.delete_chunk(chunk)
  end
end
