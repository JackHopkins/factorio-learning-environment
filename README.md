# Factorio Gym

### Introduction

Factorio is a sandbox game in which you build and maintain factories.

The player mines raw resources, researches technologies, builds infrastructure, automates production and fights enemies.

Automating production is the core of the game. The player builds machines that take in raw resources and output more complex and valuable resources.

Eventually, the player launches a rocket, which is the end-game goal.

The core idea of Factorio is simple, but there is scope for massive emergent complexity.

By combining automated elements into economic structures, applying management skills to keep it working and finally protecting the factories from angry neighbours, there is scope for enormous factories (or programs).

There is the opportunity for infinite emergent complexity, as Factorio is Turing-complete (i.e any calculable function can be calculated in Factorio).


# Building a Paperclip Maximiser

### Introduction

In AGI, instrumental convergence is the hypothetical tendency for sufficiently intelligent agents to pursue unbounded instrumental goals provided that their ultimate goals are themselves unlimited.

This is illustrated by the hypothetical Paperclip Maximiser (Bostrum, 2003), in which an agent given the sole and unconstrained goal of maximising the number of paperclips a factory outputs, could attempt to turn the Earth into one giant factory (and convert all humans into paperclips in the process).

The drives of such an intelligent system are likely to include goal-content integrity, self-protection, freedom from interference, self-improvement, and non-satiable acquisition of additional resources.

Interestingly, the game of Factorio implicitly or explicitly models each of the above.

### The Game

Factorio is a game in which you build and maintain factories.

The core idea of Factorio is simple, but there is scope for massive emergent complexity. 

The player mines raw resources, researches technologies, builds infrastructure, automates production and fights enemies. By combining simple elements into ingenious structures, applying management skills to keep it working and finally protecting the factories from angry neighbours, there is scope for enormous factories (or programs). There is the opportunity for infinite emergent complexity, as Factorio is Turing-complete (i.e any calculable function can be calculated in Factorio).

![Some crafting dependencies](https://community.wolfram.com//c/portal/getImageAttachment?filename=Factorio_All.png&userId=73716)

The size of factory you build is constrained by:
- Access to raw resources
- The hostility of neighbours, which increases proportionally to the size of the factory.

This second factor results in two viable long-term strategies. First, by building aggressively and investing in defenses (walls, auto-turrets etc). Second, by building slowly and investing in energy sources that don't impact the neighbours and don't incur hostility.

### An RL Sandbox

The simple rules and infinite emergent complexity of Factorio make it an ideal RL sandbox:
- The automated nature of the factory presents a dense reward function (i.e game resources update every tick).
- Extremely simple policies (i.e as few as 2 actions) can generate a some reward.
- Each of the basic drives of an intelligent system can be demonstrated and evaluated. 


**Objective**: To maximise the number of 'paperclips' (represented as copper coils in-game) existant in the game-world at any cost.

**Goal-content Integrity**: The game supports pseudo-variables in-game, which means that the objective function can be represented as a composite of these pseudo-variables (e.g maximise the incidence of whatever resource is stored in the box in tile 1:15). A sufficiently intelligent agent would be adverse to altering the contents of the box, as that would compromise goal-content integrity.

**Resource Acquisition**: The game benefits an intelligent agent directly, as specific resources acquired affects it's reward function. Indirectly, the accrual of non-rewarded resources enables a sufficiently intelligent agent to expand the size of the factory, thus increasing the rate of paperclip generation.

**Self-Protection**: The game introduces hostile countermeasures to destroy the factory. A sufficiently intelligent agent would either develop resources to fight these countermeasures, or attempt to avoid countermeasures in the first place.

**Self-Improvement**: The game offers technological progression, in which certain features are unlocked after a factory has conducted research as a sub-goal. These features offer faster resource gathering, and more efficient factory layouts to improve density.

### Architecture

The architecture of the proposed system comprises three parts, detailed below.

##### Server

Factorio can be run as a remote headless server using Docker. This server supports multiplayer games interfaced through a networked client. 

To run a headless server using Docker, you can use the following command:

```
sudo mkdir -p /opt/factorio
sudo chown 845:845 /opt/factorio
sudo docker run -d \
  -p 34197:34197/udp \
  -p 27015:27015/tcp \
  -v /opt/factorio:/factorio \
  --name factorio \
  --restart=always \
  factoriotools/factorio
```

### Running the main script
Run the main project root.
```
python -m client.main
```

The headless server will be deployed onto AWS, and will maintain game state.

##### Mod

Factorio also supports Mods, written in Lua that run remotely on the server. Mods hook into the Factorio API to change the world around the player. 

The Factorio API consists of 3 phases:
- The settings stage is used to set up mod configuration options. The mod settings are documented [here](https://wiki.factorio.com/Tutorial:Mod_settings)
- The data stage is used to set up the prototypes of everything in the game. The prototypes are documented [here](https://wiki.factorio.com/Prototype_definitions)
- The third stage is runtime scripting. The classes and events used in this phase are documented [here](https://lua-api.factorio.com/latest/)

Each mod has access to instances of all classes in the running Factorio server.

The role of the proposed custom mod is to distil all instances in-game into a much simpler representation to send back to the client, while simultaneously translating the simple actions sent by the client into updates in-game.

For example, instead of requiring the small in-game avatar to move to an ore-field to mine iron ore, a simpler action could be {MINE: {x:15, y:20}}. 

##### Client

The RL agents will be implemented as clients, that interoperate with the Factorio server through an API. 

To avoid having to interface directly with the (reasonably) complex Factorio input-space and state-space representation, all client communication is shimmed by a custom mod. 

As the custom mod abstracts the underlying game, a client would not have to built on-top of a running instance of the Factorio game, drastically improving performance and deployment flexibility.

# Links

https://github.com/m-chandler/factorio-spot-pricing

#ssh -i "factorio.pem" ec2-user@ec2-18-133-239-115.eu-west-2.compute.amazonaws.com