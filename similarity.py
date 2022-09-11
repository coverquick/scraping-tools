from sentence_transformers import SentenceTransformer, util
from typing import List
import torch
import json
from functools import lru_cache
# Init is ran on server startup
# Load your model to GPU as a global variable here using the variable name "model"

class Similarity:
    def __init__(self, model_path="bert-base-nli-mean-tokens"):
        self.model = SentenceTransformer(model_path)
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    def predict(self, resume:List[str], job_description:List[str], num_pairs=None, threshold=0):
        res_embeddings = self.model.encode(resume, device=self.device)
        job_embeddings = self.model.encode(job_description, device=self.device)

        cosine_scores = util.cos_sim(res_embeddings, job_embeddings)
        pairs = []
        for i, row in enumerate(cosine_scores):
            max_j = row.argmax()
            if row[max_j].item() >= threshold:
                pairs.append({"i":i, "j":max_j.item(),"score":row[max_j].item()})

		#Sort scores in decreasing order
        pairs = sorted(pairs, key=lambda x: x['score'], reverse=True)
        if num_pairs is not None:
            pairs = pairs[:num_pairs]
        return pairs
    
    def predict_all(self, embedding_dict:dict) -> dict:
        """

        :param embedding_dict: Dictionary of embeddings, where the key is the name of the embedding and the value is a list of sentences

        Args:
            embedding_dict (dict): Dictionary of sentences, where the key is an identifier for the embedding and the value is a list of sentences

        Returns:
            dict: Dictionary of pairs, where the key is an identifier for the embedding and the value is a list of pairs
        """
        embeddings = []
        for key in embedding_dict.keys():
            embeddings.extend(embedding_dict[key]['embeds_1'])
            embeddings.extend(embedding_dict[key]['embeds_2'])
        embeddings = self.model.encode(embeddings, device=self.device)
        
        # We now break our embedding array back into the dict components
        embed_start = 0 
        embed_return = {}

        for key in embedding_dict.keys():
            embed_len = len(embedding_dict[key]['embeds_1']) + len(embedding_dict[key]['embeds_2'])
            embeds_1 = embeddings[embed_start:embed_start+len(embedding_dict[key]['embeds_1'])]
            embeds_2 = embeddings[len(embedding_dict[key]['embeds_1']) + embed_start:embed_len + embed_start]
            cosine_scores = util.cos_sim(embeds_1, embeds_2)
            pairs = []
            threshold = embedding_dict[key].get('threshold', 0)
            num_pairs = embedding_dict[key].get('num_pairs', None)
            for i, row in enumerate(cosine_scores):
                max_j = row.argmax()
                if row[max_j].item() >= threshold:
                    pairs.append({"i":i, "j":max_j.item(),"score":row[max_j].item()})
            pairs = sorted(pairs, key=lambda x: x['score'], reverse=True)
            if num_pairs is not None:
                pairs = pairs[:num_pairs]
            embed_return[key] = pairs
            
            embed_start += embed_len
        
        return embed_return

@lru_cache
def get_model(model_path):
    return Similarity(model_path)

