# Notes

1. Definition `id` is not the same as instance `instance_id` - Helps with duplicating prefabs in a game instance


# Me
1. Check enemy spawning or initialization in core
2. for attack and spells, cross-reference or mention to copilot about combat related types, models and json data/schemata
3. Combat attack and spells can have multiple subfunctions to help with the resolution
4. Once attack and spells are flushed out and tested, proceed with trying to merge related or very similar functions
5. Before that, simplify cleanse by removing only negative status effects like `vulnerability`, `control` (stunned, silenced, restrained, asleep), and `DoT`

checking and improving if we can status_effect in `core/`: 
Take note of the different types of status effects and control types and how they should be resolved. Make the resolutions for each status_effect type one-by-one and we will check and proceed to the next one. We'll proceed with testing once the types have been accounted for. 

1. Start with DoT (similar to attack)
2. HoT
3. Control (usually just is_stunned functions helping turn checks, but could be more if you suggest)
4. For, immunities, resistances, and vulnerabilities in a status_effects(active) of a target entity, it lives differently from the entity's immunity, resistance and vulnerability attributes. We need to consider and to check for those so we can return and eventually merge them against the damage multiplier check.