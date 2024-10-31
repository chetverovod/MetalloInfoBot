from llama_cpp import Llama


class Llama_api():
    def __init__(self):    
        self.llm = self.load_llm()


    def load_llm(
        self,
        model_path: str="models/qwen2.5-14b-instruct-q3_k_m-00001-of-00002.gguf"
        #model_path="models/saiga-tlite-8b-Q8_0.gguf", #"models/saiga-tlite-8b-Q3_K_L.gguf",
    ) -> None:
        self.llm = Llama(
            model_path,
            seed=42,
            n_ctx=8000,
            n_gpu_layers=12,
            verbose=False
        )        


    def llm_request(self, prompt: str) -> str:
        if not hasattr(self, 'llm'):
            self.load_llm()
        answer = self.llm.create_chat_completion(
            messages = [{
				"role": "assistant",
				"content": prompt
		    }]
	    )
        return answer['choices'][0]['message']['content']