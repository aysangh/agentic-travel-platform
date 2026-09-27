from langchain_openai import OpenAIEmbeddings

from config import config


class EmbeddingService:

    def __init__(self):
        self.model = OpenAIEmbeddings(
            model=config.embedding_model,
            api_key=config.openai_api_key
        )

    async def embed(self, text: str) -> list[float]:
        return await self.model.aembed_query(text)