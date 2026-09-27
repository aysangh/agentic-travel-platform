from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from graph.build import build_travel_graph, llm
from app.api.routers import auth, conversations


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with build_travel_graph() as graph:
        app.state.graph = graph
        app.state.llm = llm
        yield


app = FastAPI(title="Travel Assistant API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       
    allow_credentials=False,   
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(conversations.router, prefix="/conversations", tags=["conversations"])