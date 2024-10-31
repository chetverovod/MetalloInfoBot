#from llama_cpp import Llama
import ollama

#MAIN_MODEL = 'llama3.1'
#MAIN_MODEL = 'qwen2.5:14b'
#MAIN_MODEL = 'qwen2.5:32b' # Компьютер не тянет.
MAIN_MODEL = 'phi3:14b'

class Llama_api():
    def __init__(self):    
        self.llm = self.load_llm()

    def load_llm(
        self,
        model_path: str=""
    ) -> None:
        self.llm = True

    def llm_request(self, prompt: str) -> str:
        if not hasattr(self, 'llm'):
            self.load_llm()
        # opt = {"temperature": 0, 'num_gpu': 15 }
        opt = {"temperature": 0 , "seed": 42, "num_ctx": 8000}
        answer = ollama.generate(model=MAIN_MODEL, prompt=prompt, options=opt)
        res = answer["response"]
        return res 