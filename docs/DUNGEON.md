# Dungeons 
> The game environment, where players act in

- Node based where each `room` is a node
- Each `room` has `connections`, an array of connected nodes or `rooms`
- Has a `start` node and an `end` node, representing the `entrance` and `exit` of the dungeon
- Each `room` may or may not have `encounters`
- `encounters` is an array of an `encounter`
- An `encounter` is a party of `enemies`
- An `encounter` has a `difficulty` and a `clear_reward` (int)
- Each `room` may allow a `rest`
- A `rest` can either be `long`, `short`, `[long, short]` or `[]`  