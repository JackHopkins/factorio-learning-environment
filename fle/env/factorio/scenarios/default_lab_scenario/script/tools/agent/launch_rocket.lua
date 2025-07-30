-- Function to find a rocket silo at the given position
local function find_rocket_silo(surface, position)
    local silo = surface.find_entities_filtered{
        name = "rocket-silo",
        position = position,
        limit = 1,
        radius=1000
    }
    return silo[1]
end

-- Function to check if the silo has a rocket ready to launch
local function is_rocket_ready(silo)
    if not silo then return false end
    if not silo.valid then return false end

    -- Check if rocket is ready for launch
    return silo.rocket_silo_status == defines.rocket_silo_status.rocket_ready
end

-- Function to launch rocket from specified position
global.actions.launch_rocket = function(x, y)
    -- Get the current game surface
    local surface = game.surfaces[1]
    local position = {x=x, y=y}
    -- Find rocket silo at the given position
    local silo = find_rocket_silo(surface, position)

    if not silo then
        game.print("No rocket silo found at specified position")
        return false
    end

    -- Check if silo has a rocket ready
    if not is_rocket_ready(silo) then
        game.print("Rocket is not ready for launch")
        return false
    end

    -- Launch the rocket
    silo.launch_rocket()
    game.print("Rocket launched successfully!")
    return true
end