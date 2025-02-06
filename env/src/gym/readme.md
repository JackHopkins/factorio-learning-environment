This is where the old implementation of the Gym API lives.

The idea is:
- Use the 'observe_all' lua script to pull an observation tensor
- Define an action tensor based on the actions + parameterisations.
- Hook into OAI gym to train a model

This is not finished, and was somewhat superceded by the focus on LLM coding models. I'm leaving it here as an example.