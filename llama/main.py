import time

from llama_cpp import Llama
llm = Llama(model_path="/Users/jackhopkins/Downloads/stable-vicuna-13B-ggml_q4_0.bin")
for i in range(5):
    start = time.time()
    output = llm("### Human: Name all of the planets in the solar system. ### Assistant: ", max_tokens=64, stop=["###"], echo=True)
    print(start-time.time(), output)