# Version 47

mcts_type:MCTSType.PLANNING
system_prompt:
version:47
version_description:
n_parallel:8
max_steps:1000
skip_failures:False
model:ft:gpt-4o-mini-2024-07-18:paperplane-ai:mcts-pruned-masked:AYIViDdb
sampler_type:SamplerType.KLD
planning_model:claude-3-5-sonnet-20241022
executor_model:ft:gpt-4o-2024-08-06:paperplane-ai:fact-instruct-1:ATSVGf4d:ckpt-step-214
objective_model:ft:gpt-4o-2024-08-06:paperplane-ai:fact-self-gen-planning:AQzcPI91
step_executor_prompt_path:../../prompts/bottoms_up_prompts/finetuning_prompts/step_supervised
step_generator_prompt_path:../../prompts/bottoms_up_prompts/finetuning_prompts/step_generator
step_judge_prompt_path:../../prompts/bottoms_up_prompts/finetuning_prompts/step_judge
example_plan_prompt_path:../../prompts/bottoms_up_prompts/finetuning_prompts/executor_plan
max_steps_per_objective:12
number_of_steps_for_judge:3
temperature:1.0
compression_strength:None
max_conversation_length:30
adaptive_period:200
window_size:100
