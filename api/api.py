from models.response import Origin, Entity

from fastapi import FastAPI
from typing import List
import logging
import os

LOGLEVEL = os.environ.get('LOGLEVEL', default='WARNING').upper()
logging.basicConfig(level=LOGLEVEL)

app = FastAPI(
    title="XDB API",
    version="0.0.1",
    description="API for the exchange database"
)

@app.get("/", response_model=List[Origin])
def get_origin():
        return [{
            "id": 123,
            "name": "fake origin",
            "description": "origin is fake"
        }]


@app.get("/{origin}/", response_model=List[Entity])
def get_entities(origin: int):
        return [{
                "entity_id": 123,
                "entity_type": "entity type",
                "name": f"belongs to {origin}"
            }]

@app.get("/{origin}/{entity}/", response_model=Entity)
def get_entity(origin: int, entity: int):
        return {
                "entity_id": entity,
                "entity_type": "entity type",
                "name": f"belongs to origin:{origin}"
           }

